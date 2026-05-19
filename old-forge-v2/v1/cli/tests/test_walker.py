"""Walker tests against the example spec (LinkHub)."""

from cli import walker


SHORT_LINK = "linkhub.shortener.links.link_manager.short_link"
REDIRECT = "linkhub.shortener.traffic.redirector.redirect"


# ---------------------------------------------------------------------------
# Bundle shape — short_link element
# ---------------------------------------------------------------------------

def test_short_link_target(idx):
    bundle, _ = walker.walk(idx, SHORT_LINK)
    assert bundle["target"]["id"] == SHORT_LINK
    assert bundle["target"]["kind"] == "element"
    assert bundle["target"]["element_kind"] == "aggregate"


def test_short_link_ancestors(idx):
    bundle, _ = walker.walk(idx, SHORT_LINK)
    assert bundle["module"]["id"] == "linkhub.shortener.links.link_manager"
    assert bundle["domain"]["id"] == "linkhub.shortener.links"
    assert bundle["system"]["id"] == "linkhub.shortener"


def test_short_link_contracts(idx):
    bundle, _ = walker.walk(idx, SHORT_LINK)
    assert "linkhub.shortener.contracts.create_short_link" in bundle["contracts"]
    assert "linkhub.shortener.contracts.resolve_short_link" in bundle["contracts"]


def test_short_link_types(idx):
    bundle, _ = walker.walk(idx, SHORT_LINK)
    types = bundle["types"]
    assert "linkhub.shortener.types.ShortCode" in types
    assert "linkhub.shortener.types.URL" in types
    assert "linkhub.shortener.types.CreateLinkInput" in types


def test_short_link_errors(idx):
    bundle, _ = walker.walk(idx, SHORT_LINK)
    errors = bundle["errors"]
    assert "linkhub.shortener.errors.InvalidUrl" in errors
    assert "linkhub.shortener.errors.LinkNotFound" in errors


def test_short_link_interactions(idx):
    bundle, _ = walker.walk(idx, SHORT_LINK)
    # redirector_resolves_link has callee = short_link.resolve
    assert "linkhub.shortener.interactions.redirector_resolves_link" in bundle["interactions"]


def test_short_link_datastores(idx):
    bundle, _ = walker.walk(idx, SHORT_LINK)
    assert "linkhub.shortener.datastores.links_db" in bundle["datastores"]


def test_short_link_policies_cascade_from_system(idx):
    bundle, _ = walker.walk(idx, SHORT_LINK)
    # standard_encryption is set at the system level and cascades down
    assert "linkhub.shortener.policies.standard_encryption" in bundle["policies_applied"]


def test_short_link_fully_resolved(idx):
    _, unresolved = walker.walk(idx, SHORT_LINK)
    assert unresolved == [], f"Unexpected unresolved refs: {unresolved}"


# ---------------------------------------------------------------------------
# Bundle shape — redirect element
# ---------------------------------------------------------------------------

def test_redirect_target(idx):
    bundle, _ = walker.walk(idx, REDIRECT)
    assert bundle["target"]["id"] == REDIRECT
    assert bundle["target"]["element_kind"] == "service"


def test_redirect_policies_include_sla(idx):
    bundle, _ = walker.walk(idx, REDIRECT)
    # redirect_sla is set at the element level
    assert "linkhub.shortener.policies.redirect_sla" in bundle["policies_applied"]
    # standard_encryption cascades from system
    assert "linkhub.shortener.policies.standard_encryption" in bundle["policies_applied"]


def test_redirect_contracts(idx):
    bundle, _ = walker.walk(idx, REDIRECT)
    assert "linkhub.shortener.contracts.resolve_short_link" in bundle["contracts"]


def test_redirect_interactions(idx):
    bundle, _ = walker.walk(idx, REDIRECT)
    # redirector_resolves_link has caller = redirect.resolve
    assert "linkhub.shortener.interactions.redirector_resolves_link" in bundle["interactions"]


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

def test_walk_unknown_id_raises_key_error(idx):
    import pytest
    with pytest.raises(KeyError):
        walker.walk(idx, "linkhub.shortener.nonexistent.element")


def test_walk_non_element_raises_value_error(idx):
    import pytest
    with pytest.raises(ValueError):
        walker.walk(idx, "linkhub.shortener.types.ShortCode")
