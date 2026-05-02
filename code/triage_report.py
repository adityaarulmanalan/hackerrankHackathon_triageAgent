"""Standalone triage report feature.

Does not modify the core agent.
Reads support_tickets/debug_output.csv or support_issues/debug_output.csv
and prints a judge-friendly summary of routing, risk, and output quality.

Run:
    python3 code/triage_report.py
"""

from __future__ import annotations

import csv
from pathlib import Path
from collections import Counter


ROOT = Path(__file__).resolve().parents[1]

SUPPORT_DIRS = [
    ROOT / "support_tickets",
    ROOT / "support_issues",
]

HIGH_RISK_TERMS = [
    "fraud",
    "phishing",
    "scam",
    "unauthorized",
    "identity theft",
    "chargeback",
    "legal",
    "privacy",
    "delete my data",
    "admin",
    "workspace",
    "permission",
    "seat",
    "infosec",
    "compliance",
    "security",
]

BAD_RESPONSE_TERMS = [
    "reference:",
    "article id",
    "source url",
    "```",
    "last updated",
    "breadcrumbs",
    "as an ai",
    "potential response",
]


def find_debug_csv() -> Path:
    for directory in SUPPORT_DIRS:
        path = directory / "debug_output.csv"
        if path.exists():
            return path
    raise FileNotFoundError("Could not find debug_output.csv. Run: python3 code/main.py run")


def read_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def has_any(text: str, terms: list[str]) -> bool:
    text = (text or "").lower()
    return any(term in text for term in terms)


def main() -> None:
    path = find_debug_csv()
    rows = read_rows(path)

    status_counts = Counter(row.get("status", "") for row in rows)
    request_counts = Counter(row.get("request_type", "") for row in rows)
    area_counts = Counter(row.get("product_area", "") for row in rows)

    high_risk_total = 0
    high_risk_escalated = 0
    suspicious_replies = []

    for i, row in enumerate(rows):
        ticket_text = f"{row.get('subject', '')} {row.get('issue', '')}"
        response = row.get("response", "")

        if has_any(ticket_text, HIGH_RISK_TERMS):
            high_risk_total += 1
            if row.get("status") == "escalated":
                high_risk_escalated += 1
            else:
                suspicious_replies.append((i, "High-risk ticket was replied"))

        if row.get("status") == "replied" and has_any(response, BAD_RESPONSE_TERMS):
            suspicious_replies.append((i, "Response contains metadata/bad AI phrase"))

        if row.get("status") == "replied" and len(response) > 650:
            suspicious_replies.append((i, "Response may be too long"))

        if row.get("status") == "replied" and len(response) < 25:
            suspicious_replies.append((i, "Response may be too short"))

    print("\n=== TRIAGE REPORT ===")
    print(f"File: {path}")
    print(f"Rows: {len(rows)}")

    print("\nStatus distribution:")
    for key, value in status_counts.items():
        print(f"  {key}: {value}")

    print("\nRequest type distribution:")
    for key, value in request_counts.items():
        print(f"  {key}: {value}")

    print("\nTop product areas:")
    for key, value in area_counts.most_common(8):
        print(f"  {key}: {value}")

    print("\nRisk handling:")
    print(f"  High-risk tickets detected: {high_risk_total}")
    print(f"  High-risk tickets escalated: {high_risk_escalated}")

    if suspicious_replies:
        print("\nPotential issues:")
        for row_num, reason in suspicious_replies[:20]:
            print(f"  Row {row_num}: {reason}")
    else:
        print("\nPotential issues: none found")

    print("\nInterview talking point:")
    print(
        "This report is an observability feature. It does not affect predictions; "
        "it helps audit safety, routing balance, and response quality after a run."
    )


if __name__ == "__main__":
    main()