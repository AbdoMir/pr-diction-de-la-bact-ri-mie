# Prédiction de la bactériémie

Modèle de classification binaire qui prédit, à partir d'analyses sanguines, si la culture de sang d'un patient révélera une bactériémie. Projet du défi 1 du cours IDS 2026 (Université de Strasbourg).

Le rendu final est un script qui lit un fichier de même structure que les données d'entraînement et produit un CSV à deux colonnes : `ID` et `pred` (0 ou 1). Les groupes sont classés au **F1 score**, puis à la **précision** en cas d'égalité.

## Données

`data/bacteriemie.csv.gz` : 11 753 patients suspectés de bactériémie à l'Hôpital général de Vienne (Autriche), entre janvier 2006 et décembre 2010, décrits par 53 colonnes.

| | |
|---|---|
| Cible | `BloodCulture` : `yes` (944 patients, 8 %) ou `no` (10 809) |
| Identifiant | `ID`, unique, à exclure des prédicteurs |
| Prédicteurs | `SEX` (1 ou 2), `AGE`, et 49 analyses biologiques continues |
| Valeurs manquantes | Notées `NA`. Seules 3 197 lignes (27 %) sont complètes ; `PAMY` en compte 48 % |

Les données ont été modifiées pour protéger la confidentialité des patients ; cette version est approuvée pour un usage public par l'Université médicale de Vienne (DC 2019-0054).

Le dictionnaire des variables est dans `doc/cahierVariables.csv`. Attention : sa colonne `From.paper` est décalée d'une ligne, les statistiques ne correspondent pas à la variable de la même ligne.

`data/train.parquet` et `data/test.parquet` contiennent le découpage 80 / 20, écrit par le notebook. Ils sont versionnés pour que le découpage reste reproductible sans relancer la préparation.

Deux fichiers ne sont pas versionnés : `doc/GroupesIDS2026.xlsx`, qui contient les noms des étudiants, et `doc/article.pdf`, l'article d'origine.

## Installation

Le projet utilise [uv](https://docs.astral.sh/uv/) et Python 3.12.

```bash
git clone https://github.com/AbdoMir/pr-diction-de-la-bact-ri-mie.git
cd pr-diction-de-la-bact-ri-mie
uv sync
```

`uv sync` crée l'environnement `.venv` et installe les versions exactes figées dans `uv.lock`. Dans VS Code, sélectionnez ensuite `.venv` comme noyau des notebooks.

## Structure

```
Predicts.py                              script de prédiction final (le rendu)
data/      bacteriemie.csv.gz            jeu de données d'origine
           train.parquet, test.parquet   découpage 80 / 20, figé par SEED = 42
doc/       cahierVariables.csv           dictionnaire des variables
           EDA_Resume.md                 les constats de l'analyse exploratoire
           transformation.md             nettoyage, réparation, variables construites
           modelisation.md               les cinq modèles, le seuil, les résultats
image/     pipeLine.png                  schéma des étapes du projet
notebook/  1.EDA.ipynb                        exploration : cible, manquants, distributions
           2.MLFLOW-Prepro&Modeling.ipynb     du CSV au modèle enregistré, avec suivi MLflow
```

Les notebooks s'exécutent depuis le dossier `notebook/`, d'où les chemins relatifs en `../data/`.

Deux dossiers sont créés à l'exécution et **ne sont pas versionnés** : `models/`, qui reçoit le modèle entraîné et le cache des hyperparamètres, et `mlartifacts/` avec `mlflow.db`, qui appartiennent à MLflow.

## Utilisation

Le chargement des données demande de déclarer les valeurs manquantes, sinon polars échoue sur la première colonne numérique contenant `NA` :

```python
df = pl.read_csv("../data/bacteriemie.csv.gz", null_values="NA")
```

**Deux notebooks.** `1.EDA.ipynb` d'abord, puis `2.MLFLOW-Prepro&Modeling.ipynb`, qui va de la lecture du CSV au modèle enregistré : nettoyage, réparation des variables reconstructibles, variables construites, comparaison de six modèles, optimisation des hyperparamètres, réglage du seuil, évaluation finale et suivi MLflow. Le pré-processing et la modélisation sont réunis parce qu'ils partagent les mêmes fonctions : les séparer obligeait à les écrire deux fois.

**Le modèle n'est pas versionné.** `models/` est ignoré par git, parce que le fichier dépasse les trois cents méga-octets. Après un clone, il faut donc exécuter `2.MLFLOW-Prepro&Modeling.ipynb` en entier : sa dernière section réentraîne le modèle retenu sur toutes les données et l'enregistre dans `models/`. Sans ce fichier, `Predicts.py` s'arrête avec un message explicite.

Pour prédire un nouveau jeu de données, depuis la racine du projet :

```bash
uv run python Predicts.py <fichier_entrée.csv> <fichier_sortie.csv>
```

Le script accepte un fichier avec ou sans la colonne `BloodCulture`, et écrit un CSV de deux colonnes, `ID` et `pred`, ne contenant que des 0 et des 1.

Le fichier d'entrée doit contenir **toutes** les colonnes d'origine, y compris `MCV`, `MCH` et `MCHC` : elles servent à reconstruire `RBC` et `HCT` avant d'être retirées, donc elles n'apparaissent pas dans le modèle mais restent indispensables en entrée.

## Suivi des expériences avec MLflow

Lancez le serveur depuis la racine du projet, dans un terminal à part :

```bash
uv run mlflow ui
```

L'interface est sur `http://localhost:5000`. La base `mlflow.db` et le dossier `mlartifacts/` sont créés dans le dossier courant.

Chaque exécution du notebook enregistre dix-huit runs : six pour la comparaison des modèles, cinq pour l'optimisation, six pour le réglage du seuil, un pour l'évaluation finale. Trois tags permettent de s'y retrouver.

| Tag | Usage |
|---|---|
| `execution` | Horodatage commun à tous les runs d'un même passage, pour comparer deux exécutions |
| `etape` | `comparaison`, `optimisation`, `seuil` ou `test` |
| `modele` | Le modèle concerné |

Les hyperparamètres retenus sont dans les runs `optimisation-*`. MLflow n'affiche aucune colonne de paramètre par défaut dans la vue tableau : ouvrez un run, ou ajoutez les colonnes avec le sélecteur.

Le run final enregistre le modèle avec sa signature, les deux figures, le rapport de classification et le classement des variables par importance de permutation.

## Conventions

- Graine aléatoire fixée à `SEED = 42` partout où un tirage intervient, pour des résultats reproductibles.
- Jeu de test interne mis de côté avant tout pré-processing, avec un découpage stratifié (80 / 20).
- Imputation, logarithme et mise à l'échelle calculés sur l'entraînement seulement, à l'intérieur d'un `Pipeline` scikit-learn, pour éviter toute fuite de données.
- Déséquilibre des classes traité par `class_weight="balanced"` et par le réglage du seuil. Onze techniques de rééchantillonnage ont été testées, dont SMOTE et ADASYN : toutes font moins bien, le détail est dans `doc/modelisation.md`.
- Le seuil de décision est choisi pour maximiser le F1, et non laissé à 0,5. Il peut être très éloigné de 0,5, ce qui est normal avec 8 % de positifs.
- Les hyperparamètres sont mis en cache dans `models/`, sous un nom contenant une empreinte de l'espace de recherche. Modifier une borne relance la recherche automatiquement.
- La préparation des données est écrite deux fois, dans le notebook et dans `Predicts.py`. **Toute modification de l'une doit être reportée dans l'autre**, sinon le jeu de test ne subit pas le même traitement que l'entraînement.
