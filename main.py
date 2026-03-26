#!/usr/bin/env python3
import json, hashlib, argparse, sys, os
from collections import defaultdict

def compute_rollups(ledger_path):
    """Compute aggregated cost metrics by agent, tool, run_id, and status."""
    rollups = defaultdict(lambda: {
        "count": 0,
        "total_prompt_tokens": 0,
        "total_completion_tokens": 0,
        "total_duration_ms": 0,
        "total_retries": 0
    })
    with open(ledger_path) as f:
        for line in f:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = (
                rec.get("agent_id"),
                rec.get("tool_name"),
                rec.get("run_id"),
                rec.get("status")
            )
            r = rollups[key]
            r["count"] += 1
            r["total_prompt_tokens"] += rec.get("prompt_tokens") or 0
            r["total_completion_tokens"] += rec.get("completion_tokens") or 0
            r["total_duration_ms"] += rec.get("duration_ms") or 0
            r["total_retries"] += rec.get("retries", 0)
    result = []
    for (agent, tool, run_id, status), sums in rollups.items():
        result.append({
            "agent_id": agent,
            "tool_name": tool,
            "run_id": run_id,
            "status": status,
            **sums,
            "total_tokens": sums["total_prompt_tokens"] + sums["total_completion_tokens"]
        })
    return result

def main():
    p = argparse.ArgumentParser(description="Agent Cost Ledger - tamper-evident tracking")
    sub = p.add_subparsers(dest="cmd", required=True)

    # Ingest command
    ingest_parser = sub.add_parser("ingest", help="Ingest events into the ledger")
    ingest_parser.add_argument("--input", required=True, help="Input events JSONL file")
    ingest_parser.add_argument("--out", required=True, help="Output ledger JSONL file (append if exists)")

    # Rollups command
    rollup_parser = sub.add_parser("rollups", help="Compute cost rollups from the ledger")
    rollup_parser.add_argument("--ledger", default="ledger.jsonl", help="Ledger JSONL file (default: ledger.jsonl)")
    rollup_parser.add_argument("--output", help="Output JSON file for rollups (default: stdout)")

    args = p.parse_args()

    if args.cmd == "ingest":
        prev_hash, records = "0"*64, []
        mode = 'a' if os.path.exists(args.out) else 'w'
        with open(args.out, mode) as outf, open(args.input) as inf:
            for n, line in enumerate(inf, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    print(f"Line {n}: invalid JSON", file=sys.stderr)
                    continue
                if not all(k in ev for k in ["tool_name", "status"]):
                    print(f"Line {n}: missing required fields (tool_name, status)", file=sys.stderr)
                    continue
                rec = {
                    "record_id": f"rec_{len(records)+1:08d}",
                    "timestamp": ev.get("timestamp", ""),
                    "agent_id": ev.get("agent_id"),
                    "tool_name": ev["tool_name"],
                    "tool_version": ev.get("tool_version"),
                    "provider": ev.get("provider"),
                    "prompt_tokens": ev.get("prompt_tokens"),
                    "completion_tokens": ev.get("completion_tokens"),
                    "duration_ms": ev.get("duration_ms"),
                    "retries": ev.get("retries", 0),
                    "status": ev["status"],
                    "error_class": ev.get("error_class"),
                    "run_id": ev.get("run_id"),
                    "prev_hash": prev_hash
                }
                rec_hash = hashlib.sha256(json.dumps(rec, sort_keys=True).encode()).hexdigest()
                rec["record_hash"] = rec_hash
                outf.write(json.dumps(rec) + "\n")
                records.append(rec)
                prev_hash = rec_hash
        print(f"Ingested {len(records)} records into {args.out}")

    elif args.cmd == "rollups":
        rollup_data = compute_rollups(args.ledger)
        output = json.dumps(rollup_data, indent=2)
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"Wrote rollups to {args.output}")
        else:
            print(output)

if __name__ == "__main__":
    main()
