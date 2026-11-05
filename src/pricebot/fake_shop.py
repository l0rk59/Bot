"""Faux magasin pour tester le bot sans toucher aux vrais sites.

Il imite un site marchand (page catégorie avec JSON-LD `ItemList`, fiches produit avec
JSON-LD `Product`). On change un prix depuis le navigateur, puis on regarde le bot réagir :

    http://127.0.0.1:8765/admin/prix?id=1&prix=129.90
    http://127.0.0.1:8765/admin/stock?id=1&dispo=0
"""

from __future__ import annotations

import html
import json
import logging
import threading
from dataclasses import dataclass
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import httpx

from pricebot.prices import format_price, parse_price

log = logging.getLogger(__name__)

PAGE_SIZE = 48
SELLER = "Faux magasin"


def gtin13(base12: str) -> str:
    """Complète 12 chiffres avec la clé de contrôle EAN-13."""
    total = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(base12))
    return base12 + str((10 - total % 10) % 10)


@dataclass
class FakeProduct:
    id: int
    name: str
    price: Decimal
    gtin: str
    in_stock: bool = True
    listing_price: Decimal | None = None  # prix différent sur la liste (cache périmé, bug…)


def default_products() -> list[FakeProduct]:
    return [
        FakeProduct(
            1, "Téléviseur OLED 55 pouces (démo)", Decimal("1299.00"), gtin13("200000000001")
        ),
        FakeProduct(2, "Carte graphique 16 Go (démo)", Decimal("1149.90"), gtin13("200000000002")),
        FakeProduct(
            3, "Ordinateur portable 15 pouces (démo)", Decimal("899.00"), gtin13("200000000003")
        ),
        FakeProduct(4, "Casque audio sans fil (démo)", Decimal("349.00"), gtin13("200000000004")),
    ]


class FakeShop:
    def __init__(
        self, base_url: str = "http://127.0.0.1:8765", products: list[FakeProduct] | None = None
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.products = {p.id: p for p in (products or default_products())}
        self.requests: list[str] = []
        self._lock = threading.Lock()

    # --- Modification des prix ---------------------------------------------------------------

    def set_price(
        self, product_id: int, price: Decimal | str, *, listing_only: bool = False
    ) -> None:
        amount = Decimal(price)
        with self._lock:
            product = self.products[product_id]
            if listing_only:
                product.listing_price = amount
            else:
                product.price, product.listing_price = amount, None

    def set_stock(self, product_id: int, in_stock: bool) -> None:
        with self._lock:
            self.products[product_id].in_stock = in_stock

    # --- Pages -------------------------------------------------------------------------------

    def product_url(self, product_id: int) -> str:
        return f"{self.base_url}/produit/{product_id}.html"

    def handle(self, path: str, query: dict[str, list[str]]) -> tuple[int, str, str]:
        """Renvoie (code HTTP, type de contenu, corps) pour un chemin donné."""
        self.requests.append(path)
        if path == "/robots.txt":
            return 200, "text/plain; charset=utf-8", "User-agent: *\nAllow: /\n"
        if path in ("/", "/categorie/"):
            return 200, "text/html; charset=utf-8", self._listing(1)
        if path.startswith("/categorie/page") and path.endswith("/"):
            page = path.removeprefix("/categorie/page").rstrip("/")
            if page.isdigit():
                return 200, "text/html; charset=utf-8", self._listing(int(page))
        if path.startswith("/produit/") and path.endswith(".html"):
            ident = path.removeprefix("/produit/").removesuffix(".html")
            if ident.isdigit() and int(ident) in self.products:
                return 200, "text/html; charset=utf-8", self._product(int(ident))
        if path in ("/admin/prix", "/admin/stock"):
            return self._admin(path, query)
        return 404, "text/plain; charset=utf-8", "Page introuvable"

    def mock_transport(self) -> httpx.MockTransport:
        """Transport httpx qui répond à la place du réseau (pour les tests)."""

        def handler(request: httpx.Request) -> httpx.Response:
            status, content_type, body = self.handle(
                request.url.path, parse_qs(request.url.query.decode())
            )
            return httpx.Response(status, text=body, headers={"Content-Type": content_type})

        return httpx.MockTransport(handler)

    def _listing(self, page: int) -> str:
        with self._lock:
            products = sorted(self.products.values(), key=lambda p: p.id)
            chunk = products[(page - 1) * PAGE_SIZE : page * PAGE_SIZE]
            items = [
                {
                    "@type": "ListItem",
                    "position": index + 1,
                    "item": {
                        "@type": "Product",
                        "name": p.name,
                        "url": self.product_url(p.id),
                        "offers": {
                            "@type": "Offer",
                            "price": str(
                                p.listing_price if p.listing_price is not None else p.price
                            ),
                            "priceCurrency": "EUR",
                            "availability": _availability(p.in_stock),
                        },
                    },
                }
                for index, p in enumerate(chunk)
            ]
        data = {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": items}
        cards = "".join(
            f'<li><a href="/produit/{p.id}.html">{html.escape(p.name)}</a></li>' for p in chunk
        )
        return _page("Catégorie", data, f"<h1>Catégorie (page {page})</h1><ul>{cards}</ul>")

    def _product(self, product_id: int) -> str:
        with self._lock:
            p = self.products[product_id]
            data = {
                "@context": "https://schema.org/",
                "@type": "Product",
                "name": p.name,
                "gtin13": p.gtin,
                "brand": {"@type": "Brand", "name": "Démo"},
                "offers": {
                    "@type": "Offer",
                    "price": str(p.price),
                    "priceCurrency": "EUR",
                    "availability": _availability(p.in_stock),
                    "itemCondition": "https://schema.org/NewCondition",
                    "seller": {"@type": "Organization", "name": SELLER},
                    "url": self.product_url(p.id),
                },
            }
            body = f"<h1>{html.escape(p.name)}</h1><p>{format_price(p.price)}</p>"
        return _page(p.name, data, body)

    def _admin(self, path: str, query: dict[str, list[str]]) -> tuple[int, str, str]:
        try:
            product_id = int(query["id"][0])
            if product_id not in self.products:
                raise KeyError(product_id)
            if path == "/admin/prix":
                price = parse_price(query["prix"][0])
                if price is None:
                    raise ValueError("prix invalide")
                self.set_price(product_id, price, listing_only=query.get("liste") == ["1"])
                message = f"Prix du produit {product_id} : {format_price(price)}"
            else:
                in_stock = query.get("dispo", ["1"])[0] != "0"
                self.set_stock(product_id, in_stock)
                message = f"Produit {product_id} : {'en stock' if in_stock else 'en rupture'}"
        except (KeyError, ValueError, IndexError):
            return (
                400,
                "text/plain; charset=utf-8",
                "Paramètres attendus : id=…&prix=… ou id=…&dispo=0|1",
            )
        log.info("%s", message)
        return 200, "text/plain; charset=utf-8", message


def make_server(shop: FakeShop, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    """Serveur HTTP local du faux magasin (port 0 = port libre choisi par le système)."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parts = urlsplit(self.path)
            status, content_type, body = shop.handle(parts.path, parse_qs(parts.query))
            payload = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            log.debug("Faux magasin : " + format, *args)

    return ThreadingHTTPServer((host, port), Handler)


def serve(shop: FakeShop, host: str = "127.0.0.1", port: int = 8765) -> None:
    """Lance le faux magasin sur http://host:port jusqu'à Ctrl+C."""
    server = make_server(shop, host, port)
    print(f"Faux magasin lancé sur http://{host}:{port}/categorie/")
    print("Produits :")
    for product in shop.products.values():
        print(f"  id={product.id}  {product.name}  {format_price(product.price)}")
    print(f"Changer un prix : http://{host}:{port}/admin/prix?id=1&prix=129.90")
    print(f"Mettre en rupture : http://{host}:{port}/admin/stock?id=1&dispo=0")
    print("Arrêt : Ctrl+C")
    try:
        server.serve_forever()
    finally:
        server.server_close()


def _availability(in_stock: bool) -> str:
    return "https://schema.org/InStock" if in_stock else "https://schema.org/OutOfStock"


def _page(title: str, data: object, body: str) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return (
        '<!doctype html><html lang="fr"><head><meta charset="utf-8">'
        f"<title>{html.escape(title)}</title>"
        f'<script type="application/ld+json">{payload}</script>'
        f"</head><body>{body}</body></html>"
    )
