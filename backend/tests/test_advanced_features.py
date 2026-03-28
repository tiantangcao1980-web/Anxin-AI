import pytest
from src.services.multimodal_service import multimodal_service, FileType
from src.services.preference_service import preference_service

@pytest.mark.asyncio
async def test_file_type_detection():
    assert multimodal_service.detect_file_type("contract.pdf") == FileType.PDF
    assert multimodal_service.detect_file_type("meeting.mp3") == FileType.AUDIO
    assert multimodal_service.detect_file_type("evidence.png") == FileType.IMAGE

@pytest.mark.asyncio
async def test_multimodal_processing_mock():
    # 测试模拟的 OCR/ASR
    res_img = await multimodal_service.process_file("dummy.png", "dummy.png", FileType.IMAGE)
    assert "OCR识别结果" in res_img["raw_text"]
    
    res_audio = await multimodal_service.process_file("dummy.mp3", "dummy.mp3", FileType.AUDIO)
    assert "ASR转录结果" in res_audio["raw_text"]

@pytest.mark.asyncio
async def test_preference_service():
    user_id = "test_user_001"
    # 更新偏好
    await preference_service.update_preference(user_id, "communication_style", "casual")
    
    # 获取后缀
    suffix = await preference_service.get_agent_system_prompt_suffix(user_id)
    assert "通俗易懂" in suffix
    
    # 验证默认值
    prefs = await preference_service.get_user_preferences("new_user")
    assert prefs["risk_tolerance"] == "conservative"
