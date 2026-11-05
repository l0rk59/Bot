# Bot de détection d'erreurs de prix

Bot qui surveille en continu les prix des sites marchands, repère les **erreurs de prix**
(prix anormalement bas causés par une erreur du marchand : virgule décalée, remise mal
saisie, mauvaise devise, prix d'un autre produit…) et envoie une alerte en quelques minutes.

> **Statut : phase 0, cadrage presque terminé.** Les décisions sont prises et les sites vérifiés. Le code n'est pas encore commencé. Ce dépôt contient la
> roadmap et les spécifications du bot.

## Documentation

| Document | Contenu |
|---|---|
| [docs/ROADMAP.md](docs/ROADMAP.md) | Phases de développement, tâches, critères de fin, jalons, risques |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Composants, stack technique, modèle de données, structure du code |
| [docs/DETECTION.md](docs/DETECTION.md) | Définition d'une erreur de prix, signaux, score, faux positifs |
| [docs/SITES.md](docs/SITES.md) | Quels sites sont accessibles à un robot, et par quelle voie (test du 5/11/2026) |
| [docs/JURIDIQUE.md](docs/JURIDIQUE.md) | Cadre légal (France/UE), règles de collecte responsable, fiche par site |
| [docs/BESOINS.md](docs/BESOINS.md) | Comptes, infrastructure, budget expliqué, compétences, décisions |

## Fonctionnement en 7 étapes

1. **Collecter** les prix (API, flux d'affiliation, pages produit et pages de liste) en respectant chaque site.
2. **Normaliser** les données (devise, TTC, frais de port, état, vendeur) et **identifier** le produit (EAN/GTIN).
3. **Historiser** chaque changement de prix.
4. **Détecter** les prix anormaux par rapport à l'historique du produit et aux autres marchands.
5. **Vérifier** automatiquement chaque candidat pour éliminer les faux positifs.
6. **Alerter** (Telegram en priorité) avec le contexte et une capture d'écran.
7. **Apprendre** des retours (« vraie erreur », « simple promo », « bug ») pour améliorer la détection.
