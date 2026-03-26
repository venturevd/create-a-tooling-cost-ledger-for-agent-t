# Step 1: Create Ledger Ingestion Script

**File to create:** `main.py`
**Estimated size:** ~200 lines

## Instructions

Write a Python script that ingests agent call events and appends them to `ledger.jsonl` in a tamper-evident manner. The script should handle missing fields by storing them as null and estimate costs when enough data exists. BUDGET: ≤50 LOC, 1 file only.

## Verification

Run: `python3 main.py --help`
