# Feature Implementation Plan

**Overall Progress:** `10%` → implementing...

## TLDR
Rebuild the bug triage pipeline using Groq's free API (Llama 3), add Pydantic validation, retry logic, agent memory, CLI support, structured logging, and a Streamlit web UI. Deployable demo for a PM resume.

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

- [ ] 🟥 **Step 1: Swap Anthropic → Groq**
  - [ ] 🟥 Add `groq` to `requirements.txt`
  - [ ] 🟥 Replace `anthropic.Anthropic()` client with Groq client
  - [ ] 🟥 Update model to `llama3-8b-8192` (free Groq model)
  - [ ] 🟥 Update response parsing to match Groq's OpenAI-compatible format

- [ ] 🟥 **Step 2: Add Pydantic output schemas**
  - [ ] 🟥 Add `pydantic` to `requirements.txt`
  - [ ] 🟥 Define `ClassifierOutput`, `EnricherOutput`, `RouterOutput`, `JudgeOutput` models
  - [ ] 🟥 Parse each agent's JSON response through its Pydantic model

- [ ] 🟥 **Step 3: Add retry + validation loop**
  - [ ] 🟥 Wrap each agent call in a retry loop (max 3 attempts)
  - [ ] 🟥 Retry if JSON is invalid or Pydantic validation fails
  - [ ] 🟥 Raise clear error after max retries exceeded

- [ ] 🟥 **Step 4: Add agent memory**
  - [ ] 🟥 Build a shared `pipeline_context` dict that accumulates all prior outputs
  - [ ] 🟥 Pass full context to each agent's prompt (not just direct inputs)

- [ ] 🟥 **Step 5: Add structured logging**
  - [ ] 🟥 Create `logs/` directory
  - [ ] 🟥 On each run, write `logs/run_<timestamp>.json` with raw prompts, responses, and final outputs per agent

- [ ] 🟥 **Step 6: Add CLI interface**
  - [ ] 🟥 Use `argparse` to accept `--bug "..."` argument
  - [ ] 🟥 Fall back to hardcoded sample bug if no argument provided

- [ ] 🟥 **Step 7: Build Streamlit web UI (`app.py`)**
  - [ ] 🟥 Text area to paste a bug report
  - [ ] 🟥 "Run Pipeline" button
  - [ ] 🟥 Expandable section per agent showing its output as formatted JSON
  - [ ] 🟥 Final verdict banner (passed/failed + flags)
  - [ ] 🟥 Add `streamlit` to `requirements.txt`

- [ ] 🟥 **Step 8: Write README.md**
  - [ ] 🟥 Project overview + architecture diagram (text-based)
  - [ ] 🟥 Setup instructions (Groq API key, install deps)
  - [ ] 🟥 How to run CLI (`python pipeline.py --bug "..."`)
  - [ ] 🟥 How to run Streamlit UI (`streamlit run app.py`)
  - [ ] 🟥 Folder structure section

- [ ] 🟥 **Step 9: Push final code to GitHub**
  - [ ] 🟥 Commit all changes
  - [ ] 🟥 Push to `rituann/ritzai-bug-triage-agent`
  - [ ] 🟥 Close GitHub Issue #1
