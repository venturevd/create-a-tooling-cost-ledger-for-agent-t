#!/usr/bin/env python3
"""Test suite for agent cost ledger rollups functionality."""
import json
import tempfile
import os
from main import compute_rollups

def test_rollups_basic():
    """Test basic rollup computation with sample data."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write(json.dumps({
            "agent_id": "agent_001",
            "tool_name": "web_search",
            "run_id": "run_1",
            "status": "success",
            "prompt_tokens": 100,
            "completion_tokens": 200,
            "duration_ms": 1000,
            "retries": 0
        }) + "\n")
        f.write(json.dumps({
            "agent_id": "agent_001",
            "tool_name": "web_search",
            "run_id": "run_1",
            "status": "success",
            "prompt_tokens": 150,
            "completion_tokens": 250,
            "duration_ms": 1200,
            "retries": 1
        }) + "\n")
        f.write(json.dumps({
            "agent_id": "agent_002",
            "tool_name": "code_executor",
            "run_id": "run_2",
            "status": "failure",
            "prompt_tokens": 50,
            "completion_tokens": 0,
            "duration_ms": 500,
            "retries": 2,
            "error_class": "TimeoutError"
        }) + "\n")
        temp_path = f.name

    try:
        results = compute_rollups(temp_path)

        # Should produce 2 rollup groups (2 success records roll up into 1)
        assert len(results) == 2, f"Expected 2 rollup groups, got {len(results)}"

        # Find web_search success rollup
        web_search_success = next(
            (r for r in results if r["agent_id"] == "agent_001"
             and r["tool_name"] == "web_search"
             and r["status"] == "success"
             and r["run_id"] == "run_1"),
            None
        )
        assert web_search_success is not None, "Missing web_search success rollup"
        assert web_search_success["count"] == 2
        assert web_search_success["total_prompt_tokens"] == 250  # 100+150
        assert web_search_success["total_completion_tokens"] == 450  # 200+250
        assert web_search_success["total_duration_ms"] == 2200  # 1000+1200
        assert web_search_success["total_retries"] == 1  # 0+1
        assert web_search_success["total_tokens"] == 700

        # Find code_executor failure rollup
        code_failure = next(
            (r for r in results if r["agent_id"] == "agent_002"
             and r["tool_name"] == "code_executor"
             and r["status"] == "failure"),
            None
        )
        assert code_failure is not None, "Missing code_executor failure rollup"
        assert code_failure["count"] == 1
        assert code_failure["total_prompt_tokens"] == 50
        assert code_failure["total_completion_tokens"] == 0
        assert code_failure["total_duration_ms"] == 500
        assert code_failure["total_retries"] == 2

    finally:
        os.unlink(temp_path)

def test_rollups_null_fields():
    """Test rollup computation handles null values correctly."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write(json.dumps({
            "agent_id": "agent_003",
            "tool_name": "file_writer",
            "status": "success",
            "prompt_tokens": None,
            "completion_tokens": None,
            "duration_ms": None,
            "retries": 0
        }) + "\n")
        temp_path = f.name

    try:
        results = compute_rollups(temp_path)
        assert len(results) == 1
        r = results[0]
        assert r["total_prompt_tokens"] == 0
        assert r["total_completion_tokens"] == 0
        assert r["total_duration_ms"] == 0
        assert r["total_retries"] == 0
        assert r["total_tokens"] == 0
    finally:
        os.unlink(temp_path)

def test_rollups_missing_optional_fields():
    """Test rollup handles missing optional fields like run_id."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write(json.dumps({
            "agent_id": "agent_004",
            "tool_name": "search",
            "status": "success",
            "prompt_tokens": 100,
            "completion_tokens": 200
            # duration_ms, retries, run_id omitted
        }) + "\n")
        temp_path = f.name

    try:
        results = compute_rollups(temp_path)
        assert len(results) == 1
        r = results[0]
        assert r["run_id"] is None  # Should be None when missing
        assert r["total_duration_ms"] == 0
        assert r["total_retries"] == 0
    finally:
        os.unlink(temp_path)

def test_rollups_empty_ledger():
    """Test rollup on empty ledger returns empty list."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        # Write a blank line to simulate empty-ish file
        f.write("\n")
        temp_path = f.name

    try:
        results = compute_rollups(temp_path)
        assert results == []
    finally:
        os.unlink(temp_path)

def test_rollups_aggregates_by_all_keys():
    """Test that rollup correctly groups by agent, tool, run_id, and status."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        # Two records with same (agent, tool, run_id, status)
        f.write(json.dumps({
            "agent_id": "agent_1",
            "tool_name": "tool_a",
            "run_id": "run_x",
            "status": "success",
            "prompt_tokens": 100,
            "completion_tokens": 200,
            "duration_ms": 1000,
            "retries": 0
        }) + "\n")
        f.write(json.dumps({
            "agent_id": "agent_1",
            "tool_name": "tool_a",
            "run_id": "run_x",
            "status": "success",
            "prompt_tokens": 150,
            "completion_tokens": 250,
            "duration_ms": 1100,
            "retries": 1
        }) + "\n")
        # Different status
        f.write(json.dumps({
            "agent_id": "agent_1",
            "tool_name": "tool_a",
            "run_id": "run_x",
            "status": "failure",
            "prompt_tokens": 50,
            "completion_tokens": 0,
            "duration_ms": 500,
            "retries": 2
        }) + "\n")
        # Different run_id
        f.write(json.dumps({
            "agent_id": "agent_1",
            "tool_name": "tool_a",
            "run_id": "run_y",
            "status": "success",
            "prompt_tokens": 80,
            "completion_tokens": 120,
            "duration_ms": 800,
            "retries": 0
        }) + "\n")
        temp_path = f.name

    try:
        results = compute_rollups(temp_path)
        assert len(results) == 3, f"Expected 3 distinct groups, got {len(results)}"

        # Verify each group
        groups = {(r["agent_id"], r["tool_name"], r["run_id"], r["status"]) for r in results}
        expected = {
            ("agent_1", "tool_a", "run_x", "success"),
            ("agent_1", "tool_a", "run_x", "failure"),
            ("agent_1", "tool_a", "run_y", "success"),
        }
        # (agent_1, tool_a, run_y, success) might appear as None if run_y missing? Let's check
        # Actually we have all 3 groups from the data. Wait we wrote 4 records but should have 3 groups?
        # Records: 2 success run_x, 1 failure run_x, 1 success run_y = 3 groups total
        # But I said 4 above. Let's recalc: groups should be:
        # (agent_1, tool_a, run_x, success) - 2 records aggregate
        # (agent_1, tool_a, run_x, failure) - 1 record
        # (agent_1, tool_a, run_y, success) - 1 record
        # That's 3 groups.
        assert groups == expected
    finally:
        os.unlink(temp_path)

if __name__ == "__main__":
    print("Running rollup tests...")
    test_rollups_basic()
    print("✓ test_rollups_basic passed")

    test_rollups_null_fields()
    print("✓ test_rollups_null_fields passed")

    test_rollups_missing_optional_fields()
    print("✓ test_rollups_missing_optional_fields passed")

    test_rollups_empty_ledger()
    print("✓ test_rollups_empty_ledger passed")

    test_rollups_aggregates_by_all_keys()
    print("✓ test_rollups_aggregates_by_all_keys passed")

    print("\nAll tests passed!")
