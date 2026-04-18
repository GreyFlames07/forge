"""Index loader + id dispatch tests."""

import pytest

from cli import index as index_mod


def test_loads_singletons(idx):
    assert idx.l0 and "naming_ledger" in idx.l0
    assert idx.l1 and "observability" in idx.l1
    assert idx.l5 and "deployment" in idx.l5


def test_loads_modules(idx):
    modules = {m.id for m in idx.by_kind("module")}
    assert "PAY" in modules
    assert "USR" in modules


def test_loads_atoms(idx):
    atoms = {a.id for a in idx.by_kind("atom")}
    assert "atm.pay.charge_card" in atoms


def test_loads_flows(idx):
    flows = {f.id for f in idx.by_kind("flow")}
    assert "flow.process_order_payment" in flows


def test_loads_journeys(idx):
    journeys = {j.id for j in idx.by_kind("journey")}
    assert "jrn.signup_flow" in journeys


def test_loads_policies(idx):
    policies = {p.id for p in idx.by_kind("policy")}
    assert "pol.pay.require_admin_for_refunds" in policies


def test_explodes_l0(idx):
    assert idx.get("PAY.VAL.001").kind == "error"
    assert idx.get("reg.pay.Charge").kind == "type"
    assert idx.get("MAX_CHARGE_CENTS").kind == "constant"
    assert idx.get("stripe").kind == "external_schema"
    assert idx.get("WRITES_DB").kind == "marker"


def test_classify_bundleable(idx):
    assert index_mod.classify(idx, "atm.pay.charge_card") == "atom"
    assert index_mod.classify(idx, "PAY") == "module"
    assert index_mod.classify(idx, "flow.process_order_payment") == "flow"


def test_classify_rejects_non_bundleable(idx):
    with pytest.raises(ValueError):
        index_mod.classify(idx, "PAY.VAL.001")
    with pytest.raises(ValueError):
        index_mod.classify(idx, "reg.pay.Charge")


def test_classify_unknown(idx):
    with pytest.raises(KeyError):
        index_mod.classify(idx, "atm.pay.does_not_exist")
