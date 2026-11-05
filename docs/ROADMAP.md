# Roadmap de développement

## Choix validés

| Sujet | Décision |
|---|---|
| **Usage** | Personnel uniquement |
| **Marché** | Monde entier, par étapes : France, puis Union européenne, puis reste du monde |
| **Verticale** | Produits physiques d'abord. Vols et hôtels plus tard |
| **Sites** | Amazon (via Keepa), sites accessibles (LDLC, Rue du Commerce, TopAchat…). Cdiscount et Fnac bloquent les robots, voir [SITES.md](SITES.md) |
| **Canal d'alerte** | Telegram |
| **Langage** | Python |
| **Achat automatique** | Non : le bot alerte, l'humain décide et achète |

Reste à décider : le **budget** et le **temps disponible par semaine**
(voir [BESOINS.md](BESOINS.md#6-décisions)). Les durées ci-dessous supposent environ 10 à
15 h par semaine. À temps plein, les diviser par environ 2,5.

## Vue d'ensemble

| Phase | Objectif | Durée indicative | Résultat visible |
|---|---|---|---|
| **0. Cadrage** | Fiches des sites, préparation du dépôt | 1 sem. | Dépôt prêt, site du MVP choisi |
| **1. MVP** | Toute la chaîne sur 1 site gratuit (LDLC ou Rue du Commerce) | 2–3 sem. | Première alerte Telegram |
| **2. Fondations et Amazon** | Système robuste, multi-sites, connecteur Amazon via Keepa | 3–4 sem. | Amazon et 4 à 5 sites surveillés 24 h/24 |
| **3. Détection avancée** | Alertes fiables, peu de faux positifs | 3–4 sem. | Score de confiance et retours utilisateur |
| **4. Couverture mondiale** | France, puis UE, puis reste du monde | continu | Plusieurs pays, prix rendu en France |
| **5. Intelligence** | Apprendre des retours, vérification par IA | 3–4 sem. | Précision mesurée et en hausse |
| **6. Produit** | *Non prévue : usage personnel* | – | – |
| **7. Extensions** | Vols, hôtels | variable | Nouvelles verticales |

### Jalons

| Jalon | Contenu | Fin de phase | Semaine estimée |
|---|---|---|---|
| **J1** | Première alerte réelle sur Telegram | 1 | S4 |
| **J2** | Premières alertes Amazon | 2 | S8 |
| **J3** | Bot fiable en production 24 h/24 | 3 | S12 |
| **J4** | Couverture Union européenne | 4 (étape B) | S16 environ |
| **J5** | Précision ≥ 70 % mesurée sur un mois | 5 | S22 environ |

---

## Phase 0 : Cadrage (1 semaine)

**Objectif** : tout décider et tout préparer pour que la phase 1 se limite à du code.

- [x] Tester l'accessibilité des sites ([SITES.md](SITES.md)).
- [ ] Fixer le budget et le temps disponible ([BESOINS.md](BESOINS.md#6-décisions)).
- [ ] Remplir la [fiche site](JURIDIQUE.md#4-fiche-site-à-remplir-avant-tout-connecteur)
      (CGU, `robots.txt`) de LDLC, Rue du Commerce, TopAchat, Electro Dépôt et Materiel.net.
- [ ] Choisir le site du MVP : **LDLC** ou **Rue du Commerce** (données structurées avec EAN).
- [ ] Constituer une liste de **100 à 300 produits témoins** (URL et EAN), de préférence chers
      et vendus à la fois sur Amazon et sur les sites accessibles, pour pouvoir les comparer.
- [ ] Initialiser le dépôt : `pyproject.toml` (uv), ruff, mypy, pytest, pre-commit, CI GitHub
      Actions, `.gitignore`, `.env.example`, `Dockerfile`.
- [ ] Créer le bot Telegram (BotFather) et un groupe privé.

**Critère de fin** : la CI passe sur le squelette de projet, et le site du MVP a une fiche validée.

---

## Phase 1 : MVP (2 à 3 semaines, gratuit)

**Objectif** : faire tourner toute la chaîne de bout en bout sur un site gratuit, sans rien dépenser.

- [ ] Client HTTP asynchrone : limite de débit par domaine, User-Agent identifiable, délais
      d'attente, nouvelles tentatives espacées progressivement, respect de `robots.txt`.
- [ ] Extracteur générique de données structurées (JSON-LD, microdata, OpenGraph) qui renvoie
      le prix, la devise, la disponibilité, l'EAN et le titre.
- [ ] Connecteur du site du MVP (pages produit et pages de liste).
- [ ] Stockage (SQLite ou directement PostgreSQL) : produits, offres, observations de prix.
- [ ] Planificateur simple : chaque offre est revérifiée toutes les N minutes.
- [ ] Une seule règle de détection : prix inférieur à 50 % de la médiane des observations
      précédentes, **ou** virgule décalée (×10 ou ×100).
- [ ] Alerte Telegram : produit, ancien prix, nouveau prix, pourcentage de baisse, lien.
- [ ] **Faux magasin local** dont on modifie les prix à volonté, pour tester sans toucher aux vrais sites.
- [ ] Tests : extraction sur des pages HTML enregistrées (fixtures), détection sur des séries de prix synthétiques.

**Livrables** : la commande `pricebot run` tourne sur l'ordinateur et envoie des alertes.

**Critère de fin** : une baisse de prix sur le faux magasin déclenche une alerte Telegram en
moins de N + 1 minutes. Le bot tourne 48 h sur le vrai site sans planter.

---

## Phase 2 : Fondations et Amazon (3 à 4 semaines)

**Objectif** : passer du prototype à un système multi-sites qui tourne seul, et ajouter Amazon.

- [ ] PostgreSQL et migrations (Alembic). Une observation n'est enregistrée que si le prix ou le stock **change**.
- [ ] Interface `Connector` commune et configuration par site en YAML : débit, priorité, activation.
- [ ] **Connecteur Amazon via l'API Keepa** (si le budget est validé) :
  - balayage régulier de l'endpoint des baisses de prix récentes (`/deal`) ;
  - historique des produits (`/product`), qui sert de prix de référence immédiat ;
  - gestion du quota de jetons (planification selon les jetons disponibles).
- [ ] Connecteurs des autres sites accessibles (TopAchat, Materiel.net, Electro Dépôt…).
- [ ] Identité produit : regroupement des offres par GTIN/EAN (et ASIN) pour comparer
      Amazon et les autres sites sur le même produit.
- [ ] File de tâches (Redis + ARQ), workers parallèles et planification par priorité.
- [ ] Santé des connecteurs : taux de succès, taux d'échec d'extraction, produits « canaris ».
      Si un site casse, le connecteur se met en pause et une alerte part vers le développeur.
- [ ] Logs structurés en JSON, erreurs envoyées vers Sentry.
- [ ] Docker Compose et déploiement sur un serveur (VPS ou machine personnelle allumée en
      permanence). Sauvegarde quotidienne de la base.

**Critère de fin** : 7 jours consécutifs sans intervention, au moins 95 % de collectes
réussies, des alertes Amazon reçues, et une casse d'extracteur provoquée volontairement est
détectée et signalée automatiquement.

---

## Phase 3 : Détection avancée (3 à 4 semaines)

**Objectif** : des alertes peu nombreuses mais justes. Le détail est dans [DETECTION.md](DETECTION.md).

- [ ] Prix de référence : médiane historique, historique Keepa, prix du marché (même EAN ailleurs).
- [ ] Signaux multiples et **score de confiance** de 0 à 100.
- [ ] Filtres contre les faux positifs : **vendeurs tiers Amazon** (arnaques fréquentes),
      produit reconditionné ou « Amazon Seconde Main », prix « à partir de », rupture de stock, etc.
- [ ] Étape de **vérification** : nouvelle collecte immédiate, cohérence entre prix barré et
      prix affiché, capture d'écran horodatée (sites accessibles).
- [ ] Déduplication et anti-spam : une seule alerte par offre et par épisode, puis un message de suivi quand le prix est corrigé.
- [ ] Boutons de retour sous chaque alerte : ✅ erreur réelle / 🏷️ simple promo / 🐛 bug de collecte.
- [ ] **Rejeu de l'historique (backtest)** pour mesurer précision et rappel avant de déployer un changement.
- [ ] Seuils relevés pendant les soldes et le Black Friday.
- [ ] **Plages horaires** : le bot surveille le monde entier 24 h/24, mais ne notifie la nuit
      que les alertes de score ≥ 90.

**Critère de fin** : sur 2 semaines, au moins 50 % des alertes sont jugées « erreur réelle »
ou « très bonne affaire », et le délai médian entre le changement de prix et l'alerte est
inférieur à 15 min sur les sources en temps réel.

---

## Phase 4 : Couverture mondiale (en continu)

**Objectif** : étendre la surveillance pays par pays, en ne gardant que les erreurs qu'on peut vraiment acheter depuis la France.

### Étape A : France
- [ ] Tous les sites accessibles de [SITES.md](SITES.md) et Amazon.fr.
- [ ] Découverte de produits : sitemaps, pages catégories, nouveautés.
- [ ] Collecte par **pages de liste** : une requête donne 20 à 60 prix (voir le
      [calcul de capacité](ARCHITECTURE.md#2-planificateur)).
- [ ] **Signal secondaire pour les sites bloqués** (Cdiscount, Fnac, Darty…) : suivre les
      flux publics des communautés de bons plans (ex. Dealabs), filtrés sur les erreurs de prix.

### Étape B : Union européenne (pas de douane)
- [ ] Amazon .de, .it, .es via Keepa.
- [ ] Sites européens accessibles (Coolblue, Otto…), après test et fiche site.
- [ ] Conversion de devises, détection de la **livraison vers la France**.

### Étape C : Reste du monde
- [ ] Amazon .co.uk, .com, .co.jp, .ca… via Keepa.
- [ ] Calcul du **prix rendu en France** : livraison, TVA à l'importation, droits de douane selon
      la catégorie et la valeur (règles douanières de l'UE en évolution, à vérifier au moment du
      développement). Une erreur à -60 % aux États-Unis peut ne plus valoir le coup une fois livrée.
- [ ] L'alerte est envoyée seulement si l'offre est livrable en France et reste intéressante une fois rendue.

### Pour toutes les étapes
- [ ] Planification adaptative : fréquence selon la valeur du produit, sa volatilité et l'historique d'erreurs du site.
- [ ] **Mesure du rappel** : comparer avec les erreurs de prix publiées par les communautés de bons plans.

**Critère de fin** (à chaque étape) : nouveaux pays couverts sans dégrader le délai d'alerte ni la précision.

---

## Phase 5 : Intelligence (3 à 4 semaines)

**Objectif** : remplacer les réglages manuels par des réglages appris sur les retours.

- [ ] Modèle de score entraîné sur les alertes notées (régression logistique, puis gradient boosting).
- [ ] Détection d'anomalies non supervisée en complément (ex. Isolation Forest).
- [ ] **Vérification par un LLM** pour les candidats ambigus (bon produit ? neuf ? vendu par le
      marchand ? prix réel ? conditions cachées ?). Budget mensuel plafonné.
- [ ] Rapprochement des produits sans EAN par similarité de titres (embeddings), y compris entre langues.

**Critère de fin** : précision d'au moins 70 % sur un mois, avec un rappel égal ou supérieur.

---

## Phase 6 : Produit (non prévue)

Le bot est destiné à un usage personnel. Si l'idée de l'ouvrir à d'autres revient un jour
(tableau de bord web, abonnements, monétisation), voir les obligations dans
[JURIDIQUE.md](JURIDIQUE.md#3-diffusion-publique-des-alertes-phase-6).

---

## Phase 7 : Extensions

- **Vols « mistake fares »** : sources différentes (API de recherche de vols), prix de
  référence par route et par saison, prix très volatils. C'est presque un second moteur de détection.
- Hôtels et locations.

---

## Indicateurs suivis dès la phase 1

| Indicateur | Définition | Cible |
|---|---|---|
| Délai d'alerte | Temps entre le changement de prix et l'alerte | < 15 min sur les sources en temps réel |
| Précision | Part des alertes jugées utiles | ≥ 50 % (phase 3), puis ≥ 70 % (phase 5) |
| Rappel | Part des erreurs publiques connues qu'on a détectées | mesuré à partir de la phase 4 |
| Couverture | Nombre de pays, de sites et d'offres suivis | en hausse |
| Taux de collecte | Part des requêtes dont on a pu extraire un prix | ≥ 95 % |
| Coût mensuel | Serveur et API | ≤ budget fixé |

## Risques principaux

| Risque | Impact | Parade |
|---|---|---|
| Les grandes enseignes bloquent les robots | Couverture limitée en France | Amazon via Keepa, sites accessibles, signal communautaire pour les autres |
| Trop de faux positifs | On finit par ignorer les alertes | Score, vérification, retours, rejeu de l'historique |
| Arnaques de vendeurs tiers (Amazon) | Perte d'argent | Forte pénalité et mention claire dans l'alerte |
| Un site accessible se met à bloquer | Perte d'un connecteur | Pause automatique, on le retire **sans contourner** |
| Changement de structure des pages | Collecte cassée sans qu'on le voie | Données structurées en priorité, canaris, fixtures de test |
| Fraîcheur des données Keepa | Erreur vue en retard | Mesurer le délai réel, combiner avec le suivi direct des produits clés |
| Commande annulée par le marchand | Déception | Inhérent aux erreurs de prix (voir [JURIDIQUE.md](JURIDIQUE.md#2-acheter-un-produit-affiché-à-un-prix-erroné)) |
| Frais d'import hors UE | Une « affaire » qui n'en est pas une | Calcul du prix rendu en France (étape C) |
| Dérive des coûts | Budget dépassé | Keepa résiliable chaque mois, LLM seulement sur les candidats, plafonds |

## Prochaines étapes

1. Fixer le budget et le temps disponible ([BESOINS.md](BESOINS.md#6-décisions)).
2. Remplir les fiches de LDLC et de Rue du Commerce.
3. Initialiser le dépôt (fin de la phase 0).
