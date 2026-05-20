#!/usr/bin/env python3
"""
AI Review Gate 入口脚本

用法：
    python review.py <role> <diff_path>

role: code | security | dependency | regression
diff_path: PR diff 文本路径

环境变量：
    ANTHROPIC_API_KEY  必填
    PR_NUMBER          必填
    REPO               必填，owner/name
    GH_TOKEN           必填，用于 gh CLI 评论

输出：
    退出码 0  = pass / warn（不阻塞 merge）
    退出码 1  = block（阻塞 merge）
    退出码 2  = 内部错误（视为 block，安全默认）
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# 模型版本写死，不读环境变量（防上游漂移）
MODEL_BY_ROLE = {
    "code": "claude-sonnet-4-6",
    "security": "claude-sonnet-4-6",
    "dependency": "claude-haiku-4-5-20251001",
    "regression": "claude-sonnet-4-6",
}

ROLE_DISPLAY = {
    "code": "🧑‍💻 Code Reviewer",
    "security": "🔐 Security Reviewer",
    "dependency": "📦 Dependency Reviewer",
    "regression": "🧪 Regression Reviewer",
}

# diff 上限：超过自动降级 warn
MAX_DIFF_TOKENS = 10_000


def sanitize_diff(text: str) -> str:
    """防 prompt 注入：转义 code fence + 截断超长行"""
    text = text.replace("```", "ʼ ʼ ʼ")
    return "\n".join(line[:2000] for line in text.splitlines())


def load_role_prompt(role: str) -> str:
    path = Path(__file__).parent / "reviewers" / f"{role}_reviewer.md"
    if not path.exists():
        raise FileNotFoundError(f"角色 prompt 缺失: {path}")
    return path.read_text(encoding="utf-8")


def load_common() -> str:
    path = Path(__file__).parent / "prompts" / "common.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def call_anthropic(model: str, system: str, diff: str) -> dict:
    """调用 Claude API；强制 JSON 输出。失败返回 block。"""
    try:
        from anthropic import Anthropic
    except ImportError:
        return {"verdict": "block", "issues": ["anthropic SDK 未安装"], "reasoning": ""}

    client = Anthropic()  # 自动读 ANTHROPIC_API_KEY
    user_msg = (
        f"以下是 PR 的完整 diff（已 sanitize），请按你的角色 review。\n\n"
        f"必须输出严格 JSON，格式：\n"
        f'{{"verdict": "pass|warn|block", "issues": [{{"file": "...", "line": int, "severity": "low|medium|high|critical", "message": "..."}}], "reasoning": "一段话"}}\n\n'
        f"DIFF 开始:\n{diff}\nDIFF 结束。"
    )

    try:
        resp = client.messages.create(
            model=model,
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        text = "".join(b.text for b in resp.content if hasattr(b, "text"))
        # 抓第一个 JSON 块
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return {"verdict": "block", "issues": [], "reasoning": "模型未返回 JSON"}
        return json.loads(match.group(0))
    except Exception as e:  # noqa: BLE001
        return {"verdict": "block", "issues": [], "reasoning": f"调用异常: {e}"}


def post_comment(role: str, result: dict) -> None:
    pr = os.environ.get("PR_NUMBER")
    repo = os.environ.get("REPO")
    if not pr or not repo:
        return
    verdict = result.get("verdict", "block").upper()
    issues = result.get("issues") or []
    reasoning = result.get("reasoning", "")

    icon = {"PASS": "✅", "WARN": "⚠️", "BLOCK": "🚫"}.get(verdict, "❓")
    title = f"### {ROLE_DISPLAY.get(role, role)}: {icon} {verdict}"
    issue_lines = []
    for i in issues[:20]:
        sev = i.get("severity", "?")
        f = i.get("file", "")
        ln = i.get("line", "")
        msg = i.get("message", "")
        issue_lines.append(f"- **{sev}** `{f}:{ln}` — {msg}")
    issues_md = "\n".join(issue_lines) if issue_lines else "_无具体问题_"
    body = f"{title}\n\n{issues_md}\n\n<details><summary>Reviewer reasoning</summary>\n\n{reasoning}\n\n</details>"

    subprocess.run(
        ["gh", "pr", "comment", pr, "--repo", repo, "--body", body],
        check=False,
    )


def main():
    if len(sys.argv) < 3:
        print("usage: review.py <role> <diff_path>")
        sys.exit(2)
    role = sys.argv[1]
    diff_path = Path(sys.argv[2])

    if role not in MODEL_BY_ROLE:
        print(f"unknown role: {role}")
        sys.exit(2)

    diff = sanitize_diff(diff_path.read_text(encoding="utf-8"))
    # 粗略 token 估算
    if len(diff) // 4 > MAX_DIFF_TOKENS:
        print(f"diff too large ({len(diff)} chars), demoting to warn")
        post_comment(role, {
            "verdict": "warn",
            "issues": [],
            "reasoning": f"Diff 超过 {MAX_DIFF_TOKENS} token 上限，仅人工 review。",
        })
        sys.exit(0)

    system = load_common() + "\n\n" + load_role_prompt(role)
    result = call_anthropic(MODEL_BY_ROLE[role], system, diff)

    post_comment(role, result)

    verdict = (result.get("verdict") or "block").lower()
    if verdict == "block":
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
