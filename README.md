# 🩺 MedInsight AI

### An Educational Medical Research & Case Exploration Platform

**MedInsight AI** is a student-developed web application designed to make medical research more accessible, organized, and interactive.

The platform allows users to explore fictional patient cases, identify relevant medical research topics, and retrieve information from established health-information sources—all within a streamlined interface.

Built with Python, FastAPI, HTML, CSS, and JavaScript, MedInsight AI combines structured case intake, synthetic patient records, and medical reference retrieval into one educational workspace.

> **Disclaimer:** MedInsight AI is an educational prototype. It does not provide medical diagnoses, treatment recommendations, clinical risk assessments, or professional medical advice. Use fictional patient information only.

---

## Features

### 1. Fictional Patient Case Analysis
- Enter fictional patient demographics, symptoms, and medical history.
- Record medications, allergies, and symptom duration.
- Generate an organized educational case report.
- Identify example condition topics through keyword-based matching.

### 2. Multi-Source Medical Research
- Retrieve medical reference information from NIH MedlinePlus.
- Search condition terminology through NLM Clinical Tables.
- Explore relevant research topics associated with case descriptions.
- View expandable condition cards with supporting information.

### 3. Synthetic Patient Integration
- Browse fictional patient records generated using Synthea.
- Load synthetic demographics and medical histories.
- Explore sample conditions, medications, and allergies.
- Work with realistic but artificially generated patient scenarios.

### 4. Integrated Medical Library
- Search MedlinePlus health topics directly from the application.
- Access external medical reference resources, including PubMed and ClinicalTrials.gov.
- Explore health information without requiring a user account.

### 5. Interactive User Interface
- Responsive dashboard with a modern teal-and-navy design.
- Expandable research results and interactive components.
- Dedicated fictional case workspace and medical library.
- Custom medical-themed branding.

---

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, FastAPI |
| ASGI Server | Uvicorn |
| Frontend | HTML, CSS, JavaScript |
| Medical Information | NIH MedlinePlus |
| Medical Terminology | NLM Clinical Tables |
| Synthetic Patient Data | Synthea |
| Version Control | Git and GitHub |

---

## Project Structure

```text
medinsight-ai/
├── backend/
│   ├── main.py
│   ├── research_engine.py
│   ├── index.html
│   ├── favicon.svg
│   └── data/                  # Local synthetic patient CSV files
├── .gitignore
└── README.md
```

The `backend/data/` directory is excluded from the repository. Synthetic datasets must be generated or obtained separately.

---

## Getting Started

### Prerequisites

- Python 3.10 or later
- pip
- Internet connection for medical reference searches

### 1. Clone the repository

```bash
git clone https://github.com/jaivenk/medinsight-ai.git
cd medinsight-ai/backend
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install fastapi "uvicorn[standard]"
```

### 4. Run the application

```bash
uvicorn main:app --reload
```

Open **http://127.0.0.1:8000** in your browser.

### 5. Optional: Add synthetic patient data

Generate or download synthetic CSV records from [Synthea](https://github.com/synthetichealth/synthea).

Place the relevant files inside `backend/data/`, including:

- `patients.csv`
- `conditions.csv`
- `medications.csv`
- `allergies.csv`

These files are needed for the synthetic patient loading feature. Other parts of the application can operate without them.

---

## How It Works

1. **Case intake:** The user enters fictional case details or loads a synthetic patient.
2. **Educational matching:** The backend identifies example condition-topic matches using predefined terminology rules.
3. **Reference retrieval:** The research engine searches external medical information sources.
4. **Results presentation:** The frontend organizes returned research topics into expandable cards and reports.

The system does not establish a diagnosis or calculate a clinically validated probability of disease.

---

## Current Limitations

- Research matches are not clinically validated.
- The application does not currently include a trained diagnostic machine-learning model.
- The system relies on the availability of external medical reference services.
- Synthetic patient datasets are not distributed with the repository.
- There is no authentication system or persistent case database.
- The application is intended for local development and educational experimentation.

---

## Future Development

Potential improvements include:

- [ ] More advanced medical terminology matching
- [ ] Improved relevance ranking and research citations
- [ ] Better search filtering and source transparency
- [ ] Automated testing and validation
- [ ] Deployment to a public hosting platform
- [ ] Expanded synthetic patient case exploration
- [ ] Improved mobile accessibility

---

## Project Purpose

MedInsight AI was created as an independent student software project exploring the intersection of biology, medicine, and computer science.

Its goal is to demonstrate how software can organize fictional clinical information and connect users with credible medical reference material through an accessible interface.

The project is under active development.

---

## Developer

**Jai Venkamsetty**

GitHub: [@jaivenk](https://github.com/jaivenk)

---

**MedInsight AI — Research, exploration, and learning.**