# Modélisation

Comment on passe des données préparées au modèle enregistré. Tout est dans `notebook/2.Preprocessing.ipynb`, sections 6 à 11.

La préparation des données est décrite dans [transformation.md](transformation.md).

---

## La stratégie

Quatre temps, dans cet ordre.

| Étape | Ce qu'on fait | Sur quoi |
|---|---|---|
| 1. Comparer | Les cinq modèles avec leurs réglages par défaut | Entraînement, validation croisée |
| 2. Optimiser | Chercher les meilleurs hyperparamètres | Entraînement, validation croisée |
| 3. Régler le seuil | Trouver le seuil de décision qui maximise le F1 | Entraînement, validation croisée |
| 4. Évaluer | Une seule mesure, définitive | Jeu de test |

**Le jeu de test n'intervient qu'à la dernière étape.** Il représente 20 % des patients, mis de côté au début et jamais consultés avant. C'est la seule garantie que le score annoncé reflète ce qui se passera sur le fichier de l'enseignant.

---

## Les cinq modèles

| Modèle | Principe | Préparation reçue |
|---|---|---|
| Boosting | Des arbres construits **en série**, chacun corrigeant les erreurs du précédent | Aucune, il gère les manquants nativement |
| Régression logistique | Une somme pondérée des variables, transformée en probabilité | Log, imputation, mise à l'échelle |
| Forêt aléatoire | Des centaines d'arbres **indépendants** qui votent | Imputation seule |
| Arbres extrêmement aléatoires | Comme la forêt, mais les seuils de coupure sont tirés au hasard | Imputation seule |
| Super-learner | Empile les quatre précédents, un dernier modèle apprend à les combiner | Celle de ses composants |

Les quatre premiers pondèrent les classes. Sans cela, le modèle apprend à toujours répondre « pas de bactériémie » : 92 % de bonnes réponses et un F1 nul.

Le super-learner, lui, n'est pas pondéré : il reçoit des probabilités déjà corrigées par les quatre autres. Le pondérer à nouveau compterait deux fois le déséquilibre.

---

## Les trois mesures, et laquelle croire

| Mesure | Ce qu'elle juge | Dépend d'un seuil ? |
|---|---|---|
| F1 score | La décision finale, 0 ou 1 | **Oui** |
| AUC | Le classement de tous les patients | Non |
| Précision moyenne | Le classement, en se concentrant sur la classe rare | Non |

C'est le F1 qui sert au classement du défi. Mais il ne se mesure qu'à un seuil donné, et le seuil par défaut de 0,5 n'a aucune raison d'être le bon quand 8 % des patients sont positifs.

**Un exemple frappant dans nos résultats** : à la première étape, le super-learner obtient le meilleur AUC et le pire F1, 0,049. Ses probabilités restent proches de la prévalence réelle et ne franchissent presque jamais 0,5, donc il ne prédit presque aucun positif. Après réglage du seuil, il passe en tête.

**Conclusion pratique** : avant le réglage du seuil, on compare les modèles sur la précision moyenne. C'est aussi le critère de l'optimisation des hyperparamètres, pour la même raison.

---

## L'optimisation des hyperparamètres

Une optimisation bayésienne : au lieu de tirer des combinaisons au hasard, elle apprend des essais précédents et vise les zones prometteuses.

Le critère est la précision moyenne, pas le F1 — régler des hyperparamètres au seuil par défaut reviendrait à juger les modèles sur une décision qui n'est pas encore prise.

**Deux points pratiques.** La recherche dure environ une heure, elle n'est donc lancée qu'une fois : les hyperparamètres retenus sont enregistrés dans `models/`, et les exécutions suivantes les relisent. Le critère et la version de l'espace de recherche figurent dans le nom du fichier, donc en changer l'un ou l'autre invalide le cache automatiquement.

Et une valeur retenue collée à une borne de l'espace de recherche signifie que cet espace est trop étroit : c'est le premier réflexe de contrôle après une recherche.

---

## Le réglage du seuil

`TunedThresholdClassifierCV` cherche le seuil qui maximise le F1, en validation croisée : chaque patient est évalué par un modèle qui ne l'a pas vu à l'entraînement.

Son intérêt par rapport à une boucle écrite à la main : l'objet renvoyé **est lui-même un classifieur**, dont la prédiction applique déjà le seuil. Il n'y a donc aucun seuil à transporter jusqu'au script de rendu, ni à réappliquer à la main.

Le seuil retenu peut être très éloigné de 0,5, et c'est normal : il se cale sur l'échelle réelle des probabilités du modèle.

---

## Les résultats

### Avant optimisation, avant réglage du seuil

| Modèle | F1 au seuil 0,5 | AUC | Précision moyenne |
|---|---|---|---|
| Super-learner | 0,049 | **0,793** | **0,299** |
| Forêt aléatoire | **0,333** | 0,791 | 0,288 |
| Régression logistique | 0,285 | 0,777 | 0,288 |
| Arbres extrêmes | 0,321 | 0,774 | 0,262 |
| Boosting | 0,323 | 0,773 | 0,259 |

### Ce que l'optimisation apporte

Précision moyenne, avant puis après :

| Modèle | Avant | Après |
|---|---|---|
| Boosting | 0,259 | **0,298** |
| Régression logistique | 0,288 | **0,297** |
| Forêt aléatoire | 0,288 | 0,290 |
| Arbres extrêmes | 0,262 | 0,263 |

Le boosting est le grand bénéficiaire. La forêt et les arbres extrêmes étaient déjà bien réglés par défaut.

### Après réglage du seuil

| Modèle | Seuil retenu | F1 |
|---|---|---|
| Super-learner | 0,193 | **0,352** |
| Forêt aléatoire | 0,527 | 0,341 |
| Boosting | 0,647 | 0,337 |
| Régression logistique | 0,649 | 0,334 |
| Arbres extrêmes | 0,263 | 0,324 |

Le super-learner devance la forêt de 0,011. L'écart reste inférieur à la variabilité d'un pli de validation croisée à l'autre, qui est de l'ordre de 0,02 à 0,04 : il faut donc rester prudent. Mais la forêt est bien plus rapide, ce qui reste un argument si le temps de calcul devient contraignant.

### Évaluation finale sur le jeu de test

Modèle retenu : le super-learner, au seuil de 0,193.

| Mesure | Valeur |
|---|---|
| F1 | **0,354** |
| Précision | 0,307 |
| Rappel | 0,418 |
| AUC | 0,773 |

Lecture clinique : parmi les patients signalés par le modèle, environ trois sur dix ont réellement une bactériémie, contre huit sur cent dans la population de départ. Le modèle en détecte un peu plus de quatre sur dix.

Un F1 de 0,35 paraît faible, mais le problème est difficile : les deux groupes se recouvrent largement, parce que tous ces patients étaient déjà suspects d'infection.

---

## Les variables qui portent la décision

Mesuré par permutation : on mélange les valeurs d'une colonne au hasard et on regarde de combien le score chute.

| Variable | Perte |
|---|---|
| `GLU` (glycémie) | 0,0793 |
| `nb_anomalies` (variable construite) | 0,0788 |
| `AGE` | 0,0734 |
| `SODIUM` | 0,0598 |
| `CHE` (cholinestérase) | 0,0581 |

Deux remarques. Le profil est **plat** : aucune variable ne domine, le signal est réparti sur beaucoup d'analyses. Et notre variable construite arrive deuxième, ce qui confirme qu'elle est réellement utilisée.

Les pertes se tenant dans un intervalle très resserré, c'est la composition du groupe de tête qu'il faut retenir, pas son ordre exact.

Attention à l'interprétation : deux variables redondantes se partagent le mérite. Mélanger l'une laisse l'autre disponible, donc les deux paraissent faibles alors que l'information compte.

---

## Ce qui a été testé puis écarté

| Piste | Résultat |
|---|---|
| Rééchantillonnage, onze variantes dont SMOTE et ADASYN | Toutes moins bonnes que la pondération des classes |
| Donner les variables brutes au super-learner en plus des probabilités | F1 plus faible qu'avec les seules probabilités |
| Miroir logarithmique de `NEUR` | Corrige la distribution, aucun effet sur le score |
| Compteurs de valeurs manquantes par panel | Redondants avec les indicateurs de l'imputation |

Sur le rééchantillonnage, le motif est net : plus une technique invente des positifs, plus elle nuit. Les méthodes qui se contentent de nettoyer sont neutres. L'explication tient à la forme des données — dans la zone où les deux classes se recouvrent, il n'y a pas de frontière à affiner, il y a du bruit, et y fabriquer des patients synthétiques amplifie ce bruit.

---

## Le rendu

Le modèle retenu est réentraîné sur **toutes** les données, entraînement et test réunis, puis enregistré dans `models/` avec la liste des colonnes attendues.

`Predicts.py` lit un CSV de test, applique exactement la même préparation que le notebook, charge le modèle et écrit deux colonnes, `ID` et `pred`. Le seuil de décision est à l'intérieur du modèle : le script n'a rien à recalculer.

**Un point de vigilance** : les fonctions de préparation sont recopiées à l'identique entre le notebook et `Predicts.py`. Toute modification de l'une doit être reportée dans l'autre, sinon le jeu de test subit un traitement différent de l'entraînement.
