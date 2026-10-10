"""Cascade / link helpers for World tab tables."""

from nowa_sandbox.gui_world_tab import (
    _choose_offer_link,
    _default_offer,
    _default_product,
    _default_supplier,
    _offer_pairs,
    _rename_offer_keys,
)


def test_rename_product_cascades_to_offers():
    offers = [
        _default_offer("product_001", "supplier_001"),
        _default_offer("product_002", "supplier_001"),
    ]
    out = _rename_offer_keys(
        offers, old_product="product_001", new_product="product_010"
    )
    assert out[0]["product_id"] == "product_010"
    assert out[1]["product_id"] == "product_002"


def test_rename_supplier_cascades_to_offers():
    offers = [_default_offer("product_001", "supplier_001")]
    out = _rename_offer_keys(
        offers, old_supplier="supplier_001", new_supplier="supplier_009"
    )
    assert out[0]["supplier_id"] == "supplier_009"


def test_offer_pairs_unique():
    offers = [
        _default_offer("A", "S1"),
        _default_offer("A", "S2"),
        _default_offer("A", "S1"),
    ]
    assert _offer_pairs(offers) == {("A", "S1"), ("A", "S2")}


def test_cascade_filter_products():
    offers = [
        _default_offer("A", "S1"),
        _default_offer("B", "S1"),
        _default_offer("A", "S2"),
    ]
    removed = {"A"}
    kept = [r for r in offers if str(r.get("product_id")) not in removed]
    assert len(kept) == 1
    assert kept[0]["product_id"] == "B"


def test_add_offer_keeps_product_one_when_pair_taken():
    """If product_001↔supplier_001 exists, add offer creates a new supplier, not product_002."""
    products = [_default_product("product_001")]
    suppliers = [_default_supplier("supplier_001")]
    offers = [_default_offer("product_001", "supplier_001")]
    choice = _choose_offer_link(
        products,
        suppliers,
        offers,
        preferred_product_id="product_001",
        preferred_supplier_id="supplier_001",
    )
    assert choice["product_id"] == "product_001"
    assert choice["create_product"] is False
    assert choice["create_supplier"] is True
    assert choice["supplier_id"] == "supplier_002"


def test_add_offer_uses_free_supplier_for_same_product():
    products = [_default_product("product_001")]
    suppliers = [
        _default_supplier("supplier_001"),
        _default_supplier("supplier_002"),
    ]
    offers = [_default_offer("product_001", "supplier_001")]
    choice = _choose_offer_link(
        products,
        suppliers,
        offers,
        preferred_product_id="product_001",
    )
    assert choice == {
        "product_id": "product_001",
        "supplier_id": "supplier_002",
        "create_product": False,
        "create_supplier": False,
    }


def test_add_offer_empty_tables_bootstraps_once():
    choice = _choose_offer_link([], [], [])
    assert choice["create_product"] is True
    assert choice["create_supplier"] is True
