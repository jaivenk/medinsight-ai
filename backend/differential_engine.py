
import re

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class FictionalCase(BaseModel):
    age: int = Field(ge=0, le=120)
    symptoms: str = Field(min_length=3, max_length=2000)
    duration: str = ""
    medical_history: str = ""


# Educational symptom profiles, not validated diagnostic criteria.
# Add new profiles only after reviewing reliable medical references.
PROFILES = [
    {
        "name": "Viral gastroenteritis",
        "terms": {
            "Diarrhea": ["diarrhea", "watery stool", "loose stools"],
            "Vomiting": ["vomiting", "throwing up"],
            "Nausea": ["nausea", "nauseous"],
            "Abdominal cramps": ["stomach cramps", "abdominal cramps"],
        },
        "question": "Were there recent sick contacts or shared exposures?",
        "topic": "gastroenteritis",
    },
    {
        "name": "Foodborne illness",
        "terms": {
            "Diarrhea": ["diarrhea", "loose stools"],
            "Vomiting": ["vomiting", "throwing up"],
            "Nausea": ["nausea", "nauseous"],
            "Abdominal pain": ["stomach pain", "abdominal pain"],
        },
        "question": "Did symptoms begin after a particular meal?",
        "topic": "food poisoning",
    },
    {
        "name": "Common cold",
        "terms": {
            "Cough": ["cough", "coughing"],
            "Runny nose": ["runny nose", "rhinorrhea"],
            "Congestion": ["congestion", "stuffy nose"],
            "Sore throat": ["sore throat"],
            "Sneezing": ["sneezing", "sneeze"],
        },
        "question": "Is there fever, and how long have symptoms lasted?",
        "topic": "common cold",
    },
    {
        "name": "Influenza",
        "terms": {
            "Fever": ["fever", "feverish"],
            "Cough": ["cough", "coughing"],
            "Body aches": ["body aches", "muscle aches", "myalgia"],
            "Fatigue": ["fatigue", "exhaustion"],
            "Chills": ["chills"],
        },
        "question": "Did symptoms begin suddenly, with fever and body aches?",
        "topic": "flu",
    },
    {
        "name": "COVID-19",
        "terms": {
            "Cough": ["cough", "coughing"],
            "Fever": ["fever", "feverish"],
            "Sore throat": ["sore throat"],
            "Fatigue": ["fatigue", "exhaustion"],
            "Congestion": ["congestion", "stuffy nose"],
            "Loss of smell": ["loss of smell", "can't smell"],
        },
        "question": "Was there recent exposure or a test result?",
        "topic": "covid-19",
    },
    {
        "name": "Seasonal allergic rhinitis",
        "terms": {
            "Sneezing": ["sneezing", "sneeze"],
            "Runny nose": ["runny nose"],
            "Congestion": ["congestion", "stuffy nose"],
            "Itchy eyes": ["itchy eyes"],
            "Watery eyes": ["watery eyes"],
        },
        "question": "Do symptoms occur around pollen, dust, or animals?",
        "topic": "hay fever",
    },
    {
        "name": "Migraine",
        "terms": {
            "Headache": ["headache", "head pain"],
            "Nausea": ["nausea", "nauseous"],
            "Light sensitivity": ["light sensitivity", "photophobia"],
            "Sound sensitivity": ["sound sensitivity", "phonophobia"],
            "Throbbing pain": ["throbbing", "pulsating headache"],
        },
        "question": "Is the headache recurrent or associated with light sensitivity?",
        "topic": "migraine",
    },
    {
        "name": "Tension-type headache",
        "terms": {
            "Headache": ["headache", "head pain"],
            "Pressure": ["head pressure", "tight band"],
            "Neck tension": ["neck tension", "tight neck"],
            "Stress": ["stress", "stressed"],
        },
        "question": "Is the pain pressing or tightening rather than pulsating?",
        "topic": "headache",
    },
    {
        "name": "Atopic dermatitis (eczema)",
        "terms": {
            "Itching": ["itching", "itchy", "pruritus"],
            "Dry skin": ["dry skin", "dry patches"],
            "Rash": ["rash", "red patches"],
            "Scaling": ["scaly skin", "scaling"],
        },
        "question": "Where is the rash, and is there a history of eczema?",
        "topic": "eczema",
    },
    {
        "name": "Contact dermatitis",
        "terms": {
            "Rash": ["rash", "red patches"],
            "Itching": ["itching", "itchy"],
            "Skin irritation": ["skin irritation", "burning skin"],
            "New exposure": ["new soap", "new detergent", "new lotion"],
        },
        "question": "Was there recent exposure to a new product or material?",
        "topic": "contact dermatitis",
    },
    {
        "name": "Urinary tract infection",
        "terms": {
            "Painful urination": ["burning urination", "painful urination", "dysuria"],
            "Urinary frequency": ["frequent urination", "peeing often"],
            "Urgency": ["urinary urgency", "urgent need to pee"],
            "Lower abdominal pain": ["lower abdominal pain", "pelvic pain"],
        },
        "question": "Are there urinary symptoms, fever, or back pain?",
        "topic": "urinary tract infections",
    },
    {
        "name": "Acid reflux (GERD)",
        "terms": {
            "Heartburn": ["heartburn", "burning chest"],
            "Acid taste": ["sour taste", "acid taste"],
            "Regurgitation": ["regurgitation", "acid reflux"],
            "After-meal discomfort": ["after eating", "after meals"],
        },
        "question": "Are symptoms worse after meals or while lying down?",
        "topic": "gerd",
    },
]


def detect_features(text, terms):
    found = []

    for feature, phrases in terms.items():
        for phrase in phrases:
            pattern = r"(?<!\w)" + re.escape(phrase) + r"(?!\w)"

            if re.search(pattern, text):
                found.append(feature)
                break

    return found


@router.post("/differential-case")
def differential_case(case: FictionalCase):
    text = " ".join([
        case.symptoms,
        case.duration,
        case.medical_history,
    ]).lower()

    candidates = []

    for profile in PROFILES:
        matches = detect_features(text, profile["terms"])

        # Require at least two distinct supporting features.
        if len(matches) < 2:
            continue

        candidates.append({
            "name": profile["name"],
            "supporting_features": matches,
            "matched_feature_count": len(matches),
            "missing_information": [
                profile["question"]
            ],
            "follow_up_question": profile["question"],
            "reference_topic": profile["topic"],
            "reference_url": (
                "https://medlineplus.gov/search/"
                "?query=" + profile["topic"].replace(" ", "%20")
            ),
        })

    # Sort by the number of distinct matching features.
    # This is not a diagnostic likelihood calculation.
    candidates.sort(
        key=lambda item: item["matched_feature_count"],
        reverse=True
    )

    selected = candidates[:4]

    return {
        "analysis_type": "educational_pseudo_diagnosis",
        "conditions": selected,
        "condition_count": len(selected),
        "database_size": len(PROFILES),
        "message": (
            "Potential research topics identified."
            if selected else
            "Insufficient matching features for a supported "
            "educational condition suggestion."
        ),
        "disclaimer": (
            "These results are unvalidated educational topic "
            "matches, not diagnoses or disease probabilities. "
            "This prototype does not assess medical urgency."
        ),
    }
