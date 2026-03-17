"""
Multi-Agent Bug Triage Pipeline
--------------------------------
4 sequential agents powered by Groq (Llama 3, free tier):
  1. Classifier  → severity, category, affected_component
  2. Enricher    → is_duplicate, similar_bugs, confidence_score
  3. Router      → assigned_team, slack_message
  4. Judge       → passed, flags

Features:
  - Pydantic schemas enforce typed outputs for every agent
  - Retry loop (up to 3 attempts) on invalid JSON or schema mismatch
  - Agent memory: each agent receives all prior outputs as context
  - Structured logging: every run saved to logs/run_<timestamp>.json
  - CLI: python pipeline.py --bug "your bug report here"
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Type

from groq import Groq
from pydantic import BaseModel, ValidationError, field_validator

# ── Client ────────────────────────────────────────────────────────────────────

# Client is initialized lazily on first use so that Streamlit Cloud has time
# to inject GROQ_API_KEY from st.secrets into os.environ before it's read.
_client: Groq | None = None

def get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    return _client

MODEL = "llama-3.1-8b-instant"
MAX_RETRIES = 3

# ── Pydantic output schemas ────────────────────────────────────────────────────
# Each schema acts as a data contract between agents.
# If the LLM returns garbage, Pydantic raises ValidationError → triggers retry.

class ClassifierOutput(BaseModel):
    severity: str           # P0 / P1 / P2
    category: str           # crash / perf / ui / logic
    affected_component: str

    @field_validator("severity")
    @classmethod
    def check_severity(cls, v: str) -> str:
        if v not in ("P0", "P1", "P2"):
            raise ValueError(f"Invalid severity: {v}")
        return v

    @field_validator("category")
    @classmethod
    def check_category(cls, v: str) -> str:
        if v not in ("crash", "perf", "ui", "logic"):
            raise ValueError(f"Invalid category: {v}")
        return v


class EnricherOutput(BaseModel):
    is_duplicate: bool
    similar_bugs: list[str]     # exactly 2 realistic example titles
    confidence_score: float     # 0.0 – 1.0

    @field_validator("similar_bugs")
    @classmethod
    def check_two_bugs(cls, v: list[str]) -> list[str]:
        if len(v) != 2:
            raise ValueError("similar_bugs must contain exactly 2 items")
        return v

    @field_validator("confidence_score")
    @classmethod
    def check_score_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("confidence_score must be between 0 and 1")
        return v


class RouterOutput(BaseModel):
    assigned_team: str
    slack_message: str


class JudgeOutput(BaseModel):
    passed: bool
    flags: list[str]    # empty list [] if no concerns


# ── Logging helpers ────────────────────────────────────────────────────────────

def setup_run_log() -> tuple[dict, Path]:
    """Create an empty log dict and a timestamped file path under logs/."""
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = logs_dir / f"run_{timestamp}.json"
    run_log: dict[str, Any] = {"timestamp": timestamp, "agents": []}
    return run_log, log_path


def save_run_log(run_log: dict, log_path: Path) -> None:
    """Flush the run log dict to disk as pretty-printed JSON."""
    with open(log_path, "w") as f:
        json.dump(run_log, f, indent=2)


# ── Core retry runner ─────────────────────────────────────────────────────────

def call_agent(
    agent_name: str,
    prompt: str,
    schema: Type[BaseModel],
    run_log: dict,
) -> BaseModel:
    """
    Call the LLM with up to MAX_RETRIES attempts.
    Each attempt is logged (prompt, raw response, status, errors).
    Raises RuntimeError if all retries are exhausted.
    """
    agent_log: dict[str, Any] = {
        "agent": agent_name,
        "prompt": prompt,
        "attempts": [],
    }

    for attempt in range(1, MAX_RETRIES + 1):
        raw_response = ""
        try:
            response = get_client().chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512,
                temperature=0.1,  # low temp = more deterministic JSON
            )
            raw_response = response.choices[0].message.content.strip()

            # Strip markdown code fences (```json ... ```) if model wraps output
            if raw_response.startswith("```"):
                raw_response = raw_response.split("```")[1]
                if raw_response.startswith("json"):
                    raw_response = raw_response[4:]
                raw_response = raw_response.strip()

            parsed = json.loads(raw_response)
            result = schema(**parsed)   # Pydantic validation

            agent_log["attempts"].append({
                "attempt": attempt,
                "raw_response": raw_response,
                "status": "success",
            })
            run_log["agents"].append(agent_log)
            return result

        except (json.JSONDecodeError, ValidationError, KeyError) as e:
            # Retryable: bad JSON or schema mismatch — try again
            agent_log["attempts"].append({
                "attempt": attempt,
                "raw_response": raw_response,
                "status": "failed",
                "error": str(e),
            })
            if attempt == MAX_RETRIES:
                run_log["agents"].append(agent_log)
                raise RuntimeError(
                    f"[{agent_name}] failed after {MAX_RETRIES} attempts. "
                    f"Last error: {e}"
                )
        except Exception as e:
            # Non-retryable: API errors (bad key, invalid model, rate limit, etc.)
            agent_log["attempts"].append({
                "attempt": attempt,
                "raw_response": raw_response,
                "status": "api_error",
                "error": f"{type(e).__name__}: {e}",
            })
            run_log["agents"].append(agent_log)
            raise RuntimeError(f"[{agent_name}] API error: {type(e).__name__}: {e}") from e


# ── Agents ────────────────────────────────────────────────────────────────────
# Each agent receives the full accumulated `context` dict (agent memory),
# so later agents can reason about earlier agents' outputs.

def classifier_agent(
    bug_report: str, context: dict, run_log: dict
) -> ClassifierOutput:
    prompt = f"""You are a bug classifier. Analyze the bug report and return ONLY a valid JSON object.

Required keys:
- "severity": one of "P0", "P1", "P2"  (P0=critical crash, P1=major, P2=minor)
- "category": one of "crash", "perf", "ui", "logic"
- "affected_component": short string, e.g. "iOS Checkout", "Cart Service"

Bug report:
{bug_report}

Return ONLY the JSON object. No markdown fences, no explanation."""
    return call_agent("classifier", prompt, ClassifierOutput, run_log)


def enricher_agent(
    bug_report: str, context: dict, run_log: dict
) -> EnricherOutput:
    prompt = f"""You are a bug enrichment agent. Review the bug report and all prior triage context.

Pipeline context so far:
{json.dumps(context, indent=2)}

Return ONLY a valid JSON object with these keys:
- "is_duplicate": boolean — is this likely a known/duplicate bug?
- "similar_bugs": array of EXACTLY 2 realistic (but fake) bug report titles
- "confidence_score": float 0.0–1.0 — how confident are you in the classification?

Return ONLY the JSON object. No markdown fences, no explanation."""
    return call_agent("enricher", prompt, EnricherOutput, run_log)


def router_agent(context: dict, run_log: dict) -> RouterOutput:
    prompt = f"""You are a bug routing agent. Based on the full triage context, assign this bug to the right team.

Pipeline context so far:
{json.dumps(context, indent=2)}

Return ONLY a valid JSON object with these keys:
- "assigned_team": team name string, e.g. "iOS Team", "Backend Team", "QA Team"
- "slack_message": a single-line Slack notification summarizing bug + priority

Return ONLY the JSON object. No markdown fences, no explanation."""
    return call_agent("router", prompt, RouterOutput, run_log)


def judge_agent(context: dict, run_log: dict) -> JudgeOutput:
    prompt = f"""You are a quality judge reviewing an automated bug triage pipeline.

Full pipeline context:
{json.dumps(context, indent=2)}

Assess whether the overall triage is accurate and complete.
Return ONLY a valid JSON object with these keys:
- "passed": boolean — true if triage looks correct and actionable
- "flags": array of concern strings — use [] if no issues found

Return ONLY the JSON object. No markdown fences, no explanation."""
    return call_agent("judge", prompt, JudgeOutput, run_log)


# ── Pipeline orchestrator ─────────────────────────────────────────────────────

def run_pipeline(bug_report: str) -> dict:
    """
    Orchestrate the full 4-agent triage pipeline.

    Agent memory: a shared `context` dict grows after each agent completes,
    and is passed to every subsequent agent so they have full history.

    Returns the final context dict (used by both CLI and Streamlit UI).
    """
    run_log, log_path = setup_run_log()

    # Shared memory: starts with bug report, grows with each agent's output
    context: dict[str, Any] = {"bug_report": bug_report}

    print("=" * 60)
    print("BUG TRIAGE PIPELINE")
    print("=" * 60)
    print(f"\nBug Report:\n  {bug_report}\n")

    # Agent 1: Classifier
    print("-" * 40)
    print("AGENT 1: Classifier")
    classification = classifier_agent(bug_report, context, run_log)
    context["classification"] = classification.model_dump()
    print(json.dumps(context["classification"], indent=2))

    # Agent 2: Enricher (receives bug + classification)
    print("\n" + "-" * 40)
    print("AGENT 2: Enricher")
    enrichment = enricher_agent(bug_report, context, run_log)
    context["enrichment"] = enrichment.model_dump()
    print(json.dumps(context["enrichment"], indent=2))

    # Agent 3: Router (receives bug + classification + enrichment)
    print("\n" + "-" * 40)
    print("AGENT 3: Router")
    routing = router_agent(context, run_log)
    context["routing"] = routing.model_dump()
    print(json.dumps(context["routing"], indent=2))

    # Agent 4: Judge (receives everything)
    print("\n" + "-" * 40)
    print("AGENT 4: Judge")
    verdict = judge_agent(context, run_log)
    context["verdict"] = verdict.model_dump()
    print(json.dumps(context["verdict"], indent=2))

    # Summary
    print("\n" + "=" * 60)
    status = "PASSED" if verdict.passed else "FAILED"
    print(f"PIPELINE COMPLETE — {status}")
    if verdict.flags:
        print("Flags:")
        for flag in verdict.flags:
            print(f"  • {flag}")
    print("=" * 60)

    # Persist full run log to disk
    run_log["final_context"] = context
    save_run_log(run_log, log_path)
    print(f"\nLog saved → {log_path}")

    return context


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Multi-agent bug triage pipeline (Groq / Llama 3)"
    )
    parser.add_argument(
        "--bug",
        type=str,
        default=(
            "App crashes on iOS 17 when user taps the checkout button after adding "
            "3+ items to cart. Happens 100% of the time. Started after last Tuesday's release."
        ),
        help="The bug report text to triage (wrap in quotes)",
    )
    args = parser.parse_args()
    run_pipeline(args.bug)
