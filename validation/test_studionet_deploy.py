from gltest import get_contract_factory, get_default_account
from gltest.assertions import tx_execution_succeeded
from gltest.utils import extract_contract_address


def test_deploy_conform_to_studionet():
    account = get_default_account()
    print(f"STUDIONET_DEPLOYER={account.address}")

    factory = get_contract_factory(contract_file_path="conform.py")
    receipt = factory.deploy_contract_tx(
        account=account,
        consensus_max_rotations=3,
    )

    print(f"STUDIONET_DEPLOY_RECEIPT={receipt}")
    assert tx_execution_succeeded(receipt), receipt

    address = extract_contract_address(receipt)
    print(f"STUDIONET_CONFORM_ADDRESS={address}")
    assert address is not None
