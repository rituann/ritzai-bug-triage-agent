# 🐛 Multi-Agent Bug Triage Pipeline

A learning project demonstrating **agentic AI patterns** using a 4-agent pipeline that automatically triages bug reports. Built with Groq's free API (Llama 3) and Streamlit.

> Built to study agentic design patterns relevant to PM roles in AI product teams.

**Live demo:** https://bug-triage-agent.streamlit.app

---

## Architecture

```
Bug Report (input)
      │
      ▼
┌─────────────────┐
│  1. Classifier  │  → severity (P0/P1/P2), category (crash/perf/ui/logic), component
└────────┬────────┘
         │ context passed forward (agent memory)
         ▼
┌─────────────────┐
│  2. Enricher    │  → is_duplicate, similar_bugs, confidence_score
└────────┬────────┘
         │ context passed forward
         ▼
┌─────────────────┐
│  3. Router      │  → assigned_team, slack_message
└────────┬────────┘
         │ context passed forward
         ▼
┌─────────────────┐
│  4. Judge       │  → passed (bool), flags (list of concerns)
└─────────────────┘
         │
         ▼
  logs/run_<timestamp>.json
```

### Key Patterns Demonstrated

| Pattern | Where |
|---------|-------|
| **Agent memory** | Each agent receives all prior outputs via shared `context` dict |
| **Pydantic contracts** | Every agent output is validated against a typed schema |
| **Retry loop** | Up to 3 retries on invalid JSON or schema mismatch |
| **Structured logging** | Full prompt + response logged per agent per run |
| **Sequential pipeline** | Agents are deterministically chained, not parallel |

---

## Setup

### 1. Get a free Groq API key

Sign up at [console.groq.com](https://console.groq.com) — no credit card required.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set your API key

```bash
# Mac/Linux
export GROQ_API_KEY=your_key_here

# Windows (Command Prompt)
set GROQ_API_KEY=your_key_here

# Windows (PowerShell)
$env:GROQ_API_KEY="your_key_here"
```

---

## Running the Pipeline

### Option A — CLI

```bash
# Use the built-in sample bug report
python pipeline.py

# Pass your own bug report
python pipeline.py --bug "Login page freezes on Android 14 after entering password."
```

**Sample output:**
```
============================================================
BUG TRIAGE PIPELINE
============================================================

Bug Report:
  App crashes on iOS 17 when user taps the checkout button...

----------------------------------------
AGENT 1: Classifier
{
  "severity": "P0",
  "category": "crash",
  "affected_component": "iOS Checkout"
}

----------------------------------------
AGENT 2: Enricher
{
  "is_duplicate": false,
  "similar_bugs": [
    "App crashes on checkout with 2+ items in cart on iOS 16",
    "Checkout button unresponsive after cart update on iPhone 14"
  ],
  "confidence_score": 0.92
}

----------------------------------------
AGENT 3: Router
{
  "assigned_team": "iOS Team",
  "slack_message": "[P0] iOS checkout crash (3+ items) — assigned to iOS Team. Immediate action required."
}

----------------------------------------
AGENT 4: Judge
{
  "passed": true,
  "flags": []
}

============================================================
PIPELINE COMPLETE — PASSED
============================================================

Log saved → logs/run_20260316_143201.json
```

### Option B — Streamlit Web UI

```bash
streamlit run app.py
```

Opens in your browser at `http://localhost:8501`. Paste any bug report and click **Run Pipeline** to see each agent's output expand in real time.

---

## Project Structure

```
bug-triage-agent/
├── pipeline.py        # Core pipeline: 4 agents, retry logic, logging, CLI
├── app.py             # Streamlit web UI
├── requirements.txt   # groq, pydantic, streamlit
├── logs/              # Auto-created; one JSON file per pipeline run
│   └── run_<timestamp>.json
├── PLAN.md            # Implementation plan with progress tracking
└── README.md          # This file
```

---

## What Each File Does

### `pipeline.py`
- **Pydantic schemas** (`ClassifierOutput`, `EnricherOutput`, `RouterOutput`, `JudgeOutput`) — typed contracts for every agent
- **`call_agent()`** — generic retry runner: calls Groq, strips markdown fences, validates with Pydantic, retries up to 3x
- **4 agent functions** — each builds a prompt using the full `context` dict (agent memory)
- **`run_pipeline()`** — orchestrates the pipeline, returns final context dict
- **CLI** — `argparse` with `--bug` flag

### `app.py`
- Streamlit UI with `st.status()` live progress per agent
- Each agent output shown in an expandable `st.json()` block
- Final verdict banner + Slack message callout
- Saves run log same as CLI

---

## Learning Notes (for PM context)

**Why sequential agents?**
Each agent's output improves the next agent's reasoning. The Judge can only evaluate if it sees everything the Router saw.

**Why Pydantic?**
In real agentic systems, agents talk to each other. Without schema validation, one agent's malformed output silently breaks the next. Pydantic makes failures loud and retryable.

**Why retry loops?**
LLMs are probabilistic — they occasionally return markdown fences, extra text, or wrong field names. A retry loop makes the system production-grade without needing a more expensive model.

**Why log raw prompts?**
Observability is how you debug agentic systems. `logs/run_*.json` lets you see exactly what each agent was told and what it said — essential for improving prompts.
