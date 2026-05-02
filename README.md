# Support Ticket Triage Agent (HackerRank Orchestrate 2026)

## Overview

This project is a deterministic support ticket triage agent built for the HackerRank Orchestrate hackathon.

The system processes real-world support tickets across three ecosystems:
- HackerRank
- Claude
- Visa

For each ticket, it:
- Classifies the request
- Retrieves relevant documentation
- Generates a grounded response
- Decides whether to reply or escalate

The system prioritizes **correctness, safety, and explainability** over generative flexibility.

---

## Problem

Support teams handle large volumes of tickets involving:
- Billing issues
- Account access
- Security concerns
- Product usage queries

A naive AI system may generate fluent responses but risks:
- Hallucination
- Incorrect guidance
- Unsafe decisions

This project focuses on building a **reliable triage system** that:
> Answers when safe, escalates when uncertain.

---

## Approach

The system follows a structured pipeline:

### 1. Preprocessing
- Cleans ticket text
- Removes noise and formatting
- Normalizes input for consistent processing

---

### 2. Classification
- Rule-based classifier (no ML model)
- Outputs:
  - `request_type` (product_issue, bug, invalid)
  - `product_area` (billing, security, team_and_enterprise, etc.)

Why rule-based?
- Deterministic
- Transparent
- Easy to debug

---

### 3. Retrieval

- Keyword-based retrieval (BM25-style scoring)
- Uses local documentation corpus (no external APIs)

#### Query Expansion
- Adds synonyms (e.g. login ↔ access, billing ↔ payment)
- Improves recall for varied user phrasing

---

### 4. Document Chunking
- 1200 character chunks
- 200 character overlap

Ensures:
- Context preservation
- No information loss at boundaries

---

### 5. Sentence Extraction & Scoring

Instead of returning full documents:
- Extracts sentences
- Scores them using:

Signals:
- Keyword overlap with ticket
- Actionable language (click, update, contact)
- Penalties for:
  - headings
  - noise
  - overly long text

Selects top 1–2 sentences.

---

### 6. Response Validation

Filters out:
- Incomplete responses ("Click the...")
- Headings or titles
- Irrelevant or weak matches
- Noisy or malformed text

Ensures only **usable support responses** are returned.

---

### 7. Routing Logic (Reply vs Escalate)

#### Reply when:
- Strong retrieval match
- Valid response

#### Escalate when:
- Admin / permission issues
- Fraud / security concerns
- Compliance / infosec
- Low confidence

Key principle:
> A wrong answer is worse than escalation.

---

### 8. Output

Each ticket generates:

| Field | Description |
|------|------------|
| status | replied / escalated |
| product_area | classified domain |
| response | user-facing answer |
| justification | reasoning for decision |
| request_type | type of request |

Outputs saved to:

support_tickets/output.csv
support_tickets/debug_output.csv


---

## Example Output

status: escalated
product_area: team_and_enterprise
response: This request requires support assistance because access is managed by your organization's admin.
justification: Account, workspace, admin, or permission changes require human support review.
request_type: product_issue


---

## AI Usage

AI was used in:

### Development
- Debugging logic
- Designing validation layers
- Improving response quality

### Runtime (Optional)
- Local AI (Ollama) tested for response generation
- Only used if:
  - Output is validated
  - No hallucination risk

Final system remains:
> Deterministic-first, AI-optional

---

## Design Philosophy

### Priorities
- Correctness over fluency
- Safety over coverage
- Explainability over complexity

### Trade-offs
- Less conversational responses
- More reliable behavior

---

## Key Features

- Deterministic pipeline (no black-box decisions)
- Grounded responses from documentation
- Query expansion for better recall
- Sentence-level scoring
- Strong validation layer
- Safe escalation handling
- Debug traceability

---

## Limitations

- Keyword-based retrieval (no embeddings)
- No learning or feedback loop
- Single-pass pipeline (no multi-step reasoning)
- Limited handling of complex paraphrasing

---

## Future Improvements

- Semantic retrieval (embeddings)
- Cross-encoder reranking
- Learning from past tickets
- Controlled LLM generation
- Multi-step agent workflows

---

## Project Structure

.
├── code/
│ ├── main.py
│ ├── agent.py
│ ├── classifier.py
│ ├── retrieval.py
│ ├── responder.py
│ └── utils.py
│
├── data/
│ └── docs.zip # compressed documentation corpus
│
├── support_tickets/
│ ├── input_sample.csv
│ ├── output_sample.csv
│ └── debug_output.csv
│
└── README.md


---

## Setup

### 1. Clone repo

```bash
git clone https://github.com/adityaarulmanalan/hackerrankHackathon_triageAgent.git
cd hackerrankHackathon_triageAgent
```


### 2. Unzip documentation corpus

```bash
unzip data/docs.zip -d data/

```

---

### 3. Run

```bash
python3 code/main.py run
```

### Why This Approach?

Instead of building a purely generative system, this project treats triage as:

A decision-making system, not a chatbot

This ensures:

Predictable outputs
Easier debugging
Production-like reliability

---
Conclusion

This system demonstrates how combining:

retrieval
scoring
validation
routing

can produce a robust and explainable support agent without relying entirely on LLMs.

Author

Aditya Arul Manalan


---
