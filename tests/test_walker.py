"""Walker tests against src/example/ fixtures."""

from cli import walker


# ---------- Atom ----------

def test_atom_bundle_shape(idx):
    bundle, _ = walker.walk(idx, "atm.pay.charge_card")
    assert bundle["target"] == {"id": "atm.pay.charge_card", "kind": "atom", "atom_kind": "PROCEDURAL"}
    assert bundle["l1_conventions"]["observability"]
    assert bundle["l2_module"]["id"] == "PAY"
    assert bundle["l3_atom"]["id"] == "atm.pay.charge_card"
    assert bundle["l5_operations"]["deployment"]


def test_atom_l0_slice_is_targeted(idx):
    bundle, _ = walker.walk(idx, "atm.pay.charge_card")
    slice_ = bundle["l0_registry_slice"]
    # Errors referenced by the atom are present.
    for code in ["PAY.VAL.001", "PAY.VAL.002", "PAY.NET.001", "PAY.EXT.003"]:
        assert code in slice_["errors"], f"{code} missing from slice"
    # Wrap_unexpected code is pulled in via L1.
    assert "SYS.SYS.999" in slice_["errors"]
    # Unrelated error is NOT included.
    assert "USR.VAL.001" not in slice_["errors"]
    # Constant referenced via const.MAX_CHARGE_CENTS is present.
    assert "MAX_CHARGE_CENTS" in slice_["constants"]
    # Markers declared in side_effects are present.
    for marker in ["WRITES_DB", "EMITS_EVENT", "CALLS_EXTERNAL"]:
        assert marker in slice_["side_effect_markers"]
    # Unrelated marker excluded.
    assert "READS_FS" not in slice_["side_effect_markers"]
    # External schema referenced in logic is present.
    assert "stripe" in slice_["external_schemas"]
    assert "sendgrid" not in slice_["external_schemas"]


def test_atom_l4_caller_detected(idx):
    bundle, _ = walker.walk(idx, "atm.pay.charge_card")
    callers = bundle["l4_callers"]
    assert "orchestrations" in callers
    flow_ctx = callers["orchestrations"][0]
    assert flow_ctx["flow_id"] == "flow.process_order_payment"
    assert flow_ctx["transaction_boundary"] == "saga"
    match = flow_ctx["matches"][0]
    assert match["step"] == "charge"
    assert match["compensation"] == "atm.pay.refund_charge"
    # Implications derived from on_error.
    implications = " ".join(flow_ctx["implications"])
    assert "retry-safe" in implications or "RETRY" in implications


def test_atom_policies_filtered(idx):
    # charge_card does NOT match the refund policy predicate.
    bundle, _ = walker.walk(idx, "atm.pay.charge_card")
    assert bundle["policies_applied"] == {}


def test_atom_unresolved_signatures(idx):
    bundle, unresolved = walker.walk(idx, "atm.pay.charge_card")
    sigs = bundle["called_atom_signatures"]
    # These atoms are referenced but have no spec file in the example set.
    for aid in ["atm.usr.fetch_customer", "atm.pay.find_by_idempotency_key", "atm.pay.persist_charge"]:
        assert sigs[aid]["status"] == "UNRESOLVED"
        assert aid in unresolved


# ---------- Module ----------

def test_module_bundle_shape(idx):
    bundle, _ = walker.walk(idx, "PAY")
    assert bundle["target"]["kind"] == "module"
    assert bundle["l2_module"]["id"] == "PAY"
    assert "atm.pay.charge_card" in bundle["owned_atoms"]
    # Aggregated L0 slice should cover the union of owned atoms.
    slice_ = bundle["l0_registry_slice"]
    assert "PAY.VAL.001" in slice_["errors"]
    # Tables' entity types are pulled in.
    assert "reg.pay.Charge" in slice_["types"]
    assert "reg.pay.Refund" in slice_["types"]


def test_module_shared_deps(idx):
    bundle, _ = walker.walk(idx, "PAY")
    shared = bundle["shared_module_interfaces"]
    assert "USR" in shared
    assert "NTF" in shared


# ---------- Flow ----------

def test_flow_bundle_shape(idx):
    bundle, _ = walker.walk(idx, "flow.process_order_payment")
    assert bundle["target"]["kind"] == "flow"
    assert bundle["l4_orchestration"]["id"] == "flow.process_order_payment"
    sigs = bundle["step_atom_signatures"]
    # Both invoke atoms and compensations are listed.
    assert "atm.pay.charge_card" in sigs
    assert "atm.pay.refund_charge" in sigs
    assert "atm.inv.release_items" in sigs
    # Trigger payload type pulled into L0 slice.
    assert "reg.ord.OrderPlacedEvent" in bundle["l0_registry_slice"]["types"]


def test_flow_entry_point_detected(idx):
    bundle, _ = walker.walk(idx, "flow.process_order_payment")
    # PAY module has an event_consumer entry point invoking this flow.
    eps = bundle["l2_entry_points"]
    assert any(ep.get("invokes") == "flow.process_order_payment" for ep in eps)


# ---------- Journey ----------

def test_journey_bundle_shape(idx):
    bundle, _ = walker.walk(idx, "jrn.signup_flow")
    assert bundle["target"]["kind"] == "journey"
    assert bundle["l4_journey"]["id"] == "jrn.signup_flow"
    # Handler atoms should have been resolved into the handler_atoms dict.
    assert isinstance(bundle["handler_atoms"], dict)


# ---------- Artifact ----------

def test_artifact_bundle_shape(idx):
    bundle, _ = walker.walk(idx, "art.usr.labeled_emails_v3")
    assert bundle["target"]["kind"] == "artifact"
    assert bundle["l3_artifact"]["id"] == "art.usr.labeled_emails_v3"
