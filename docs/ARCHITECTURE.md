# Architecture

## Vue d'ensemble

```mermaid
flowchart LR
    subgraph Sources
        A1[API officielles]
        A2[Flux d'affiliation]
        A3[Pages produit et pages de liste]
    end
    S[Planificateur<br/>priorités et débit par site] --> Q[(File de tâches<br/>Redis)]
    Q --> W[Workers de collecte<br/>HTTP ou Playwright]
    A1 --> W
    A2 --> W
    A3 --> W
    W --> E[Extraction<br/>JSON-LD, sélecteurs]
    E --> N[Normalisation<br/>et identité produit]
    N --> DB[(PostgreSQL<br/>historique des prix)]
    N --> D[Moteur de détection]
    DB --> D
    D --> V[Vérification]
    V --> AL[Alertes<br/>Telegram, Discord]
    AL --> F[Retours utilisateur]
    F --> DB
    DB --> UI[Tableau de bord<br/>phase 6]
    M[Supervision<br/>santé des sites, logs, Sentry] -.-> W
```

Chaque brique est indépendante et testable seule. Ajouter un site revient à écrire un
connecteur et sa configuration, sans toucher au reste.

---

## 1. Sources de données

Par ordre de préférence :

| Source | Avantages | Inconvénients | Usage |
|---|---|---|---|
| **API de données** (Keepa pour Amazon) | Fiable, structurée, autorisée, plusieurs pays, historique inclus | Payante, quota de jetons | **Source Amazon** si l'option de budget C est choisie (voir [SITES.md](SITES.md)) |
| **API officielle** (ex. Creators API d'Amazon) | Fiable, structurée, autorisée | Réservée aux affiliés qui génèrent des ventes | Écartée pour un usage personnel |
| **API publiques gratuites** (eBay Browse API, Rakuten Japon, Best Buy) | Autorisées, structurées, multi-pays (eBay) | Quotas (eBay : 5 000 appels par jour), compte développeur | **Source « monde entier »** |
| **Plateformes e-commerce ouvertes** (Shopify `/products.json`) | Un seul connecteur pour des milliers de boutiques, JSON propre | Ouvert boutique par boutique, CGU de chaque boutique | **Source « monde entier »** |
| **Flux produits d'affiliation** (Awin, Effiliation, Kwanko, Rakuten…) | Catalogue complet avec EAN, autorisé | Inscription avec un site ou une chaîne, mise à jour souvent quotidienne | Écartés pour un usage personnel |
| **Données structurées des pages** (JSON-LD schema.org `Product`/`Offer`) | Résiste aux refontes visuelles, une seule méthode pour beaucoup de sites | Il faut récupérer la page | Collecte principale par défaut |
| **Pages de liste** (catégories, recherche) | 20 à 60 prix par requête | Moins de détails, EAN souvent absent | Balayage large |
| **Sélecteurs HTML propres au site** | Fonctionne partout | Fragile, demande de la maintenance | Solution de secours |
| **Communautés de bons plans** | Vérité terrain, couvrent les sites bloqués | L'erreur est déjà publique | Signal secondaire, mesure du rappel |

## 2. Planificateur

Le planificateur décide **quoi vérifier et quand**, dans la limite du débit autorisé pour chaque site.

- Chaque offre a une `priority` et une date `next_check_at`.
- Intervalle de vérification = `intervalle_de_base / poids`. Le poids augmente avec la valeur
  du produit, sa volatilité, l'historique d'erreurs du site et la popularité de la catégorie.
- Chaque site dispose d'un **budget de requêtes** (ex. 1 requête toutes les 2 s). Le planificateur ne le dépasse jamais.

### Calcul de capacité

À 1 requête toutes les 2 secondes, un site donne **1 800 pages par heure** :

| Méthode | Prix obtenus par heure et par site |
|---|---|
| Pages produit (1 prix par page) | 1 800 |
| Pages de liste (environ 48 prix par page) | environ 86 000 |

La stratégie en découle : **balayer large avec les pages de liste, vérifier avec les pages
produit**. Une baisse repérée sur une liste déclenche immédiatement une vérification de la page produit.

## 3. Collecte

- `httpx` asynchrone, délais d'attente stricts.
- Nouvelles tentatives avec attente croissante sur les erreurs 5xx et 429, en respectant l'en-tête `Retry-After`.
- Limite de débit par domaine (token bucket) et requêtes conditionnelles (`ETag`, `If-Modified-Since`).
- User-Agent identifiable, avec une URL de contact.
- `robots.txt` lu, mis en cache et respecté, avec `protego`. Le module standard de Python
  (`urllib.robotparser`) ne gère pas les jokers `*` qu'utilisent LDLC, Rue du Commerce ou Electro Dépôt.
- Playwright (navigateur sans interface) seulement pour les sites qui affichent le prix en JavaScript.
  Il est 10 à 50 fois plus coûteux qu'une requête HTTP.
- Option : conserver le HTML brut compressé pendant quelques jours, pour déboguer et rejouer les extracteurs.
- **Aucun contournement des protections** (CAPTCHA, blocage d'IP, pages nécessitant un compte).
  Si un site bloque, on passe par son API ou son flux, ou on le retire. Voir [JURIDIQUE.md](JURIDIQUE.md).

## 4. Extraction

Les méthodes sont essayées dans cet ordre : JSON-LD, puis microdata, puis balises OpenGraph
(`product:price:amount`), puis sélecteurs CSS propres au site.

Le résultat est un objet `RawOffer` (Pydantic) : titre, prix, devise, prix barré, disponibilité,
état, vendeur, EAN, ASIN ou référence fabricant, URL, image.

Pièges à couvrir par des tests :

- Prix au format français : `1 299,99 €`, espaces insécables, centimes dans une balise séparée.
- Prix mensuel (« 39 €/mois »), prix « à partir de », prix avec reprise ou avec offre de remboursement.
- Prix d'une autre variante (couleur, capacité) que celle affichée.
- Éco-participation affichée à part.
- Prix barré pris pour le prix réel, et inversement.

**Les prix sont manipulés avec `Decimal`, jamais avec `float`.**

### Trois types de connecteurs

La plupart des sites accessibles exposent du JSON-LD (voir [SITES.md](SITES.md)). On ne code
donc pas un connecteur par site, mais trois connecteurs réutilisables :

| Connecteur | Couvre | Ajouter une source |
|---|---|---|
| `jsonld` (générique) | Tous les sites avec données structurées : LDLC, Alternate, Cyberport, Elgiganten… | Un fichier YAML (domaine, pages de liste ou sitemap, débit), **sans code** |
| `shopify` | Toutes les boutiques Shopify qui exposent `/products.json` | Une ligne : le domaine de la boutique |
| `api` (un par API) | eBay, Rakuten Japon, Best Buy, Keepa (Amazon) | Clé d'API dans `.env` |

Un connecteur spécifique n'est écrit que si un site sort du lot (prix en JavaScript, structure particulière).

## 5. Normalisation

- Devise au format ISO 4217 et conversion en euros (taux quotidiens de la BCE).
- Prix TTC, frais de port séparés.
- Pays du site et **livraison vers la France** (oui, non ou inconnu).
- **Prix rendu en France** pour les offres hors UE : prix, livraison, TVA à l'importation et
  droits de douane estimés. La détection compare ce prix-là, pas le prix affiché.
- État : `new`, `refurbished` ou `used`.
- Vendeur : le marchand lui-même ou un vendeur tiers de marketplace (nom et note si disponibles).
- Disponibilité : `in_stock`, `out_of_stock`, `preorder` ou `unknown`.
- GTIN/EAN validé par sa clé de contrôle.

## 6. Identité produit

Pour comparer un même produit chez plusieurs marchands :

1. **GTIN/EAN** : identifiant le plus fiable.
2. **ASIN**, ou **marque et référence fabricant**.
3. **Similarité de titres** par embeddings (phase 5), pour les produits sans identifiant.

Le modèle distingue le **produit** (un objet du monde réel) de l'**offre** (ce produit, chez
tel marchand, vendu par tel vendeur, dans tel état).

## 7. Modèle de données

```text
retailer            id, name, domain, country, currency, enabled, config (jsonb)
product             id, gtin, brand, mpn, asin, title, category
offer               id, product_id?, retailer_id, url, seller, condition,
                    priority, next_check_at, last_checked_at
price_observation   id, offer_id, observed_at, price, shipping, currency,
                    list_price, availability          -- uniquement quand quelque chose change
anomaly             id, offer_id, detected_at, price, reference_price, ratio,
                    score, signals (jsonb), status, screenshot_path, resolved_at
alert               id, anomaly_id, channel, sent_at, message_id, feedback, feedback_at
connector_health    retailer_id, window_start, requests, successes, parse_failures
```

Volume : en stockant seulement les changements, 100 000 offres représentent quelques dizaines
de milliers de lignes par jour, ce que PostgreSQL gère sans difficulté. TimescaleDB ne devient
utile qu'au-delà de plusieurs millions d'offres.

## 8. Détection et vérification

Voir [DETECTION.md](DETECTION.md).

## 9. Alertes

- **Telegram** (aiogram) : canal principal, instantané, avec boutons de retour.
- Webhook Discord et récapitulatif par e-mail en option.
- Un canal développeur séparé pour les pannes et les connecteurs cassés.
- Les limites d'envoi de Telegram sont respectées grâce à une file d'envoi.

Exemple de message :

```text
🚨 ERREUR DE PRIX PROBABLE (score 92/100)
Téléviseur OLED 55" Marque X (EAN 1234567890123)
💶 129,90 € au lieu d'environ 1 299 € (-90 %)
🔎 Signaux : virgule décalée ×10 · -90 % sur la médiane 30 j · -90 % sur 4 autres marchands
🏪 Vendu et expédié par ExempleShop · En stock · Neuf
🕒 Détecté à 14:32 (prix précédent relevé à 14:17)
⚠️ Le marchand peut annuler la commande.
[Voir l'offre]   [✅ Erreur]   [🏷️ Promo]   [🐛 Bug]
```

## 10. Supervision

- Indicateurs par connecteur : taux de succès, taux d'échec d'extraction, temps de réponse, codes HTTP.
- **Canaris** : quelques produits au prix connu et stable, vérifiés en continu. Si leur prix
  extrait change bizarrement, c'est l'extracteur qui est cassé.
- Si les anomalies se multiplient d'un coup sur un même site, les alertes de ce site sont
  suspendues et un humain vérifie. Il peut s'agir d'un bug de collecte ou d'une vraie erreur de prix massive.
- Message quotidien « le bot fonctionne » avec les statistiques du jour.
- Sentry pour les exceptions, logs JSON (structlog). Prometheus et Grafana plus tard si besoin.

## 11. Stack technique

État au MVP : ✅ = utilisé aujourd'hui, ⏳ = prévu dans une phase suivante.

| Besoin | Choix recommandé | Alternatives |
|---|---|---|
| Langage | ✅ **Python 3.12+** (meilleur écosystème pour la collecte et l'analyse de données) | – |
| Outillage | ✅ uv, ruff, mypy, pytest | Poetry |
| HTTP | ✅ httpx (asynchrone) | aiohttp |
| Navigateur | ⏳ Playwright (captures d'écran, sites en JavaScript) | – |
| Analyse HTML | ✅ selectolax (moteur lexbor) | parsel, BeautifulSoup |
| Données structurées | ✅ extracteur JSON-LD maison (`extract.py`), plus léger qu'extruct | extruct |
| `robots.txt` | ✅ protego | – |
| Modèles et réglages | ✅ Pydantic v2, pydantic-settings (fichier `.env`) | – |
| Base de données | ✅ SQLite (MVP), ⏳ PostgreSQL | – |
| ORM et migrations | ⏳ SQLAlchemy 2 et Alembic (requêtes SQL directes au MVP) | SQLModel |
| File de tâches | ⏳ Redis et ARQ (boucle asyncio simple au MVP) | Celery, Dramatiq |
| Telegram | ✅ API Bot appelée avec httpx (MVP), ⏳ aiogram 3 pour les boutons de retour | python-telegram-bot |
| API et tableau de bord | ⏳ FastAPI (avec HTMX ou un petit front) | Django |
| Supervision | ✅ journal `data/pricebot.log`, ⏳ structlog, Sentry | Prometheus et Grafana |
| Déploiement | ✅ directement sous Windows (MVP), ⏳ Docker Compose, puis un VPS si besoin. ✅ CI GitHub Actions (Linux et Windows) | – |
| Surveillance de disponibilité | ✅ Healthchecks.io (offre gratuite, optionnel) : prévient si le bot ne donne plus signe de vie | – |

Pour un balayage à grande échelle, Scrapy est une alternative crédible à httpx avec un
planificateur maison : limitation de débit intégrée, respect de `robots.txt`, pipelines.

## 12. Structure du dépôt

### Aujourd'hui (MVP)

```text
.
├── pyproject.toml / uv.lock     # dépendances (uv)
├── .env.example                 # modèle de réglages (le vrai .env n'est jamais committé)
├── .github/workflows/ci.yml     # ruff, mypy, pytest sous Linux et Windows
├── config/retailers/            # un fichier YAML par site (ldlc.yaml, fake-shop.yaml)
├── src/pricebot/
│   ├── cli.py                   # pricebot run | check | stats | telegram-test | fake-shop
│   ├── settings.py              # réglages lus dans .env
│   ├── models.py                # RawOffer, Availability, Condition
│   ├── prices.py                # lecture et mise en forme des prix (Decimal)
│   ├── http.py                  # client poli : débit, robots.txt, nouvelles tentatives
│   ├── extract.py               # JSON-LD / OpenGraph → offres
│   ├── retailers.py             # chargement et validation des YAML
│   ├── storage.py               # SQLite : offres, historique, anomalies
│   ├── detection.py             # prix habituel, règles, verdict
│   ├── alerts.py                # Telegram et console
│   ├── engine.py                # un passage : collecte → détection → vérification → alerte
│   └── fake_shop.py             # faux magasin pour les tests et la démo
├── tests/                       # 103 tests, sans accès aux vrais sites
│   └── fixtures/                # pages d'exemple synthétiques (aucune copie de vrai site)
└── docs/
```

### Cible (phases 2 et suivantes)

Les modules deviennent des paquets quand ils grossissent : `connectors/` (JSON-LD générique,
Shopify, API eBay, Keepa), `storage/` (SQLAlchemy et Alembic), `monitoring/` (santé des
connecteurs, canaris), `api/` (tableau de bord éventuel).

## 13. Configuration et secrets

- Les secrets (`PRICEBOT_TELEGRAM_TOKEN`, puis les clés d'API) sont dans `.env`, qui n'est
  **jamais committé**. Un fichier `.env.example` sans valeurs sert de modèle. Le journal
  n'affiche jamais l'URL de l'API Telegram, qui contient le jeton.
- Un fichier YAML par site, validé au démarrage (une clé inconnue ou un débit trop rapide pour
  un vrai site est refusé) :

```yaml
id: exemple-shop                 # identifiant (option --only)
name: Exemple Shop
base_url: https://www.exemple-shop.fr
enabled: true
country: FR
currency: EUR
min_interval_seconds: 5          # au plus 1 requête toutes les 5 s (minimum 1 s)
own_seller_names: ["Exemple Shop"]  # les autres vendeurs sont signalés comme tiers
page_url_template: "{url}page{page}/"  # facultatif : pagination des catégories
listings:                        # pages catégories à parcourir
  - url: https://www.exemple-shop.fr/tv/c123/
    max_pages: 2
products:                        # fiches produit à suivre en plus
  - https://www.exemple-shop.fr/fiche/P1.html
```

Prévu plus tard dans ce format : rendu JavaScript, sélecteurs CSS de secours, informations
reprises de la fiche site.

## 14. Stratégie de tests

| Niveau | Contenu |
|---|---|
| Unitaires | Lecture des prix (formats FR), validation EAN, calcul des signaux et du score |
| Extracteurs | Pages d'exemple synthétiques dans `tests/fixtures` (structure des vrais sites, sans copie de leur contenu), avec le résultat attendu |
| Détection | Séries de prix synthétiques : promo normale, virgule décalée, bruit, rupture de stock |
| Bout en bout | Faux magasin local dont on change les prix, puis vérification de l'alerte reçue |
| Rejeu (backtest) | Historique réel rejoué avec de nouveaux paramètres, puis mesure de la précision et du rappel |
