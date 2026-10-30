
import html
import csv
from research_engine import router as research_router
from differential_engine import router as differential_router
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from xml.etree import ElementTree as ET

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

app = FastAPI(title="MedInsight AI", version="0.3.0")
app.include_router(research_router)
app.include_router(differential_router)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


class PatientCase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=0, le=120)
    symptoms: str = Field(min_length=1, max_length=2000)
    duration: str = ""
    medical_history: str = ""
    medications: str = ""
    allergies: str = ""


@app.get("/")
def home():
    return FileResponse(BASE_DIR / "index.html")


import re

# Educational examples, NOT clinically validated rules.
DEMO_CONDITIONS = [
    {
        "name": "Eczema",
        "keywords": [
            "itchy", "itching", "dry skin",
            "dry patches", "red patches", "eczema"
        ]
    },
    {
        "name": "Contact Dermatitis",
        "keywords": [
            "rash", "itching", "new soap",
            "detergent", "skin irritation"
        ]
    },
    {
        "name": "Acne",
        "keywords": [
            "pimples", "blackheads", "whiteheads",
            "acne", "pustules"
        ]
    },
    {
        "name": "Psoriasis",
        "keywords": [
            "scaly patches", "thick plaques",
            "silvery scales", "psoriasis"
        ]
    },
    {
        "name": "Fungal Skin Infections",
        "keywords": [
            "ring shaped", "ring-shaped",
            "ringworm", "athlete's foot"
        ]
    }
]


def find_demo_conditions(patient):
    symptoms = patient.symptoms.lower()
    matches = []

    for condition in DEMO_CONDITIONS:
        found = []

        for keyword in condition["keywords"]:
            pattern = (
                r"(?<!\w)" +
                re.escape(keyword) +
                r"(?!\w)"
            )

            if re.search(pattern, symptoms):
                found.append(keyword)

        if found:
            matches.append({
                "condition": condition["name"],
                "matched_terms": found,
                "explanation": (
                    "This topic matched terms in the "
                    "fictional symptom description."
                )
            })

    return matches


@app.post("/analyze")
def analyze_patient(patient: PatientCase):

    matches = find_demo_conditions(patient)

    summary = f"""
MEDINSIGHT AI — FICTIONAL CASE REPORT

Patient: {patient.name}
Age: {patient.age}

SYMPTOMS
{patient.symptoms}

DURATION
{patient.duration or "Not provided"}

MEDICAL HISTORY
{patient.medical_history or "Not provided"}

MEDICATIONS
{patient.medications or "Not provided"}

ALLERGIES
{patient.allergies or "Not provided"}

------------------------------------

EDUCATIONAL TOPIC MATCHES
"""

    if matches:
        for match in matches:
            summary += (
                f"\n{match['condition']}"
                f"\nMatched: "
                f"{', '.join(match['matched_terms'])}\n"
            )
    else:
        summary += "\nNo demonstration rules matched.\n"

    summary += """
------------------------------------

These are keyword-based research examples,
not diagnoses, probabilities, or clinical triage.

Use fictional patient data only.
"""

    return {
        "summary": summary,
        "possible_conditions": matches,
        "count": len(matches)
    }


# Read an official Synthea CSV file
def read_csv(filename):
    path = DATA_DIR / filename

    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"{filename} not found in backend/data"
        )

    with path.open(
        encoding="utf-8-sig",
        newline=""
    ) as file:
        return list(csv.DictReader(file))


# Show available synthetic patients
@app.get("/patients")
def list_patients():
    patients = read_csv("patients.csv")

    return [
        {
            "id": p["Id"] if "Id" in p else p["ID"],
            "name": (
                p.get("FIRST", "") + " " +
                p.get("LAST", "")
            ).strip()
        }
        for p in patients[:100]
    ]


# Load an individual synthetic medical history
@app.get("/patients/{patient_id}")
def patient_details(patient_id: str):
    patients = read_csv("patients.csv")

    patient = next(
        (
            p for p in patients
            if p.get("Id", p.get("ID")) == patient_id
        ),
        None
    )

    if patient is None:
        raise HTTPException(
            status_code=404,
            detail="Synthetic patient not found"
        )

    def related_records(filename):
        records = read_csv(filename)
        return [
            record for record in records
            if record.get("PATIENT") == patient_id
        ][:100]

    return {
        "patient": {
            "id": patient_id,
            "name": (
                patient.get("FIRST", "") + " " +
                patient.get("LAST", "")
            ).strip(),
            "birthdate": patient.get("BIRTHDATE"),
            "gender": patient.get("GENDER")
        },
        "conditions": related_records("conditions.csv"),
        "medications": related_records("medications.csv"),
        "allergies": related_records("allergies.csv")
    }


# Search the live NIH MedlinePlus database

@app.get("/medical-topics")
def medical_topics(
    search: str = Query(min_length=2, max_length=100)
):
    params = urlencode({
        "db": "healthTopics",
        "term": search,
        "retmax": 5,
        "rettype": "brief",
        "tool": "medinsightstudent"
    })

    url = (
        "https://wsearch.nlm.nih.gov/ws/query?"
        + params
    )

    try:
        with urlopen(url, timeout=10) as response:
            xml_data = response.read()

        root = ET.fromstring(xml_data)
        topics = []

        for document in root.findall(".//document"):
            fields = {}

            for content in document.findall("content"):
                field_name = content.get("name", "")
                raw_text = "".join(content.itertext())

                # Remove HTML markup from NIH summaries.
                plain_text = re.sub(
                    r"<[^>]+>", " ", html.unescape(raw_text)
                )
                plain_text = " ".join(plain_text.split())

                fields[field_name.lower()] = plain_text

            summary = (
                fields.get("fullsummary")
                or fields.get("snippet")
                or "No summary available."
            )

            # Keep the search preview reasonably short.
            if len(summary) > 450:
                summary = summary[:450].rsplit(" ", 1)[0] + "..."

            topics.append({
                "title": fields.get("title", "Health topic"),
                "summary": summary,
                "url": document.get("url", ""),
                "source": "MedlinePlus"
            })

        return {
            "search": search,
            "topics": topics,
            "note": (
                "Educational health information from "
                "the National Library of Medicine."
            )
        }

    except Exception:
        raise HTTPException(
            status_code=502,    
            detail="MedlinePlus service unavailable"
        )


@app.get("/favicon.svg", include_in_schema=False)
def favicon():
    favicon_path = BASE_DIR / "favicon.svg"
    return FileResponse(
        favicon_path,
        media_type="image/svg+xml"
    )

