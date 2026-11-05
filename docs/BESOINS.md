# Tout ce qu'il faut pour le bot

## 1. Comptes et accès

| Élément | À quoi il sert | Phase | Coût |
|---|---|---|---|
| GitHub (déjà en place) | Code, CI | 0 | Gratuit |
| Bot Telegram (via @BotFather) et un groupe privé | Recevoir les alertes | 0 | Gratuit |
| **Keepa API** | Prix et historiques Amazon dans une dizaine de pays | 2 | **Environ 49 € par mois** (formule d'entrée, à confirmer sur keepa.com/api), résiliable chaque mois |
| Serveur allumé 24 h/24 | Faire tourner le bot | 2 | 0 € (ordinateur personnel) ou environ 5 € par mois (VPS) |
| Sentry | Suivre les erreurs | 2 | Offre gratuite suffisante |
| Clé d'API LLM *(option)* | Vérification des candidats ambigus | 5 | À l'usage, avec un plafond (quelques euros par mois) |

Les réseaux d'affiliation (Awin…) et l'API officielle d'Amazon sont écartés : ils demandent un
site ou des ventes générées, ce qui ne correspond pas à un usage personnel (voir [SITES.md](SITES.md)).

## 2. Infrastructure

| Stade | Machine | Services |
|---|---|---|
| Phases 0 et 1 | Ordinateur personnel (Python 3.12+, Docker) | SQLite ou PostgreSQL en Docker |
| Phase 2 et suivantes | VPS 2 vCPU, 4 Go de RAM (ou ordinateur allumé en permanence) | PostgreSQL, Redis, workers, bot Telegram |
| Si beaucoup de pages en JavaScript | VPS 4 vCPU, 8 Go de RAM | Idem, plus de workers |

Sauvegarde quotidienne de la base (`pg_dump`) stockée hors du serveur.

## 3. Budget : pourquoi et combien

Le budget, c'est ce que le bot coûte **chaque mois** pour fonctionner. Deux postes seulement :

**1. Une machine allumée 24 h/24.** Les erreurs de prix sont souvent corrigées en quelques
minutes ou quelques heures. Si le bot ne tourne que quand l'ordinateur est allumé, il rate la
plupart d'entre elles. Deux possibilités :
- l'ordinateur personnel, laissé allumé en permanence : gratuit, mais le bot s'arrête à chaque extinction ou coupure ;
- un petit serveur loué (VPS, ex. Hetzner, OVH) : **environ 5 € par mois**, toujours allumé.

**2. L'accès aux données d'Amazon.** Amazon interdit les robots sur son site. La voie propre
est l'API Keepa, qui suit Amazon dans une dizaine de pays : **environ 49 € par mois**. C'est le principal poste de dépense.

Tous les autres sites accessibles (LDLC, Rue du Commerce, TopAchat…) sont gratuits.

| Option | Contenu | Coût mensuel |
|---|---|---|
| **A. Gratuit** | Ordinateur personnel, sites accessibles uniquement, **pas d'Amazon** | 0 € |
| **B. Serveur** | VPS, sites accessibles uniquement, **pas d'Amazon** | environ 5 € |
| **C. Complet** | VPS, sites accessibles **et Amazon dans une dizaine de pays** | environ 55 € |

**Recommandation** : commencer gratuitement (option A) pendant la phase 1, le temps de voir le
bot fonctionner. Passer à l'option C au début de la phase 2. Keepa se résilie à tout moment :
si les résultats ne suivent pas, on arrête.

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

- **Sites** : voir [SITES.md](SITES.md). Pour le MVP : LDLC ou Rue du Commerce.
- **Produits témoins** : 100 à 300 produits avec URL et EAN, de préférence chers (plus de
  100 €) et vendus à la fois sur Amazon et sur les sites accessibles.
- **Catégories prioritaires** : high-tech (là où les sites accessibles sont les plus forts),
  électroménager, jeux vidéo et jouets, maison.

## 6. Décisions

| # | Question | Réponse |
|---|---|---|
| 1 | Usage | ✅ **Personnel uniquement** |
| 2 | Marchés | ✅ **Monde entier**, par étapes : France, puis UE, puis reste du monde |
| 3 | Verticales | ✅ **Produits d'abord** |
| 4 | Sites | ✅ Amazon (via Keepa) et sites accessibles. Cdiscount et Fnac bloquent les robots : signal secondaire seulement |
| 5 | Canal d'alerte | ✅ Telegram |
| 6 | Langage | ✅ Python |
| 7 | Achat automatique | ✅ Non |
| 8 | **Budget** | ⏳ Option A, B ou C (section 3). Recommandation : A pour la phase 1, puis C |
| 9 | **Temps disponible par semaine** | ⏳ À préciser, pour recalibrer les durées |
| 10 | Seuil minimal d'une alerte | Proposé : baisse d'au moins 50 % **et** au moins 30 € d'économie (réglable) |
