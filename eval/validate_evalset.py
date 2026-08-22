#!/usr/bin/env python3
"""Validate BookForge evaluation set JSON files.

Usage:
    python eval/validate_evalset.py eval/bookforge-comprehensive.evalset.json
    python eval/validate_evalset.py eval/*.evalset.json
"""

import json
import sys
from pathlib import Path
from typing import Any


def validate_eval_case(case: dict[str, Any], case_idx: int) -> list[str]:
    """Validate a single eval case structure."""
    errors = []
    
    # Required fields
    if "eval_id" not in case:
        errors.append(f"Case {case_idx}: Missing 'eval_id'")
    elif not isinstance(case["eval_id"], str) or not case["eval_id"]:
        errors.append(f"Case {case_idx}: 'eval_id' must be non-empty string")
    
    if "conversation" not in case:
        errors.append(f"Case {case_idx}: Missing 'conversation'")
    elif not isinstance(case["conversation"], list) or not case["conversation"]:
        errors.append(f"Case {case_idx}: 'conversation' must be non-empty list")
    else:
        for inv_idx, invocation in enumerate(case["conversation"]):
            if "invocation_id" not in invocation:
                errors.append(
                    f"Case {case_idx}, invocation {inv_idx}: Missing 'invocation_id'"
                )
            if "user_content" not in invocation:
                errors.append(
                    f"Case {case_idx}, invocation {inv_idx}: Missing 'user_content'"
                )
            if "final_response" not in invocation:
                errors.append(
                    f"Case {case_idx}, invocation {inv_idx}: Missing 'final_response'"
                )
    
    if "session_input" not in case:
        errors.append(f"Case {case_idx}: Missing 'session_input'")
    else:
        session = case["session_input"]
        if "app_name" not in session:
            errors.append(f"Case {case_idx}: session_input missing 'app_name'")
        elif session["app_name"] != "bookforge":
            errors.append(
                f"Case {case_idx}: app_name must be 'bookforge', got '{session['app_name']}'"
            )
        if "user_id" not in session:
            errors.append(f"Case {case_idx}: session_input missing 'user_id'")
        if "state" not in session:
            errors.append(f"Case {case_idx}: session_input missing 'state'")
    
    return errors


def validate_evalset(path: Path) -> tuple[bool, list[str]]:
    """Validate an entire evalset file."""
    errors = []
    
    # Load JSON
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        return False, [f"Invalid JSON: {exc}"]
    except Exception as exc:
        return False, [f"Failed to read file: {exc}"]
    
    # Top-level structure
    if not isinstance(data, dict):
        return False, ["Root must be an object"]
    
    # Required top-level fields
    if "eval_set_id" not in data:
        errors.append("Missing 'eval_set_id'")
    elif not isinstance(data["eval_set_id"], str):
        errors.append("'eval_set_id' must be string")
    
    if "name" not in data:
        errors.append("Missing 'name'")
    elif not isinstance(data["name"], str):
        errors.append("'name' must be string")
    
    if "eval_cases" not in data:
        errors.append("Missing 'eval_cases'")
        return False, errors
    
    if not isinstance(data["eval_cases"], list):
        errors.append("'eval_cases' must be list")
        return False, errors
    
    if not data["eval_cases"]:
        errors.append("'eval_cases' must not be empty")
        return False, errors
    
    # Validate each eval case
    eval_ids = set()
    for idx, case in enumerate(data["eval_cases"]):
        case_errors = validate_eval_case(case, idx)
        errors.extend(case_errors)
        
        # Check for duplicate eval_ids
        eval_id = case.get("eval_id")
        if eval_id:
            if eval_id in eval_ids:
                errors.append(f"Duplicate eval_id: '{eval_id}'")
            eval_ids.add(eval_id)
    
    # Summary info
    if not errors:
        print(f"[OK] {path.name}: Valid")
        print(f"   - eval_set_id: {data['eval_set_id']}")
        print(f"   - name: {data['name']}")
        print(f"   - eval_cases: {len(data['eval_cases'])}")
        
        # Category breakdown
        categories = {}
        for case in data["eval_cases"]:
            eval_id = case.get("eval_id", "")
            category = eval_id.split("_")[0] if "_" in eval_id else "other"
            categories[category] = categories.get(category, 0) + 1
        
        if categories:
            print("   - categories:")
            for cat, count in sorted(categories.items()):
                print(f"     - {cat}: {count}")
    
    return len(errors) == 0, errors


def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python validate_evalset.py <evalset.json> [...]")
        return 1
    
    paths = [Path(arg) for arg in sys.argv[1:]]
    
    all_valid = True
    for path in paths:
        if not path.exists():
            print(f"[FAIL] {path}: File not found")
            all_valid = False
            continue
        
        valid, errors = validate_evalset(path)
        if not valid:
            print(f"[FAIL] {path.name}: Invalid")
            for error in errors:
                print(f"   - {error}")
            all_valid = False
        print()
    
    return 0 if all_valid else 1


if __name__ == "__main__":
    sys.exit(main())
