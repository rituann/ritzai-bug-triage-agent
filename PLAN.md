# Feature Implementation Plan

**Overall Progress:** `100%` ✅

## TLDR
Rebuilt the bug triage pipeline using Groq's free API (Llama 3), added Pydantic validation, retry logic, agent memory, CLI support, structured logging, and a Streamlit web UI. Deployable demo for a PM resume.

## Critical Decisions
- **Groq over Gemini:** Free, fast, OpenAI-compatible SDK — minimal rewiring
- **Streamlit for UI:** Best Python demo tool, no frontend code needed
- **Pydantic for contracts:** Each agent has a typed output schema — agents can't silently return garbage
- **Agent memory via accumulated context:** Each agent receives all prior outputs, not just its direct input
- **File-based logging:** One JSON file per run in `logs/` — easy to inspect and show in demos
- **Single repo:** Everything in `ritzai-bug-triage-agent`, CLI + UI coexist

## Tasks

- [x] 🟩 **Step 0: Project scaffolding (already done)**
  - [x] 🟩 `pipeline.py` created with 4 Anthropic-based agents
  - [x] 🟩 GitHub repo pushed (`rituann/ritzai-bug-triage-agent`)

- [x] 🟩 **Step 1: Swap Anthropic → Groq**
  - [x] 🟩 Add `groq` to `requirements.txt`
  - [x] 🟩 Replace `anthropic.Anthropic()` client with Groq client
  - [x] 🟩 Update model to `llama3-8b-8192` (free Groq model)
  - [x] 🟩 Update response parsing to match Groq's OpenAI-compatible format

- [x] 🟩 **Step 2: Add Pydantic output schemas**
  - [x] 🟩 Add `pydantic` to `requirements.txt`
  - [x] 🟩 Define `ClassifierOutput`, `EnricherOutput`, `RouterOutput`, `JudgeOutput` models
  - [x] 🟩 Parse each agent's JSON response through its Pydantic model

- [x] 🟩 **Step 3: Add retry + validation loop**
  - [x] 🟩 Wrap each agent call in a retry loop (max 3 attempts)
  - [x] 🟩 Retry if JSON is invalid or Pydantic validation fails
  - [x] 🟩 Raise clear error after max retries exceeded

- [x] 🟩 **Step 4: Add agent memory**
  - [x] 🟩 Build a shared `pipeline_context` dict that accumulates all prior outputs
  - [x] 🟩 Pass full context to each agent's prompt (not just direct inputs)

- [x] 🟩 **Step 5: Add structured logging**
  - [x] 🟩 Create `logs/` directory
  - [x] 🟩 On each run, write `logs/run_<timestamp>.json` with raw prompts, responses, and final outputs per agent

- [x] 🟩 **Step 6: Add CLI interface**
  - [x] 🟩 Use `argparse` to accept `--bug "..."` argument
  - [x] 🟩 Fall back to hardcoded sample bug if no argument provided

- [x] 🟩 **Step 7: Build Streamlit web UI (`app.py`)**
  - [x] 🟩 Text area to paste a bug report
  - [x] 🟩 "Run Pipeline" button
  - [x] 🟩 Live `st.status()` per agent during execution
  - [x] 🟩 Expandable section per agent showing its output as formatted JSON
  - [x] 🟩 Final verdict banner (passed/failed + flags)
  - [x] 🟩 Slack message callout
  - [x] 🟩 Add `streamlit` to `requirements.txt`

- [x] 🟩 **Step 8: Write README.md**
  - [x] 🟩 Project overview + architecture diagram (text-based)
  - [x] 🟩 Setup instructions (Groq API key, install deps)
  - [x] 🟩 How to run CLI (`python pipeline.py --bug "..."`)
  - [x] 🟩 How to run Streamlit UI (`streamlit run app.py`)
  - [x] 🟩 Folder structure section
  - [x] 🟩 PM learning notes section

- [x] 🟩 **Step 9: Push final code to GitHub**
  - [x] 🟩 Commit all changes
  - [x] 🟩 Push to `rituann/ritzai-bug-triage-agent`
  - [x] 🟩 Close GitHub Issue #1
