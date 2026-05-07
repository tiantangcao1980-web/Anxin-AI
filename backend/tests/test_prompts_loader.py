from pathlib import Path

from src import prompts


def test_load_prompt_reads_formats_and_invalidates_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(prompts, "_PROMPTS_DIR", tmp_path)
    prompts.invalidate_cache()
    prompt_file = tmp_path / "agents" / "demo.txt"
    prompt_file.parent.mkdir()
    prompt_file.write_text("你好 {name}", encoding="utf-8")

    assert prompts.load_prompt("agents/demo.txt", name="安心") == "你好 安心"
    prompt_file.write_text("更新 {name}", encoding="utf-8")
    prompts.invalidate_cache("agents/demo.txt")

    assert prompts.load_prompt("agents/demo.txt", name="法务") == "更新 法务"


def test_load_prompt_returns_fallback_for_missing_file(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(prompts, "_PROMPTS_DIR", tmp_path)
    prompts.invalidate_cache()

    assert prompts.load_prompt("missing.txt", fallback="fallback {value}", value="ok") == "fallback ok"
    assert prompts.load_prompt("missing.txt") == ""
