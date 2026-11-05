from decimal import Decimal

from conftest import load_fixture

from pricebot.extract import (
    canonical_gtin,
    extract_page,
    extract_product,
    is_valid_gtin,
    normalize_url,
)
from pricebot.models import Availability, Condition

PAGE = "https://shop.example/categorie/c4402/"


def test_listing_page_reads_itemlist_products() -> None:
    data = extract_page(load_fixture("listing_itemlist.html"), PAGE)

    assert data.products == []
    assert len(data.listing) == 2  # le produit sans prix est ignoré
    first, second = data.listing
    assert first.title == 'Téléviseur Exemple 55" OLED'  # entité HTML décodée
    assert first.price == Decimal("1299.95")
    assert first.currency == "EUR"
    assert first.availability is Availability.IN_STOCK
    assert first.url == "https://shop.example/fiche/P001.html"
    assert first.image == "https://shop.example/img/P001.jpg"
    assert second.url == "https://shop.example/fiche/P002.html"  # URL relative complétée
    assert second.availability is Availability.OUT_OF_STOCK


def test_product_page_reads_all_details() -> None:
    url = "https://shop.example/fiche/P100.html"
    offer = extract_product(load_fixture("product_simple.html"), url)

    assert offer is not None
    assert offer.title == "Casque gaming Exemple GS505"
    assert offer.price == Decimal("129.90")
    assert offer.availability is Availability.IN_STOCK
    assert offer.condition is Condition.NEW
    assert offer.seller == "Boutique Exemple"
    assert offer.gtin == "3700527316901"
    assert offer.mpn == "EX316901"
    assert offer.sku == "SKU-0001"
    assert offer.brand == "Exemple Audio"
    assert offer.image == "https://shop.example/img/casque-1.jpg"
    assert offer.list_price is None
    assert offer.url == url


def test_marketplace_offer_keeps_list_price_seller_and_condition() -> None:
    url = "https://shop.example/p/m24070722510.html"
    offer = extract_product(load_fixture("product_marketplace.html"), url)

    assert offer is not None
    assert offer.price == Decimal("788.00")
    assert offer.list_price == Decimal("903.00")  # prix barré, pas le prix payé
    assert offer.seller == "Vendeur Tiers SARL"
    assert offer.condition is Condition.REFURBISHED


def test_aggregate_offer_is_not_a_product_price() -> None:
    data = extract_page(
        load_fixture("category_aggregate.html"), "https://shop.example/arrivages.html"
    )
    assert data.products == []
    assert data.listing == []


def test_graph_with_broken_block_comment_wrapper_and_several_offers() -> None:
    offer = extract_product(load_fixture("graph_multi_offers.html"), "https://shop.example/console")

    assert offer is not None
    assert offer.title == "Console de jeu Exemple Pro"
    # On garde l'offre la moins chère, avec son vendeur et sa disponibilité.
    assert offer.price == Decimal("749.50")
    assert offer.seller == "Autre vendeur"
    assert offer.availability is Availability.PREORDER
    assert offer.gtin == "0711719577294"  # GTIN-14 ramené en EAN-13


def test_opengraph_fallback() -> None:
    url = "https://shop.example/aspirateur-x1.html"
    offer = extract_product(load_fixture("opengraph_only.html"), url)

    assert offer is not None
    assert offer.title == "Aspirateur robot Exemple X1"
    assert offer.price == Decimal("1249.00")
    assert offer.url == url  # ancre #avis retirée
    assert offer.image == "https://shop.example/img/x1.jpg"


def test_page_without_structured_data() -> None:
    html = "<html><body><p>Prix : 12,99 €</p></body></html>"
    assert extract_product(html, "https://shop.example/x") is None


def test_product_group_variants_are_read() -> None:
    html = """
    <script type="application/ld+json">
    {"@context": "https://schema.org", "@type": "ProductGroup", "name": "T-shirt",
     "hasVariant": [
       {"@type": "Product", "name": "T-shirt S", "url": "/s",
        "offers": {"@type": "Offer", "price": "19.99"}},
       {"@type": "Product", "name": "T-shirt M", "url": "/m",
        "offers": {"@type": "Offer", "price": "21.99"}}
     ]}
    </script>"""
    data = extract_page(html, "https://shop.example/tshirt")
    assert [offer.title for offer in data.products] == ["T-shirt S", "T-shirt M"]
    assert data.products[0].url == "https://shop.example/s"


def test_gtin_validation() -> None:
    assert is_valid_gtin("3700527316901")
    assert not is_valid_gtin("3700527316902")  # mauvaise clé de contrôle
    assert not is_valid_gtin("12345")
    assert not is_valid_gtin("37005273169AB")
    assert canonical_gtin("00711719577294") == "0711719577294"
    assert canonical_gtin("711719577294") == "0711719577294"
    assert canonical_gtin("0000000000000") is None
    assert canonical_gtin("3700527316902") is None


def test_invalid_gtin_is_dropped() -> None:
    html = """<script type="application/ld+json">
    {"@type": "Product", "name": "X", "gtin13": "1234567890123",
     "offers": {"@type": "Offer", "price": "10"}}</script>"""
    offer = extract_product(html, "https://shop.example/x")
    assert offer is not None
    assert offer.gtin is None


def test_normalize_url() -> None:
    assert normalize_url(" https://shop.example/a#b ") == "https://shop.example/a"
