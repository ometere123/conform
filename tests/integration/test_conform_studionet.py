"""Disposable final-source Studionet proof.

Run explicitly with ``--network studionet``.  The generated gltest account is
used; no repository wallet, key, or secret is required.
"""

from pathlib import Path

from gltest import get_contract_factory, get_default_account


def test_final_source_can_deploy_on_studionet():
    account = get_default_account()
    factory = get_contract_factory(contract_file_path=Path("conform.py"))
    contract = factory.deploy(
        args=[],
        account=account,
        consensus_max_rotations=3,
        wait_interval=10000,
        wait_retries=20,
    )
    assert contract.address
    agent_id = contract.register_agent(
        "Conform Ubuntu proof",
        "https://test-server.genlayer.com",
        "The endpoint must expose a stable public health response.",
        8000,
        5000,
        0,
        account=account,
        wait_interval=10000,
        wait_retries=20,
    )
    probe_id = contract.add_probe(
        agent_id,
        "health",
        1,
        "/",
        "",
        "The endpoint must return a stable successful health response.",
        2,
        account=account,
        wait_interval=10000,
        wait_retries=20,
    )
    assert int(probe_id) == 1
    agent = contract.get_agent(agent_id)
    assert agent["current_definition_hash"]
    assert contract.is_audit_due(agent_id) is True
