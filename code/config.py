from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SUPPORT_DIR = ROOT / "support_tickets"
INPUT_FILE = SUPPORT_DIR / "support_tickets.csv"
SAMPLE_FILE = SUPPORT_DIR / "sample_support_tickets.csv"
OUTPUT_FILE = SUPPORT_DIR / "output.csv"
DEBUG_OUTPUT_FILE = SUPPORT_DIR / "debug_output.csv"

OUTPUT_COLUMNS = ["status", "product_area", "response", "justification", "request_type"]
DEBUG_COLUMNS = ["issue", "subject", "company", *OUTPUT_COLUMNS]

HOME_LOG_DIR = Path.home() / "hackerrank_orchestrate"
HOME_LOG_FILE = HOME_LOG_DIR / "log.txt"
LOCAL_LOG_DIR = ROOT / "logs"
LOCAL_LOG_FILE = LOCAL_LOG_DIR / "log.txt"

MIN_REPLY_SCORE = 8.0
