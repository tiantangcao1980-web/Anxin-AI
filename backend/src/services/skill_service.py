"""
技能管理服务 (Skill Service)
负责加载、解析和管理本地技能库
"""

import glob
import os
from typing import Any

import yaml  # type: ignore[import-untyped,unused-ignore]
from loguru import logger

from src.services.skill_evolution_service import SkillEvolutionService


class Skill:
    def __init__(self, path: str, metadata: dict[str, Any], content: str) -> None:
        self.path = path
        self.name = str(metadata.get("name", "unknown"))
        self.description = str(metadata.get("description", ""))
        self.version = str(metadata.get("version", "1.0.0"))
        raw_triggers = metadata.get("triggers", [])
        self.triggers = [str(trigger) for trigger in raw_triggers] if isinstance(raw_triggers, list) else []
        self.content = content

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "triggers": self.triggers,
            "content": self.content[:500] + "..." # 摘要
        }

class SkillService:
    def __init__(
        self,
        skill_root_dir: str = "skills",
        *,
        evolution_service: SkillEvolutionService | None = None,
        only_enabled_skills: bool = False,
    ) -> None:
        # 向上寻找 skills 目录
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.skill_dir = os.path.join(base_path, skill_root_dir)
        self.evolution_service = evolution_service
        self.only_enabled_skills = only_enabled_skills
        self.skills: list[Skill] = []
        self._loaded = False

    def load_skills(self) -> None:
        """加载所有技能"""
        if self._loaded:
            return

        logger.info(f"正在从 {self.skill_dir} 加载技能...")
        self.skills = []

        # 递归查找所有 SKILL.md
        pattern = os.path.join(self.skill_dir, "**", "SKILL.md")
        skill_files = glob.glob(pattern, recursive=True)

        for file_path in skill_files:
            try:
                self._parse_skill_file(file_path)
            except Exception as e:
                logger.error(f"解析技能文件失败 {file_path}: {e}")

        self._loaded = True
        logger.info(f"成功加载 {len(self.skills)} 个技能")

    def _parse_skill_file(self, file_path: str) -> None:
        """解析单个技能文件 (YAML Front Matter + Markdown)"""
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        # 分割 Front Matter
        if content.startswith("---"):
            try:
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    yaml_content = parts[1]
                    markdown_content = parts[2]

                    metadata = yaml.safe_load(yaml_content)
                    if isinstance(metadata, dict):
                        skill = Skill(file_path, metadata, markdown_content.strip())
                        self.skills.append(skill)
                        logger.debug(f"已加载技能: {skill.name}")
            except Exception as e:
                logger.warning(f"技能文件格式错误 {file_path}: {e}")

    def get_skill_by_name(self, name: str, version: str | None = None) -> Skill | None:
        """根据名称获取技能"""
        self.load_skills()
        for skill in self.skills:
            version_matches = version is None or skill.version == version
            if skill.name == name and version_matches and self._skill_can_execute(skill):
                return skill
        return None

    def match_skills(self, query: str) -> list[Skill]:
        """根据查询匹配相关技能"""
        self.load_skills()
        query = query.lower()
        matched: list[Skill] = []

        for skill in self.skills:
            if not self._skill_can_execute(skill):
                continue
            # 1. 检查 triggers
            for trigger in skill.triggers:
                if trigger.lower() in query:
                    matched.append(skill)
                    break
            else:
                # 2. 检查 name 和 description
                if skill.name.lower() in query or skill.description.lower() in query:
                    matched.append(skill)

        return matched

    def get_all_skills_info(self) -> list[dict[str, Any]]:
        """获取所有技能的摘要信息"""
        self.load_skills()
        return [s.to_dict() for s in self.skills if self._skill_can_execute(s)]

    def _skill_can_execute(self, skill: Skill) -> bool:
        if not self.only_enabled_skills:
            return True
        if self.evolution_service is None:
            return False
        return self.evolution_service.is_skill_enabled(skill.name, skill.version)

# 全局实例
skill_service = SkillService()
