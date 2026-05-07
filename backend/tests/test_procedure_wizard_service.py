from src.services.procedure_wizard_service import ProcedureWizardService


def test_procedure_wizard_starts_and_advances_to_completion():
    service = ProcedureWizardService()

    instance = service.start_wizard("employee_termination")

    assert instance.current_step == 1
    assert instance.steps[0].status == "current"
    assert "辞退" in instance.title

    for _ in range(instance.total_steps):
        instance = service.advance_step(instance.wizard_id)

    assert instance.status == "completed"
    assert instance.progress == 1
    assert "所有步骤已完成" in service.get_current_step_guide(instance.wizard_id)


def test_procedure_wizard_lists_and_renders_overview():
    service = ProcedureWizardService()

    available = service.get_available_wizards()
    overview = service.get_wizard_overview_markdown("contract_breach")

    assert any(item["type"] == "contract_breach" for item in available)
    assert "流程概览" in overview
    assert "合同违约处理流程向导" in overview
