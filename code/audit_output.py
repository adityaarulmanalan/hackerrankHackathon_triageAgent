from __future__ import annotations
import csv, re
from config import OUTPUT_FILE, DEBUG_OUTPUT_FILE, OUTPUT_COLUMNS
VALID_STATUS={"replied","escalated"}; VALID_REQUEST={"product_issue","feature_request","bug","invalid"}
BAD=["as an ai","potential response","source_url","title_slug","article_id","breadcrumbs","outside the evidence"]
HIGH=["identity theft","fraud","unauthorized","phishing","scam","chargeback","legal","workspace","admin","permission","infosec","compliance"]
BUG=["site is down","not accessible","bug","error","crash","broken","not loading","unable to","blocker"]

def load(path):
    with open(path,newline="",encoding="utf-8") as f: return list(csv.DictReader(f))

def audit() -> int:
    if not OUTPUT_FILE.exists(): print("❌ output.csv missing"); return 1
    rows=load(OUTPUT_FILE); ok=True
    print("OFFICIAL OUTPUT CHECK\n---------------------")
    if not rows: print("❌ output.csv empty"); return 1
    cols=list(rows[0].keys())
    if cols != OUTPUT_COLUMNS: print("❌ wrong columns", cols); ok=False
    else: print("✅ Correct 5-column schema")
    print(f"Rows: {len(rows)}\n")
    source=DEBUG_OUTPUT_FILE if DEBUG_OUTPUT_FILE.exists() else OUTPUT_FILE
    rows=load(source)
    print("NEAR-JUDGE AUDIT\n----------------")
    flagged=[]
    for i,r in enumerate(rows):
        probs=[]; resp=r.get("response",""); status=r.get("status","").lower(); req=r.get("request_type","").lower()
        text=f"{r.get('subject','')} {r.get('issue','')}".lower()
        if status not in VALID_STATUS: probs.append("bad status")
        if req not in VALID_REQUEST: probs.append("bad request_type")
        if len(resp.split()) < 6: probs.append("response too short")
        if len(resp.split()) > 120: probs.append("response too long")
        if any(b in resp.lower() for b in BAD): probs.append("bad/generated noise")
        if source == DEBUG_OUTPUT_FILE:
            if any(x in text for x in HIGH) and status != "escalated": probs.append("high-risk not escalated")
            if any(x in text for x in BUG) and status != "escalated": probs.append("bug-like not escalated")
        if probs: flagged.append((i,probs,r))
    if not flagged: print("✅ No obvious judge-risk issues found."); return 0 if ok else 1
    print(f"⚠️ Rows needing review: {len(flagged)}")
    for i,probs,r in flagged:
        print("="*80); print("ROW",i,"|", "; ".join(probs)); print("Subject:",r.get("subject","") or r.get("Subject","")); print("Issue:",r.get("issue","") or r.get("Issue","")); print("Prediction:", {k:r.get(k,"") for k in OUTPUT_COLUMNS})
    return 1 if not ok else 0

if __name__ == "__main__": raise SystemExit(audit())
