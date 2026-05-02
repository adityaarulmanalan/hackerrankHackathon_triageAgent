from __future__ import annotations
from dataclasses import dataclass
from classifier import Classification
from retrieval import RetrievalResult
from config import MIN_REPLY_SCORE

@dataclass
class RouteDecision:
    status: str
    reason: str
    safe_guidance: str = ""

def has(text: str, terms: list[str]) -> bool:
    text=text.lower(); return any(t in text for t in terms)

HIGH_RISK=["identity theft","stolen identity","fraud","unauthorized","chargeback","scam","phishing","legal","lawsuit","privacy request","delete my data","cheating","plagiarism","candidate dispute"]
SECURITY_COMPLIANCE=["infosec","security questionnaire","security form","compliance form","vendor form","fill in the forms","fill out the forms"]
ADMIN=["restore access","lost access","removed my seat","workspace owner","workspace admin","admin","owner","permission","seat"]
SESSION=["session timeout","timed out","inactivity","kicked out","sent back to the hr lobby"]

def route(issue: str, subject: str, classification: Classification, retrieved: list[RetrievalResult], confidence: dict) -> RouteDecision:
    text=f"{subject} {issue}".lower()
    if classification.request_type == "invalid":
        return RouteDecision("replied","The request is invalid or outside supported support domains.")
    if has(text,HIGH_RISK):
        return RouteDecision("escalated","Sensitive security, privacy, legal, fraud, or payment-risk issue requires human review.","For urgent card or account safety, contact the issuer or official support channel.")
    if has(text,SECURITY_COMPLIANCE):
        return RouteDecision("escalated","Security, compliance, vendor, or infosec form requests require human support review.")
    if has(text,ADMIN):
        return RouteDecision("escalated","Account, workspace, admin, seat, or permission changes require human support review.")
    if has(text,SESSION):
        return RouteDecision("escalated","Session timeout or inactivity behavior requires support review.")
    if classification.company == "None":
        return RouteDecision("escalated","The company or support domain is unclear.")
    if classification.request_type == "feature_request":
        return RouteDecision("escalated","Feature requests require product or support-team review.")
    if classification.request_type == "bug":
        return RouteDecision("escalated","Bug, outage, error, or platform failure requires investigation by support.")
    if not retrieved:
        return RouteDecision("escalated","No relevant local documentation was found.")
    top_score=confidence.get("top_score",0.0); overlap=confidence.get("overlap",0.0)
    if top_score < MIN_REPLY_SCORE:
        return RouteDecision("escalated",f"Low retrieval confidence ({top_score}) makes a direct answer unsafe.")
    if overlap < 0.02 and top_score < 30:
        return RouteDecision("escalated","Retrieved evidence does not overlap enough with the ticket to answer safely.")
    return RouteDecision("replied",f"Relevant local documentation supports a direct answer (score {top_score}).")
