# Tout ce qu'il faut pour le bot

## 1. Comptes et accès

| Élément | À quoi il sert | Phase | Coût |
|---|---|---|---|
| GitHub (déjà en place) | Code, CI | 0 | Gratuit |
| Bot Telegram (via @BotFather) et un groupe privé | Recevoir les alertes | 0 | Gratuit |
| Sentry | Suivre les erreurs du bot | 2 | Offre gratuite |
| Healthchecks.io | Être prévenu si le bot s'arrête (ordinateur éteint, plantage) | 2 | Offre gratuite |
| Keepa API *(option C)* | Prix et historiques Amazon dans une dizaine de pays | Module Amazon | Environ 49 € par mois, résiliable chaque mois |
| Clé d'API LLM *(option)* | Vérification des candidats ambigus | 5 | Quelques euros par mois, plafonnés |

Les réseaux d'affiliation (Awin…) et l'API officielle d'Amazon sont écartés : ils demandent un
site ou des ventes générées, ce qui ne correspond pas à un usage personnel (voir [SITES.md](SITES.md)).

## 2. L'ordinateur (option A)

Le bot tourne sur l'ordinateur personnel. Il faut :

| Élément | Minimum |
|---|---|
| Mémoire vive | 8 Go (16 Go confortable : PostgreSQL, Redis et un navigateur sans interface tournent en parallèle) |
| Disque libre | 10 Go |
| Logiciels | Python 3.12+, Git, Docker (Docker Desktop sous Windows et macOS) |
| Réglages | **Mise en veille désactivée**, Docker lancé au démarrage, redémarrage automatique après une mise à jour système |
| Connexion | Une connexion domestique suffit (le bot fait peu de requêtes) |

Le bot consomme peu : environ une requête toutes les 5 secondes par site.

Si l'ordinateur est souvent éteint, on peut passer à l'option B (petit serveur loué, environ
5 € par mois) sans rien changer au code : c'est le même `docker-compose.yml`.

## 3. Budget : option A retenue (0 €)

| Option | Contenu | Coût mensuel |
|---|---|---|
| **A. Gratuit** ✅ | Ordinateur personnel, sites autorisés uniquement, pas d'Amazon | 0 € |
| B. Serveur | VPS, sites autorisés uniquement, pas d'Amazon | environ 5 € |
| C. Complet | VPS, sites autorisés et Amazon dans une dizaine de pays (Keepa) | environ 55 € |

On peut passer à B ou C à tout moment. Le module Amazon est prévu dans la
[roadmap](ROADMAP.md#module-optionnel--amazon-via-keepa).

## 4. Compétences

| Compétence | Utilité | Niveau requis |
|---|---|---|
| Python, y compris `async`/`await` | Tout le projet | Intermédiaire |
| HTML, sélecteurs CSS, outils de développement du navigateur | Écrire et réparer les extracteurs | Intermédiaire |
| SQL et PostgreSQL | Historique, requêtes d'analyse | Bases |
| Git et Docker | Lancer et mettre à jour le bot | Bases |
| Statistiques simples (médiane, percentiles, MAD) | Détection | Bases |
| Apprentissage automatique | Phase 5 | Notions, à apprendre en cours de route |

## 5. Données de départ

- **Sites** : LDLC pour le MVP, puis Rue du Commerce et Electro Dépôt. Voir [SITES.md](SITES.md).
- **Produits témoins** : 100 à 300 produits LDLC avec URL et EAN, de préférence chers (plus de
  100 €) et vendus aussi sur Rue du Commerce.
- **Catégories prioritaires** : high-tech et informatique (le point fort des sites autorisés),
  puis électroménager.

## 6. Décisions

| # | Question | Réponse |
|---|---|---|
| 1 | Usage | ✅ Personnel uniquement |
| 2 | Marchés | ✅ Monde entier, par étapes : France, puis UE, puis reste du monde |
| 3 | Verticales | ✅ Produits d'abord |
| 4 | Sites | ✅ LDLC (MVP), Rue du Commerce, Electro Dépôt. TopAchat exclu (CGU). Cdiscount et Fnac : signal secondaire |
| 5 | Canal d'alerte | ✅ Telegram |
| 6 | Langage | ✅ Python |
| 7 | Achat automatique | ✅ Non |
| 8 | Budget | ✅ Option A (0 €) |
| 9 | Temps disponible | ✅ Plein temps |
| 10 | Seuil minimal d'une alerte | Proposé : baisse d'au moins 50 % **et** au moins 30 € d'économie (réglable) |

## 7. À faire de votre côté

1. **Créer le bot Telegram** (5 minutes) :
   - dans Telegram, ouvrir une conversation avec **@BotFather** et envoyer `/newbot` ;
   - choisir un nom, puis un identifiant qui finit par `bot` ;
   - BotFather renvoie un **jeton** (token). Le garder secret : il ira dans le fichier `.env`
     de l'ordinateur, **jamais** dans le dépôt GitHub ni dans une conversation ;
   - créer un groupe privé, y ajouter le bot, et y envoyer un premier message.
2. **Indiquer le système d'exploitation** de l'ordinateur (Windows, macOS ou Linux), pour adapter
   les instructions d'installation.
3. **Désactiver la mise en veille** de l'ordinateur (l'écran peut s'éteindre, pas la machine).
