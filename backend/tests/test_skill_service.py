from pathlib import Path

from src.services.skill_service import Skill, SkillService


def write_skill(root: Path, folder: str, text: str) -> None:
    skill_path = root / folder / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(text, encoding="utf-8")


def test_skill_service_loads_and_matches_front_matter(tmp_path):
    write_skill(
        tmp_path,
        "labor",
        """---
name: labor-dispute
description: 劳动争议处理
version: 1.2.3
triggers:
  - 辞退
  - 劳动仲裁
---
# 劳动争议

处理劳动争议的步骤。
""",
    )

    service = SkillService(skill_root_dir=str(tmp_path))

    skill = service.get_skill_by_name("labor-dispute")
    matched = service.match_skills("员工被辞退后准备劳动仲裁")

    assert skill is not None
    assert skill.version == "1.2.3"
    assert skill.content.startswith("# 劳动争议")
    assert [item.name for item in matched] == ["labor-dispute"]


def test_skill_normalizes_non_list_triggers():
    skill = Skill(
        "/tmp/SKILL.md",
        {
            "name": "contract",
            "description": "合同审查",
            "triggers": "合同",
        },
        "content",
    )

    assert skill.triggers == []
    assert skill.to_dict()["name"] == "contract"
