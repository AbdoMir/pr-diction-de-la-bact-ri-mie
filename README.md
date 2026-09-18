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

Le fichier `doc/GroupesIDS2026.xlsx` n'est pas versionné : il contient les noms des étudiants.

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
Predicts.py                          script de prédiction final (le rendu)
data/      bacteriemie.csv.gz        jeu de données d'entraînement
doc/       cahierVariables.csv       dictionnaire des variables
image/     pipeLine.png              schéma des étapes du projet
models/                              modèle entraîné, sauvegardé avec joblib
notebook/  1.EDA.ipynb               exploration : cible, valeurs manquantes, distributions
           2.Preprocessing.ipynb     imputation, transformations, gestion du déséquilibre
           3.Modélisation.ipynb      entraînement, comparaison des modèles, choix du seuil
```

Les notebooks s'exécutent depuis le dossier `notebook/`, d'où les chemins relatifs en `../data/`.

## Utilisation

Le chargement des données demande de déclarer les valeurs manquantes, sinon polars échoue sur la première colonne numérique contenant `NA` :

```python
df = pl.read_csv("../data/bacteriemie.csv.gz", null_values="NA")
```

Lancez les notebooks dans l'ordre : `1.EDA`, `2.Preprocessing`, puis `3.Modélisation`, qui sauvegarde le modèle retenu dans `models/`.

Pour prédire un nouveau jeu de données, depuis la racine du projet :

```bash
uv run python Predicts.py <fichier_entrée.csv.gz> <fichier_sortie.csv>
```

Le script accepte un fichier avec ou sans la colonne `BloodCulture`, et écrit un CSV de deux colonnes, `ID` et `pred`, ne contenant que des 0 et des 1.

## Conventions

- Graine aléatoire fixée à `SEED = 42` partout où un tirage intervient (découpage, modèles, rééchantillonnage), pour des résultats reproductibles.
- Jeu de test interne mis de côté avant tout pre-processing, avec un découpage stratifié (80 / 20).
- Imputation, mise à l'échelle et rééchantillonnage calculés sur l'entraînement seulement, à l'intérieur d'un `Pipeline` scikit-learn, pour éviter toute fuite de données.
- Le seuil de décision est choisi pour maximiser le F1, et non laissé à 0,5.

## Échéances

| Date | Rendu |
|---|---|
| 05/10/2026, 18h | Script sur Moodle |
| 07/10/2026, 18h | CSV de prédiction du jeu de test |
| 08/10/2026, 14h-16h | Présentation orale et classement |
