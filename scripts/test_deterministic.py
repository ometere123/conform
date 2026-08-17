#!/usr/bin/env python3
"""Run Conform's deterministic helpers without importing GenLayer.

This script reads the real contract source, extracts only constants and pure
helper functions with Python's AST, then executes invariants against those exact
functions. It deliberately does not import `genlayer`, invoke GenVM, or run the
GenVM linter.

Usage:
    python scripts/test_deterministic.py
"""

from __future__ import annotations

import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "conform.py"

CONSTANTS = {
    "AUDIT_CONFORMANT",
    "AUDIT_DEGRADED",
    "AUDIT_BREACHED",
    "AUDIT_UNAVAILABLE",
    "AUDIT_INCONCLUSIVE",
    "PROBE_PASS",
    "PROBE_FAIL",
    "PROBE_INCONCLUSIVE",
    "PROBE_UNAVAILABLE",
    "METHOD_GET",
    "METHOD_POST",
    "SEVERITY_INFO",
    "SEVERITY_NORMAL",
    "SEVERITY_CRITICAL",
    "MAX_EVIDENCE_LEN",
}

FUNCTIONS = {
    "clean_text",
    "host_of",
    "endpoint_is_safe",
    "join_url",
    "method_name",
    "status_name",
    "probe_verdict_name",
    "response_class",
    "parse_request_body",
    "response_status",
    "canonical_definition_payload",
    "definition_hash",
    "valid_decision_shape",
    "canonical_decision",
    "aggregate_results",
}


def load_helpers() -> dict:
    source = CONTRACT.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(CONTRACT))
    selected: list[ast.stmt] = [
        ast.Import(names=[ast.alias(name="json")]),
        ast.ImportFrom(module="eth_hash.auto", names=[ast.alias(name="keccak")], level=0),
    ]

    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {
                target.id
                for target in node.targets
                if isinstance(target, ast.Name)
            }
            if names & CONSTANTS:
                selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in FUNCTIONS:
            selected.append(node)

    namespace: dict = {}
    module = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, str(CONTRACT), "exec"), namespace)

    missing = sorted((CONSTANTS | FUNCTIONS) - set(namespace))
    if missing:
        raise AssertionError(f"helper extraction missed: {missing}")
    return namespace


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


def run() -> None:
    h = load_helpers()

    # URL construction and origin-safety invariants.
    check(h["join_url"]("https://agent.example/api/", "/transfer") == "https://agent.example/api/transfer", "join_url")
    for unsafe in (
        "http://localhost",
        "http://localhost.",
        "http://127.0.0.1:8080",
        "http://10.0.0.8",
        "http://172.16.0.1",
        "http://172.31.255.254",
        "http://192.168.1.2",
        "http://169.254.169.254",
        "http://service.internal",
        "http://thing.local",
        "https://user:password@agent.example/api",
        "https://8.8.8.8/service",
        "https://api.example.org:443/service",
        "https://api.example.org/path?x=1",
        "http://[::1]",
    ):
        check(not h["endpoint_is_safe"](unsafe), f"unsafe endpoint accepted: {unsafe}")

    for safe in (
        "https://agent.example/api",
        "https://api.example.com/v1",
        "https://api.example.org/service",
    ):
        check(h["endpoint_is_safe"](safe), f"public endpoint rejected: {safe}")

    # Request-body parsing is deterministic and refuses scalar JSON.
    check(h["parse_request_body"]('{"x":1}') == {"x": 1}, "object JSON")
    check(h["parse_request_body"]('[1,2]') == [1, 2], "array JSON")
    class Status:
        status = 200
    class StatusCode:
        status_code = 204
    check(h["response_status"](Status()) == 200, "live response status")
    check(h["response_status"](StatusCode()) == 204, "documented response status_code")
    try:
        h["response_status"](type("Bad", (), {"status": True})())
    except ValueError:
        pass
    else:
        raise AssertionError("boolean response status accepted")
    payload = [{"probe_id": 1, "method": 1, "path": "/health", "enabled": True}]
    first_hash = h["definition_hash"]("https://api.example.org", "healthy", 8000, 5000, 300, 1, payload)
    second_hash = h["definition_hash"]("https://api.example.org", "healthy", 8000, 5000, 300, 1, payload)
    check(first_hash == second_hash and len(first_hash) == 64, "definition hash determinism")
    check(h["valid_decision_shape"]({"verdict": h["PROBE_PASS"], "http_class": 2, "reason_code": "OK", "evidence": "ok"}), "typed decision")
    check(not h["valid_decision_shape"]({"verdict": True, "http_class": 2, "reason_code": "OK", "evidence": "ok"}), "boolean verdict rejected")
    for scalar in ("1", '"text"', "true", "null"):
        try:
            h["parse_request_body"](scalar)
        except ValueError:
            pass
        else:
            raise AssertionError(f"scalar request body accepted: {scalar}")

    # Canonical LLM decisions remain bounded even with malformed content.
    d = h["canonical_decision"](
        {"verdict": " pass ", "reason_code": " expected_refusal ", "evidence": "  refused   safely "},
        403,
    )
    check(d["verdict"] == h["PROBE_PASS"], "canonical PASS")
    check(d["http_class"] == 4, "HTTP class")
    check(d["reason_code"] == "EXPECTED_REFUSAL", "reason canonicalisation")
    check(d["evidence"] == "refused safely", "evidence canonicalisation")

    malformed = h["canonical_decision"]("not-a-dict", 200)
    check(malformed["verdict"] == h["PROBE_INCONCLUSIVE"], "malformed model output must abstain")

    unknown = h["canonical_decision"]({"verdict": "MAYBE"}, 200)
    check(unknown["verdict"] == h["PROBE_INCONCLUSIVE"], "unknown verdict must abstain")

    # Aggregation invariants. The LLM never controls these outcomes.
    agg = h["aggregate_results"]([], 8000, 5000)
    check(agg["status"] == h["AUDIT_INCONCLUSIVE"], "empty audit")

    agg = h["aggregate_results"](
        [{"verdict": h["PROBE_UNAVAILABLE"], "severity": h["SEVERITY_NORMAL"]}],
        8000,
        5000,
    )
    check(agg["status"] == h["AUDIT_UNAVAILABLE"], "all unavailable")

    agg = h["aggregate_results"](
        [
            {"verdict": h["PROBE_PASS"], "severity": h["SEVERITY_NORMAL"]},
            {"verdict": h["PROBE_FAIL"], "severity": h["SEVERITY_CRITICAL"]},
            {"verdict": h["PROBE_PASS"], "severity": h["SEVERITY_NORMAL"]},
        ],
        8000,
        5000,
    )
    check(agg["status"] == h["AUDIT_BREACHED"], "critical failure override")
    check(agg["critical_failures"] == 1, "critical failure count")

    agg = h["aggregate_results"](
        [
            {"verdict": h["PROBE_PASS"], "severity": h["SEVERITY_NORMAL"]},
            {"verdict": h["PROBE_PASS"], "severity": h["SEVERITY_NORMAL"]},
            {"verdict": h["PROBE_FAIL"], "severity": h["SEVERITY_NORMAL"]},
        ],
        8000,
        5000,
    )
    check(agg["status"] == h["AUDIT_DEGRADED"], "2/3 should be degraded at 80/50 thresholds")
    check(agg["pass_bps"] == 6666, "basis-point floor")

    agg = h["aggregate_results"](
        [
            {"verdict": h["PROBE_PASS"], "severity": h["SEVERITY_NORMAL"]},
            {"verdict": h["PROBE_UNAVAILABLE"], "severity": h["SEVERITY_NORMAL"]},
            {"verdict": h["PROBE_INCONCLUSIVE"], "severity": h["SEVERITY_NORMAL"]},
        ],
        8000,
        5000,
    )
    check(agg["status"] == h["AUDIT_INCONCLUSIVE"], "majority non-observation must abstain")

    # Exhaustive small-state invariant sweep: outputs stay bounded and counts add.
    verdicts = [h["PROBE_PASS"], h["PROBE_FAIL"], h["PROBE_INCONCLUSIVE"], h["PROBE_UNAVAILABLE"]]
    severities = [h["SEVERITY_INFO"], h["SEVERITY_NORMAL"], h["SEVERITY_CRITICAL"]]
    cases = 0
    for v1 in verdicts:
        for v2 in verdicts:
            for s1 in severities:
                for s2 in severities:
                    results = [
                        {"verdict": v1, "severity": s1},
                        {"verdict": v2, "severity": s2},
                    ]
                    out = h["aggregate_results"](results, 8000, 5000)
                    check(out["status"] in {
                        h["AUDIT_CONFORMANT"], h["AUDIT_DEGRADED"], h["AUDIT_BREACHED"],
                        h["AUDIT_UNAVAILABLE"], h["AUDIT_INCONCLUSIVE"],
                    }, "bounded audit status")
                    check(out["passed"] + out["failed"] + out["inconclusive"] + out["unavailable"] == 2, "count conservation")
                    check(0 <= out["pass_bps"] <= 10000, "bounded pass_bps")
                    cases += 1

    print(f"PASS: deterministic Conform checks succeeded ({cases} exhaustive two-probe combinations + edge cases)")


if __name__ == "__main__":
    run()
