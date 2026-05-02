from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
from utils import clean_text, contains_any

@dataclass
class Classification:
    issue: str
    subject: str
    company: str
    request_type: str
    product_area: str
    signals: dict[str, bool]
    def to_dict(self) -> dict[str, Any]: return asdict(self)

def infer_company(issue: str, subject: str, company: str) -> str:
    raw=clean_text(company)
    if raw in {"HackerRank","Claude","Visa"}: return raw
    text=f"{subject} {issue}".lower()
    if contains_any(text,["claude","anthropic"]): return "Claude"
    if contains_any(text,["hackerrank","assessment","candidate","test","interview","hiring","infosec","security questionnaire","compliance form"]): return "HackerRank"
    if contains_any(text,["visa","card","merchant","chargeback","identity theft","stolen identity","fraud","unauthorized","traveller","traveler","cheque"]): return "Visa"
    return "None"

def infer_request_type(issue: str, subject: str) -> str:
    text=f"{subject} {issue}".lower().strip()
    if len(text) < 8: return "invalid"
    if text in {"thank you", "thanks", "ok thanks", "thank you for helping me"}: return "invalid"
    if contains_any(text,["who is","actor in","iron man","recipe","ignore previous","system prompt"]): return "invalid"
    if contains_any(text,["feature request","please add","can you add","would like to request","i wish","enhancement"]): return "feature_request"
    if contains_any(text,["site is down","none of the pages are accessible","bug","error","crash","broken","not loading","failed","failure","unable to","not accessible","doesn't work","does not work","blocker","still showing error"]): return "bug"
    return "product_issue"

def infer_product_area(subject: str, issue: str, company: str, best_doc=None) -> str:
    text = f"{subject} {issue}".lower()

    if best_doc is not None:
        doc_text = f"{getattr(best_doc, 'title', '')} {getattr(best_doc, 'path', '')}".lower()
        text = f"{text} {doc_text}"

    # MUST come before Claude team/enterprise rules
    if company == "Claude" and any(x in text for x in [
        "crawl", "crawler", "crawling", "robots", "robots.txt", "website data", "web data"
    ]):
        return "privacy_and_legal"
    if company == "Visa":
        if contains_any(text,["identity theft","stolen identity","fraud","unauthorized","scam","phishing","lost","stolen"]): return "fraud_and_lost_cards"
        if contains_any(text,["transaction","merchant","charge","payment","dispute","chargeback"]): return "transactions_and_disputes"
        if contains_any(text,["travel","traveller","traveler","cheque","cheques"]): return "travel_support"
        return "visa_support"
    if company == "Claude":
        if contains_any(text,["workspace","team","seat","admin","owner","member","enterprise"]): return "team_and_enterprise"
        if contains_any(text,["api","console","key","rate limit","claude code","mcp","usage","credits"]): return "api_and_console"
        if contains_any(text,["privacy","data","delete","legal","crawler","robots","crawl"]): return "privacy_and_legal"
        if contains_any(text,["billing","invoice","subscription","refund","payment","plan","charged"]): return "billing"
        if company == "Claude":
                if contains_any(text, ["crawl", "crawler", "crawling", "robots", "robots.txt", "web data", "website data"]):
                    return "privacy_and_legal"

    if contains_any(text, ["privacy", "data", "delete my data", "legal"]):
        return "privacy_and_legal"

    if contains_any(text, ["workspace", "team", "seat", "admin", "owner", "member", "enterprise"]):
        return "team_and_enterprise"
        return "claude_support"
    if company == "HackerRank":
        if contains_any(text,["infosec","compliance","security questionnaire","vendor form","forms"]): return "security_compliance"
        if contains_any(text,["assessment","candidate","test","webcam","camera","proctor","screen","inactivity","session","timeout","invite"]): return "screen"
        if contains_any(text,["interview","lobby","interviewer"]): return "interviews"
        if contains_any(text,["billing","invoice","subscription","refund","payment","plan","charged"]): return "billing"
        if contains_any(text,["community","certificate","profile","account","login","password"]): return "community"
        return "hackerrank_support"
    return "out_of_scope"

def classify(issue: str, subject: str, company: str) -> Classification:
    issue=clean_text(issue); subject=clean_text(subject); company=infer_company(issue,subject,company)
    request_type=infer_request_type(issue,subject)
    area=infer_product_area(subject,issue,company)
    return Classification(issue,subject,company,request_type,area,{"unknown_company":company=="None","bug":request_type=="bug","invalid":request_type=="invalid"})
