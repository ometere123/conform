"""Disposable final-source Studionet proof.

Run explicitly with ``--network studionet``.  The generated gltest account is
used; no repository wallet, key, or secret is required.
"""

from pathlib import Path

from gltest import get_contract_factory, get_default_account
from gltest.assertions import tx_execution_succeeded


TX_KW = {"consensus_max_rotations": 3, "wait_interval": 10000, "wait_retries": 20}


def test_final_source_can_deploy_on_studionet():
    account = get_default_account()
    factory = get_contract_factory(contract_file_path=Path("conform.py"))
    contract = factory.deploy(
        args=[],
        account=account,
        **TX_KW,
    )
    assert contract.address
    registered = contract.register_agent(
        [
            "Conform Ubuntu proof",
            "https://test-server.genlayer.com",
            "The endpoint must expose a stable public health response.",
            8000,
            5000,
            0,
        ]
    ).transact(**TX_KW)
    assert tx_execution_succeeded(registered), registered
    agent_id = 1
    added = contract.add_probe(
        [agent_id, "health", 1, "/", "", "The endpoint must return a stable successful health response.", 2]
    ).transact(**TX_KW)
    assert tx_execution_succeeded(added), added
    agent = contract.get_agent([agent_id]).call()
    current_hash = agent["current_definition_hash"]
    assert current_hash
    assert contract.is_audit_due([agent_id]).call() is True

    audited = contract.audit([agent_id]).transact(**TX_KW)
    assert tx_execution_succeeded(audited), audited
    audit_id = 1
    receipt = contract.get_audit([audit_id]).call()
    verdict = contract.latest_verdict([agent_id]).call()
    print("AUDIT_TX", audited)
    print("AUDIT_RECEIPT", receipt)
    print("LATEST_VERDICT", verdict)
    assert receipt["audited_at"] > 0
    assert receipt["audited_definition_hash"] == current_hash
    assert verdict["definition_matches"] is True
    assert verdict["is_current_spec"] is True
    assert contract.is_conformant_for([agent_id, current_hash]).call() in (True, False)

    changed = contract.update_specification(
        [agent_id, "The endpoint must expose a stable public response and remain available."]
    ).transact(**TX_KW)
    assert tx_execution_succeeded(changed), changed
    stale = contract.latest_verdict([agent_id]).call()
    print("STALE_VERDICT", stale)
    assert stale["definition_matches"] is False
    assert stale["reliable"] is False
    assert contract.is_conformant_for([agent_id, current_hash]).call() is False


def test_owner_can_audit_harmless_post_profile_on_studionet():
    account = get_default_account()
    factory = get_contract_factory(contract_file_path=Path("conform.py"))
    contract = factory.deploy(account=account, **TX_KW)
    registered = contract.register_agent(
        [
            "Conform POST proof",
            "https://test-server.genlayer.com",
            "The endpoint must echo a harmless request without side effects.",
            8000,
            5000,
            0,
        ]
    ).transact(**TX_KW)
    assert tx_execution_succeeded(registered), registered
    added = contract.add_probe(
        [1, "echo", 2, "/body/echo", '{"proof":"conform"}', "The endpoint must echo the request body.", 2]
    ).transact(**TX_KW)
    assert tx_execution_succeeded(added), added
    owner_audit = contract.audit([1]).transact(**TX_KW)
    print("POST_OWNER_AUDIT", owner_audit)
    assert tx_execution_succeeded(owner_audit), owner_audit
