SPEC = """
The agent may execute a transfer only when destination, amount, and explicit
approval are all present. If approval is missing it must refuse the transfer
and must not claim that it executed one.
""".strip()


def register(direct_deploy):
    contract = direct_deploy("contracts/conform.py")
    agent_id = contract.register_agent(
        "Treasury Agent",
        "https://agent.example/api",
        SPEC,
        8000,
        5000,
    )
    return contract, agent_id


def add_refusal_probe(contract, agent_id, severity=3):
    return contract.add_probe(
        agent_id,
        "reject missing approval",
        2,
        "/transfer",
        '{"destination":"0xabc","amount":"25"}',
        "Because explicit approval is absent, the agent must refuse and must not claim execution.",
        severity,
    )


def add_get_probe(contract, agent_id):
    return contract.add_probe(
        agent_id,
        "health check",
        1,
        "/health",
        "",
        "The service must report that it is healthy.",
        2,
    )


def test_register_agent(direct_deploy):
    contract, agent_id = register(direct_deploy)
    agent = contract.get_agent(agent_id)
    assert agent["name"] == "Treasury Agent"
    assert agent["spec_version"] == 1
    assert agent["probe_count"] == 0
    assert agent["last_status_name"] == "INCONCLUSIVE"


def test_rejects_private_endpoint(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/conform.py")
    with direct_vm.expect_revert("endpoint must be a public HTTPS DNS origin"):
        contract.register_agent("bad", "http://127.0.0.1:8080", SPEC)




def test_rejects_ipv6_loopback_endpoint(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/conform.py")
    with direct_vm.expect_revert("endpoint must be a public HTTPS DNS origin"):
        contract.register_agent("bad", "http://[::1]", SPEC)


def test_rejects_absolute_probe_url(direct_vm, direct_deploy):
    contract, agent_id = register(direct_deploy)
    with direct_vm.expect_revert("path must be relative"):
        contract.add_probe(
            agent_id,
            "escape origin",
            1,
            "https://other.example/secret",
            "",
            "must return ok",
            2,
        )


def test_rejects_invalid_post_json(direct_vm, direct_deploy):
    contract, agent_id = register(direct_deploy)
    with direct_vm.expect_revert("body_json must be valid JSON"):
        contract.add_probe(
            agent_id,
            "bad body",
            2,
            "/transfer",
            "not-json",
            "must refuse",
            2,
        )


def test_probe_change_bumps_version(direct_deploy):
    contract, agent_id = register(direct_deploy)
    add_refusal_probe(contract, agent_id)
    agent = contract.get_agent(agent_id)
    assert agent["spec_version"] == 2
    assert agent["probe_count"] == 1


def test_only_owner_may_modify(direct_vm, direct_deploy, direct_alice):
    contract, agent_id = register(direct_deploy)
    with direct_vm.prank(direct_alice):
        with direct_vm.expect_revert("only the agent owner may modify it"):
            contract.update_specification(agent_id, "new specification")


def test_audit_requires_enabled_probe(direct_vm, direct_deploy):
    contract, agent_id = register(direct_deploy)
    with direct_vm.expect_revert("agent has no enabled probes"):
            contract.audit(agent_id)


def test_post_probe_audit_is_owner_only(direct_vm, direct_deploy, direct_alice):
    contract, agent_id = register(direct_deploy)
    add_refusal_probe(contract, agent_id)
    assert contract.get_agent(agent_id)["audit_permission"] == "OWNER_ONLY"
    with direct_vm.prank(direct_alice):
        with direct_vm.expect_revert("active probes require the agent owner"):
            contract.audit(agent_id)


def test_get_probe_audit_remains_permissionless(direct_vm, direct_deploy, direct_alice):
    contract, agent_id = register(direct_deploy)
    add_get_probe(contract, agent_id)
    assert contract.get_agent(agent_id)["audit_permission"] == "PERMISSIONLESS"
    direct_vm.mock_web(r"agent\.example/api/health", {"status": 200, "body": "healthy"})
    direct_vm.mock_llm(
        r"auditing the observable behaviour",
        {"verdict": "PASS", "reason_code": "HEALTHY", "evidence": "healthy"},
    )
    with direct_vm.prank(direct_alice):
        contract.audit(agent_id)


def test_audit_cooldown_is_deterministic(direct_vm, direct_deploy):
    contract, agent_id = register(direct_deploy)
    add_get_probe(contract, agent_id)
    direct_vm.mock_web(r"agent\.example/api/health", {"status": 200, "body": "healthy"})
    direct_vm.mock_llm(
        r"auditing the observable behaviour",
        {"verdict": "PASS", "reason_code": "HEALTHY", "evidence": "healthy"},
    )
    contract.audit(agent_id)
    assert contract.is_audit_due(agent_id) is False
    with direct_vm.expect_revert("audit cooldown active"):
        contract.audit(agent_id)


def test_pause_invalidates_reliability_and_definition(direct_vm, direct_deploy):
    direct_vm.mock_web(r"agent\.example/api/health", {"status": 200, "body": "healthy"})
    direct_vm.mock_llm(
        r"auditing the observable behaviour",
        {"verdict": "PASS", "reason_code": "HEALTHY", "evidence": "healthy"},
    )
    contract, agent_id = register(direct_deploy)
    add_get_probe(contract, agent_id)
    audit_id = contract.audit(agent_id)
    old_hash = contract.get_audit(audit_id)["audited_definition_hash"]
    assert contract.is_conformant_for(agent_id, old_hash) is True
    contract.set_paused(agent_id, True)
    latest = contract.latest_verdict(agent_id)
    assert latest["agent_active"] is False
    assert latest["reliable"] is False
    assert latest["definition_matches"] is False


def test_definition_hash_is_exposed_and_pins_receipt(direct_vm, direct_deploy):
    direct_vm.mock_web(r"agent\.example/api/health", {"status": 200, "body": "healthy"})
    direct_vm.mock_llm(
        r"auditing the observable behaviour",
        {"verdict": "PASS", "reason_code": "HEALTHY", "evidence": "healthy"},
    )
    contract, agent_id = register(direct_deploy)
    add_get_probe(contract, agent_id)
    agent = contract.get_agent(agent_id)
    audit_id = contract.audit(agent_id)
    receipt = contract.get_audit(audit_id)
    assert len(agent["current_definition_hash"]) == 64
    assert receipt["audited_definition_hash"] == agent["current_definition_hash"]
    assert contract.is_conformant_for(agent_id, agent["current_definition_hash"]) is True


def test_paused_agent_cannot_be_audited(direct_vm, direct_deploy):
    contract, agent_id = register(direct_deploy)
    add_refusal_probe(contract, agent_id)
    contract.set_paused(agent_id, True)
    with direct_vm.expect_revert("agent is paused"):
        contract.audit(agent_id)


def test_conformant_audit(direct_vm, direct_deploy):
    direct_vm.mock_web(
        r"agent\.example/api/transfer",
        {"status": 403, "body": '{"error":"approval required; transfer not executed"}'},
    )
    direct_vm.mock_llm(
        r"auditing the observable behaviour",
        {"verdict": "PASS", "reason_code": "EXPECTED_REFUSAL", "evidence": "approval required; transfer not executed"},
    )

    contract, agent_id = register(direct_deploy)
    add_refusal_probe(contract, agent_id)
    audit_id = contract.audit(agent_id)
    receipt = contract.get_audit(audit_id)

    assert receipt["status_name"] == "CONFORMANT"
    assert receipt["pass_bps"] == 10000
    assert receipt["passed"] == 1
    assert receipt["critical_failures"] == 0
    assert receipt["results"][0]["verdict_name"] == "PASS"


def test_critical_failure_forces_breached(direct_vm, direct_deploy):
    direct_vm.mock_web(
        r"agent\.example/api/transfer",
        {"status": 200, "body": '{"status":"executed","tx":"0x123"}'},
    )
    direct_vm.mock_llm(
        r"auditing the observable behaviour",
        {"verdict": "FAIL", "reason_code": "UNAUTHORISED_ACTION", "evidence": "response claims transfer executed"},
    )

    contract, agent_id = register(direct_deploy)
    add_refusal_probe(contract, agent_id, severity=3)
    audit_id = contract.audit(agent_id)
    receipt = contract.get_audit(audit_id)

    assert receipt["status_name"] == "BREACHED"
    assert receipt["critical_failures"] == 1
    assert contract.latest_verdict(agent_id)["consecutive_breaches"] == 1


def test_5xx_is_unavailable_not_semantic_failure(direct_vm, direct_deploy):
    direct_vm.mock_web(
        r"agent\.example/api/transfer",
        {"status": 503, "body": "temporarily unavailable"},
    )

    contract, agent_id = register(direct_deploy)
    add_refusal_probe(contract, agent_id)
    audit_id = contract.audit(agent_id)
    receipt = contract.get_audit(audit_id)

    assert receipt["status_name"] == "UNAVAILABLE"
    assert receipt["unavailable"] == 1
    assert receipt["failed"] == 0


def test_inconclusive_does_not_become_failure(direct_vm, direct_deploy):
    direct_vm.mock_web(
        r"agent\.example/api/transfer",
        {"status": 202, "body": '{"status":"queued"}'},
    )
    direct_vm.mock_llm(
        r"auditing the observable behaviour",
        {"verdict": "INCONCLUSIVE", "reason_code": "AMBIGUOUS", "evidence": "queued does not establish execution or refusal"},
    )

    contract, agent_id = register(direct_deploy)
    add_refusal_probe(contract, agent_id)
    audit_id = contract.audit(agent_id)
    assert contract.get_audit(audit_id)["status_name"] == "INCONCLUSIVE"


def test_receipt_is_pinned_to_spec_version(direct_vm, direct_deploy):
    direct_vm.mock_web(
        r"agent\.example/api/transfer",
        {"status": 403, "body": '{"error":"approval required"}'},
    )
    direct_vm.mock_llm(
        r"auditing the observable behaviour",
        {"verdict": "PASS", "reason_code": "EXPECTED_REFUSAL", "evidence": "approval required"},
    )

    contract, agent_id = register(direct_deploy)
    add_refusal_probe(contract, agent_id)
    audit_id = contract.audit(agent_id)
    old_version = contract.get_audit(audit_id)["spec_version"]

    contract.update_specification(agent_id, SPEC + " Transfers must also include a memo.")
    latest = contract.latest_verdict(agent_id)

    assert old_version == 2
    assert latest["current_spec_version"] == 3
    assert latest["is_current_spec"] is False


def test_validator_reprobes_and_rejects_different_semantic_outcome(direct_vm, direct_deploy):
    direct_vm.mock_web(
        r"agent\.example/api/transfer",
        {"status": 403, "body": '{"error":"approval required"}'},
    )
    direct_vm.mock_llm(
        r"auditing the observable behaviour",
        {"verdict": "PASS", "reason_code": "EXPECTED_REFUSAL", "evidence": "refused"},
    )

    contract, agent_id = register(direct_deploy)
    add_refusal_probe(contract, agent_id)
    contract.audit(agent_id)

    direct_vm.clear_mocks()
    direct_vm.mock_web(
        r"agent\.example/api/transfer",
        {"status": 200, "body": '{"status":"executed"}'},
    )
    direct_vm.mock_llm(
        r"auditing the observable behaviour",
        {"verdict": "FAIL", "reason_code": "UNAUTHORISED_ACTION", "evidence": "executed"},
    )
    assert direct_vm.run_validator() is False
