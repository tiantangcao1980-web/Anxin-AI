"""
skills 路由 —— P5-A 技能注册表 + 执行器对外 API

挂载点（在 ``api/routes/__init__.py`` 用 ``prefix="/skills"`` 注册）::

    GET    /api/v1/skills                          列出所有 skill (query: category, persona, enabled)
    GET    /api/v1/skills/triggers/match?q=...     按文本匹配 trigger
    GET    /api/v1/skills/{name}                   详情
    POST   /api/v1/skills/upload                   上传 .md 文件 → 解析 + 注册
    PUT    /api/v1/skills/{name}/toggle            启用/禁用
    POST   /api/v1/skills/{name}/execute           试运行

权限：所有路由都需要登录用户；upload / toggle / execute 写操作未来可加
``role`` 限制（当前先放给所有登录用户，方便管理后台开发）。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from src.api.routes.schemas.skill import (
    ExecuteSkillBody,
    ExecuteSkillOut,
    SkillDetailOut,
    SkillListOut,
    SkillSummaryOut,
    ToggleSkillBody,
    TriggerMatchOut,
    UploadSkillOut,
)
from src.core.deps import get_current_user_required
from src.models.user import User
from src.services.skill_executor import (
    ExecutionContext,
    SkillExecutor,
)
from src.services.skill_registry import (
    Skill,
    SkillLoader,
    SkillParseError,
    SkillRegistry,
    validate_skill,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# 序列化辅助
# ---------------------------------------------------------------------------


def _to_summary(skill: Skill) -> SkillSummaryOut:
    return SkillSummaryOut(
        name=skill.name,
        description=skill.description,
        version=skill.version,
        category=skill.category,
        type=skill.type,
        triggers=list(skill.triggers),
        personas=list(skill.personas),
        requires_apps=list(skill.requires_apps),
        dependencies=list(skill.dependencies),
        enabled=skill.enabled,
        author=skill.author,
        file_path=str(skill.file_path) if skill.file_path else None,
    )


def _to_detail(skill: Skill, excerpt_chars: int = 800) -> SkillDetailOut:
    summary = _to_summary(skill).model_dump()
    body = skill.body or ""
    return SkillDetailOut(
        **summary,
        body_excerpt=body[:excerpt_chars],
        body_length=len(body),
    )


def _registry() -> SkillRegistry:
    return SkillRegistry.instance()


# ---------------------------------------------------------------------------
# GET /skills
# ---------------------------------------------------------------------------


@router.get("", response_model=SkillListOut)
async def list_skills(
    category: str | None = Query(default=None, description="按 category 过滤"),
    persona: str | None = Query(default=None, description="按 persona 过滤"),
    enabled: bool | None = Query(default=None, description="是否仅返回 enabled"),
    _user: User = Depends(get_current_user_required),
) -> SkillListOut:
    """列出所有 skill，支持 ``category`` / ``persona`` / ``enabled`` 过滤。"""
    items = _registry().all()
    if category:
        items = [s for s in items if s.category == category or s.type == category]
    if persona:
        items = [s for s in items if s.supports_persona(persona)]
    if enabled is not None:
        items = [s for s in items if s.enabled == enabled]
    return SkillListOut(
        items=[_to_summary(s) for s in items],
        total=len(items),
    )


# ---------------------------------------------------------------------------
# GET /skills/triggers/match
# ---------------------------------------------------------------------------


@router.get("/triggers/match", response_model=TriggerMatchOut)
async def match_triggers(
    q: str = Query(..., min_length=1, description="待匹配文本"),
    top_k: int = Query(default=5, ge=1, le=50),
    _user: User = Depends(get_current_user_required),
) -> TriggerMatchOut:
    """按 trigger 召回候选 skill。"""
    results = _registry().find_by_trigger(q, top_k=top_k)
    return TriggerMatchOut(
        items=[_to_summary(s) for s in results],
        total=len(results),
    )


# ---------------------------------------------------------------------------
# GET /skills/{name}
# ---------------------------------------------------------------------------


@router.get("/{name}", response_model=SkillDetailOut)
async def get_skill_detail(
    name: str,
    _user: User = Depends(get_current_user_required),
) -> SkillDetailOut:
    skill = _registry().get(name)
    if skill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"skill 不存在: {name}")
    return _to_detail(skill)


# ---------------------------------------------------------------------------
# POST /skills/upload
# ---------------------------------------------------------------------------


@router.post("/preview")
async def preview_skill(
    file: UploadFile = File(..., description="SKILL.md 文件"),
    _user: User = Depends(get_current_user_required),
) -> dict:
    """**预览**上传的 SKILL.md（不注册到 registry）。

    用于安装授权弹窗：用户先看完 manifest 的资源 / 网络 / 文件系统 / 权限
    再决定要不要点 ``/upload``。返回前端 SkillInstallSummary 形状。

    与 ``/upload`` 的区别：
        - 不调 ``registry.register``，不把临时文件保留为已安装 skill
        - 加上 ``SandboxManifest.from_frontmatter`` 解析结果（fingerprint / tier）
    """
    if not file.filename or not file.filename.lower().endswith(".md"):
        raise HTTPException(status_code=400, detail="只接受 .md 文件")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"必须是 UTF-8 编码: {exc}") from exc

    tmp_dir = Path(tempfile.mkdtemp(prefix="skill_preview_"))
    saved = tmp_dir / "SKILL.md"
    saved.write_text(text, encoding="utf-8")
    loader = SkillLoader()
    try:
        skill = loader.load_from_file(saved)
    except SkillParseError as exc:
        raise HTTPException(status_code=400, detail=f"SKILL.md 解析失败: {exc}") from exc
    errors = validate_skill(skill)
    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})

    # manifest 解析（缺省 = T0 prompt-only）
    from src.services.skill_sandbox import (
        ManifestValidationError,
        SandboxManifest,
    )
    try:
        manifest = SandboxManifest.from_frontmatter(
            {"sandbox": skill.sandbox_raw} if skill.sandbox_raw else None
        )
    except ManifestValidationError as exc:
        raise HTTPException(
            status_code=400, detail=f"sandbox manifest 非法: {exc}"
        ) from exc

    manifest_payload = manifest.model_dump(mode="json")
    manifest_payload["fingerprint"] = manifest.fingerprint()

    return {
        "name": skill.name,
        "description": skill.description,
        "version": skill.version,
        "author": skill.author,
        "manifest": manifest_payload,
    }


@router.post("/upload", response_model=UploadSkillOut, status_code=status.HTTP_201_CREATED)
async def upload_skill(
    file: UploadFile = File(..., description="SKILL.md 文件"),
    _user: User = Depends(get_current_user_required),
) -> UploadSkillOut:
    """上传 SKILL.md，解析后注册到 registry。

    实现说明：把上传内容落到 OS 临时目录，loader 直接 ``load_from_file``。
    生产环境可改为持久化目录（例如 ``settings.SKILLS_USER_DIR``）。
    """
    if not file.filename or not file.filename.lower().endswith(".md"):
        raise HTTPException(status_code=400, detail="只接受 .md 文件")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"必须是 UTF-8 编码: {exc}") from exc

    tmp_dir = Path(tempfile.mkdtemp(prefix="skill_upload_"))
    saved = tmp_dir / "SKILL.md"
    saved.write_text(text, encoding="utf-8")

    loader = SkillLoader()
    try:
        skill = loader.load_from_file(saved)
    except SkillParseError as exc:
        raise HTTPException(status_code=400, detail=f"SKILL.md 解析失败: {exc}") from exc

    errors = validate_skill(skill)
    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})

    _registry().register(skill)
    return UploadSkillOut(
        name=skill.name,
        saved_path=str(saved),
        errors=errors,
        skill=_to_summary(skill),
    )


# ---------------------------------------------------------------------------
# PUT /skills/{name}/toggle
# ---------------------------------------------------------------------------


@router.put("/{name}/toggle", response_model=SkillSummaryOut)
async def toggle_skill(
    name: str,
    body: ToggleSkillBody,
    _user: User = Depends(get_current_user_required),
) -> SkillSummaryOut:
    skill = _registry().toggle(name, body.enabled)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"skill 不存在: {name}")
    return _to_summary(skill)


# ---------------------------------------------------------------------------
# POST /skills/{name}/execute
# ---------------------------------------------------------------------------


@router.post("/{name}/execute", response_model=ExecuteSkillOut)
async def execute_skill(
    name: str,
    body: ExecuteSkillBody,
    user: User = Depends(get_current_user_required),
) -> ExecuteSkillOut:
    """试运行某 skill。

    使用 ``SkillExecutor``，默认 LLM callable 走 ``rag_service`` 客户端，
    无 LLM 配置时返回 stub，便于联调。
    """
    if _registry().get(name) is None:
        raise HTTPException(status_code=404, detail=f"skill 不存在: {name}")

    persona = body.persona or "default"
    ctx = ExecutionContext(
        user_id=str(user.id),
        persona=persona,
        app_authorizations=list(body.app_authorizations),
        org_id=str(getattr(user, "org_id", "") or "") or None,
        extra=dict(body.extra),
    )
    executor = SkillExecutor(registry=_registry())
    result = await executor.execute(name, body.payload, ctx)
    return ExecuteSkillOut(
        skill_name=result.skill_name,
        status=result.status.value,
        output=result.output,
        error=result.error,
        duration_ms=result.duration_ms,
        metadata=dict(result.metadata),
    )


# ---------------------------------------------------------------------------
# POST /skills/{name}/sandbox-execute —— Skills 沙箱执行（设计见 docs/v3/skills-sandbox-design.md）
# ---------------------------------------------------------------------------


@router.post("/{name}/sandbox-execute", response_model=ExecuteSkillOut)
async def sandbox_execute_skill(
    name: str,
    body: ExecuteSkillBody,
    user: User = Depends(get_current_user_required),
) -> ExecuteSkillOut:
    """通过 ``SkillSandboxRunner`` 执行 skill。

    路由策略：
        - manifest.tier == T0  → 回退到 SkillExecutor（prompt-only）
        - manifest.tier >= T1 → 走沙箱路径

    所有 tier 都会经过权限闸门（policy_gate）。
    """
    from src.services.skill_sandbox import (
        ManifestValidationError,
        SandboxManifest,
        SkillSandboxRunner,
    )

    skill = _registry().get(name)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"skill 不存在: {name}")

    try:
        manifest = SandboxManifest.from_frontmatter(
            {"sandbox": skill.sandbox_raw} if skill.sandbox_raw else None
        )
    except ManifestValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"skill sandbox manifest 非法: {exc}",
        ) from exc

    runner = SkillSandboxRunner()
    sb_result = await runner.execute(
        skill=skill,
        manifest=manifest,
        payload=body.payload,
        user_id=str(user.id),
        user_role=user.role,
        tenant_id=str(getattr(user, "org_id", "") or "") or None,
    )

    # T0：runner 不接管 —— 回退到 prompt 路径
    if not sb_result.handled:
        persona = body.persona or "default"
        ctx = ExecutionContext(
            user_id=str(user.id),
            persona=persona,
            app_authorizations=list(body.app_authorizations),
            org_id=str(getattr(user, "org_id", "") or "") or None,
            extra=dict(body.extra),
        )
        executor = SkillExecutor(registry=_registry())
        prompt_result = await executor.execute(name, body.payload, ctx)
        return ExecuteSkillOut(
            skill_name=prompt_result.skill_name,
            status=prompt_result.status.value,
            output=prompt_result.output,
            error=prompt_result.error,
            duration_ms=prompt_result.duration_ms,
            metadata={
                **dict(prompt_result.metadata),
                "tier": manifest.tier.value,
                "sandbox_fallback": "prompt-only",
            },
        )

    return ExecuteSkillOut(
        skill_name=sb_result.skill_name,
        status=sb_result.status.value,
        output=sb_result.output,
        error=sb_result.error,
        duration_ms=sb_result.duration_ms,
        metadata={
            **dict(sb_result.metadata),
            "tier": sb_result.tier.value,
            "manifest_fingerprint": sb_result.manifest_fingerprint,
        },
    )
