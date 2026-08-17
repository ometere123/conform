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
    assert agent["current_definition_hash"]
    assert contract.is_audit_due([agent_id]).call() is True
