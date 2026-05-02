from __future__ import annotations
import re
from collections import Counter

from ai_model import ask_local_ai
from router import RouteDecision
from retrieval import RetrievalResult
from utils import keyword_overlap, sentence_split, strip_markdown, tokenize, clean_text

ACTION = {
    "click", "select", "open", "go", "update", "set", "enable", "disable",
    "contact", "submit", "download", "delete", "remove", "change", "choose",
    "enter", "navigate", "report",
}

VERB_HINT = {
    "is", "are", "was", "were", "be", "been", "can", "could", "will", "would",
    "must", "should", "may", "might", "do", "does", "did", "have", "has", "had",
    "use", "using", "click", "go", "see", "find", "need", "want", "try", "contact",
    "visit", "open", "set", "allow", "block", "configure", "control", "include",
    "remain", "expire", "access", "delete", "remove", "update", "create", "send",
    "get", "show", "help", "support", "works", "work", "take", "make", "give",
    "keep", "leave", "turn", "sign", "log", "pay", "buy", "cancel", "refund",
}

CLAUDE_ROBOTS_REPLY = (
    "You can control Claude's web crawling by configuring your site's robots.txt "
    "to allow or block Anthropic's crawlers."
)

SAFETY_FALLBACK_MSG = (
    "This request requires support assistance as it is not clearly covered by "
    "the available documentation."
)

GENERIC_REPLY_MARKERS = (
    "needs investigation beyond",
    "cannot be resolved via documentation",
    "beyond public documentation",
    "beyond documentation",
    "cannot be resolved from documentation",
)

GERUND_TO_VERB = {
    "updating": "update",
    "changing": "change",
    "managing": "manage",
    "setting": "set",
    "removing": "remove",
    "adding": "add",
    "deleting": "delete",
}

BILLING_SUBSCRIPTION_FALLBACK = (
    "You can pause your subscription from the billing settings in your account."
)

GENERAL_QUALITY_FALLBACK = (
    "You can manage this request from the relevant settings in your account or "
    "contact support if the option is not available."
)

# Prefer grounded sentences that read like actionable instructions.
INSTRUCTION_VERB_PHRASES = ("click", "go to", "update", "contact", "manage")

# Incomplete UI fragments / dangling imperatives (response ends like this → invalid).
ABRUPT_END_PHRASES = (
    "click the",
    "click a",
    "go to",
    "open the",
    "visit the",
    "tap the",
    "choose the",
    "select the",
    "select",
)

BILLING_SUBSCRIPTION_TERMS = (
    "subscription",
    "billing",
    "invoice",
    "payment",
    "credit card",
    "pause",
    "cancel plan",
    "renew",
    "charge",
    "refund",
    "plan",
    "stripe",
    "upgrade",
    "downgrade",
)


def cleanup_response_text(s: str) -> str:
    """Strip documentation cruft: separators, metadata, IDs, markup; normalize space."""
    if not s:
        return ""
    t = str(s)
    # Strip reference labels (numeric IDs) without removing following prose on the same line.
    t = re.sub(r"(?i)\breference\s*:\s*\d+\s*", " ", t)
    t = re.sub(r"(?im)^\s*reference\s*:\s*\S+\s*$", " ", t)
    t = re.sub(r"[-_=]{4,}", " ", t)
    t = re.sub(r"(?im)^\s*[-–—=*_]{2,}\s*$", " ", t)
    t = re.sub(r"(?i)last\s+updated[^\n.!?]*", " ", t)
    t = re.sub(r"(?i)\barticle\s*(?:id|#)?\s*:?\s*\d+", " ", t)
    t = re.sub(r"\b\d{5,}\b", " ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"```[\s\S]*?```", " ", t)
    t = re.sub(r"`+", " ", t)
    t = re.sub(r"(?m)^\s{0,3}#{1,6}\s+.+$", " ", t)
    t = re.sub(r"\[[^\]]+\]\([^)]+\)", " ", t)
    t = clean_text(t)
    return t


def _ticket_is_safety_reporting(ticket: str) -> bool:
    t = clean_text(ticket).lower()
    return any(
        x in t
        for x in (
            "safety",
            "usersafety",
            "report abuse",
            "trust and safety",
            "harmful",
            "illegal content",
            "csam",
            "child safety",
        )
    )


def _strip_irrelevant_emails(text: str, ticket: str) -> str:
    """Remove usersafety@... unless the ticket is actually about safety reporting."""
    safety_ok = _ticket_is_safety_reporting(ticket)

    def repl(m: re.Match[str]) -> str:
        addr = m.group(0).lower()
        if "usersafety" in addr:
            return m.group(0) if safety_ok else " "
        return m.group(0)

    return re.sub(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", repl, text)


def _strip_fused_doc_title_prefix(t: str) -> str:
    """Remove heading text merged onto the same line as the first real sentence (common in stripped MD)."""
    if not t:
        return t
    return re.sub(
        r"(?i)^(Updating|Changing|Managing|Setting|Removing|Adding|Deleting)\s+"
        r"(?:[A-Za-z][a-z]*\s+){1,7}(?=(?:You|We|If|When|To|This|That|Our|Please)\s)",
        "",
        t.strip(),
    )


def _looks_like_doc_heading(s: str) -> bool:
    """Standalone doc titles without real sentence punctuation (e.g. 'Updating credit card information')."""
    s = s.strip()
    if not s or len(s) > 100:
        return False
    if s[-1] in ".!?":
        return False
    words = s.split()
    if len(words) < 2 or len(words) > 14:
        return False
    low = {w.lower() for w in words}
    if VERB_HINT & low:
        return False
    starters = ("you ", "we ", "if ", "when ", "to ", "this ", "that ", "our ", "please ", "for ")
    if s[:6].lower().startswith(starters) or s[:4].lower().startswith(("the ", "a ")):
        return False
    return True


def _clean_response(text: str, ticket: str = "") -> str:
    """Final pass: support-style reply text only — no doc metadata, noise emails, or title lines."""
    if not text:
        return ""
    t = cleanup_response_text(text)
    t = _strip_fused_doc_title_prefix(t)
    t = _strip_irrelevant_emails(t, ticket)
    t = re.sub(r"\S*cdn-cgi/email-protection\S*", "support team", t, flags=re.I)
    t = re.sub(r"\[email protected\][^\s]*", "support team", t, flags=re.I)
    t = re.sub(r"(?i)\b(?:doc|document|section)\s+id\s*:?\s*\d+", " ", t)
    t = re.sub(r"(?i)\bsource_url\b[^\s.,!?]*", " ", t)
    t = re.sub(r"(?i)\btitle_slug\b[^\s.,!?]*", " ", t)
    t = clean_text(t)
    if len(t) > 25:
        parts = sentence_split(t)
        if parts:
            kept = [p for p in parts if not _looks_like_doc_heading(p)]
            t = " ".join(kept) if kept else ""
    t = clean_text(t)
    return t


def limit_to_sentences(text: str, max_sentences: int = 2) -> str:
    c = _clean_response(text, "")
    parts = sentence_split(c)
    if not parts:
        rough = [p.strip() for p in re.split(r"(?<=[.!?])\s+", c) if len(p.strip()) > 10]
        parts = rough[:max_sentences]
        if parts:
            return _clean_response(" ".join(parts), "")
        return c[:400].strip() if c else ""
    out = " ".join(parts[:max_sentences]).strip()
    return _clean_response(out, "")


def shares_meaningful_terms_with_ticket(ticket: str, response: str) -> bool:
    tt = set(tokenize(ticket))
    rt = set(tokenize(response))
    overlap = tt & rt
    if len(overlap) >= 2:
        return True
    if len(overlap) == 1:
        w = next(iter(overlap))
        return len(w) >= 4
    return False


def ticket_response_overlap_ok(ticket: str, response: str) -> bool:
    """Stricter grounding: token overlap plus normalized overlap score."""
    if not response.strip():
        return False
    if not shares_meaningful_terms_with_ticket(ticket, response):
        return False
    ko = keyword_overlap(ticket, response)
    if ko < 0.06 and len(tokenize(ticket)) >= 4:
        return False
    return True


def _split_sentences_loose(text: str) -> list[str]:
    if not text or not str(text).strip():
        return []
    parts = re.split(r"(?<=[.!?])\s+|\n+", str(text).strip())
    out = [p.strip(" -•\t") for p in parts if p.strip()]
    return out if out else [str(text).strip()]


def _fix_merged_sentence_boundaries(text: str) -> str:
    if not text.strip():
        return text
    t = text.strip()
    # Likely two sentences run together: "...issue Visit..." → "...issue. Visit..."
    return re.sub(r"([a-z])\s+([A-Z][a-z]{2,})\b", r"\1. \2", t)


def _capitalize_sentences(text: str) -> str:
    if not text.strip():
        return text
    parts = _split_sentences_loose(text)
    capped = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        capped.append(p[0].upper() + p[1:] if len(p) > 1 else p.upper())
    return " ".join(capped)


def _dedupe_sentences(sentences: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for s in sentences:
        key = re.sub(r"\s+", " ", s.lower().strip())[:120]
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(s.strip())
    return out


def _finalize_support_response(text: str, ticket: str = "") -> str:
    """Dedupe phrasing, fix run-ons, trim to two sentences, normalize capitalization."""
    if not text.strip():
        return ""
    t = _clean_response(text, ticket)
    t = _fix_merged_sentence_boundaries(t)
    sents = _dedupe_sentences(_split_sentences_loose(t))
    sents = sents[:2]
    t = " ".join(sents)
    t = _clean_response(t, ticket)
    t = _capitalize_sentences(t)
    return t.strip()


def _reframe_to_support_tone(text: str) -> str:
    """Nudge replies toward natural support wording (e.g. You can … by …)."""
    if not text.strip():
        return text
    t = text.strip()
    low = t.lower()
    if low.startswith("you can "):
        return t
    base = t.rstrip(".!?").strip()
    visit_m = re.match(r"(?i)^visit\s+(.+)$", base)
    if visit_m:
        rest = visit_m.group(1).strip()
        if rest:
            return f"You can get help by visiting {rest}."
    first, rest = _first_sentence_rest(t)
    gm = re.match(
        r"(?i)^(Updating|Changing|Managing|Setting|Removing|Adding|Deleting)\s+(.+)$",
        first.strip(),
    )
    if gm:
        g = gm.group(1).lower()
        body = gm.group(2).strip()
        verb = GERUND_TO_VERB.get(g)
        if verb:
            tail = f" {rest}".rstrip() if rest else ""
            combined = f"You can {verb} {body}".strip()
            if combined[-1:] not in ".!?":
                combined += "."
            return (combined + tail).strip()
    return t


def _first_sentence_rest(text: str) -> tuple[str, str]:
    m = re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)
    first = m[0].strip()
    rest = m[1].strip() if len(m) > 1 else ""
    return first, rest


def _extraction_line_is_headingish(s: str) -> bool:
    """Skip doc titles / merged headings (e.g. 'Pause Subscription -'), very short fragments."""
    s = s.strip()
    if not s:
        return True
    if " - " in s:
        return True
    if re.match(r"(?i)^[A-Za-z0-9][A-Za-z0-9\s]{0,80}\s-\s*$", s):
        return True
    if len(s) < 18:
        return True
    return False


def _instruction_verb_overlap_score(sent: str) -> int:
    sl = sent.lower()
    score = 0
    if "go to" in sl:
        score += 4
    for ph in ("click", "update", "contact", "manage"):
        if ph in sl:
            score += 3
    return min(score, 9)


def _has_heading_or_title_fragment(text: str) -> bool:
    if " - " in text:
        return True
    t = text.strip()
    if re.search(r"\s-\s*$", t):
        return True
    return bool(re.search(r"(?i)^\s*[A-Za-z][A-Za-z\s]{2,40}\s-\s*", t))


def _ends_abruptly(text: str) -> bool:
    t = text.lower().rstrip('.!?)\'"]').strip()
    if not t:
        return True

    for phrase in ABRUPT_END_PHRASES:
        if t.endswith(phrase):
            return True

    words = t.split()
    if not words:
        return True

    last = words[-1]

    # Always invalid if it ends on a dangling connector/preposition.
    if last in {
        "as", "the", "a", "an", "to", "by", "for", "and", "or", "of",
        "with", "from", "in", "on", "at", "select", "click", "choose"
    }:
        return True

    return False


def _forms_complete_sentence(text: str) -> bool:
    t = text.strip()
    if not t:
        return False

    if _ends_abruptly(t):
        return False

    if t[-1] in ".!?":
        return True

    if len(t) >= 2 and t[-1] in '"\'' and t[-2] in ".!?":
        return True

    return False


def _response_extract_quality_invalid(response: str) -> bool:
    """True if extracted/final reply is a fragment, heading merge, or abrupt UI stub."""
    if not response.strip():
        return True
    words = response.split()
    if len(words) < 6:
        return True
    if _has_heading_or_title_fragment(response):
        return True
    if _ends_abruptly(response):
        return True
    if not _forms_complete_sentence(response):
        return True
    return False


def _is_billing_or_subscription_issue(issue: str) -> bool:
    t = clean_text(issue).lower()
    return any(x in t for x in BILLING_SUBSCRIPTION_TERMS)


def _quality_fallback_for_issue(issue: str) -> str:
    if _is_billing_or_subscription_issue(issue):
        return BILLING_SUBSCRIPTION_FALLBACK
    return GENERAL_QUALITY_FALLBACK


def _response_is_too_generic(response: str) -> bool:
    t = response.lower().strip()
    if len(t) < 28:
        return True
    if any(b in t for b in GENERIC_REPLY_MARKERS):
        return True
    toks = tokenize(response)
    if len(toks) < 3:
        return True
    return False


def _needs_safety_fallback(issue: str, response: str) -> bool:
    if not response.strip():
        return True
    if looks_like_messy_evidence(response):
        return True
    if not ticket_response_overlap_ok(issue, response):
        return True
    if _response_is_too_generic(response):
        return True
    return False


def _polish_reply(text: str, issue: str) -> str:
    x = _reframe_to_support_tone(text)
    x = _finalize_support_response(x, issue)
    if _response_extract_quality_invalid(x):
        return _quality_fallback_for_issue(issue)
    if _needs_safety_fallback(issue, x):
        return SAFETY_FALLBACK_MSG
    return x


def looks_like_messy_evidence(text: str) -> bool:
    s = cleanup_response_text(text)
    if len(s) < 22:
        return True
    letters = sum(c.isalpha() for c in s)
    if letters / max(len(s), 1) < 0.42:
        return True
    words = s.lower().split()
    if len(words) >= 10:
        top_n, top_c = Counter(words).most_common(1)[0]
        if len(top_n) > 2 and top_c >= max(4, len(words) // 3):
            return True
    return False


def build_justification(route_reason: str, top_score: float | None = None) -> str:
    if route_reason:
        return route_reason
    if top_score is not None:
        return f"Matched support documentation with evidence score {round(top_score, 2)}."
    return "Matched relevant support documentation."


def score_sentence(ticket: str, sent: str) -> int:
    tt = set(tokenize(ticket))
    st = set(tokenize(sent))
    score = len(tt & st)
    if st & ACTION:
        score += 2
    score += _instruction_verb_overlap_score(sent)
    if _looks_like_doc_heading(sent):
        score -= 12
    if any(
        x in sent.lower()
        for x in [
            "can", "cannot", "must", "will", "only", "unless", "active", "expire",
            "expiration", "refund", "access", "report", "contact", "delete", "remove",
            "remain",
        ]
    ):
        score += 2
    if any(
        b in sent.lower()
        for b in [
            "last updated",
            "source_url",
            "title_slug",
            "article_id",
            "breadcrumbs",
            ".png",
            "image",
            "reference:",
        ]
    ):
        score -= 10
    if len(sent.split()) > 55:
        score -= 3
    return score


def extract_grounded_response(
    ticket: str, retrieved: list[RetrievalResult], max_sentences: int = 2
) -> str:
    candidates = []
    for r in retrieved[:2]:
        raw = _clean_response(strip_markdown(r.chunk), ticket)
        if looks_like_messy_evidence(raw):
            continue
        for s in sentence_split(raw):
            if _looks_like_doc_heading(s):
                continue
            if _extraction_line_is_headingish(s):
                continue
            s = _clean_response(re.sub(r"\b\d{5,}\b", " ", s), ticket)
            if len(s) < 22:
                continue
            sc = score_sentence(ticket, s)
            if sc > 0:
                candidates.append((sc, s))
    candidates.sort(key=lambda x: x[0], reverse=True)
    selected = []
    seen = set()
    for _, s in candidates:
        key = s.lower()[:90]
        if key in seen:
            continue
        seen.add(key)
        selected.append(s)
        if len(selected) >= max_sentences:
            break
    joined = " ".join(selected).strip()
    joined = _clean_response(joined, ticket)
    if looks_like_messy_evidence(joined):
        return ""
    if not ticket_response_overlap_ok(ticket, joined):
        return ""
    return joined


def ai_to_response(ai: dict | None, ticket: str) -> str | None:
    if not ai:
        return None
    direct = ai.get("direct_answer", "").strip()
    if not direct:
        return None
    direct = _clean_response(direct, ticket)
    direct = re.sub(r"(?i)reference\s*:?\s*\S+", "", direct)
    direct = _clean_response(direct, ticket)
    if not direct:
        return None
    out = limit_to_sentences(direct, 2)
    out = _clean_response(out, ticket)
    if looks_like_messy_evidence(out):
        return None
    if not ticket_response_overlap_ok(ticket, out):
        return None
    return out


def _escalation_reply_for_issue(text: str) -> str:
    t = text.lower()
    if any(
        x in t
        for x in ["identity theft", "stolen identity", "fraud", "unauthorized", "scam", "phishing"]
    ):
        return (
            "This request requires support assistance because sensitive account safety "
            "issues are reviewed by our security team."
        )
    if any(x in t for x in ["workspace", "admin", "seat", "permission", "access"]):
        return (
            "This request requires support assistance because access is managed by "
            "your organization's admin."
        )
    if any(x in t for x in ["infosec", "compliance", "security questionnaire", "forms"]):
        return (
            "This request requires support assistance because compliance and security "
            "forms are handled manually."
        )
    return SAFETY_FALLBACK_MSG


def _is_claude_crawl_robots_issue(issue: str) -> bool:
    t = issue.lower()
    if "claude" not in t:
        return False
    return any(k in t for k in ("crawl", "crawler", "crawling", "robots.txt", "robots"))


def make_response(
        
    status: str,
    issue: str,
    retrieved: list[RetrievalResult],
    route: RouteDecision,
    company: str = "",
    product_area: str = "",
) -> str:
    text = issue.lower()
    if status == "escalated":
        if any(
            t in text
            for t in [
                "identity theft",
                "stolen identity",
                "fraud",
                "unauthorized",
                "scam",
                "phishing",
            ]
        ):
            return (
                "This request requires support assistance because sensitive account safety "
                "issues are reviewed by our security team."
            )
        if any(t in text for t in ["workspace", "admin", "seat", "permission", "access"]):
            return (
                "This request requires support assistance because access is managed by "
                "your organization's admin."
            )
        if any(t in text for t in ["infosec", "compliance", "security questionnaire", "forms"]):
            return (
                "This request requires support assistance because compliance and security "
                "forms are handled manually."
            )
        if "cut-off score" in text or "cutoff score" in text or "qualified candidates" in text:
            return (
                "Candidates are marked as passed or failed based on the configured cut-off score. "
                "You can review qualified candidates from the Candidate Status section."
        )
        return SAFETY_FALLBACK_MSG
    if _is_claude_crawl_robots_issue(issue):
        cr = _reframe_to_support_tone(CLAUDE_ROBOTS_REPLY)
        return _finalize_support_response(cr, issue)
    ai = ai_to_response(ask_local_ai(issue, company, product_area, retrieved), issue)
    if ai:
        return _polish_reply(ai, issue)
    grounded = extract_grounded_response(issue, retrieved, max_sentences=2)
    if grounded:
        return _polish_reply(grounded, issue)

    return _escalation_reply_for_issue(issue)

