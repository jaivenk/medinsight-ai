
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_gastrointestinal_case():
    response = client.post("/differential-case", json={
        "age": 24,
        "symptoms": (
            "Nausea, vomiting, diarrhea, "
            "and abdominal cramps"
        ),
        "duration": "1 day"
    })

    assert response.status_code == 200

    data = response.json()

    assert data["condition_count"] >= 1
    assert data["condition_count"] <= 4

    names = [
        condition["name"]
        for condition in data["conditions"]
    ]

    assert "Viral gastroenteritis" in names


def test_insufficient_information():
    response = client.post("/differential-case", json={
        "age": 22,
        "symptoms": "I feel unwell"
    })

    assert response.status_code == 200
    assert response.json()["condition_count"] == 0


def test_invalid_age():
    response = client.post("/differential-case", json={
        "age": -4,
        "symptoms": "Nausea and vomiting"
    })

    assert response.status_code == 422
