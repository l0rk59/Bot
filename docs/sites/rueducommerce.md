# Rue du Commerce

- Domaine : www.rueducommerce.fr (Groupe LDLC)
- Date de revue : 5 novembre 2026

## Accès aux données
- [ ] API officielle disponible ? → Aucune API publique connue
- [ ] Flux produits d'affiliation ? → Non étudié (usage personnel)
- [x] Données structurées JSON-LD `Product`/`Offer` sur les pages produit ? → Oui : prix et **EAN**
- [x] Prix visible sans JavaScript ? → Oui
- [x] Pages de liste exploitables ? → **Première page seulement** (47 produits) : la pagination
      `/*/produits/page*` est interdite par `robots.txt`
- [x] Sitemap produits disponible ? → Oui : `sitemap_index.xml`, utile pour découvrir les produits

## Cadre
- [x] CGV (PDF) et informations légales lues : **aucune clause sur l'extraction automatisée**.
      Même clause de propriété intellectuelle que LDLC (pas de reproduction du site).
- [x] `robots.txt` : pages produit (`/p/…`) et premières pages de catégories (`/r/<id>/…`)
      autorisées. Interdits : pagination des listes, `/recherche/`, `/bons-plans/o*`, `/ventes-flash/*`.
- [x] Protection anti-robot observée ? → Aucune (test du 5/11/2026)
- Même point d'attention que [LDLC](ldlc.md) (groupe sensible au scraping).
- Débit retenu : **1 requête toutes les 5 s** au maximum.

## Intérêt
- Catégories : informatique, high-tech, électroménager, maison.
- Marketplace : **très présente**. Le filtrage des vendeurs tiers est indispensable (risque d'arnaque).

## Décision
- [x] **OK pour collecte** (usage personnel, débit faible, aucune republication)
- Deuxième site, en phase 2. Découverte des produits par le sitemap plutôt que par la pagination.
