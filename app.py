"""
Streamlit Web UI — Multi-Agent Bug Triage Pipeline
----------------------------------------------------
Paste a bug report, click Run, and watch 4 AI agents
triage it in real time.

Run with:
  streamlit run app.py
"""

import json
import streamlit as st
from pipeline import (
    classifier_agent,
    enricher_agent,
    router_agent,
    judge_agent,
    setup_run_log,
    save_run_log,
)

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Bug Triage Agent",
    page_icon="🐛",
    layout="centered",
)

# ── Header ────────────────────────────────────────────────────────────────────

st.title("🐛 Multi-Agent Bug Triage Pipeline")
st.caption(
    "Powered by **Groq (Llama 3)** · 4 AI agents · "
    "Pydantic validation · Retry logic · Agent memory"
)
st.divider()

# ── Input ─────────────────────────────────────────────────────────────────────

SAMPLE = (
    "App crashes on iOS 17 when user taps the checkout button after adding "
    "3+ items to cart. Happens 100% of the time. Started after last Tuesday's release."
)

bug_report = st.text_area(
    "**Paste your bug report:**",
    height=130,
    placeholder=SAMPLE,
)

col1, col2 = st.columns([1, 4])
with col1:
    run = st.button("▶ Run Pipeline", type="primary", disabled=not bug_report.strip())
with col2:
    if st.button("Load sample"):
        bug_report = SAMPLE
        st.rerun()

# ── Pipeline execution ────────────────────────────────────────────────────────

if run and bug_report.strip():
    run_log, log_path = setup_run_log()
    context: dict = {"bug_report": bug_report}

    st.divider()
    st.subheader("Pipeline Output")

    # ── Agent 1: Classifier ──────────────────────────────────────────────────
    with st.status("🔍 Agent 1: Classifier — analyzing severity & category...", expanded=True) as s:
        try:
            classification = classifier_agent(bug_report, context, run_log)
            context["classification"] = classification.model_dump()
            s.update(label="🔍 Agent 1: Classifier ✅", state="complete")
        except RuntimeError as e:
            s.update(label="🔍 Agent 1: Classifier ❌", state="error")
            st.error(str(e))
            st.stop()

    with st.expander("Classifier output", expanded=True):
        st.json(context["classification"])

    # ── Agent 2: Enricher ────────────────────────────────────────────────────
    with st.status("🔎 Agent 2: Enricher — checking for duplicates...", expanded=True) as s:
        try:
            enrichment = enricher_agent(bug_report, context, run_log)
            context["enrichment"] = enrichment.model_dump()
            s.update(label="🔎 Agent 2: Enricher ✅", state="complete")
        except RuntimeError as e:
            s.update(label="🔎 Agent 2: Enricher ❌", state="error")
            st.error(str(e))
            st.stop()

    with st.expander("Enricher output", expanded=True):
        st.json(context["enrichment"])

    # ── Agent 3: Router ──────────────────────────────────────────────────────
    with st.status("📬 Agent 3: Router — assigning team...", expanded=True) as s:
        try:
            routing = router_agent(context, run_log)
            context["routing"] = routing.model_dump()
            s.update(label="📬 Agent 3: Router ✅", state="complete")
        except RuntimeError as e:
            s.update(label="📬 Agent 3: Router ❌", state="error")
            st.error(str(e))
            st.stop()

    with st.expander("Router output", expanded=True):
        st.json(context["routing"])

    # ── Agent 4: Judge ───────────────────────────────────────────────────────
    with st.status("⚖️ Agent 4: Judge — reviewing pipeline quality...", expanded=True) as s:
        try:
            verdict = judge_agent(context, run_log)
            context["verdict"] = verdict.model_dump()
            s.update(label="⚖️ Agent 4: Judge ✅", state="complete")
        except RuntimeError as e:
            s.update(label="⚖️ Agent 4: Judge ❌", state="error")
            st.error(str(e))
            st.stop()

    with st.expander("Judge output", expanded=True):
        st.json(context["verdict"])

    # ── Final verdict ────────────────────────────────────────────────────────
    st.divider()
    if verdict.passed:
        st.success("✅ Triage **passed** — all agents agree, no concerns raised.")
    else:
        st.error("❌ Triage **flagged** — review concerns below.")

    if verdict.flags:
        st.warning("**Flags raised by Judge:**\n" + "\n".join(f"- {f}" for f in verdict.flags))

    # Slack message callout
    st.info(f"📣 **Slack message:** {routing.slack_message}")

    # ── Save log ─────────────────────────────────────────────────────────────
    run_log["final_context"] = context
    save_run_log(run_log, log_path)
    st.caption(f"Run log saved → `{log_path}`")
