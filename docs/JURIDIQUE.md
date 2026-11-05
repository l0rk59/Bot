# Cadre juridique et règles de collecte

> Ce document n'est pas un avis juridique. Il recense les points à connaître pour un projet
> en France et dans l'UE. **Avant toute diffusion publique ou commerciale, faire valider le
> projet par un juriste.**

## 1. Collecter des prix sur des sites tiers

La collecte automatisée (« scraping ») n'est pas interdite en soi, mais plusieurs règles l'encadrent :

| Règle | Ce qu'elle implique pour le bot |
|---|---|
| **CGU de chaque site** | Beaucoup interdisent l'extraction automatisée. Les enfreindre expose à des poursuites contractuelles et à un blocage. Il faut les lire pour chaque site et noter la conclusion dans sa fiche. |
| **Droit des bases de données** (art. L342-1 et suivants du Code de la propriété intellectuelle) | Le producteur d'une base peut interdire l'extraction d'une partie substantielle de son contenu, ou l'extraction répétée et systématique de petites parties. On ne collecte que le nécessaire et on ne republie pas les catalogues. |
| **Accès frauduleux à un système informatique** (art. 323-1 du Code pénal) | Contourner une protection technique (CAPTCHA, blocage d'IP, connexion requise) peut constituer un accès ou un maintien frauduleux. **On ne contourne jamais.** |
| **RGPD** | Les prix ne sont pas des données personnelles. En revanche, le nom d'un vendeur particulier sur une marketplace en est une : on ne le stocke pas. Les données des futurs utilisateurs du bot (phase 6) sont soumises au RGPD. |

### Règles de bonne conduite du projet

1. Privilégier les **API officielles** et les **flux d'affiliation**.
2. Respecter `robots.txt`.
3. Garder un débit faible, mettre en cache et utiliser les requêtes conditionnelles.
4. Utiliser un User-Agent identifiable avec une URL de contact.
5. **Ne jamais contourner une protection** : pas de résolution de CAPTCHA, pas de rotation
   d'IP pour échapper à un blocage, pas de pages nécessitant un compte, pas de faux comptes.
6. Arrêter immédiatement la collecte sur un site qui le demande ou qui bloque le bot.
7. Ne collecter que le strict nécessaire : prix, titre, identifiants, disponibilité, vendeur professionnel.
8. Ne pas republier les catalogues ni les historiques complets d'un site.

## 2. Acheter un produit affiché à un prix erroné

- **Le marchand peut souvent annuler la vente.** Un contrat à titre onéreux est nul si la
  contrepartie est « illusoire ou dérisoire » (art. 1169 du Code civil), et la jurisprudence
  admet l'annulation pour une **erreur matérielle manifeste**. Les contrats doivent en outre
  être exécutés de bonne foi (art. 1104 du Code civil).
- Une confirmation de commande ne garantit pas la livraison. Le marchand peut rembourser et annuler.
- Le bot doit l'indiquer clairement dans chaque alerte. Les achats massifs et la revente sont à
  éviter : ils peuvent être vus comme de la mauvaise foi.
- **Pas d'achat automatique** : l'humain reste maître de chaque commande.

## 3. Diffusion publique des alertes (phase 6)

Si les alertes sont un jour partagées au-delà d'un usage personnel :

- **Mentions légales** (LCEN), **CGU** et **politique de confidentialité** (RGPD).
- **Liens affiliés** : les signaler clairement. Les pratiques commerciales trompeuses sont
  interdites par le Code de la consommation. Vérifier aussi les obligations de la loi
  n° 2023-451 du 9 juin 2023 sur l'influence commerciale.
- **Règles des programmes d'affiliation** : ils imposent souvent des règles d'affichage des
  prix (fraîcheur, horodatage, mentions). Les lire avant de publier.
- **Revenus** : choisir un statut adapté (ex. micro-entreprise) et les déclarer.

## 4. Fiche site (à remplir avant tout connecteur)

Copier ce modèle dans `docs/sites/<site>.md` pour chaque site candidat.

```markdown
# <Nom du site>

- Domaine :
- Date de revue :

## Accès aux données
- [ ] API officielle disponible ?            → lien, conditions :
- [ ] Flux produits d'affiliation ?          → réseau (Awin, Effiliation…) :
- [ ] Données structurées JSON-LD Product/Offer sur les pages produit ?
- [ ] Prix visible sans JavaScript ?
- [ ] Pages de liste exploitables (catégories, tri par prix) ?
- [ ] Sitemap produits disponible ?

## Cadre
- [ ] CGU lues → clause sur l'extraction automatisée (citer) :
- [ ] robots.txt → chemins produit autorisés ? Crawl-delay ?
- [ ] Protection anti-robot observée (CAPTCHA, blocage) ? → si oui : pas de collecte HTML
- Débit retenu :

## Intérêt
- Catégories :
- Marketplace (vendeurs tiers) ? :
- Erreurs de prix passées connues ? :

## Décision
- [ ] OK pour collecte    [ ] Via API ou flux uniquement    [ ] Exclu
- Raison :
```
