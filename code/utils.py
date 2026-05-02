from __future__ import annotations
import re
from typing import Iterable

STOPWORDS = {
    "a","an","and","are","as","at","be","but","by","can","could","do","does","for","from",
    "had","has","have","how","i","if","in","into","is","it","its","me","my","of","on","or",
    "our","please","should","so","that","the","their","them","then","there","this","to","us",
    "was","we","were","what","when","where","which","who","why","with","you","your","im","i'm",
    "need","want","help","hi","hello","thanks","thank"
}

def clean_text(text: object) -> str:
    if text is None:
        return ""
    s = str(text).replace("\ufeff", " ").replace("\\", "")
    s = re.sub(r"```.*?```", " ", s, flags=re.DOTALL)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"https?://\S+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def strip_markdown(text: object) -> str:
    s = str(text or "")
    s = re.sub(r"^---.*?---", " ", s, flags=re.DOTALL)
    s = re.sub(r"```.*?```", " ", s, flags=re.DOTALL)
    s = re.sub(r"`([^`]*)`", r"\1", s)
    s = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", s)
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    s = re.sub(r"^\s{0,3}#{1,6}\s*", "", s, flags=re.MULTILINE)
    s = re.sub(r"[*_~>`]+", " ", s)
    s = re.sub(r"\b\d{6,}\b", " ", s)
    s = re.sub(r"(title_slug|article_id|source_url|breadcrumbs|last_updated|last updated).*", " ", s, flags=re.I)
    return clean_text(s)

def tokenize(text: object, keep_stopwords: bool = False) -> list[str]:
    toks = re.findall(r"[a-z0-9][a-z0-9_+.-]*", clean_text(text).lower())
    if keep_stopwords:
        return toks
    return [t for t in toks if len(t) > 1 and t not in STOPWORDS]

def sentence_split(text: object) -> list[str]:
    s = strip_markdown(text)
    if not s:
        return []
    parts = re.split(r"(?<=[.!?])\s+|\n+", s)
    return [p.strip(" -•\t") for p in parts if len(p.strip(" -•\t")) > 20]

split_sentences = sentence_split

def contains_any(text: object, keywords: Iterable[str]) -> bool:
    t = clean_text(text).lower()
    return any(k.lower() in t for k in keywords)

def get_field(row: dict, key: str) -> str:
    wanted = key.lower().replace(" ", "_")
    for k, v in row.items():
        if k.lower().replace(" ", "_") == wanted:
            return clean_text(v)
    return ""

def keyword_overlap(a: object, b: object) -> float:
    aa = set(tokenize(a)); bb = set(tokenize(b))
    if not aa or not bb:
        return 0.0
    return len(aa & bb) / max(1, min(len(aa), len(bb)))
