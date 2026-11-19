import json
from urllib.error import HTTPError

import pytest
from fastapi.testclient import TestClient

import analyzer_engine as engine
from main import app

client = TestClient(app)
REFERENCE = {"name": "Eczema", "description": "Eczema can cause dry, itchy skin. Treatments include corticosteroids for skin inflammation.",
             "url": "https://medlineplus.gov/eczema.html"}


def plan(queries=None, level="not_assessed", message=""):
    return engine.SearchPlan(queries=["eczema"] if queries is None else queries,
                             warning_level=level, warning_message=message)


def answer(source_ids=None):
    ids = source_ids or ["S1"]
    return {"sections": [{"explanation": "Several conditions can overlap.", "source_ids": ids}],
            "possibilities": [{"name": "Eczema", "why_it_might_fit": "Dry, itchy skin can fit.",
                "what_else_to_check": "Ask about location and exposures.", "source_ids": ids,
                "evidence_quote": "Eczema can cause dry, itchy skin."}],
            "medication_options": [{"name": "corticosteroids", "used_for": "Some diagnosed skin inflammation.",
                "cautions": "Discuss with a clinician; suitability and interactions have not been checked.",
                "source_ids": ids, "evidence_quote": "Treatments include corticosteroids for skin inflammation."}],
            "follow_up_questions": ["When did the symptoms start?"]}


@pytest.fixture(autouse=True)
def isolate_services(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(engine, "cached_medline", lambda *_: [REFERENCE])
    monkeypatch.setattr(engine, "plan_research", lambda _: plan())


def test_reference_mode_does_not_call_ai(monkeypatch):
    def unexpected(*_):
        pytest.fail("AI requires opt-in")
    monkeypatch.setattr(engine, "plan_research", unexpected)
    monkeypatch.setattr(engine, "synthesize", unexpected)
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret")
    data = client.post("/ai-analyzer", json={"prompt": "Explain eczema"}).json()
    assert data["mode"] == "reference_only"
    assert len(data["sources"]) == 1
    assert data["sections"] == [] and data["medication_options"] == []
    assert data["searched_terms"] == ["Explain eczema"]


def test_ai_uses_full_description_and_plan_queries(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "private-test-token")
    description = "My fingers tingle at night but I have no rash. It started after repetitive wrist work."
    def planner(prompt):
        assert prompt == description
        return plan(["carpal tunnel syndrome", "peripheral neuropathy"])
    queries = []
    monkeypatch.setattr(engine, "plan_research", planner)
    monkeypatch.setattr(engine, "cached_medline", lambda term, _: queries.append(term) or [REFERENCE])
    monkeypatch.setattr(engine, "synthesize", lambda *_: answer())
    data = client.post("/ai-analyzer", json={"prompt": description, "use_ai": True}).json()
    assert data["mode"] == "ai_assisted"
    assert set(queries) == {"carpal tunnel syndrome", "peripheral neuropathy"}
    assert len(data["sources"]) == 1
    assert data["possibilities"] and data["medication_options"]


@pytest.mark.parametrize("query", ["jane@example.com", "https://evil.test", "5551234567", "x" * 100])
def test_plan_rejects_contact_details_urls_and_oversized_queries(query):
    with pytest.raises(ValueError):
        plan([query])


@pytest.mark.parametrize("prompt", ["     ", "hi", "x" * 2001])
def test_invalid_input(prompt):
    assert client.post("/ai-analyzer", json={"prompt": prompt}).status_code == 422


def test_vague_description_does_not_invent_diseases(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "private-test-token")
    monkeypatch.setattr(engine, "plan_research", lambda _: plan([]))
    data = client.post("/ai-analyzer", json={"prompt": "I feel unwell", "use_ai": True}).json()
    assert not data["sources"] and not data["possibilities"] and not data["medication_options"]
    assert "timing and severity" in data["warnings"][0]


def test_emergency_notice_skips_differential_and_medicines(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "private-test-token")
    monkeypatch.setattr(engine, "plan_research", lambda _: plan([], "emergency", "Seek emergency help now."))
    def unexpected(*_):
        pytest.fail("Do not delay an emergency notice for retrieval or synthesis")
    monkeypatch.setattr(engine, "cached_medline", unexpected)
    monkeypatch.setattr(engine, "synthesize", unexpected)
    data = client.post("/ai-analyzer", json={"prompt": "Severe chest pain and cannot breathe", "use_ai": True}).json()
    assert data["mode"] == "safety_notice"
    assert data["safety"]["message"]
    assert not data["possibilities"] and not data["medication_options"]


def test_reference_outage(monkeypatch):
    def unavailable(*_):
        raise OSError("internal service details")
    monkeypatch.setattr(engine, "cached_medline", unavailable)
    response = client.post("/ai-analyzer", json={"prompt": "Explain eczema", "use_ai": True})
    assert response.status_code == 200
    assert not response.json()["sources"]
    assert "internal service details" not in response.text


@pytest.mark.parametrize("url", ["javascript:alert(1)", "https://medlineplus.gov.evil.test/x", "https://evil.test/x"])
def test_untrusted_reference_links_removed(monkeypatch, url):
    monkeypatch.setattr(engine, "cached_medline", lambda *_: [{**REFERENCE, "url": url}])
    assert not client.post("/ai-analyzer", json={"prompt": "Explain eczema"}).json()["sources"]


def test_ai_not_configured_falls_back():
    data = client.post("/ai-analyzer", json={"prompt": "Explain eczema", "use_ai": True}).json()
    assert data["mode"] == "reference_only" and data["sources"]
    assert any("not configured" in warning for warning in data["warnings"])


def test_empty_retrieval_never_calls_ai_synthesis(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "private-test-token")
    monkeypatch.setattr(engine, "cached_medline", lambda *_: [])
    def unexpected(*_):
        pytest.fail("AI must not generate an assessment without evidence")
    monkeypatch.setattr(engine, "synthesize", unexpected)
    data = client.post("/ai-analyzer", json={"prompt": "Explain eczema", "use_ai": True}).json()
    assert not data["sources"] and not data["sections"]


@pytest.mark.parametrize("stage", ["plan_research", "synthesize"])
@pytest.mark.parametrize("status", [400, 401, 403, 404, 429, 500])
def test_provider_failures_never_expose_credentials(monkeypatch, stage, status):
    monkeypatch.setenv("OPENAI_API_KEY", "private-test-token")
    def failure(*_):
        raise HTTPError("https://api.openai.com/", status, "private-test-token", {}, None)
    monkeypatch.setattr(engine, stage, failure)
    response = client.post("/ai-analyzer", json={"prompt": "Explain eczema", "use_ai": True})
    assert response.status_code == 200
    assert "private-test-token" not in response.text
    assert response.json()["mode"] == "reference_only"
    assert response.json()["warnings"]


def install_provider(monkeypatch, data, finish="stop", refusal=None):
    monkeypatch.setenv("OPENAI_API_KEY", "private-test-token")
    class Response:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def read(self, *_):
            return json.dumps({"choices": [{"finish_reason": finish, "message": {
                "content": json.dumps(data), "refusal": refusal}}]}).encode()
    def provider(request, timeout):
        payload = json.loads(request.data)
        if payload["response_format"]["json_schema"]["name"] == "symptom_exploration":
            inputs = json.loads(payload["messages"][1]["content"])
            for item in [*data.get("possibilities", []), *data.get("medication_options", [])]:
                item.pop("source_ids", None)
                if "evidence_quote" in item:
                    quote = item.pop("evidence_quote")
                    item["evidence_id"] = next((passage["id"] for source in inputs["sources"]
                        for passage in source["evidence_passages"] if passage["text"] == quote), "invented")
        assert request.full_url == "https://api.openai.com/v1/chat/completions"
        assert payload["store"] is False
        assert "private-test-token" not in request.data.decode()
        return Response()
    monkeypatch.setattr(engine, "urlopen", provider)


@pytest.mark.parametrize("change", ["valid", "unknown_citation", "fake_quote", "unsupported_medicine"])
def test_synthesis_checks_citations_quotes_and_medication_names(monkeypatch, change):
    data = answer()
    if change == "unknown_citation": data["sections"][0]["source_ids"] = ["invented"]
    if change == "fake_quote": data["possibilities"][0]["evidence_quote"] = "This quote is not in any source."
    if change == "unsupported_medicine": data["medication_options"][0]["name"] = "amoxicillin"
    install_provider(monkeypatch, data)
    sources = [{"id": "S1", "excerpt": REFERENCE["description"]}]
    if change == "valid":
        assert engine.synthesize("itchy skin", sources)["medication_options"]
    elif change == "unsupported_medicine":
        result = engine.synthesize("itchy skin", sources)
        assert not result["medication_options"]
        assert result["possibilities"] and result["evidence_warnings"]
    else:
        with pytest.raises(ValueError): engine.synthesize("itchy skin", sources)


@pytest.mark.parametrize("finish, refusal", [("length", None), ("stop", "Cannot comply")])
def test_incomplete_and_refused_output_rejected(monkeypatch, finish, refusal):
    install_provider(monkeypatch, answer(), finish, refusal)
    with pytest.raises(ValueError): engine.synthesize("itchy skin", [{"id":"S1", "excerpt":REFERENCE["description"]}])


def test_zero_medication_options_is_valid(monkeypatch):
    data = answer()
    data["medication_options"] = []
    install_provider(monkeypatch, data)
    result = engine.synthesize("itchy skin", [{"id":"S1", "excerpt":REFERENCE["description"]}])
    assert result["medication_options"] == []


def test_status_only_exposes_availability(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "private-test-token")
    assert client.get("/ai-analyzer/status").json() == {"ai_available": True}


def test_favicon_and_existing_patient_routes():
    assert client.get("/favicon.svg").headers["content-type"].startswith("image/svg+xml")
    patients = client.get("/patients").json()
    assert client.get("/patients/" + patients[0]["id"]).status_code == 200
    assert client.get("/patients/not-a-patient").status_code == 404


def test_medical_search_queries_can_include_disease_numbers():
    assert plan(["COVID-19", "type 2 diabetes"]).queries == ["COVID-19", "type 2 diabetes"]


def test_evidence_choices_remain_verbatim_and_keep_treatment_context():
    text = "An initial symptom description. " + "Long background context. " * 40 + "Treatment may include antihistamines for allergies."
    passages = engine.evidence_passages(text)
    assert passages and len(passages) <= 10
    assert all(passage in text and 20 <= len(passage) <= 500 for passage in passages)
    assert any("antihistamines" in passage for passage in passages)
