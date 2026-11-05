# Bot de détection d'erreurs de prix

Bot personnel qui surveille en continu les prix des sites marchands, repère les **erreurs de
prix** (prix anormalement bas causés par une erreur du marchand : virgule décalée, remise mal
saisie, prix d'un autre produit…) et envoie une alerte sur Telegram en quelques minutes.

> **Statut : phase 1 (MVP).** Le bot surveille 32 catégories de LDLC (environ 1 400 prix par
> passage), détecte les prix anormaux, les vérifie sur la fiche produit et envoie une alerte
> Telegram. Prochaine étape : la [phase 2](docs/ROADMAP.md#phase-2--fondations-15-semaine)
> (plusieurs sites, fonctionnement 24 h/24).

## Installation sous Windows

Toutes les commandes se tapent dans **PowerShell** (menu Démarrer, puis « PowerShell »).

**1. Installer Git et uv** (uv installe aussi Python automatiquement) :

```powershell
winget install --id Git.Git -e
winget install --id astral-sh.uv -e
```

Fermez PowerShell puis rouvrez-le pour que les nouvelles commandes soient reconnues.

**2. Télécharger le bot** :

```powershell
cd $HOME\Documents
git clone https://github.com/l0rk59/Bot.git
cd Bot
uv sync
```

**3. Créer le fichier de réglages** :

```powershell
copy .env.example .env
notepad .env
```

Collez le jeton donné par @BotFather après `PRICEBOT_TELEGRAM_TOKEN=`, puis enregistrez.
Ce fichier reste sur votre ordinateur : il n'est jamais envoyé sur GitHub.

**4. Relier le bot à votre groupe Telegram** :

1. Ajoutez votre bot à votre groupe Telegram et envoyez-y `/start`.
2. Lancez `uv run pricebot telegram-test`. La commande affiche l'identifiant du groupe (un
   nombre qui commence souvent par `-100`).
3. Collez-le après `PRICEBOT_TELEGRAM_CHAT_ID=` dans le fichier `.env`.
4. Relancez `uv run pricebot telegram-test` : vous devez recevoir un message de test dans le groupe.

## Essayer sans risque avec le faux magasin

Le faux magasin imite un site marchand sur votre ordinateur. Vous changez un prix, le bot réagit.

1. Dans une **première** fenêtre PowerShell, lancez le magasin : `uv run pricebot fake-shop`
2. Dans une **deuxième** fenêtre (dans le dossier `Bot`), lancez le bot avec un passage toutes
   les 30 secondes : `uv run pricebot run --only fake-shop --interval 0.5`
3. Attendez le premier passage. Le bot apprend alors les prix « normaux ».
4. Ouvrez dans votre navigateur <http://127.0.0.1:8765/admin/prix?id=1&prix=129.90>
   (le téléviseur passe de 1 299 € à 129,90 €).
5. Au passage suivant, l'alerte arrive sur Telegram (ou dans le terminal si Telegram n'est pas
   configuré). Remettez le prix à 1299 : un message « fin de l'erreur » suit.

`Ctrl+C` arrête le bot ou le magasin. La base du faux magasin et celle de LDLC sont la même
(`data/pricebot.sqlite3`) : supprimez ce fichier pour repartir de zéro.

## Lancer la surveillance de LDLC

```powershell
uv run pricebot run
```

- Un passage toutes les 15 minutes (réglable dans `.env`), environ 3 minutes par passage. Le
  bot lit au plus une page toutes les 5 secondes, pour ménager le site.
- **Les alertes commencent au deuxième passage** : le bot doit d'abord connaître le prix
  habituel de chaque produit. Plus il tourne longtemps, plus son jugement est fiable.
- L'ordinateur doit rester allumé, sans mise en veille. Le journal est écrit dans `data/pricebot.log`.

## Commandes

| Commande | Rôle |
|---|---|
| `uv run pricebot run` | Surveillance continue (`--once` pour un seul passage, `--only ldlc` pour un seul site) |
| `uv run pricebot check URL` | Lire une page et afficher les prix trouvés, sans rien enregistrer |
| `uv run pricebot stats` | Nombre d'offres suivies, de changements de prix et d'alertes |
| `uv run pricebot telegram-test` | Vérifier la configuration Telegram |
| `uv run pricebot fake-shop` | Lancer le faux magasin de démonstration |

## Réglages (`.env`)

| Réglage | Par défaut | Rôle |
|---|---|---|
| `PRICEBOT_TELEGRAM_TOKEN` | vide | Jeton du bot Telegram |
| `PRICEBOT_TELEGRAM_CHAT_ID` | vide | Groupe qui reçoit les alertes |
| `PRICEBOT_CHECK_INTERVAL_MINUTES` | 15 | Minutes entre deux passages |
| `PRICEBOT_MAX_RATIO` | 0.5 | Alerte si le prix tombe sous 50 % du prix habituel |
| `PRICEBOT_MIN_SAVING` | 30 | Économie minimale en euros |
| `PRICEBOT_HEALTHCHECK_URL` | vide | Adresse Healthchecks.io, pour être prévenu si le bot s'arrête |

Les sites surveillés sont décrits dans `config/retailers/` (un fichier YAML par site).

## Mettre à jour le bot

```powershell
cd $HOME\Documents\Bot
git pull
uv sync
```

## Développement

```powershell
uv run pytest           # tests (aucun accès aux vrais sites)
uv run ruff check .     # style
uv run mypy             # types
```

La CI GitHub exécute ces vérifications sous Linux et sous Windows à chaque envoi.

## Documentation

| Document | Contenu |
|---|---|
| [docs/ROADMAP.md](docs/ROADMAP.md) | Phases de développement, tâches, critères de fin, jalons, risques |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Composants, stack technique, modèle de données, structure du code |
| [docs/DETECTION.md](docs/DETECTION.md) | Définition d'une erreur de prix, signaux, score, faux positifs |
| [docs/SITES.md](docs/SITES.md) | Quels sites sont accessibles à un robot, et par quelle voie |
| [docs/JURIDIQUE.md](docs/JURIDIQUE.md) | Cadre légal (France/UE), règles de collecte responsable, fiche par site |
| [docs/BESOINS.md](docs/BESOINS.md) | Comptes, infrastructure, budget, compétences, décisions |
