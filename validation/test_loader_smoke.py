def test_minimal_contract_loads(direct_deploy):
    contract = direct_deploy("validation/minimal_contract.py")
    assert int(contract.get()) == 1


def test_interface_contract_loads(direct_deploy):
    contract = direct_deploy("validation/interface_contract.py")
    assert int(contract.get()) == 1
