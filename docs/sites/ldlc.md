# LDLC

- Domaine : www.ldlc.com (Groupe LDLC)
- Date de revue : 5 novembre 2026

## Accès aux données
- [ ] API officielle disponible ? → Aucune API publique connue
- [ ] Flux produits d'affiliation ? → Non étudié (usage personnel)
- [x] Données structurées JSON-LD `Product`/`Offer` sur les pages produit ? → Oui : prix et **EAN**
- [x] Prix visible sans JavaScript ? → Oui
- [x] Pages de liste exploitables ? → **Page 1 uniquement** : elle contient ses 48 produits et
      leurs prix (JSON-LD `ItemList`). Les pages suivantes chargent les prix en JavaScript depuis
      `/stock-price/`, chemin interdit par `robots.txt`. On couvre donc plus de produits en
      ajoutant des catégories (32 vérifiées, environ 1 400 prix par passage).
- [ ] Sitemap produits disponible ? → Non annoncé dans `robots.txt`, à vérifier

## Cadre
- [x] CGV (PDF) et informations légales lues : **aucune clause sur l'extraction automatisée**.
      La clause de propriété intellectuelle interdit la « reproduction ou représentation totale
      ou partielle […] de ce site » sans autorisation du Groupe LDLC. Le bot ne republie rien
      (usage personnel), ce qui est compatible.
- [x] `robots.txt` : pages produit (`/fiche/…`) et catégories autorisées. Interdits notamment :
      `/recherche/`, `/coin-des-affaires/`, `/stock-price/`, `/Catalogue/`, `/mise-au-panier/`,
      `/navigation/`, `*/stocks/`.
- [x] Protection anti-robot observée ? → Aucune (test du 5/11/2026)
- **Point d'attention** : TopAchat, du même groupe, interdit explicitement le scraping dans
  ses CGU ([fiche](topachat.md)). Le groupe est donc sensible au sujet : garder un débit très
  faible et arrêter immédiatement en cas de demande ou de blocage.
- Débit retenu : **1 requête toutes les 5 s** au maximum (720 pages par heure).

## Intérêt
- Catégories : informatique, composants, high-tech, téléphonie, électroménager.
- Marketplace : oui (CGU marketplace), donc les vendeurs tiers sont à filtrer.
- Vend en propre : oui. Les erreurs sur son propre catalogue sont les plus intéressantes.

## Décision
- [x] **OK pour collecte** (usage personnel, débit faible, aucune republication)
- **Site retenu pour le MVP** : données structurées complètes avec EAN, page 1 des catégories
  exploitable, vente en propre. Configuration : `config/retailers/ldlc.yaml`.
