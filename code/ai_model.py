from __future__ import annotations
import json, os, re, urllib.request
from utils import strip_markdown, keyword_overlap

OLLAMA_URL=os.getenv("OLLAMA_URL","http://localhost:11434/api/generate")
OLLAMA_MODEL=os.getenv("OLLAMA_MODEL","llama3.2:3b")

def enabled() -> bool:
    return os.getenv("USE_LOCAL_AI","0") == "1"

def allow_steps(ticket: str) -> bool:
    t=ticket.lower()
    return any(w in t for w in ["how","steps","step-by-step","reinvite","delete","update","change","add","remove","configure","set up","setup"])

def clean_step(s: str) -> str:
    s=re.sub(r"\b\d{5,}\b"," ",str(s)); s=re.sub(r"^[\s\-•0-9.]+","",s); return re.sub(r"\s+"," ",s).strip()

def validate(parsed: object, evidence: str, ticket: str) -> dict | None:
    if not isinstance(parsed, dict): return None
    direct=str(parsed.get("direct_answer","")).strip()
    steps=parsed.get("steps",[]); warning=str(parsed.get("warning","")).strip()
    if not direct: return None
    if len(direct.split()) > 45: direct=" ".join(direct.split()[:45]).rstrip(",;")+"."
    bad=["as an ai","potential response","outside the evidence","according to my knowledge","i cannot verify","source:","path:"]
    joined=(direct+" "+" ".join(steps if isinstance(steps,list) else [])+" "+warning).lower()
    if any(b in joined for b in bad): return None
    if keyword_overlap(direct, evidence+" "+ticket) < 0.08 and "escalated" not in direct.lower(): return None
    clean_steps=[]
    if isinstance(steps,list) and allow_steps(ticket):
        for st in steps:
            st=clean_step(st)
            if len(st.split()) >= 3:
                clean_steps.append(" ".join(st.split()[:28]).rstrip(",;"))
    return {"direct_answer":direct,"steps":clean_steps[:4],"warning":warning}

def ask_local_ai(ticket_text: str, company: str, product_area: str, retrieved_docs: list) -> dict | None:
    if not enabled() or not retrieved_docs: return None
    blocks=[]
    for r in retrieved_docs[:2]:
        blocks.append(f"TITLE: {r.document.title}\nTEXT:\n{strip_markdown(r.chunk)[:900]}")
    evidence="\n---\n".join(blocks)
    prompt=f"""
You are a strict evidence extractor for support triage. Use only the evidence.
Return ONLY valid JSON: {{"direct_answer":"...","steps":["..."],"warning":""}}
Rules:
- direct_answer is ONE short sentence answering the user directly.
- steps must be empty unless ALLOW_STEPS is true.
- do not invent policies, links, phone numbers, metadata, IDs, or article titles.
- if evidence is insufficient, direct_answer must be: This should be escalated to support for review.
ALLOW_STEPS: {str(allow_steps(ticket_text)).lower()}
Company: {company}
Product area: {product_area}
Ticket: {ticket_text}
Evidence: {evidence}
"""
    payload={"model":OLLAMA_MODEL,"prompt":prompt,"stream":False,"format":"json","options":{"temperature":0,"top_p":0.1,"num_predict":120}}
    req=urllib.request.Request(OLLAMA_URL,data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"},method="POST")
    try:
        with urllib.request.urlopen(req,timeout=30) as resp:
            raw=json.loads(resp.read().decode()).get("response","")
        return validate(json.loads(raw), evidence, ticket_text)
    except Exception:
        return None
