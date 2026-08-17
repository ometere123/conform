"""Single-disposable-deployment Studionet lifecycle proof."""

from pathlib import Path

from gltest import get_contract_factory, get_default_account
from gltest.assertions import tx_execution_succeeded


TX_KW = {"consensus_max_rotations": 3, "wait_interval": 10000, "wait_retries": 20}
SPEC = "The endpoint must expose a stable public health response."


def tx_summary(label, tx):
    if isinstance(tx, dict):
        safe = {key: tx[key] for key in ("transaction_hash", "status") if key in tx}
        consensus = tx.get("consensus_data")
        if isinstance(consensus, dict):
            safe["consensus_keys"] = sorted(consensus.keys())
            leaders = consensus.get("leader_receipt")
            if isinstance(leaders, list) and leaders and isinstance(leaders[0], dict):
                safe["leader_execution"] = leaders[0].get("execution_result")
        print(label, safe)
    else:
        print(label, {"type": type(tx).__name__})


def test_final_source_full_passive_lifecycle_on_studionet():
    account = get_default_account()
    contract = get_contract_factory(contract_file_path=Path("conform.py")).deploy(
        account=account, **TX_KW
    )
    print("DEPLOYED_CONTRACT", contract.address)

    registered = contract.register_agent(
        ["Conform GET proof", "https://test-server.genlayer.com", SPEC, 8000, 5000, 0]
    ).transact(**TX_KW)
    tx_summary("REGISTER", registered)
    assert tx_execution_succeeded(registered), registered

    added = contract.add_probe(
        [1, "health", 1, "/static/genvm/hello.html", "", "The endpoint must return a stable successful response.", 2]
    ).transact(**TX_KW)
    tx_summary("ADD_PROBE", added)
    assert tx_execution_succeeded(added), added

    agent = contract.get_agent([1]).call()
    current_hash = agent["current_definition_hash"]
    print("AGENT", {"agent_id": 1, "current_definition_hash": current_hash})
    assert current_hash

    audited = contract.audit([1]).transact(**TX_KW)
    tx_summary("AUDIT", audited)
    assert tx_execution_succeeded(audited), audited

    receipt = contract.get_audit([1]).call()
    verdict = contract.latest_verdict([1]).call()
    print("AUDIT_RECEIPT", {key: receipt.get(key) for key in ("audit_id", "status", "status_name", "audited_at", "audited_definition_hash")})
    print("LATEST_VERDICT", {key: verdict.get(key) for key in ("status", "status_name", "definition_matches", "is_current_spec", "reliable", "audited_at")})
    assert receipt["audited_at"] > 0
    assert receipt["audited_definition_hash"] == current_hash
    assert verdict["definition_matches"] is True
    assert verdict["is_current_spec"] is True
    assert contract.is_conformant_for([1, current_hash]).call() in (True, False)

    changed = contract.update_specification(
        [1, SPEC + " The response must remain available."]
    ).transact(**TX_KW)
    tx_summary("UPDATE_SPECIFICATION", changed)
    assert tx_execution_succeeded(changed), changed
    stale = contract.latest_verdict([1]).call()
    print("STALE_VERDICT", stale)
    assert stale["definition_matches"] is False
    assert stale["reliable"] is False
    assert contract.is_conformant_for([1, current_hash]).call() is False
