
import html
import json
import re
import time
from functools import lru_cache
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()

# Only fictional case data is supported in this prototype.
class ResearchCase(BaseModel):
    symptoms: str = Field(min_length=2, max_length=2000)
    age: int = Field(ge=0, le=120)
    duration: str = ""
    medical_history: str = ""
    medications: str = ""
    allergies: str = ""


def fetch_url(base, params):
    url = base + "?" + urlencode(params)
    request = Request(
        url,
        headers={"User-Agent": "MedInsightStudentDemo/0.8"}
    )
    with urlopen(request, timeout=8) as response:
        return response.read()


def clean_text(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]*>", " ", value)
    return " ".join(value.split())


# Cache reference queries for up to 12 hours.
# No patient details are included in these queries.
@lru_cache(maxsize=256)
def cached_medline(term, cache_period):
    raw = fetch_url(
        "https://wsearch.nlm.nih.gov/ws/query",
        {
            "db": "healthTopics",
            "term": term,
            "retmax": 10,
            "rettype": "brief",
            "tool": "MedInsightStudentDemo"
        }
    )

    root = ET.fromstring(raw)
    items = []

    for document in root.findall(".//document"):
        fields = {}

        for content in document.findall("content"):
            name = content.get("name", "").lower()
            fields[name] = clean_text(
                "".join(content.itertext())
            )

        items.append({
            "name": fields.get("title", "Medical topic"),
            "description": (
                fields.get("fullsummary")
                or fields.get("snippet")
                or "Description unavailable."
            )[:900],
            "url": document.get("url", ""),
            "source": "MedlinePlus"
        })

    return items


@lru_cache(maxsize=256)
def cached_conditions(term, cache_period):
    raw = fetch_url(
        "https://clinicaltables.nlm.nih.gov/api/"
        "conditions/v3/search",
        {
            "terms": term,
            "count": 10,
            "df": "consumer_name"
        }
    )

    data = json.loads(raw)
    rows = data[3] if len(data) > 3 else []

    return [
        {
            "name": row[0],
            "description": (
                "Medical condition vocabulary match. "
                "This is not a patient-specific diagnosis."
            ),
            "source": "NLM Clinical Tables",
            "url": ""
        }
        for row in rows
        if row and row[0]
    ]


STOPWORDS = {
    "the", "and", "with", "have", "having",
    "been", "for", "from", "this", "that",
    "some", "about", "very", "days", "weeks",
    "months", "years", "pain", "feel", "feeling",
    "left", "right", "both", "since"
}


def research_terms(symptoms):
    # Use symptom phrases rather than sending patient records.
    parts = re.split(r"[,;]|\band\b", symptoms.lower())

    terms = []
    for part in parts:
        cleaned = re.sub(r"[^a-z -]", " ", part)
        words = [
            word for word in cleaned.split()
            if len(word) >= 3 and word not in STOPWORDS
        ]

        if words:
            terms.append(" ".join(words[:5]))

    # Also include meaningful individual words as fallback.
    for word in re.findall(r"[a-z]{4,}", symptoms.lower()):
        if word not in STOPWORDS:
            terms.append(word)

    # Avoid excessive API calls.
    return list(dict.fromkeys(terms))[:3]


@router.post("/research-case")
def research_case(patient: ResearchCase):
    terms = research_terms(patient.symptoms)

    if not terms:
        return {
            "matches": [],
            "searched_terms": [],
            "warnings": ["No usable search terms found."],
            "note": "No diagnosis has been performed."
        }

    matches = {}
    warnings = []

    # Rotate cache every 12 hours.
    cache_period = int(time.time() // 43200)

    for term in terms:
        for source_name, lookup in [
            ("MedlinePlus", cached_medline),
            ("NLM Clinical Tables", cached_conditions)
        ]:
            try:
                items = lookup(term, cache_period)

                for item in items:
                    key = item["name"].lower().strip()

                    if key not in matches:
                        matches[key] = {
                            **item,
                            "matched_search_terms": [term]
                        }
                    elif term not in matches[key]["matched_search_terms"]:
                        matches[key]["matched_search_terms"].append(term)

            except Exception:
                warnings.append(
                    f"{source_name} was unavailable for '{term}'."
                )

    return {
        "searched_terms": terms,
        "matches": list(matches.values())[:25],
        "warnings": warnings,
        "context": {
            "age": patient.age,
            "duration": patient.duration,
            "history_provided": bool(patient.medical_history),
            "medications_provided": bool(patient.medications),
            "allergies_provided": bool(patient.allergies)
        },
        "note": (
            "Educational retrieval results only. "
            "Search order is not diagnostic likelihood. "
            "Medical history, age, and medications have not "
            "been clinically interpreted. "
            "Do not use this output for diagnosis or triage."
        )
    }
