#!/usr/bin/env python3
"""Apply the two evidence-backed Conform fixes in a CI checkout.

This script is validation-only. It deliberately edits the checked-out contract
rather than the repository branch so the proposed source changes can be tested
before they are promoted.
"""

from pathlib import Path


PATH = Path(__file__).resolve().parents[1] / "contracts" / "conform.py"
source = PATH.read_text(encoding="utf-8")

old_host = '''    if "@" in text:
        text = text.split("@", 1)[1]
    if ":" in text:
        text = text.split(":", 1)[0]
    return text.strip(".")
'''
new_host = '''    if "@" in text:
        text = text.split("@", 1)[1]
    if text.startswith("["):
        end = text.find("]")
        if end == -1:
            return ""
        return text[1:end].strip(".")
    if ":" in text:
        text = text.split(":", 1)[0]
    return text.strip(".")
'''

old_endpoint = '''    if host in ("localhost", "0.0.0.0", "::1"):
        return False
    if host.endswith(".local") or host.endswith(".internal"):
'''
new_endpoint = '''    if host in ("localhost", "0.0.0.0", "::1"):
        return False
    if ":" in host:
        # Fail closed for IPv6 until private/link-local IPv6 classification is
        # implemented. This prevents alternate-address SSRF bypasses.
        return False
    if host.endswith(".local") or host.endswith(".internal"):
'''

old_active = '''        active: list[Probe] = []
        for probe in agent.probes:
            if bool(probe.enabled):
                active.append(probe)
'''
new_active = '''        active: list[Probe] = []
        for probe in agent.probes:
            if bool(probe.enabled):
                # Storage-backed objects must be copied before they are captured
                # by non-deterministic leader/validator closures.
                active.append(gl.storage.copy_to_memory(probe))
'''

for label, old, new in (
    ("IPv6 host parsing", old_host, new_host),
    ("IPv6 fail-closed guard", old_endpoint, new_endpoint),
    ("storage-to-memory probe snapshot", old_active, new_active),
):
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"refusing patch: expected one {label} target, found {count}")
    source = source.replace(old, new, 1)

PATH.write_text(source, encoding="utf-8")
print("PASS: applied validation-only IPv6 and storage-snapshot fixes")
