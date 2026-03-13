# AeroSpec Agent
## Trustworthy Hyperspectral Mission Design Copilot for Aviation

AeroSpec Agent is a production-style **agentic AI system** for aviation remote sensing mission design.  
It converts free-text mission intent into a structured, constrained, and verified spectral plan using LangGraph orchestration and deterministic scientific tooling.

---

## Why this is an agent (not a chatbot/classifier)

AeroSpec Agent does not directly answer with unconstrained LLM text. It runs a real multi-step workflow:
1. Interprets mission intent into structured mission JSON.
2. Retrieves candidate spectral regions only from local seed knowledge.
3. Scores candidates with transparent deterministic rules.
4. Applies hard constraints (band budget and redundancy).
5. Verifies recommendation consistency and risk.
6. Produces a structured report with alternatives, caveats, and confidence.

The LLM is only used for mission normalization (optional) and cannot invent spectral answers.

---

## Architecture

```text
Gradio UI
  |
  v
LangGraph State Machine
  ├── Mission Interpreter (LLM optional, schema-constrained)
  ├── Knowledge Retriever (local seed rules JSON)
  ├── Constraint + Ranking (deterministic scoring + pruning)
  ├── Verification (rule-based consistency checks)
  └── Report Agent (structured mission package)
  |
  v
Outputs: workflow log, recommended plans, spectral plot, debug JSON, markdown report
```

---

## Core Design Principles

- **Tool-first decisions**: wavelengths come from retrieved rules and scoring tools, not free-form LLM generation.
- **Deterministic scientific layer**: scoring, constraints, and verification are Python logic.
- **Transparent trust features**: confidence, warnings, assumptions, alternatives, and step-by-step logs.
- **Demo-ready UX**: curated sample missions and visible reasoning artifacts.

---

## Project Structure

```text
aerospec-agent/
  app.py
  config.py
  requirements.txt
  .env.example
  README.md
  agents/
    graph.py
    nodes.py
    prompts.py
    state.py
  tools/
    mission_parser.py
    knowledge_retriever.py
    photon_flux_estimator.py
    wavelength_ranker.py
    constraint_checker.py
    verification.py
    report_generator.py
    plotting.py
  core/
    schemas.py
    constants.py
    utils.py
  data/
    spectral_rules.json
    aviation_missions.json
    sample_wavelengths.json
    sample_scene_metadata.json
  demos/
    demo_inputs.json
  tests/
    test_ranker.py
    test_constraints.py
    test_verification.py
```

---

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Environment variables
- `OPENAI_API_KEY` (optional)
- `OPENAI_MODEL` (default: `gpt-4o-mini`)

If no API key is set, the app runs in deterministic parsing mode.

---

## Run

```bash
python app.py
```

---

## Agent Workflow Details

### 1) Mission Interpreter
- Normalizes mission inputs into strict schema fields.
- Uses LLM only for normalization with hard prompt constraints.
- Falls back to deterministic parser on any failure.

### 2) Knowledge Retriever
- Loads local seed rules from `data/spectral_rules.json`.
- Computes evidence scores from target match + keyword match.
- Filters out low-evidence candidates.

### 3) Constraint + Ranking
- Deterministic weighted scoring:
  - mission relevance
  - photon flux suitability
  - interpretability
  - compactness
  - robustness
  - knowledge confidence
- Applies conflict penalties and mission-priority emphasis.
- Enforces max band budget and reduces overlapping bands.

### 4) Verification
- Checks target alignment, photon suitability, provenance coverage, and confidence level.
- Emits warnings and a trust-calibrated confidence score.

### 5) Report
- Returns `best_overall`, `best_compact`, and `best_robust` plans.
- Includes rationale, retrieval reason, caveats, and component scores.

---

## Sample Missions
- Thin cirrus cloud sensing
- Standing water near runway
- Compact moisture mission (4 bands, low photon flux)
- Drone vegetation stress sweep
- All-weather compact hazard scan

---

## Trust & Safety Notes

- Seed knowledge is demo data, not comprehensive scientific authority.
- Recommendations are decision support, not autonomous mission approval.
- Operational use requires calibration with sensor SRF and atmospheric modeling.

---

## Tests

```bash
pytest -q
```

---

## Live Demo UX Highlights
- Executive mission brief card with confidence tier language.
- Numbered 5-step workflow logs for easy narration on stage.
- Visual recommendation cards with range, score, and evidence rationale.
- Spectral plot with VIS/NIR/SWIR context bands and on-bar labels.
- In-app section: **Why this is agentic AI (not a chatbot)**.

---

## Future Enhancements
- Sensor-specific response-function aware optimization
- Better atmospheric transfer integration
- Persistent multi-user mission history store
- Report export artifacts (PDF/HTML) and provenance trace UI
