from pathlib import Path

from src.services.skill_evolution_service import REQUIRED_SKILL_EVAL_CHECKS, SkillEvolutionService
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


def test_skill_service_can_filter_to_governed_enabled_version(tmp_path):
    write_skill(
        tmp_path,
        "contract-v1",
        """---
name: contract
description: 合同审查
version: 1.0.0
triggers:
  - 合同
---
# v1
""",
    )
    write_skill(
        tmp_path,
        "contract-v2",
        """---
name: contract
description: 合同审查
version: 1.1.0
triggers:
  - 合同
---
# v2
""",
    )
    evolution = SkillEvolutionService()
    service = SkillService(
        skill_root_dir=str(tmp_path),
        evolution_service=evolution,
        only_enabled_skills=True,
    )

    proposal = evolution.create_proposal(
        skill_name="contract",
        current_version="1.0.0",
        proposed_version="1.1.0",
        source="eval:nightly-44",
        created_by="agent-7",
        created_by_role="agent",
    )

    assert service.get_skill_by_name("contract").version == "1.0.0"
    assert [skill.version for skill in service.match_skills("合同审查")] == ["1.0.0"]

    evolution.record_eval(
        proposal.proposal_id,
        dict.fromkeys(REQUIRED_SKILL_EVAL_CHECKS, True),
        actor="eval-harness",
    )
    evolution.approve(
        proposal.proposal_id,
        approver="owner-1",
        approver_role="owner",
    )
    evolution.gray_release(
        proposal.proposal_id,
        percentage=100,
        actor="release-manager",
    )

    assert service.get_skill_by_name("contract").version == "1.1.0"
    assert [skill.version for skill in service.match_skills("合同审查")] == ["1.1.0"]

    evolution.rollback(
        proposal.proposal_id,
        reason="privacy regression",
        actor="owner-1",
    )

    assert service.get_skill_by_name("contract").version == "1.0.0"
