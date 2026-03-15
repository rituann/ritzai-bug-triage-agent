import anthropic
import json

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-6"


def classifier_agent(bug_report: str) -> dict:
    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": f"""You are a bug classifier. Analyze this bug report and return ONLY valid JSON with these exact keys:
- severity: one of P0, P1, P2
- category: one of crash, perf, ui, logic
- affected_component: short string naming the component

Bug report: {bug_report}

Respond ONLY with JSON, no extra text.""",
            }
        ],
    )
    return json.loads(response.content[0].text)


def enricher_agent(bug_report: str, classification: dict) -> dict:
    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": f"""You are a bug enrichment agent. Given a bug report and its classification, return ONLY valid JSON with these exact keys:
- is_duplicate: boolean
- similar_bugs: list of exactly 2 fake but realistic bug titles (strings)
- confidence_score: float between 0 and 1

Bug report: {bug_report}
Classification: {json.dumps(classification)}

Respond ONLY with JSON, no extra text.""",
            }
        ],
    )
    return json.loads(response.content[0].text)


def router_agent(classification: dict, enrichment: dict) -> dict:
    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": f"""You are a bug routing agent. Based on classification and enrichment data, return ONLY valid JSON with these exact keys:
- assigned_team: team name string (e.g. "iOS Team", "Backend Team", "QA Team")
- slack_message: one-line Slack notification string summarizing the bug and its priority

Classification: {json.dumps(classification)}
Enrichment: {json.dumps(enrichment)}

Respond ONLY with JSON, no extra text.""",
            }
        ],
    )
    return json.loads(response.content[0].text)


def judge_agent(
    bug_report: str,
    classification: dict,
    enrichment: dict,
    routing: dict,
) -> dict:
    all_outputs = {
        "bug_report": bug_report,
        "classification": classification,
        "enrichment": enrichment,
        "routing": routing,
    }
    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": f"""You are a quality judge agent. Review all pipeline outputs and return ONLY valid JSON with these exact keys:
- passed: boolean — true if the triage looks accurate and complete
- flags: list of concern strings (empty list if none)

All pipeline outputs: {json.dumps(all_outputs, indent=2)}

Respond ONLY with JSON, no extra text.""",
            }
        ],
    )
    return json.loads(response.content[0].text)


def run_pipeline(bug_report: str) -> None:
    print("=" * 60)
    print("BUG TRIAGE PIPELINE")
    print("=" * 60)
    print(f"\nBug Report:\n  {bug_report}\n")

    print("-" * 40)
    print("AGENT 1: Classifier")
    classification = classifier_agent(bug_report)
    print(json.dumps(classification, indent=2))

    print("\n" + "-" * 40)
    print("AGENT 2: Enricher")
    enrichment = enricher_agent(bug_report, classification)
    print(json.dumps(enrichment, indent=2))

    print("\n" + "-" * 40)
    print("AGENT 3: Router")
    routing = router_agent(classification, enrichment)
    print(json.dumps(routing, indent=2))

    print("\n" + "-" * 40)
    print("AGENT 4: Judge")
    verdict = judge_agent(bug_report, classification, enrichment, routing)
    print(json.dumps(verdict, indent=2))

    print("\n" + "=" * 60)
    print(f"PIPELINE COMPLETE — Passed: {verdict['passed']}")
    if verdict["flags"]:
        print("Flags:")
        for flag in verdict["flags"]:
            print(f"  • {flag}")
    print("=" * 60)


if __name__ == "__main__":
    bug_report = (
        "App crashes on iOS 17 when user taps the checkout button after adding "
        "3+ items to cart. Happens 100% of the time. Started after last Tuesday's release."
    )
    run_pipeline(bug_report)
