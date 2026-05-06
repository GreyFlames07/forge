"""Index loader and id-dispatch tests against the example spec (LinkHub)."""

import pytest

from cli import index as index_mod


# ---------------------------------------------------------------------------
# Structural nodes
# ---------------------------------------------------------------------------

def test_loads_conception(idx):
    entry = idx.get("linkhub")
    assert entry is not None
    assert entry.kind == "conception"


def test_loads_system(idx):
    entry = idx.get("linkhub.shortener")
    assert entry is not None
    assert entry.kind == "system"


def test_loads_domains(idx):
    domains = {e.id for e in idx.by_kind("domain")}
    assert "linkhub.shortener.links" in domains
    assert "linkhub.shortener.traffic" in domains


def test_loads_modules(idx):
    modules = {e.id for e in idx.by_kind("module")}
    assert "linkhub.shortener.links.link_manager" in modules
    assert "linkhub.shortener.traffic.redirector" in modules
    assert "linkhub.shortener.traffic.click_recorder" in modules


def test_loads_elements(idx):
    elements = {e.id for e in idx.by_kind("element")}
    assert "linkhub.shortener.links.link_manager.short_link" in elements
    assert "linkhub.shortener.traffic.redirector.redirect" in elements
    assert "linkhub.shortener.traffic.click_recorder.click" in elements


# ---------------------------------------------------------------------------
# Registry nodes
# ---------------------------------------------------------------------------

def test_loads_types(idx):
    types = {e.id for e in idx.by_kind("type")}
    assert "linkhub.shortener.types.ShortCode" in types
    assert "linkhub.shortener.types.URL" in types
    assert "linkhub.shortener.types.CreateLinkInput" in types
    assert "linkhub.shortener.types.ClickRecord" in types


def test_loads_errors(idx):
    errors = {e.id for e in idx.by_kind("error")}
    assert "linkhub.shortener.errors.InvalidUrl" in errors
    assert "linkhub.shortener.errors.LinkNotFound" in errors


def test_loads_policies(idx):
    policies = {e.id for e in idx.by_kind("policy")}
    assert "linkhub.shortener.policies.creator_auth" in policies
    assert "linkhub.shortener.policies.redirect_sla" in policies
    assert "linkhub.shortener.policies.standard_encryption" in policies


def test_loads_contracts(idx):
    contracts = {e.id for e in idx.by_kind("contract")}
    assert "linkhub.shortener.contracts.create_short_link" in contracts
    assert "linkhub.shortener.contracts.resolve_short_link" in contracts


def test_loads_interactions(idx):
    interactions = {e.id for e in idx.by_kind("interaction")}
    assert "linkhub.shortener.interactions.redirector_resolves_link" in interactions


def test_loads_flows(idx):
    flows = {e.id for e in idx.by_kind("flow")}
    assert "linkhub.shortener.flows.user_redirect" in flows


# ---------------------------------------------------------------------------
# Implementation nodes
# ---------------------------------------------------------------------------

def test_loads_datastores(idx):
    datastores = {e.id for e in idx.by_kind("datastore")}
    assert "linkhub.shortener.datastores.links_db" in datastores
    assert "linkhub.shortener.datastores.clicks_store" in datastores


def test_loads_environments(idx):
    envs = {e.id for e in idx.by_kind("environment")}
    assert len(envs) >= 1


def test_loads_tests(idx):
    tests = {e.id for e in idx.by_kind("test")}
    assert len(tests) >= 1


# ---------------------------------------------------------------------------
# Inline sub-nodes (properties + operations)
# ---------------------------------------------------------------------------

def test_indexes_inline_properties(idx):
    assert idx.get("linkhub.shortener.links.link_manager.short_link.code") is not None
    assert idx.get("linkhub.shortener.links.link_manager.short_link.destination_url") is not None
    prop = idx.get("linkhub.shortener.links.link_manager.short_link.code")
    assert prop.kind == "property"


def test_indexes_inline_operations(idx):
    op = idx.get("linkhub.shortener.links.link_manager.short_link.create")
    assert op is not None
    assert op.kind == "operation"
    op2 = idx.get("linkhub.shortener.links.link_manager.short_link.resolve")
    assert op2 is not None


# ---------------------------------------------------------------------------
# Framework builtins
# ---------------------------------------------------------------------------

def test_framework_builtins_indexed(idx):
    # Built-in scalars from framework.yaml
    assert idx.get("system.types.String") is not None
    assert idx.get("system.types.UUID") is not None
    # Built-in errors
    assert idx.get("system.errors.NotFound") is not None
    assert idx.get("system.errors.Unauthorized") is not None


# ---------------------------------------------------------------------------
# classify
# ---------------------------------------------------------------------------

def test_classify_element(idx):
    assert index_mod.classify(idx, "linkhub.shortener.links.link_manager.short_link") == "element"


def test_classify_rejects_non_bundleable_type(idx):
    with pytest.raises(ValueError):
        index_mod.classify(idx, "linkhub.shortener.types.ShortCode")


def test_classify_rejects_non_bundleable_error(idx):
    with pytest.raises(ValueError):
        index_mod.classify(idx, "linkhub.shortener.errors.InvalidUrl")


def test_classify_raises_for_unknown(idx):
    with pytest.raises(KeyError):
        index_mod.classify(idx, "linkhub.shortener.links.link_manager.does_not_exist")
