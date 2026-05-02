from __future__ import annotations
import csv
from dataclasses import dataclass
from pathlib import Path
from config import DATA_DIR, INPUT_FILE, SAMPLE_FILE, OUTPUT_FILE, DEBUG_OUTPUT_FILE
from utils import clean_text

@dataclass(frozen=True)
class Document:
    company: str
    section: str
    title: str
    path: str
    content: str

def load_documents() -> list[Document]:
    docs: list[Document] = []
    for path in DATA_DIR.rglob("*.md"):
        rel = path.relative_to(DATA_DIR)
        parts = rel.parts
        company = parts[0] if parts else "unknown"
        section = parts[1] if len(parts) > 1 else "general"
        docs.append(Document(
            company=company,
            section=section,
            title=path.stem.replace("-", " "),
            path=str(rel),
            content=path.read_text(encoding="utf-8", errors="ignore"),
        ))
    return docs

def load_tickets(sample: bool = False) -> list[dict]:
    path = SAMPLE_FILE if sample else INPUT_FILE
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)

def output_csv_path() -> Path:
    return OUTPUT_FILE

def debug_csv_path() -> Path:
    return DEBUG_OUTPUT_FILE
