from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent import SupportTriageAgent
from audit_output import audit as audit_output
from config import DEBUG_COLUMNS, OUTPUT_COLUMNS
from loader import debug_csv_path, load_documents, load_tickets, output_csv_path, write_csv
from logger import log_event
from retrieval import BM25Retriever
from utils import get_field

def build_agent():
    docs=load_documents(); return SupportTriageAgent(BM25Retriever(docs)), len(docs)

def cmd_run(args):
    agent, docs=build_agent(); rows=load_tickets(sample=False); out=[]; debug=[]
    for i,row in enumerate(rows):
        p=agent.process(row,i); out.append(p); debug.append({"issue":get_field(row,"Issue"),"subject":get_field(row,"Subject"),"company":get_field(row,"Company"),**p})
    write_csv(output_csv_path(), out, OUTPUT_COLUMNS); write_csv(debug_csv_path(), debug, DEBUG_COLUMNS)
    print(f"Wrote {len(out)} rows to {output_csv_path()}"); print(f"Wrote debug rows to {debug_csv_path()}")
    log_event("RUN_COMPLETE", {"rows":len(out),"docs":docs}); return 0

def cmd_evaluate(args):
    agent, docs=build_agent(); rows=load_tickets(sample=True); total=0; sc=0; rc=0
    print("Evaluation details\n------------------")
    for i,row in enumerate(rows):
        p=agent.process(row,i); es=get_field(row,"Status").lower(); er=get_field(row,"Request Type").lower()
        ps=p["status"].lower(); pr=p["request_type"].lower();
        if es: total += 1; sc += (ps==es)
        if er: rc += (pr==er)
        print(f"Row {i}: status {ps} vs {es or 'unknown'} | request_type {pr} vs {er or 'unknown'}")
    print("\nSummary\n-------"); print(f"Rows: {len(rows)}"); print(f"Status accuracy: {sc}/{total}"); print(f"Request type accuracy: {rc}/{total}")
    log_event("EVALUATE_COMPLETE", {"rows":len(rows),"status":f"{sc}/{total}","request_type":f"{rc}/{total}","docs":docs}); return 0

def cmd_inspect(args):
    agent,_=build_agent(); rows=load_tickets(sample=args.sample)
    if args.row<0 or args.row>=len(rows): print("row out of range"); return 1
    rep=agent.inspect(rows[args.row],args.row); print(json.dumps(rep, indent=2, ensure_ascii=False)); return 0

def cmd_audit(args): return audit_output()

def main(argv=None):
    parser=argparse.ArgumentParser(); sub=parser.add_subparsers(dest="command", required=True)
    sub.add_parser("run").set_defaults(func=cmd_run); sub.add_parser("evaluate").set_defaults(func=cmd_evaluate); sub.add_parser("audit").set_defaults(func=cmd_audit)
    p=sub.add_parser("inspect"); p.add_argument("--row",type=int,required=True); p.add_argument("--sample",action="store_true"); p.set_defaults(func=cmd_inspect)
    args=parser.parse_args(argv); return args.func(args)
if __name__ == "__main__": raise SystemExit(main())
