# État des lieux des sites

**Test du 5 novembre 2026**, réalisé depuis un serveur cloud (comme celui qui fera tourner
le bot), avec un User-Agent de robot honnête. Une requête est envoyée sur la page d'accueil,
puis, si elle passe, sur une page produit pour vérifier la présence de données structurées.

> Ce test ne remplace pas la lecture des CGU : la
> [fiche site](JURIDIQUE.md#4-fiche-site-à-remplir-avant-tout-connecteur) reste à remplir
> avant d'écrire un connecteur. Un site accessible aujourd'hui peut se protéger demain.
> Règle du projet : **si un site bloque les robots, on ne le contourne pas.**

## Les trois sites demandés

| Site | Constat | Voie retenue |
|---|---|---|
| **Amazon** (tous pays) | Les conditions d'utilisation d'Amazon interdisent les robots et les outils d'extraction de données | **API Keepa** (payante, voir ci-dessous). L'API officielle d'Amazon (*Creators API*, qui remplace PA-API 5.0 depuis 2026) est réservée aux affiliés qui génèrent des ventes : elle ne convient pas à un usage personnel |
| **Cdiscount** | Page de défi JavaScript anti-robot | Pas de collecte directe. Le flux produits d'affiliation (Awin) exige d'avoir un site ou une chaîne de diffusion. À défaut, signal secondaire via les communautés de bons plans |
| **Fnac** | Refus 403 (Akamai), y compris sur `robots.txt` | Comme Cdiscount (la Fnac a un programme Awin avec flux XML/CSV) |

### Amazon via Keepa

- Keepa suit les prix d'une dizaine de marchés Amazon : États-Unis, Royaume-Uni, Allemagne,
  France, Japon, Canada, Italie, Espagne, Inde, Mexique, Brésil (liste à confirmer dans la doc officielle).
- L'endpoint `/deal` renvoie les **baisses de prix récentes** (jusqu'à 150 produits pour
  5 jetons). L'endpoint `/product` donne l'historique complet d'un produit (1 jeton), ce qui
  fournit des prix de référence dès le premier jour.
- Formule d'entrée : 20 jetons par minute, **environ 49 € par mois** (tarif relevé par des
  sites tiers, à confirmer sur keepa.com/api). Paiement mensuel, résiliable à tout moment.
- Capacité de cette formule : 1 200 jetons par heure. Balayer les baisses de prix de
  8 marchés toutes les 5 minutes coûte 480 jetons par heure. Il en reste environ 700 pour
  vérifier en détail environ 700 produits par heure.

## Autres sites testés

### Accessibles : candidats pour les connecteurs

| Site | Pays | Résultat | Données structurées | CGU | Décision |
|---|---|---|---|---|---|
| **[LDLC](sites/ldlc.md)** | FR | ✅ Accueil et page produit | JSON-LD avec prix et **EAN** | Pas de clause anti-extraction | ✅ **MVP** |
| **[Rue du Commerce](sites/rueducommerce.md)** | FR | ✅ Page de liste (47 produits) et page produit | JSON-LD avec prix et **EAN** | Pas de clause anti-extraction | ✅ Phase 2 |
| **[Electro Dépôt](sites/electrodepot.md)** | FR | ✅ Accueil et page produit | JSON-LD avec prix, sans EAN | Pas de clause anti-extraction | ✅ Phase 2 |
| Materiel.net | FR | ✅ Accueil et page de liste | À vérifier | À lire (Groupe LDLC) | ⏳ |
| Coolblue | NL/BE | ✅ Accueil | À vérifier | À lire | ⏳ Phase 4 |
| Otto | DE | ✅ Accueil | À vérifier | À lire | ⏳ Phase 4 |

### Accessibles mais exclus par leurs CGU

| Site | Pays | Raison |
|---|---|---|
| [TopAchat](sites/topachat.md) | FR | Les CGU interdisent explicitement « toute extraction […] ou aspiration de données (scraping) » |

### Accessibles mais protégés : blocage probable

| Site | Pays | Résultat |
|---|---|---|
| Auchan | FR | Page servie, protection DataDome présente |
| E.Leclerc | FR | Page presque vide (rendu JavaScript ou défi) |
| Best Buy | US | Page servie, protection Akamai présente |
| Walmart | US | Page servie, protections Akamai et PerimeterX présentes |

### Bloqués : exclus de la collecte directe

| Site | Pays | Résultat |
|---|---|---|
| Darty | FR | 403 (Akamai) |
| Boulanger | FR | 400 (Akamai) |
| Carrefour | FR | Défi Cloudflare |
| Decathlon | FR | Défi Cloudflare |
| Leroy Merlin | FR | CAPTCHA DataDome |
| ManoMano | FR | Défi Cloudflare |
| Rakuten | FR | Défi Cloudflare |
| Conforama | FR | Défi Cloudflare |
| Castorama | FR | 503 |
| Micromania | FR | Défi Imperva |
| MediaMarkt | DE | Défi Cloudflare |
| Bol.com | NL | 403 (Akamai) |
| Argos | UK | 403 (Akamai) |
| Currys | UK | Défi anti-robot |

## Conclusion

La plupart des grandes enseignes françaises bloquent les robots. La couverture réaliste repose sur trois sources :

1. **Amazon, dans une dizaine de pays, via Keepa** : la source la plus riche en erreurs de
   prix. Nécessite l'option de budget C, donc **pas pour l'instant** (option A retenue).
2. **Les sites accessibles dont les CGU ne l'interdisent pas**, surtout en high-tech (LDLC,
   Rue du Commerce, Electro Dépôt, peut-être Materiel.net), là où les erreurs rapportent le plus.
3. **Les communautés de bons plans** comme signal secondaire pour les sites bloqués (Cdiscount,
   Fnac, Darty…). L'erreur y est déjà publique, mais on est quand même alerté.

D'autres pays seront testés de la même façon au fil de la phase 4.
