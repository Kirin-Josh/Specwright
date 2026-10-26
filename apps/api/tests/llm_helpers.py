from app.pipeline.llm import extract_json, inline_refs
from app.schemas import Plan


def test_inline_refs_removes_all_refs():
    schema = inline_refs(Plan.model_json_schema())
    assert "$defs" not in schema and "$ref" not in str(schema)
    assert "milestones" in schema["properties"]


def test_extract_json_from_fenced_reply():
    text = 'Sure! Here it is:\n```json\n{"requirements": []}\n```'
    assert extract_json(text) == {"requirements": []}


def test_extract_json_from_bare_reply():
    assert extract_json('Result: {"a": 1} done') == {"a": 1}


def test_retries_once_with_validation_error(monkeypatch):
    from app.pipeline import llm
    from app.pipeline.agents import RequirementList

    replies = iter([
        {"requirements": [{"req_id": "EF-01"}]},  # missing fields -> invalid
        {"requirements": [{"req_id": "EF-01", "text": "Login", "type": "functional",
                           "section": "Auth"}]},
    ])
    prompts = []

    def fake(model, system, prompt, *args):
        prompts.append(prompt)
        return next(replies)

    monkeypatch.setattr(llm.settings, "llm_provider", "groq")
    monkeypatch.setattr(llm, "_call_openai_compatible", fake)
    result = llm.structured_call(model="m", system="s", spec_text="spec", instruction="go",
                                 output=RequirementList)
    assert result.requirements[0].req_id == "EF-01"
    assert "failed validation" in prompts[1]