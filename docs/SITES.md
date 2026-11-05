# État des lieux des sites

**Tests du 5 novembre 2026** sur environ 120 sites et 4 API. Les tests ont été faits depuis un
serveur, avec un User-Agent de robot honnête. Pour chaque site : page d'accueil, `robots.txt`,
une page produit (trouvée sur l'accueil ou dans le sitemap) pour vérifier les données
structurées, puis une recherche automatique de clauses anti-robot dans les pages légales.

> Ces tests ne remplacent pas la lecture des CGU. La
> [fiche site](JURIDIQUE.md#4-fiche-site-à-remplir-avant-tout-connecteur) reste à remplir
> avant d'écrire un connecteur. Un site accessible aujourd'hui peut se protéger demain.
> Règle du projet : **si un site bloque les robots ou l'interdit dans ses CGU, on ne le surveille pas.**

## Vue d'ensemble

| Catégorie | Nombre | Exemples |
|---|---|---|
| ✅ Accessibles avec données structurées | 20 | LDLC, Alternate, Son-Vidéo, Cyberport, Elgiganten, Overclockers |
| 🔎 Accessibles, structure à vérifier | 13 | Materiel.net, Grosbill, Cybertek, Mindfactory, Scan, JB Hi-Fi |
| 🔌 API ou plateformes ouvertes | 4 | eBay (API), boutiques Shopify, Rakuten Japon (API), Best Buy (API) |
| ⚠️ Accessibles mais protection anti-robot présente | 6 | John Lewis, Home Depot, Auchan, King Jouet, Best Buy US, Walmart |
| ❌ Exclus par leurs CGU | 3 | TopAchat, Costco, Target |
| ❌ Bloqués (anti-robot) | ~70 | Cdiscount, Fnac, Darty, Boulanger, Carrefour, Decathlon, Zalando… |
| ⏳ Non testés (erreur réseau) | 6 | Galaxus, Komplett, Ebuyer, GAME, Yodobashi, Bic Camera |
| 💶 Amazon (payant, via Keepa) | 1 | Option de budget C |

## ✅ Accessibles avec données structurées

« EAN » signifie que le code-barres est présent dans les données, ce qui permet de comparer le
même produit d'un site à l'autre.

### France

| Site | Données | CGU | Statut |
|---|---|---|---|
| **[LDLC](sites/ldlc.md)** | JSON-LD + EAN | Pas de clause anti-extraction | ✅ **MVP** |
| **[Rue du Commerce](sites/rueducommerce.md)** | JSON-LD + EAN | Pas de clause anti-extraction | ✅ Phase 2 |
| **[Electro Dépôt](sites/electrodepot.md)** | JSON-LD | Pas de clause anti-extraction | ✅ Phase 2 |
| **Alternate.fr** | JSON-LD + EAN | Aucune clause trouvée dans les CGV | 📝 Fiche à faire |
| **Son-Vidéo.com** | JSON-LD + EAN | Lecture à faire | 📝 Fiche à faire |
| **Brico Dépôt** | JSON-LD + EAN | Lecture à faire | 📝 Fiche à faire |
| IKEA | JSON-LD | Lecture à faire | 📝 Fiche à faire |
| Lidl | JSON-LD | Lecture à faire | 📝 Fiche à faire |
| JouéClub | JSON-LD | Lecture à faire | 📝 Fiche à faire |
| Gifi | JSON-LD | Lecture à faire | 📝 Fiche à faire |
| Miliboo | Microdata | Lecture à faire | 📝 Fiche à faire |

### Europe

| Site | Pays | Données | Remarque |
|---|---|---|---|
| **Alternate** | DE, NL (et FR) | JSON-LD (+ EAN en NL) | Un seul connecteur pour plusieurs pays |
| **Cyberport** | DE | JSON-LD + EAN | |
| **Elgiganten** | SE | JSON-LD + EAN | Même groupe en DK, NO et FI (Elkjøp, Gigantti), à tester |
| Lidl | DE (et FR) | JSON-LD | Boutique en ligne dans plusieurs pays de l'UE |
| Morele | PL | JSON-LD | |
| Megekko | NL | JSON-LD + EAN | Politique publique : **au plus 1 requête automatisée par heure**. Une page de liste par heure seulement |
| Coolblue | NL/BE | Accueil OK | Structure à vérifier |
| Otto | DE | Accueil OK | Structure à vérifier |

### Reste du monde

| Site | Pays | Données | Remarque |
|---|---|---|---|
| **Overclockers** | UK | JSON-LD + EAN | Hors UE : prix rendu en France à calculer |
| Mwave | AU | JSON-LD | Livraison vers la France à vérifier |

## 🔎 Accessibles, structure à vérifier

La page testée n'était peut-être pas une page produit. À revoir lors de la fiche site.

| Pays | Sites |
|---|---|
| FR | Materiel.net (JSON-LD vu au premier test), Grosbill, Cybertek, Bureau Vallée |
| DE | Mindfactory |
| IT | Unieuro |
| PL | Euro.com.pl |
| UK | Scan |
| CA | Canada Computers |
| AU | JB Hi-Fi, Officeworks |

## 🔌 API et plateformes ouvertes

Ces sources sont **autorisées par conception**. Elles sont souvent la meilleure voie pour couvrir le monde entier.

| Source | Couverture | Accès | Remarque |
|---|---|---|---|
| **API eBay (Browse API)** | Tous les pays eBay (FR, DE, UK, US, IT, ES, AU…) | Compte développeur gratuit, **5 000 appels par jour** | Surtout des vendeurs tiers : filtrer les vendeurs pros bien notés. Vérifier que l'usage personnel respecte la licence de l'API |
| **Boutiques Shopify** | Des milliers de boutiques dans le monde | `/products.json` public sur beaucoup de boutiques (testé : Allbirds ✅, Gymshark ❌) | **Un seul connecteur pour toutes les boutiques Shopify**. Les CGU de chaque boutique restent à respecter. Les erreurs de prix sont fréquentes sur les petites boutiques |
| API Rakuten Ichiba | Japon | Identifiant d'application gratuit, environ 1 requête par seconde | Livraison vers la France rare. Étape C |
| API Best Buy | États-Unis | Clé gratuite, attribution incertaine (adresses e-mail gratuites refusées) | À tenter. Étape C |

## ⚠️ Accessibles mais protégés

Les pages passent aujourd'hui, mais une protection anti-robot est présente. Un blocage est probable.

| Site | Pays | Protection |
|---|---|---|
| John Lewis | UK | Akamai (JSON-LD + EAN présent) |
| Home Depot | US | Akamai (JSON-LD + EAN présent) |
| Auchan | FR | DataDome |
| King Jouet | FR | DataDome |
| Best Buy | US | Akamai |
| Walmart | US | Akamai et PerimeterX |

## ❌ Exclus par leurs CGU

| Site | Pays | Clause |
|---|---|---|
| [TopAchat](sites/topachat.md) | FR | « Toute extraction […] ou aspiration de données (scraping) […] est strictement interdite » |
| Costco | US | Interdit « data mining, robots, agents or similar data gathering or extraction methods » |
| Target | US | Vise explicitement les « crawlers, robots, […] data mining or extraction tools » |

## ❌ Bloqués par une protection anti-robot

| Pays | Sites |
|---|---|
| FR | Cdiscount, Fnac, Darty, Boulanger, Carrefour, E.Leclerc, Leclerc Drive, Intermarché, Monoprix, Decathlon, Intersport, Go Sport, Leroy Merlin, Castorama, Mr Bricolage, Bricomarché, ManoMano, Conforama, But, Maisons du Monde, Alinéa, Ubaldi, La Redoute, Galeries Lafayette, Kiabi, Vertbaudet, Zalando, Sephora, Nocibé, Cultura, Micromania, Oxybul, Norauto, Feu Vert, Rakuten, Back Market, Action, PCComponentes, eBay (site web) |
| DE | MediaMarkt, Saturn, Notebooksbilliger, Conrad, Caseking, Proshop |
| ES, IT, PT | El Corte Inglés, Worten, MediaWorld, ePRICE |
| NL, PL, SE | Bol.com, x-kom, Allegro, Inet |
| UK | Argos, Currys, Very, AO, Box, Boots |
| US, CA | Newegg, B&H, Lowe's, Micro Center, Adorama, Kohl's, Macy's, Memory Express, Best Buy Canada |
| JP, AU | Ark, Kogan |

## Amazon

Les conditions d'utilisation d'Amazon interdisent les robots. La seule voie propre est l'**API
Keepa** (environ 49 € par mois, une dizaine de marchés Amazon), soit l'option de budget C.
L'API officielle d'Amazon (*Creators API*, qui remplace PA-API 5.0 depuis 2026) est réservée
aux affiliés qui génèrent des ventes.

## Conclusion

Près de 40 sources sont directement exploitables, plus des milliers de boutiques Shopify, contre 3 au départ :

1. **Un connecteur générique JSON-LD** couvre la plupart des sites ✅ et 🔎. Ajouter un site
   revient à écrire un fichier de configuration, sans code (voir [ARCHITECTURE.md](ARCHITECTURE.md#4-extraction)).
2. **Des connecteurs multi-pays** : Alternate, Lidl, IKEA, Elgiganten et ses sites frères.
3. **Deux connecteurs « monde entier »** : l'API eBay et les boutiques Shopify.
4. **Amazon** plus tard, si le budget passe à l'option C.
5. **Les communautés de bons plans** comme signal secondaire pour les sites bloqués (Cdiscount, Fnac…).
