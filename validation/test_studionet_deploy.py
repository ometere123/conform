import inspect
from pathlib import Path

from gltest import get_default_account
from gltest.assertions import tx_execution_succeeded
from gltest.clients import get_gl_client
from gltest.utils import extract_contract_address


def accepted_kwargs(call, values):
    params = inspect.signature(call).parameters
    return {key: value for key, value in values.items() if key in params}


def wait_for_acceptance(client, tx_hash):
    return client.wait_for_transaction_receipt(
        **accepted_kwargs(
            client.wait_for_transaction_receipt,
            {
                "transaction_hash": tx_hash,
                "interval": 2000,
                "retries": 60,
                "full_transaction": True,
            },
        )
    )


def write(client, account, address, function_name, args):
    print(f"WRITE_SIGNATURE={inspect.signature(client.write_contract)}")
    values = {
        "address": address,
        "function_name": function_name,
        "account": account,
        "value": 0,
        "consensus_max_rotations": 3,
        "leader_only": False,
        "args": args,
        "sim_config": None,
    }
    tx_hash = client.write_contract(**accepted_kwargs(client.write_contract, values))
    print(f"{function_name.upper()}_TX={tx_hash}")
    receipt = wait_for_acceptance(client, tx_hash)
    print(f"{function_name.upper()}_RECEIPT={receipt}")
    assert tx_execution_succeeded(receipt), receipt
    return receipt


def read(client, account, address, function_name, args):
    print(f"READ_SIGNATURE={inspect.signature(client.read_contract)}")
    values = {
        "address": address,
        "function_name": function_name,
        "account": account,
        "args": args,
        "sim_config": None,
    }
    result = client.read_contract(**accepted_kwargs(client.read_contract, values))
    print(f"{function_name.upper()}_RESULT={result}")
    return result


def test_full_conform_lifecycle_on_studionet():
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
    tx_hash = client.deploy_contract(
        **accepted_kwargs(client.deploy_contract, deploy_values)
    )
    print(f"STUDIONET_DEPLOY_TX={tx_hash}")

    receipt = wait_for_acceptance(client, tx_hash)
    print(f"STUDIONET_DEPLOY_RECEIPT={receipt}")
    assert tx_execution_succeeded(receipt), receipt

    address = extract_contract_address(receipt)
    print(f"STUDIONET_CONFORM_ADDRESS={address}")
    assert address is not None

    write(
        client,
        account,
        address,
        "register_agent",
        [
            "Conform Studionet Smoke",
            "https://example.com",
            "The endpoint should identify itself as the Example Domain used for illustrative examples.",
            8000,
            5000,
        ],
    )

    write(
        client,
        account,
        address,
        "add_probe",
        [
            1,
            "example domain identity",
            1,
            "",
            "",
            "The response should identify the Example Domain and indicate that it is intended for illustrative examples.",
            2,
        ],
    )

    agent = read(client, account, address, "get_agent", [1])
    assert agent["name"] == "Conform Studionet Smoke"
    assert agent["probe_count"] == 1
    assert agent["spec_version"] == 2

    write(client, account, address, "audit", [1])

    audit = read(client, account, address, "get_audit", [1])
    print(f"STUDIONET_AUDIT_STATUS={audit['status_name']}")
    print(f"STUDIONET_AUDIT_PASS_BPS={audit['pass_bps']}")
    assert audit["evaluated"] + audit["inconclusive"] + audit["unavailable"] == 1
    assert len(audit["results"]) == 1
