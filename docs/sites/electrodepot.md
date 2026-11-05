# Electro Dépôt

- Domaine : www.electrodepot.fr
- Date de revue : 5 novembre 2026

## Accès aux données
- [ ] API officielle disponible ? → Aucune API publique connue
- [x] Données structurées JSON-LD `Product`/`Offer` sur les pages produit ? → Oui : prix,
      **sans EAN**
- [x] Prix visible sans JavaScript ? → Oui
- [x] Pages de liste exploitables ? → Pages catégories simples uniquement. Les paramètres de tri
      et de filtre (`?price`, `?sort=`, `?filter`, `?dir`, `?limit=all`…) sont interdits par `robots.txt`

## Cadre
- [x] Conditions générales et informations légales lues : **aucune clause sur l'extraction automatisée trouvée**.
- [x] `robots.txt` : interdits notamment `/catalog/`, `/catalogsearch/`, `/checkout/`,
      `/customer/` et les paramètres de tri et de filtre.
- [x] Protection anti-robot observée ? → Aucune (test du 5/11/2026)
- Débit retenu : **1 requête toutes les 5 s** au maximum.

## Intérêt
- Catégories : électroménager, high-tech, informatique.
- Beaucoup de marques propres (pas d'EAN commun avec les autres sites), donc la détection se
  fera surtout sur l'historique du produit.

## Décision
- [x] **OK pour collecte** (usage personnel, débit faible, aucune republication)
- Phase 2.
