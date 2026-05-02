from __future__ import annotations
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from loader import Document
from utils import strip_markdown, tokenize, keyword_overlap

QUERY_EXPANSIONS = {
    "login":["login","signin","sign","access","account"], "password":["password","reset","login","account"],
    "delete":["delete","remove","close","deletion","account"], "card":["card","visa","credit","debit"],
    "stolen":["stolen","lost","missing"], "lost":["lost","stolen","missing","access"],
    "payment":["payment","pay","billing","invoice","charge","transaction"], "refund":["refund","reimburse","billing"],
    "test":["test","assessment","screen"], "assessment":["assessment","test","screen"],
    "active":["active","expiration","expire","end"], "expire":["expire","expiration","end","active"],
    "candidate":["candidate","invite","assessment","test"], "workspace":["workspace","team","admin","seat","member"],
    "api":["api","console","usage","credits","key"], "cheque":["cheque","cheques","traveler","traveller"],
    "cheques":["cheque","cheques","traveler","traveller"], "infosec":["security","compliance","questionnaire","forms"],
    "inactivity":["inactivity","timeout","session","lobby"], "crawler":["crawler","crawl","robots","bot"],
}

@dataclass(frozen=True)
class RetrievalResult:
    score: float
    document: Document
    chunk: str
    overlap: float

def expand(tokens: list[str]) -> list[str]:
    out: list[str] = []
    for t in tokens:
        out.extend(QUERY_EXPANSIONS.get(t, [t]))
    return out

def chunks_for(doc: Document, size: int = 1200, overlap: int = 200) -> list[str]:
    txt = strip_markdown(doc.content)
    if not txt:
        return []
    chunks=[]; start=0
    while start < len(txt):
        chunks.append(txt[start:start+size])
        start += size - overlap
    return chunks

class BM25Retriever:
    def __init__(self, docs: list[Document]):
        self.items=[]; self.postings=defaultdict(list); df=defaultdict(int)
        for doc in docs:
            for chunk in chunks_for(doc):
                text = f"{doc.title} {doc.section} {doc.path} {chunk}"
                counts = Counter(tokenize(text))
                idx=len(self.items)
                item={"doc":doc,"chunk":chunk,"counts":counts,"length":sum(counts.values()) or 1,
                      "title":set(tokenize(doc.title)),"path":set(tokenize(doc.path)),"section":set(tokenize(doc.section))}
                self.items.append(item)
                for tok, freq in counts.items():
                    self.postings[tok].append((idx, freq)); df[tok]+=1
        n=len(self.items) or 1
        self.avg_len=sum(i["length"] for i in self.items)/n
        self.idf={tok: math.log(1 + ((n - f + 0.5)/(f + 0.5))) for tok,f in df.items()}

    def _company_ok(self, company: str, doc: Document) -> bool:
        return company == "None" or company.lower() in doc.company.lower()

    def search(self, query: str, company: str = "None", top_k: int = 5) -> list[RetrievalResult]:
        q_tokens = expand(tokenize(query))
        if not q_tokens: return []
        scores=defaultdict(float); k1=1.5; b=0.75
        for tok in q_tokens:
            idf=self.idf.get(tok,0.0)
            for idx, freq in self.postings.get(tok,[]):
                item=self.items[idx]; doc=item["doc"]
                if not self._company_ok(company, doc): continue
                denom=freq + k1*(1-b+b*item["length"]/self.avg_len)
                scores[idx] += idf*((freq*(k1+1))/denom)
        results=[]
        for idx, score in scores.items():
            item=self.items[idx]; doc=item["doc"]
            for tok in q_tokens:
                if tok in item["title"]: score += 4
                if tok in item["path"]: score += 3
                if tok in item["section"]: score += 2
            if company != "None" and company.lower() in doc.company.lower(): score += 3
            ov=keyword_overlap(query, f"{doc.title} {doc.path} {item['chunk']}")
            results.append(RetrievalResult(round(score,3), doc, item["chunk"], ov))
        results.sort(key=lambda r: r.score, reverse=True)
        seen=set(); uniq=[]
        for r in results:
            if r.document.path in seen: continue
            seen.add(r.document.path); uniq.append(r)
            if len(uniq)>=top_k: break
        return uniq
