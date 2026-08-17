import inspect
import time
from pathlib import Path

from gltest import get_default_account
from gltest.assertions import tx_execution_succeeded
from gltest.clients import get_gl_client
from gltest.utils import extract_contract_address


def accepted_kwargs(call, values):
    params = inspect.signature(call).parameters
    return {key: value for key, value in values.items() if key in params}


def wait_for_acceptance(client, tx_hash):
    values = {
        "transaction_hash": tx_hash,
        "interval": 6000,
        "retries": 60,
        "full_transaction": True,
    }

    for attempt in range(4):
        try:
            return client.wait_for_transaction_receipt(
                **accepted_kwargs(client.wait_for_transaction_receipt, values)
            )
        except Exception as exc:
            if "Rate limit exceeded" not in str(exc) or attempt == 3:
                raise
            print(f"STUDIONET_RATE_LIMIT_BACKOFF attempt={attempt + 1}: {exc}")
            time.sleep(30)


def write(client, account, address, function_name, args):
    print(f"WRITE_SIGNATURE={inspect.signature(client.write_contract)}")
    values = {
        "address": address,
        "contract_address": address,
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
    return tx_hash, receipt


def read(client, account, address, function_name, args):
    print(f"READ_SIGNATURE={inspect.signature(client.read_contract)}")
    values = {
        "address": address,
        "contract_address": address,
        "function_name": function_name,
        "account": account,
        "args": args,
        "sim_config": None,
    }
    result = client.read_contract(**accepted_kwargs(client.read_contract, values))
    print(f"{function_name.upper()}_RESULT={result}")
    return result


def diagnostic_read(client, account, address, function_name, args):
    try:
        return read(client, account, address, function_name, args)
    except Exception as exc:
        print(f"{function_name.upper()}_READ_DIAGNOSTIC={type(exc).__name__}: {exc}")
        return None


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
    tx_hash = client.deploy_contract(**accepted_kwargs(client.deploy_contract, deploy_values))
    print(f"STUDIONET_DEPLOY_TX={tx_hash}")

    receipt = wait_for_acceptance(client, tx_hash)
    print(f"STUDIONET_DEPLOY_RECEIPT={receipt}")
    assert tx_execution_succeeded(receipt), receipt

    address = extract_contract_address(receipt)
    print(f"STUDIONET_CONFORM_ADDRESS={address}")
    assert address is not None

    register_tx, register_receipt = write(
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
    print(f"STUDIONET_REGISTER_TX={register_tx}")
    print(f"STUDIONET_REGISTER_RECEIPT={register_receipt}")

    probe_tx, probe_receipt = write(
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
    print(f"STUDIONET_ADD_PROBE_TX={probe_tx}")
    print(f"STUDIONET_ADD_PROBE_RECEIPT={probe_receipt}")

    agent = diagnostic_read(client, account, address, "get_agent", [1])
    if agent is not None:
        print(f"STUDIONET_AGENT={agent}")

    audit_tx, audit_receipt = write(client, account, address, "audit", [1])
    print(f"STUDIONET_AUDIT_TX={audit_tx}")
    print(f"STUDIONET_AUDIT_RECEIPT={audit_receipt}")

    audit = diagnostic_read(client, account, address, "get_audit", [1])
    if audit is not None:
        print(f"STUDIONET_AUDIT_VIEW={audit}")
        print(f"STUDIONET_AUDIT_STATUS={audit['status_name']}")
        print(f"STUDIONET_AUDIT_PASS_BPS={audit['pass_bps']}")
        assert audit["evaluated"] + audit["inconclusive"] + audit["unavailable"] == 1
        assert len(audit["results"]) == 1
