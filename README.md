# Agent Cost Ledger
Tamper-evident ledger for agent tool call costs. CLI: `ingest` and `rollups`.

## Installation
Python 3.x, no dependencies.

## Usage
### Ingest
JSON Lines input. Example:
```bash
python3 main.py ingest --input sample_events.jsonl --out ledger.jsonl
```
Appends to existing ledger.

### Rollups
Aggregate by agent, tool, run_id, status:
```bash
python3 main.py rollups --ledger ledger.jsonl
```
Add `--output file.json` to save.

Example output:
```json
{
  "agent_id": "agent_001",
  "tool_name": "web_search",
  "status": "success",
  "count": 5,
  "total_prompt_tokens": 1500,
  "total_completion_tokens": 3000,
  "total_tokens": 4500,
  "total_duration_ms": 6250,
  "total_retries": 2
}
```

## Input Event Schema
Required: `tool_name`, `status`.
Optional: `agent_id`, `run_id`, `tool_version`, `provider`, `prompt_tokens`, `completion_tokens`, `duration_ms`, `retries` (default 0), `error_class`.

## Integrity
Records contain `prev_hash` and `record_hash` (SHA-256). First `prev_hash` is all zeros, forming a tamper-evident chain.
