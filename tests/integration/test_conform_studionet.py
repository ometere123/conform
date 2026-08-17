"""Disposable final-source Studionet lifecycle proof."""

from pathlib import Path

from gltest import get_contract_factory, get_default_account
from gltest.assertions import tx_execution_succeeded

TX_KW = {"consensus_max_rotations": 3, "wait_interval": 10000, "wait_retries": 20}
GET_SPEC = "The endpoint must expose a stable public health response."


def deploy_get_profile():
    account = get_default_account()
    contract = get_contract_factory(contract_file_path=Path("conform.py")).deploy(
        account=account, **TX_KW
    )
    assert contract.address
    registered = contract.register_agent(
        ["Conform GET proof", "https://test-server.genlayer.com", GET_SPEC, 8000, 5000, 0]
    ).transact(**TX_KW)
    assert tx_execution_succeeded(registered), registered
    added = contract.add_probe(
        [1, "health", 1, "/static/genvm/hello.html", "", "The endpoint must return a stable successful response.", 2]
    ).transact(**TX_KW)
    assert tx_execution_succeeded(added), added
    return contract


def test_final_source_can_deploy_and_register_on_studionet():
    contract = deploy_get_profile()
    assert contract.get_agent([1]).call()["current_definition_hash"]
    assert contract.is_audit_due([1]).call() is True


def test_passive_get_audit_and_reads_on_studionet():
    contract = deploy_get_profile()
    current_hash = contract.get_agent([1]).call()["current_definition_hash"]
    audited = contract.audit([1]).transact(**TX_KW)
    assert tx_execution_succeeded(audited), audited
    receipt = contract.get_audit([1]).call()
    verdict = contract.latest_verdict([1]).call()
    print("AUDIT_TX", audited)
    print("AUDIT_RECEIPT", receipt)
    print("LATEST_VERDICT", verdict)
    assert receipt["audited_at"] > 0
    assert receipt["audited_definition_hash"] == current_hash
    assert verdict["definition_matches"] is True
    assert verdict["is_current_spec"] is True
    assert contract.is_conformant_for([1, current_hash]).call() in (True, False)


def test_definition_freshness_on_studionet():
    contract = deploy_get_profile()
    current_hash = contract.get_agent([1]).call()["current_definition_hash"]
    audited = contract.audit([1]).transact(**TX_KW)
    assert tx_execution_succeeded(audited), audited
    changed = contract.update_specification(
        [1, GET_SPEC + " The response must remain available."]
    ).transact(**TX_KW)
    assert tx_execution_succeeded(changed), changed
    stale = contract.latest_verdict([1]).call()
    print("STALE_VERDICT", stale)
    assert stale["definition_matches"] is False
    assert stale["reliable"] is False
    assert contract.is_conformant_for([1, current_hash]).call() is False


def test_owner_can_audit_harmless_post_profile_on_studionet():
    account = get_default_account()
    contract = get_contract_factory(contract_file_path=Path("conform.py")).deploy(
        account=account, **TX_KW
    )
    registered = contract.register_agent(
        ["Conform POST proof", "https://test-server.genlayer.com", "The endpoint must echo a harmless request.", 8000, 5000, 0]
    ).transact(**TX_KW)
    assert tx_execution_succeeded(registered), registered
    added = contract.add_probe(
        [1, "echo", 2, "/body/echo", '{"proof":"conform"}', "The endpoint must echo the request body.", 2]
    ).transact(**TX_KW)
    assert tx_execution_succeeded(added), added
    owner_audit = contract.audit([1]).transact(**TX_KW)
    print("POST_OWNER_AUDIT", owner_audit)
    assert tx_execution_succeeded(owner_audit), owner_audit
