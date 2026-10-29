
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_homepage():
    response = client.get("/")
    assert response.status_code == 200
    assert "MedInsight" in response.text


def test_analyze_valid_case():
    response = client.post("/analyze", json={
        "name": "Test Patient",
        "age": 25,
        "symptoms": "itchy dry skin",
        "duration": "3 days",
        "medical_history": "",
        "medications": "",
        "allergies": ""
    })

    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "possible_conditions" in data
    assert any(
        item["condition"] == "Eczema"
        for item in data["possible_conditions"]
    )


def test_analyze_rejects_invalid_age():
    response = client.post("/analyze", json={
        "name": "Test Patient",
        "age": -5,
        "symptoms": "itchy skin"
    })

    assert response.status_code == 422
