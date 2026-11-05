# Roadmap de développement

## Choix validés

| Sujet | Décision |
|---|---|
| **Usage** | Personnel uniquement |
| **Marché** | Monde entier, par étapes : France, puis Union européenne, puis reste du monde |
| **Verticale** | Produits physiques d'abord. Vols et hôtels plus tard |
| **Sites** | LDLC (MVP), Rue du Commerce, Electro Dépôt, puis d'autres après vérification. Voir [SITES.md](SITES.md) |
| **Budget** | **Option A, 0 €** : le bot tourne sur l'ordinateur personnel, pas d'Amazon pour l'instant |
| **Temps** | **Plein temps** (environ 35 h par semaine) |
| **Canal d'alerte** | Telegram |
| **Langage** | Python |
| **Achat automatique** | Non : le bot alerte, l'humain décide et achète |

Ce que l'option A implique :
- **Pas d'Amazon** tant que le budget ne passe pas à l'option C (environ 55 € par mois). Le
  module Amazon est prévu et prêt à être ajouté (voir [Module optionnel : Amazon](#module-optionnel--amazon-via-keepa)).
- **L'ordinateur doit rester allumé** (mise en veille désactivée), sinon le bot rate des
  erreurs. Un service gratuit prévient si le bot cesse de donner signe de vie.

## Vue d'ensemble

| Phase | Objectif | Durée | Résultat visible |
|---|---|---|---|
| **0. Cadrage** | Fiches des sites, préparation du dépôt | 2–3 jours | Dépôt prêt, CI verte |
| **1. MVP** | Toute la chaîne sur LDLC | 1 sem. | Première alerte Telegram |
| **2. Fondations** | Système robuste, 3 sites, tourne seul sur l'ordinateur | 1,5 sem. | Surveillance 24 h/24 |
| **3. Détection avancée** | Alertes fiables, peu de faux positifs | 1,5 sem. | Score de confiance et retours |
| **4. Couverture mondiale** | France, puis UE, puis reste du monde | continu | Plusieurs pays, prix rendu en France |
| **5. Intelligence** | Apprendre des retours, vérification par IA | 1,5 sem. | Précision mesurée et en hausse |
| **6. Produit** | *Non prévue : usage personnel* | – | – |
| **7. Extensions** | Vols, hôtels | variable | Nouvelles verticales |

Certains critères de fin demandent d'**attendre des données** (par exemple 2 semaines
d'alertes notées). Pendant ce temps, le développement continue sur la phase suivante.

### Jalons

| Jalon | Contenu | Phase | Semaine |
|---|---|---|---|
| **J1** | Première alerte réelle (LDLC) | 1 | S2 |
| **J2** | Bot multi-sites qui tourne seul | 2 | S3–S4 |
| **J3** | Score de confiance et retours en place | 3 | S5 |
| **J4** | Couverture France complète (sites autorisés) | 4, étape A | S6–S7 |
| **J5** | Précision ≥ 70 % mesurée sur un mois | 5 | S10 environ |

---

## Phase 0 : Cadrage (2 à 3 jours)

- [x] Tester l'accessibilité des sites ([SITES.md](SITES.md)).
- [x] Fixer le budget (option A) et le temps disponible (plein temps).
- [x] Fiches des sites : [LDLC](sites/ldlc.md), [Rue du Commerce](sites/rueducommerce.md),
      [Electro Dépôt](sites/electrodepot.md), [TopAchat](sites/topachat.md) (exclu).
- [x] Choisir le site du MVP : **LDLC**.
- [ ] Créer le bot Telegram (BotFather) et un groupe privé (voir [BESOINS.md](BESOINS.md#7-à-faire-de-votre-côté)).
- [ ] Préparer l'ordinateur : Python 3.12+, Docker, Git, mise en veille désactivée.
- [ ] Initialiser le dépôt : `pyproject.toml` (uv), ruff, mypy, pytest, pre-commit, CI GitHub
      Actions, `.gitignore`, `.env.example`, `Dockerfile`, `docker-compose.yml`.
- [ ] Constituer une liste de **100 à 300 produits témoins** LDLC (URL et EAN), de
      préférence chers (plus de 100 €) et vendus aussi sur Rue du Commerce, pour pouvoir les comparer.

**Critère de fin** : la CI passe sur le squelette de projet et `pricebot --help` fonctionne.

---

## Phase 1 : MVP sur LDLC (1 semaine)

**Objectif** : faire tourner toute la chaîne de bout en bout sur un seul site.

- [ ] Client HTTP asynchrone : au plus 1 requête toutes les 5 s par site, User-Agent
      identifiable, délais d'attente, nouvelles tentatives espacées progressivement, `robots.txt` respecté (protego).
- [ ] Extracteur générique de données structurées (JSON-LD, microdata, OpenGraph) qui renvoie
      le prix, la devise, la disponibilité, l'EAN et le titre.
- [ ] Connecteur LDLC : pages produit et pages catégories.
- [ ] Stockage SQLite : produits, offres, observations de prix (seulement quand le prix change).
- [ ] Planificateur simple : chaque offre est revérifiée toutes les N minutes.
- [ ] Une seule règle de détection : prix inférieur à 50 % de la médiane des observations
      précédentes, **ou** virgule décalée (×10 ou ×100).
- [ ] Alerte Telegram : produit, ancien prix, nouveau prix, pourcentage de baisse, lien.
- [ ] **Faux magasin local** dont on modifie les prix à volonté, pour tester sans toucher à LDLC.
- [ ] Tests : extraction sur des pages LDLC enregistrées (fixtures), détection sur des séries de prix synthétiques.

**Livrables** : la commande `pricebot run` tourne sur l'ordinateur et envoie des alertes.

**Critère de fin** : une baisse de prix sur le faux magasin déclenche une alerte Telegram en
moins de N + 1 minutes. Le bot tourne 48 h sur LDLC sans planter.

---

## Phase 2 : Fondations (1,5 semaine)

**Objectif** : passer du prototype à un système multi-sites qui tourne seul sur l'ordinateur.

- [ ] PostgreSQL et migrations (Alembic), dans Docker.
- [ ] Interface `Connector` commune et configuration par site en YAML : débit, priorité, activation.
- [ ] Connecteurs **Rue du Commerce** (découverte par le sitemap, pas de pagination) et
      **Electro Dépôt** (catégories sans tri ni filtre).
- [ ] Identité produit : regroupement des offres par EAN pour comparer LDLC et Rue du Commerce.
- [ ] File de tâches (Redis + ARQ), workers parallèles et planification par priorité.
- [ ] Santé des connecteurs : taux de succès, taux d'échec d'extraction, produits « canaris ».
      Si un site casse ou bloque, le connecteur se met en pause et une alerte est envoyée.
- [ ] Logs structurés en JSON, erreurs envoyées vers Sentry (offre gratuite).
- [ ] **Fonctionnement 24 h/24 sur l'ordinateur** :
  - Docker Compose avec redémarrage automatique (`restart: unless-stopped`), lancement au démarrage ;
  - reprise après une coupure : les produits prioritaires sont revérifiés en premier ;
  - battement de cœur vers Healthchecks.io, qui prévient sur Telegram si le bot s'arrête ;
  - message quotidien « je tourne » avec les statistiques du jour.
- [ ] Sauvegarde quotidienne de la base.

**Critère de fin** : 7 jours consécutifs sans intervention, au moins 95 % de collectes
réussies, et une casse d'extracteur provoquée volontairement est détectée et signalée automatiquement.

---

## Phase 3 : Détection avancée (1,5 semaine)

**Objectif** : des alertes peu nombreuses mais justes. Le détail est dans [DETECTION.md](DETECTION.md).

- [ ] Prix de référence : médiane historique et prix du marché (même EAN sur les autres sites).
- [ ] Signaux multiples et **score de confiance** de 0 à 100.
- [ ] Filtres contre les faux positifs : **vendeurs tiers des marketplaces** (LDLC, Rue du
      Commerce), produits reconditionnés, prix « à partir de », rupture de stock, etc.
- [ ] Étape de **vérification** : nouvelle collecte immédiate, cohérence entre prix barré et
      prix affiché, capture d'écran horodatée.
- [ ] Déduplication et anti-spam : une seule alerte par offre et par épisode, puis un message de suivi quand le prix est corrigé.
- [ ] Boutons de retour sous chaque alerte : ✅ erreur réelle / 🏷️ simple promo / 🐛 bug de collecte.
- [ ] **Rejeu de l'historique (backtest)** pour mesurer précision et rappel avant de déployer un changement.
- [ ] Seuils relevés pendant les soldes et le Black Friday.
- [ ] **Plages horaires** : surveillance 24 h/24, mais la nuit seules les alertes de score ≥ 90 sont notifiées.

**Critère de fin** : sur 2 semaines, au moins 50 % des alertes sont jugées « erreur réelle »
ou « très bonne affaire », avec un délai médian inférieur à 15 min entre le changement de prix et l'alerte.

---

## Phase 4 : Couverture mondiale (en continu)

**Objectif** : étendre la surveillance pays par pays, en ne gardant que les erreurs qu'on peut
vraiment acheter depuis la France. Chaque nouveau site passe d'abord par le test d'accès et la
[fiche site](JURIDIQUE.md#4-fiche-site-à-remplir-avant-tout-connecteur).

### Étape A : France
- [ ] Materiel.net (fiche à faire) et autres sites accessibles dont les CGU le permettent.
- [ ] Découverte de produits : sitemaps et pages catégories autorisées.
- [ ] Planification adaptative : fréquence selon la valeur du produit, sa volatilité et l'historique d'erreurs du site.
- [ ] **Signal secondaire pour les sites bloqués** (Cdiscount, Fnac, Darty…) : flux publics des
      communautés de bons plans (ex. Dealabs), filtrés sur les erreurs de prix.

### Étape B : Union européenne (pas de douane)
- [ ] Tester puis ajouter les sites européens accessibles (Coolblue, Otto, puis d'autres pays).
- [ ] Conversion de devises, détection de la **livraison vers la France**.

### Étape C : Reste du monde
- [ ] Tester puis ajouter des sites hors UE accessibles.
- [ ] Calcul du **prix rendu en France** : livraison, TVA à l'importation, droits de douane selon
      la catégorie et la valeur (règles douanières de l'UE en évolution, à vérifier au moment du
      développement). Alerte seulement si l'offre reste intéressante une fois livrée.

### Pour toutes les étapes
- [ ] **Mesure du rappel** : comparer avec les erreurs de prix publiées par les communautés de bons plans.

**Critère de fin** (à chaque étape) : nouveaux pays couverts sans dégrader le délai d'alerte ni la précision.

---

## Module optionnel : Amazon via Keepa

À activer si le budget passe à l'option C (environ 49 € par mois pour Keepa). Le reste du
système (détection, alertes, identité produit par EAN) sera déjà prêt à l'accueillir.

- [ ] Connecteur Keepa : balayage de l'endpoint des baisses de prix récentes (`/deal`) sur
      plusieurs marchés (France, Allemagne, Italie, Espagne, Royaume-Uni, États-Unis, Japon…).
- [ ] Historique des produits (`/product`) comme prix de référence immédiat.
- [ ] Planification selon les jetons disponibles (20 par minute avec la formule d'entrée).
- [ ] Filtres propres à Amazon : vendeurs tiers, Amazon Seconde Main, reconditionné.

Durée estimée : 1 semaine.

---

## Phase 5 : Intelligence (1,5 semaine)

**Objectif** : remplacer les réglages manuels par des réglages appris sur les retours.

- [ ] Modèle de score entraîné sur les alertes notées (régression logistique, puis gradient boosting).
- [ ] Détection d'anomalies non supervisée en complément (ex. Isolation Forest).
- [ ] Vérification par un LLM pour les candidats ambigus. Optionnelle, car payante à l'usage
      (quelques euros par mois) : à décider le moment venu.
- [ ] Rapprochement des produits sans EAN par similarité de titres (embeddings), y compris entre
      langues. Utile pour Electro Dépôt et ses marques propres.

**Critère de fin** : précision d'au moins 70 % sur un mois, avec un rappel égal ou supérieur.

---

## Phase 6 : Produit (non prévue)

Le bot est destiné à un usage personnel. Si l'idée de l'ouvrir à d'autres revient un jour, voir
les obligations dans [JURIDIQUE.md](JURIDIQUE.md#3-diffusion-publique-des-alertes-phase-6).

## Phase 7 : Extensions

- **Vols « mistake fares »** : sources différentes (API de recherche de vols), prix de
  référence par route et par saison, prix très volatils. C'est presque un second moteur de détection.
- Hôtels et locations.

---

## Indicateurs suivis dès la phase 1

| Indicateur | Définition | Cible |
|---|---|---|
| Disponibilité | Part du temps où le bot tourne (ordinateur allumé) | ≥ 95 % |
| Délai d'alerte | Temps entre le changement de prix et l'alerte | < 15 min sur les produits prioritaires |
| Précision | Part des alertes jugées utiles | ≥ 50 % (phase 3), puis ≥ 70 % (phase 5) |
| Rappel | Part des erreurs publiques connues qu'on a détectées | mesuré à partir de la phase 4 |
| Couverture | Nombre de pays, de sites et d'offres suivis | en hausse |
| Taux de collecte | Part des requêtes dont on a pu extraire un prix | ≥ 95 % |
| Coût mensuel | Serveur et API | 0 € (option A) |

## Risques principaux

| Risque | Impact | Parade |
|---|---|---|
| Ordinateur éteint ou en veille | Erreurs ratées | Veille désactivée, redémarrage automatique, alerte Healthchecks.io. Passer à un VPS (environ 5 € par mois) si ça arrive souvent |
| Les grandes enseignes bloquent les robots | Couverture limitée | Sites autorisés, signal communautaire, Amazon plus tard via Keepa |
| Un site autorisé se met à bloquer ou change ses CGU | Perte d'un connecteur | Pause automatique, relecture des CGU tous les trimestres, retrait **sans contourner** |
| Trop de faux positifs | On finit par ignorer les alertes | Score, vérification, retours, rejeu de l'historique |
| Arnaques de vendeurs tiers | Perte d'argent | Forte pénalité et mention claire dans l'alerte |
| Changement de structure des pages | Collecte cassée sans qu'on le voie | Données structurées en priorité, canaris, fixtures de test |
| Commande annulée par le marchand | Déception | Inhérent aux erreurs de prix (voir [JURIDIQUE.md](JURIDIQUE.md#2-acheter-un-produit-affiché-à-un-prix-erroné)) |
| Frais d'import hors UE | Une « affaire » qui n'en est pas une | Calcul du prix rendu en France (étape C) |

## Prochaines étapes

1. Créer le bot Telegram et indiquer le système d'exploitation de l'ordinateur ([BESOINS.md](BESOINS.md#7-à-faire-de-votre-côté)).
2. Initialiser le dépôt (fin de la phase 0).
3. Démarrer la phase 1 sur LDLC.
