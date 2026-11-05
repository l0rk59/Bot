# Tout ce qu'il faut pour le bot

## 1. Comptes et accès

| Élément | À quoi il sert | Phase | Coût |
|---|---|---|---|
| GitHub (déjà en place) | Code, CI | 0 | Gratuit |
| Bot Telegram (via @BotFather) et un groupe privé | Recevoir les alertes | 0 | Gratuit |
| VPS (ex. Hetzner, OVH, Scaleway) | Faire tourner le bot 24 h/24 | 2 | Environ 5 à 20 € par mois |
| Sentry | Suivre les erreurs | 2 | Offre gratuite suffisante |
| Réseaux d'affiliation (Awin, Effiliation, Kwanko…) | Flux produits | 4 | Gratuit, inscription soumise à validation (un site ou une chaîne est souvent demandé) |
| Amazon Partenaires et son API produits | Données Amazon | 4 | Gratuit, accès conditionné à des ventes (vérifier la version actuelle de l'API) |
| Keepa *(option)* | Historique des prix Amazon | 3–4 | Abonnement payant |
| Clé d'API LLM *(option)* | Vérification des candidats | 5 | À l'usage, avec un plafond |
| Nom de domaine *(option)* | Tableau de bord public | 6 | Environ 10 € par an |

## 2. Infrastructure

| Stade | Machine | Services |
|---|---|---|
| Phases 0 et 1 | Ordinateur personnel (Python 3.12+, Docker) | SQLite ou PostgreSQL en Docker |
| Phases 2 et 3 | VPS 2 vCPU, 4 Go de RAM, 40 Go SSD | PostgreSQL, Redis, workers, bot Telegram |
| Phase 4 et suivantes | VPS 4 vCPU, 8 Go de RAM (Playwright est gourmand) | Idem, plus de workers |

Sauvegarde quotidienne de la base (`pg_dump`) stockée hors du serveur.

## 3. Budget estimé

| Stade | Coût mensuel |
|---|---|
| Phases 0 et 1 (en local) | 0 € |
| Phases 2 et 3 (VPS) | 5 à 20 € |
| Phases 4 et 5 (serveur plus gros, Keepa et LLM en option) | 30 à 100 € selon les options |
| Phase 6 (public) | Selon le trafic |

## 4. Compétences

| Compétence | Utilité | Niveau requis |
|---|---|---|
| Python, y compris `async`/`await` | Tout le projet | Intermédiaire |
| HTML, sélecteurs CSS, outils de développement du navigateur | Écrire et réparer les extracteurs | Intermédiaire |
| SQL et PostgreSQL | Historique, requêtes d'analyse | Bases |
| Git, Docker, Linux | Déploiement, serveur | Bases |
| Statistiques simples (médiane, percentiles, MAD) | Détection | Bases |
| Apprentissage automatique | Phase 5 | Notions, à apprendre en cours de route |

## 5. Données de départ

- **Sites candidats à évaluer** avec la [fiche site](JURIDIQUE.md#4-fiche-site-à-remplir-avant-tout-connecteur)
  (exemples de grands sites français à étudier, sans préjuger de leurs CGU) : Amazon.fr,
  Cdiscount, Fnac, Darty, Boulanger, Rue du Commerce, LDLC, Carrefour, Auchan, E.Leclerc,
  Conforama, Decathlon, Leroy Merlin, ManoMano, Rakuten.
- **Produits témoins** : 100 à 300 produits avec URL et EAN, de préférence chers (plus de
  100 €) et vendus par plusieurs marchands, pour pouvoir les comparer.
- **Catégories prioritaires** : high-tech, électroménager, jeux vidéo et jouets, maison et bricolage.

## 6. Décisions à prendre

Elles sont nécessaires avant de démarrer la phase 1. Une recommandation est proposée pour chacune.

| # | Question | Recommandation |
|---|---|---|
| 1 | Usage : personnel, entre amis, public, commercial ? | **Personnel** d'abord, ce qui simplifie le juridique et l'infrastructure |
| 2 | Marchés : France seulement ou Europe ? | **France**, puis Amazon UE en phase 4 |
| 3 | Verticales : produits seulement, ou aussi vols et hôtels ? | **Produits** d'abord, vols en phase 7 |
| 4 | Sites pilotes (3 à 5) | À choisir après les fiches site |
| 5 | Catégories prioritaires | High-tech, électroménager, jeux vidéo et jouets, maison |
| 6 | Canal d'alerte | **Telegram** |
| 7 | Seuil minimal d'une alerte | Baisse d'au moins 50 % **et** au moins 30 € d'économie |
| 8 | Budget mensuel maximal | 20 € jusqu'à la phase 3 |
| 9 | Langage | **Python** |
| 10 | Achat automatique | **Non** |
| 11 | Temps disponible par semaine | À préciser, pour recalibrer les durées de la roadmap |
