from app.pipeline import llm
from app.pipeline.agents import RequirementList


def test_fit_budget_caps_output_only_when_a_limit_is_set(monkeypatch):
    monkeypatch.setattr(llm.settings, "specwright_request_token_limit", 0)
    assert llm.fit_budget(12000, "x" * 9000) == 12000
    monkeypatch.setattr(llm.settings, "specwright_request_token_limit", 8000)
    assert llm.fit_budget(12000, "x" * 9000) == 5000  # 8000 - 9000 // 3


def test_cut_off_output_is_retried(monkeypatch):
    calls = []

    def fake(model, system, prompt, *args):
        calls.append(prompt)
        if len(calls) == 1:
            raise llm.InvalidOutput("output was cut off at max_tokens=100")
        return {"requirements": []}

    monkeypatch.setattr(llm.settings, "llm_provider", "groq")
    monkeypatch.setattr(llm, "_call_openai_compatible", fake)
    result = llm.structured_call(model="m", system="s", spec_text="spec", instruction="go",
                                 output=RequirementList)
    assert result.requirements == []
    assert "cut off" in calls[1]
