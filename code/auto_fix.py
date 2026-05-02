"""Conservative post-processing safety pass.

It only fixes clearly bad rows and writes back to output.csv.
"""
from __future__ import annotations

import csv

from config import OUTPUT_COLUMNS, OUTPUT_CSV


BAD_TERMS = [
    "article id",
    "source url",
    "reference:",
    "breadcrumbs",
    "```",
    "---",
    "test cases",
    "sample template",
]


def _clean_response(resp: str) -> str:
    resp = " ".join((resp or "").split())
    parts = [p.strip() for p in resp.split(".") if p.strip()]
    resp = ". ".join(parts[:2]).strip()
    if resp and not resp.endswith("."):
        resp += "."
    return resp[:360]


def _is_bad(resp: str) -> bool:
    low = (resp or "").lower()
    return any(t in low for t in BAD_TERMS) or len(resp) > 700


def main() -> int:
    if not OUTPUT_CSV.exists():
        print(f"Auto-fix skipped: missing {OUTPUT_CSV}")
        return 0

    with open(OUTPUT_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    fixed = []
    changed = 0

    for row in rows:
        if row.get("status") == "replied":
            response = row.get("response", "")
            if _is_bad(response):
                row["status"] = "escalated"
                row["response"] = "This needs support review because the extracted response was not clean or safe enough for a direct answer."
                row["justification"] = "Response quality was insufficient for a safe direct reply."
                changed += 1
            else:
                cleaned = _clean_response(response)
                if cleaned != response:
                    row["response"] = cleaned
                    changed += 1

        fixed.append(row)

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in fixed:
            writer.writerow({c: row.get(c, "") for c in OUTPUT_COLUMNS})

    print(f"Auto-fix updated output.csv; changed rows: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())