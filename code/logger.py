from __future__ import annotations
from datetime import datetime
import json, subprocess
from config import HOME_LOG_DIR, HOME_LOG_FILE, LOCAL_LOG_DIR, LOCAL_LOG_FILE, ROOT

def now_iso(): return datetime.now().astimezone().isoformat(timespec="seconds")

def branch():
    try:
        r=subprocess.run(["git","-C",str(ROOT),"branch","--show-current"],capture_output=True,text=True,check=False)
        return r.stdout.strip() or "unknown"
    except Exception: return "unknown"

def log_event(title: str, details: dict | None = None):
    details=details or {}
    entry=f"""## [{now_iso()}] {title}

User Prompt (verbatim, secrets redacted):
Command-line run or development action.

Agent Response Summary:
{json.dumps(details, ensure_ascii=False)}

Actions:
* CLI action

Context:
tool=custom_python_agent
branch={branch()}
repo_root={ROOT}
worktree=main
parent_agent=none

"""
    for d,f in [(HOME_LOG_DIR,HOME_LOG_FILE),(LOCAL_LOG_DIR,LOCAL_LOG_FILE)]:
        d.mkdir(parents=True, exist_ok=True)
        with open(f,"a",encoding="utf-8") as fp: fp.write(entry)
