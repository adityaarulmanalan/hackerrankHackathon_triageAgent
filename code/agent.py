from __future__ import annotations
from classifier import Classification, classify, infer_product_area
from retrieval import BM25Retriever, RetrievalResult
from responder import build_justification, make_response
from router import route
from utils import get_field

class SupportTriageAgent:
    def __init__(self, retriever: BM25Retriever):
        self.retriever = retriever

    def _run(self, ticket: dict, row_index: int = 0) -> dict:
        issue=get_field(ticket,"Issue") or get_field(ticket,"issue")
        subject=get_field(ticket,"Subject") or get_field(ticket,"subject")
        company_raw=get_field(ticket,"Company") or get_field(ticket,"company")
        c=classify(issue, subject, company_raw)
        query=f"{subject} {issue}".strip()
        retrieved=self.retriever.search(query, c.company, top_k=5)
        if not retrieved and c.company != "None":
            retrieved=self.retriever.search(query, "None", top_k=5)
        top_doc=retrieved[0].document if retrieved else None
        product_area=infer_product_area(subject, issue, c.company, top_doc)
        c.product_area=product_area
        confidence={"top_score": retrieved[0].score if retrieved else 0.0, "overlap": retrieved[0].overlap if retrieved else 0.0}
        decision=route(issue, subject, c, retrieved, confidence)
        response=make_response(decision.status, query, retrieved, decision, c.company, product_area)
        justification=build_justification(decision.reason, confidence["top_score"])
        pred={"status":decision.status,"product_area":product_area,"response":response,"justification":justification,"request_type":c.request_type}
        return {"ticket":{"issue":issue,"subject":subject,"company":company_raw},"classification":c.to_dict(),"confidence":confidence,"prediction":pred,"retrieved":[{"score":r.score,"path":r.document.path,"title":r.document.title,"overlap":r.overlap} for r in retrieved]}

    def process(self, ticket: dict, row_index: int = 0) -> dict:
        return self._run(ticket, row_index)["prediction"]

    def inspect(self, ticket: dict, row_index: int = 0) -> dict:
        return self._run(ticket, row_index)
