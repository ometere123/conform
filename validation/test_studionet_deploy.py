import inspect
from pathlib import Path

from gltest import get_default_account
from gltest.assertions import tx_execution_succeeded
from gltest.clients import get_gl_client
from gltest.utils import extract_contract_address


def accepted_kwargs(call, values):
    params = inspect.signature(call).parameters
    return {key: value for key, value in values.items() if key in params}


def test_deploy_conform_to_studionet():
    account = get_default_account()
    client = get_gl_client()
    code = Path("contracts/conform.py").read_text(encoding="utf-8")

    print(f"STUDIONET_DEPLOYER={account.address}")
    print(f"DEPLOY_SIGNATURE={inspect.signature(client.deploy_contract)}")

    deploy_values = {
        "code": code,
        "args": None,
        "account": account,
        "consensus_max_rotations": 3,
        "leader_only": False,
        "sim_config": None,
    }
    deploy_kwargs = accepted_kwargs(client.deploy_contract, deploy_values)
    print(f"DEPLOY_KWARGS={sorted(deploy_kwargs.keys())}")

    tx_hash = client.deploy_contract(**deploy_kwargs)
    print(f"STUDIONET_DEPLOY_TX={tx_hash}")

    print(f"WAIT_SIGNATURE={inspect.signature(client.wait_for_transaction_receipt)}")
    wait_values = {
        "transaction_hash": tx_hash,
        "wait_until": "decided",
        "interval": 2000,
        "retries": 60,
    }
    receipt = client.wait_for_transaction_receipt(
        **accepted_kwargs(client.wait_for_transaction_receipt, wait_values)
    )

    print(f"STUDIONET_DEPLOY_RECEIPT={receipt}")
    assert tx_execution_succeeded(receipt), receipt

    address = extract_contract_address(receipt)
    print(f"STUDIONET_CONFORM_ADDRESS={address}")
    assert address is not None
