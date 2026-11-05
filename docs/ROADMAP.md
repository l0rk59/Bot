# Roadmap de développement

## Hypothèses de départ

Ces hypothèses fixent le périmètre initial. Elles sont à confirmer, voir
[BESOINS.md › Décisions à prendre](BESOINS.md#6-décisions-à-prendre).

- **Usage** : outil personnel d'abord, ouverture éventuelle à d'autres utilisateurs ensuite.
- **Marché** : sites marchands français, puis européens.
- **Verticale** : e-commerce (produits physiques). Les vols et hôtels viennent plus tard.
- **Canal d'alerte** : Telegram.
- **Langage** : Python.
- **Pas d'achat automatique** : le bot alerte, l'humain décide et achète.
- **Rythme** : un développeur à temps partiel (environ 10 à 15 h par semaine). Les durées
  sont indicatives. À temps plein, les diviser par environ 2,5.

## Vue d'ensemble

| Phase | Objectif | Durée indicative | Résultat visible |
|---|---|---|---|
| **0. Cadrage** | Fixer le périmètre, préparer le dépôt | 1 sem. | Dépôt prêt, sites pilotes choisis |
| **1. MVP** | Faire fonctionner toute la chaîne sur 1 site | 2–3 sem. | Première alerte Telegram |
| **2. Fondations** | Rendre le système robuste et multi-sites | 3–4 sem. | 5 à 10 sites surveillés 24 h/24 sur un serveur |
| **3. Détection avancée** | Alertes fiables, peu de faux positifs | 3–4 sem. | Score de confiance et retours utilisateur |
| **4. Couverture** | Surveiller beaucoup plus de produits | continu | Découverte automatique, plus de 20 sites |
| **5. Intelligence** | Apprendre des retours, vérification par IA | 3–4 sem. | Précision mesurée et en hausse |
| **6. Produit** *(optionnelle)* | Multi-utilisateurs, tableau de bord | 4–6 sem. | Interface web, abonnements filtrés |
| **7. Extensions** | Vols, hôtels, autres pays | variable | Nouvelles verticales |

### Jalons

| Jalon | Contenu | Fin de phase | Semaine estimée |
|---|---|---|---|
| **J1** | Première alerte réelle reçue sur Telegram | 1 | S4 |
| **J2** | Bot personnel fiable, en production 24 h/24 | 3 | S12 |
| **J3** | Précision ≥ 70 % mesurée sur un mois | 5 | S20 environ |
| **J4** | Ouverture à d'autres utilisateurs | 6 | S26 environ |

---

## Phase 0 : Cadrage (1 semaine)

**Objectif** : tout décider et tout préparer pour que la phase 1 se limite à du code.

- [ ] Valider les [décisions ouvertes](BESOINS.md#6-décisions-à-prendre).
- [ ] Présélectionner 5 à 8 sites candidats et remplir une **fiche par site**
      ([modèle](JURIDIQUE.md#4-fiche-site-à-remplir-avant-tout-connecteur)) : CGU, `robots.txt`,
      API ou flux d'affiliation, présence de données structurées (JSON-LD `Product`/`Offer`),
      rendu JavaScript nécessaire ou non, protections anti-robot.
- [ ] Retenir 3 à 5 **sites pilotes** parmi ceux dont la fiche est « OK pour collecte ».
- [ ] Constituer une liste de **100 à 300 produits témoins** (URL et EAN) dans les catégories
      où les erreurs sont fréquentes (high-tech, électroménager, jeux vidéo et jouets, maison).
- [ ] Initialiser le dépôt : `pyproject.toml` (uv), ruff, mypy, pytest, pre-commit, CI GitHub
      Actions, `.gitignore`, `.env.example`, `Dockerfile`.
- [ ] Créer le bot Telegram (BotFather) et un groupe privé de test.

**Livrables** : dépôt initialisé avec CI verte, fiches des sites, liste de produits témoins.

**Critère de fin** : la CI passe sur le squelette de projet. Chaque site pilote a une fiche validée.

---

## Phase 1 : MVP (2 à 3 semaines)

**Objectif** : faire tourner toute la chaîne de bout en bout sur un seul site, dans sa version la plus simple.

- [ ] Client HTTP asynchrone : limite de débit par domaine, User-Agent identifiable, délais
      d'attente, nouvelles tentatives espacées progressivement, respect de `robots.txt`.
- [ ] Extracteur générique de données structurées (JSON-LD, microdata, OpenGraph) qui renvoie
      le prix, la devise, la disponibilité, l'EAN et le titre.
- [ ] Connecteur du premier site pilote (le plus simple : données structurées présentes, pas de JavaScript requis).
- [ ] Stockage (SQLite ou directement PostgreSQL) : produits, offres, observations de prix.
- [ ] Planificateur simple : chaque offre est revérifiée toutes les N minutes.
- [ ] Une seule règle de détection : prix inférieur à 50 % de la médiane des observations
      précédentes, **ou** virgule décalée (×10 ou ×100).
- [ ] Alerte Telegram : produit, ancien prix, nouveau prix, pourcentage de baisse, lien.
- [ ] **Faux magasin local** (mini serveur web dont on modifie les prix à volonté) pour tester sans toucher aux vrais sites.
- [ ] Tests : extraction sur des pages HTML enregistrées (fixtures), détection sur des séries de prix synthétiques.

**Livrables** : la commande `pricebot run` tourne en local et envoie des alertes.

**Critère de fin** : une baisse de prix sur le faux magasin déclenche une alerte Telegram en
moins de N + 1 minutes. Le bot tourne 48 h sur le vrai site pilote sans planter.

---

## Phase 2 : Fondations (3 à 4 semaines)

**Objectif** : passer d'un prototype à un système multi-sites qui tourne seul sur un serveur.

- [ ] PostgreSQL et migrations (Alembic). Une observation n'est enregistrée que si le prix ou
      le stock **change** (et l'heure de dernière vérification est mise à jour à chaque passage).
- [ ] Interface `Connector` commune et configuration par site en YAML : débit, priorité, activation.
- [ ] 5 à 10 connecteurs.
- [ ] Rendu JavaScript via Playwright, **uniquement** pour les sites qui l'exigent.
- [ ] File de tâches (Redis + ARQ), workers parallèles et planification par priorité.
- [ ] Identité produit : regroupement des offres par GTIN/EAN (et ASIN ou référence fabricant)
      pour comparer un même produit d'un marchand à l'autre.
- [ ] Santé des connecteurs : taux de succès, taux d'échec d'extraction, produits « canaris »
      au prix connu. Si un site casse, le connecteur se met en pause et une alerte part vers le développeur.
- [ ] Logs structurés en JSON, erreurs envoyées vers Sentry.
- [ ] Docker Compose et déploiement sur un VPS. Sauvegarde quotidienne de la base.

**Critère de fin** : 7 jours consécutifs en production sans intervention, au moins 95 % de
collectes réussies, et une casse d'extracteur provoquée volontairement est détectée et signalée automatiquement.

---

## Phase 3 : Détection avancée (3 à 4 semaines)

**Objectif** : des alertes peu nombreuses mais justes. Le détail est dans [DETECTION.md](DETECTION.md).

- [ ] Prix de référence : médiane historique et prix du marché (même EAN chez les autres marchands).
- [ ] Signaux multiples et **score de confiance** de 0 à 100.
- [ ] Filtres contre les faux positifs : vendeur tiers de marketplace, produit reconditionné,
      prix « à partir de », prix mensuel, produit en rupture, etc.
- [ ] Étape de **vérification** : nouvelle collecte immédiate, cohérence entre prix barré et
      prix affiché, capture d'écran horodatée.
- [ ] Déduplication et anti-spam : une seule alerte par offre et par épisode, puis un message
      de suivi quand le prix est corrigé.
- [ ] Boutons de retour sous chaque alerte : ✅ erreur réelle / 🏷️ simple promo / 🐛 bug de collecte.
- [ ] **Rejeu de l'historique (backtest)** : rejouer les données stockées avec de nouveaux
      seuils pour mesurer précision et rappel avant de déployer un changement.
- [ ] Seuils relevés pendant les soldes et le Black Friday.

**Critère de fin** : sur 2 semaines, au moins 50 % des alertes sont jugées « erreur réelle »
ou « très bonne affaire », et le délai médian entre le changement de prix et l'alerte est
inférieur à 15 min sur les produits prioritaires.

---

## Phase 4 : Couverture (en continu)

**Objectif** : trouver des erreurs sur des produits qu'on n'a pas listés à la main.

- [ ] Découverte de produits : sitemaps, pages catégories, nouveautés.
- [ ] Collecte par **pages de liste** (catégories triées par prix, résultats de recherche) :
      une seule requête donne 20 à 60 prix (voir le
      [calcul de capacité](ARCHITECTURE.md#2-planificateur)).
- [ ] Intégration des **flux produits d'affiliation** (Awin, Effiliation, Kwanko…) : catalogues
      complets avec EAN, obtenus légalement, utiles pour la découverte et les prix de référence.
- [ ] Planification adaptative : fréquence de vérification selon la valeur du produit, sa
      volatilité et l'historique d'erreurs du site.
- [ ] Marchés européens (Amazon .de, .it, .es…) avec conversion de devises.
- [ ] **Mesure du rappel** : comparer avec les erreurs de prix publiées par les communautés de
      bons plans (ex. Dealabs). Les avait-on détectées, et avant elles ?

**Critère de fin** (à chaque itération) : doubler le nombre de produits suivis sans dégrader
le délai d'alerte ni le taux de collecte.

---

## Phase 5 : Intelligence (3 à 4 semaines)

**Objectif** : remplacer les réglages manuels par des réglages appris sur les retours.

- [ ] Modèle de score entraîné sur les alertes notées (régression logistique, puis gradient boosting).
- [ ] Détection d'anomalies non supervisée en complément (ex. Isolation Forest).
- [ ] **Vérification par un LLM** pour les candidats ambigus. Il lit la page et répond : bon
      produit ? neuf ? vendu par le marchand ? prix réel TTC ? conditions cachées ? Budget mensuel plafonné.
- [ ] Rapprochement des produits sans EAN par similarité de titres (embeddings).

**Critère de fin** : précision d'au moins 70 % sur un mois, avec un rappel égal ou supérieur à celui de la phase 4.

---

## Phase 6 : Produit (optionnelle, 4 à 6 semaines)

**Objectif** : ouvrir le bot à d'autres personnes.

- [ ] API (FastAPI) et tableau de bord web : historique des prix, alertes, santé des sites.
- [ ] Abonnements par utilisateur : catégories, marques, baisse minimale, prix maximal, mots-clés.
- [ ] Gestion des comptes et conformité légale : RGPD, CGU, mentions légales (voir [JURIDIQUE.md](JURIDIQUE.md#3-diffusion-publique-des-alertes-phase-6)).
- [ ] Monétisation éventuelle (liens affiliés signalés comme tels, offre premium) et statut juridique adapté.

**Critère de fin** : 10 utilisateurs test pendant un mois, retours collectés.

---

## Phase 7 : Extensions

- **Vols « mistake fares »** : sources différentes (API de recherche de vols), prix de
  référence par route et par saison, prix très volatils. C'est presque un second moteur de détection.
- Hôtels et locations.
- Prix en magasin et en drive.
- Autres pays.

---

## Indicateurs suivis dès la phase 1

| Indicateur | Définition | Cible |
|---|---|---|
| Délai d'alerte | Temps entre le changement de prix et l'alerte | < 15 min sur les produits prioritaires |
| Précision | Part des alertes jugées utiles | ≥ 50 % (phase 3), puis ≥ 70 % (phase 5) |
| Rappel | Part des erreurs publiques connues qu'on a détectées | mesuré à partir de la phase 4 |
| Couverture | Nombre de sites et d'offres suivis | en hausse |
| Taux de collecte | Part des requêtes dont on a pu extraire un prix | ≥ 95 % |
| Coût mensuel | Serveur et API | ≤ budget fixé |

## Risques principaux

| Risque | Impact | Parade |
|---|---|---|
| Trop de faux positifs | On finit par ignorer les alertes | Score, vérification, retours, rejeu de l'historique |
| Blocage par un site | Perte de couverture | Débit modéré, API et flux d'affiliation. Si le site bloque, on le retire, **sans contourner** |
| Changement de structure des pages | Collecte cassée sans qu'on le voie | Données structurées en priorité, canaris, fixtures de test, pause automatique |
| Pas d'historique au démarrage | Pas de référence pour juger un prix | Comparaison entre marchands dès le premier jour, flux d'affiliation, services d'historique |
| Commande annulée par le marchand | Déception de l'utilisateur | Le dire clairement : c'est inhérent aux erreurs de prix (voir [JURIDIQUE.md](JURIDIQUE.md#2-acheter-un-produit-affiché-à-un-prix-erroné)) |
| Risque juridique | Mise en demeure, poursuites | Règles de [JURIDIQUE.md](JURIDIQUE.md), avis d'un juriste avant toute ouverture publique |
| Dérive des coûts (navigateur, LLM) | Budget dépassé | Playwright seulement si nécessaire, LLM seulement sur les candidats, plafonds de dépense |

## Prochaines étapes

1. Répondre aux [décisions à prendre](BESOINS.md#6-décisions-à-prendre).
2. Remplir les fiches des sites candidats.
3. Lancer la phase 0 (initialisation du dépôt).
