# Support Ticket Triage System

## Overview

This project is a deterministic support ticket triage system built for the HackerRank AI challenge.

It processes incoming support tickets and:
- Classifies them into request type and product area
- Retrieves relevant documentation
- Generates grounded responses
- Decides whether to reply or escalate

The system is designed to prioritize **correctness, consistency, and explainability** over generative flexibility.

---

## Problem Statement

Support teams spend significant time:
- Reading and understanding tickets
- Finding relevant documentation
- Deciding whether to resolve or escalate

A naive AI solution may generate fluent responses but risks **hallucination and incorrect guidance**, which is unacceptable in support workflows.

This project focuses on building a **reliable and auditable triage system**.

---

## Approach

The system follows a structured pipeline:

### 1. Input Processing
- Cleans and normalizes ticket text
- Removes noise (links, markdown, formatting)

---

### 2. Classification
- Rule-based classification (no ML model)
- Outputs:
  - `request_type` (product_issue, bug, invalid, etc.)
  - `product_area` (billing, security, screen, etc.)

Why rule-based?
- Deterministic
- Transparent
- Easy to debug

---

### 3. Retrieval
- Uses keyword/token overlap (BM25-style)
- Retrieves top relevant documents

#### Query Expansion
- Adds synonyms (e.g. login ↔ access, billing ↔ payment)
- Improves recall for vocabulary mismatch

---

### 4. Chunking Strategy
- Documents split into:
  - 1200 character chunks
  - 200 character overlap

Why?
- Maintains context
- Prevents boundary information loss
- Works better than inconsistent paragraph splits

---

### 5. Sentence Extraction & Scoring

Instead of returning full chunks, the system:
- Splits documents into sentences
- Scores each sentence

#### Scoring signals:
- Keyword overlap with ticket
- Presence of actionable verbs (click, update, contact)
- Penalties for:
  - headings
  - noisy text
  - overly long sentences

Top 1–2 sentences are selected.

---

### 6. Response Validation

Ensures quality by rejecting:
- Incomplete sentences ("Click the...")
- Headings or titles
- Irrelevant or low-overlap content
- Noisy or malformed text

If validation fails → fallback or escalation

---

### 7. Routing (Reply vs Escalate)

The system decides:

#### Reply if:
- Strong retrieval match
- Valid response

#### Escalate if:
- Admin / permission issues
- Security / fraud
- Compliance / infosec
- Low confidence

Key principle:
> A wrong answer is worse than escalation.

---

### 8. Output Generation

Each ticket produces:

- status (replied / escalated)
- product_area
- response
- justification
- request_type

Saved in:
- `output.csv`
- `debug_output.csv` (for traceability)

---

## Example Output

status: escalated
product_area: team_and_enterprise
response: This request requires support assistance because access is managed by your organization’s admin.
justification: Account, workspace, admin, or permission changes require human support review.
request_type: product_issue

---

## AI Usage

AI was used in two ways:

### 1. Development Phase
- Debugging errors
- Refining response logic
- Designing validation rules

### 2. Optional Runtime Integration
- Local AI model (Ollama) tested for response generation
- Only used if:
  - Output is validated
  - No hallucination risk

Final system remains:
> Deterministic-first, AI-optional

---

## Design Philosophy

### Priorities:
- Correctness
- Consistency
- Explainability

### Trade-off:
- Less fluent responses
- More reliable behavior

---

## Key Features

- Deterministic pipeline (no black-box decisions)
- Grounded responses (no hallucination)
- Query expansion for better retrieval
- Sentence-level scoring (not raw chunk output)
- Strong validation layer
- Safe escalation logic
- Debug traceability

---

## Limitations

- Keyword-based retrieval (not semantic)
- No learning or feedback loop
- Single-step agent (no planning)
- Limited handling of complex paraphrasing

---

## Future Improvements

- Embedding-based semantic retrieval
- Learning from past tickets
- Better ranking (cross-encoder)
- Controlled LLM-based response generation
- Multi-step agent behavior

---

## Why This Approach?

Instead of building a fully generative system, this project treats the problem as:

> A decision-making system, not a chatbot

This ensures:
- Predictable outputs
- Easier debugging
- Production-like reliability

---

## Conclusion

This system demonstrates how combining:
- retrieval
- scoring
- validation
- routing

can produce a **reliable and explainable support agent** without relying entirely on LLMs.

---

## Author

Aditya Arul Manalan
