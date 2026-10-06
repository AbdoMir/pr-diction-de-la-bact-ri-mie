# Prédiction de la bactériémie : résumé de l'analyse exploratoire

Tous les chiffres cités sont produits par une cellule de `notebook/1.EDA.ipynb`.

---

## L'objectif

À partir d'une simple prise de sang, prédire si l'hémoculture d'un patient révélera une bactérie.

L'hémoculture est longue et peu rentable : la grande majorité des prélèvements revient négative. Un modèle de risque bâti sur des analyses de routine aide à repérer les patients à très faible risque.

Le classement du défi se fait au **F1 score**, puis à la précision en cas d'égalité. Il faut donc détecter le maximum de bactériémies sans multiplier les fausses alertes.

---

## Les chiffres clés

| | |
|---|---|
| Patients | **11 753** |
| Variables | **53** (âge, sexe, 50 analyses, résultat de l'hémoculture) |
| Bactériémies | **944**, soit **8 %** |
| Doublons | **aucun** |
| Patients avec un bilan complet | **3 197**, soit **27 %** |

---

## Résultat 1 : les classes sont très déséquilibrées

Sur 100 patients, 8 seulement ont une bactériémie. Un modèle qui répondrait « non » à tout le monde aurait 92 % de bonnes réponses en étant inutile.

**Ce qu'on en fait** : pondérer les classes et régler le seuil de décision au lieu de garder 0,5.

---

## Résultat 2 : les données manquantes suivent une logique

Les trous se regroupent par **panel d'analyses**, c'est-à-dire par ensemble d'examens prescrits ensemble.

| Analyse | Part manquante |
|---|---|
| `PAMY` (amylase pancréatique) | 48 % |
| `TRIG`, `CHOL` (bilan lipidique) | 34 % |
| `GLU` (glycémie) | 29 % |
| `AMY`, `LIP` (pancréas) | 25 % |
| Hémogramme, âge, sexe | moins de 1 % |

Le dendrogramme des manquants fait apparaître **11 groupes** correspondant aux panels du laboratoire. Une classification hiérarchique automatique retrouve la même structure.

**Ce qu'on en fait** : aucune suppression de patients, on en perdrait 73 %. Imputation accompagnée d'un indicateur de manquant.

---

## Résultat 3 : l'absence d'une analyse est parfois plus parlante que sa valeur

| | Plaquettes médianes | Part en thrombopénie |
|---|---|---|
| `MPV` mesuré | 209 G/L | 25 % |
| `MPV` manquant | **55 G/L** | **86 %** |

Quand l'automate ne calcule pas les indices plaquettaires, c'est qu'il n'a pas assez de plaquettes. L'absence de la mesure signale donc une thrombopénie sévère. Même phénomène pour la formule leucocytaire : quand `LYMR` manque, la médiane des globules blancs est de 20,7 G/L contre 9,5 sinon.

C'est la définition du mécanisme MNAR : le fait qu'une donnée manque dépend de la valeur qu'on aurait mesurée.

**Une hypothèse écartée** : `PAMY` n'est pas un dosage de deuxième intention. Elle est présente chez 70 % des patients à amylase normale contre 68 % à amylase élevée, donc prescrite avec `AMY` et non après.

---

## Résultat 4 : des variables font double emploi

**Les indices érythrocytaires sont calculés**, pas mesurés.

| Calculée | À partir de | Corrélation avec le recalcul |
|---|---|---|
| `MCV` | `HCT` et `RBC` | 0,99 |
| `MCH` | `HGB` et `RBC` | 0,94 |
| `MCHC` | `HGB` et `HCT` | 0,97 |

**Les pourcentages leucocytaires sont redondants de deux façons.** Chacun vaut la valeur absolue divisée par le nombre de globules blancs :

| Pourcentage | Formule | Corrélation | Écart moyen |
|---|---|---|---|
| `BASOR` | `BASO` / `WBC` × 100 | 0,997 | 0,00 |
| `EOSR` | `EOS` / `WBC` × 100 | 0,995 | 0,03 |
| `NEUR` | `NEU` / `WBC` × 100 | 0,978 | 1,42 |
| `LYMR` | `LYM` / `WBC` × 100 | 0,956 | 0,66 |
| `MONOR` | `MONO` / `WBC` × 100 | 0,933 | 0,29 |

Et leur somme vaut exactement 100 : `NEUR` = 100 − (`LYMR` + `MONOR` + `EOSR` + `BASOR`), avec une corrélation de **1,000000**. C'est une dépendance linéaire parfaite.

**Un enseignement de méthode** : la matrice de corrélation ne suffit pas à repérer ces redondances. `MCV` et `HCT` n'ont qu'une corrélation de 0,01, alors que `MCV` se déduit exactement de `HCT` et `RBC`. Une corrélation ne mesure qu'un lien entre deux variables, pas un rapport entre trois.

**Ce qu'on en fait** : les indices érythrocytaires servent d'abord à reconstruire `RBC` et `HCT` là où ils manquent, puis sont retirés. Les cinq pourcentages sont écartés du seul modèle linéaire ; les arbres les gardent. Détail dans [transformation.md](transformation.md).

---

## Résultat 5 : une population de patients déjà fragiles

| Anomalie | Part des patients |
|---|---|
| CRP au-dessus de la norme | **93 %** |
| Lymphocytes en proportion trop basse (`LYMR`) | 79 % |
| Fibrinogène élevé | 75 % |
| Neutrophiles en proportion trop haute (`NEUR`) | 60 % |
| Anémie | 58 % |
| Albumine basse | 57 % |
| Hyperglycémie | 54 % |
| Anisocytose (`RDW` élevé) | 48 % |
| Hypocalcémie | 44 % |
| Lymphopénie | 44 % |
| Thrombopénie | 28 % |

Deux profils se superposent : l'**inflammation**, où la CRP et le fibrinogène montent tandis que l'albumine baisse, et la **réaction bactérienne**, où les neutrophiles montent tandis que les lymphocytes baissent.

**La difficulté** : tous ces patients ont eu une hémoculture, donc le médecin suspectait déjà une infection. Il n'y a aucun sujet sain dans les données. Nous devons distinguer une bactériémie d'une infection localisée, pas d'un patient en bonne santé. C'est pourquoi les deux groupes se chevauchent autant, et pourquoi le réglage du seuil est décisif.

---

## Résultat 6 : compter les organes touchés apporte une information différente

Une variable compte les anomalies dans six systèmes : plaquettes, rein, foie, coagulation, inflammation, immunité. Note de 0 à 6.

Sa performance est comparable à celle de la meilleure variable brute, pas supérieure :

| Découpage en 5 groupes de taille égale | Du plus bas au plus haut |
|---|---|
| Quintiles de `NEUR` | 3,3 % → 17,9 % |
| Compte d'anomalies | 3,0 % → 15,4 % |

AUC de 0,655 pour le compte contre 0,696 pour `NEUR`.

**Son intérêt est ailleurs** : il n'est corrélé qu'à 0,31 avec `NEUR`. Il mesure le nombre d'organes touchés, là où `NEUR` mesure la réaction immunitaire. Les deux se complètent.

---

## Résultat 7 : quelques valeurs sont fausses

| Variable | Anomalie | Décision |
|---|---|---|
| `HCT` | valeurs à 0 ou presque, alors que l'hémoglobine est normale | passer en manquant |
| `PLT` | valeurs à 0 chez des patients par ailleurs normaux | passer en manquant |
| `POTASS` | valeurs au-dessus de 10 mmol/L, dont une à 36,6 | passer en manquant |
| `MCHC` | une valeur à 43,5, au-delà du maximum physiologique | signaler |

À l'inverse, beaucoup de valeurs extrêmes sont **vraies** : une créatine kinase à 98 801 U/L traduit une destruction musculaire. On ne les supprime pas.

**Une limite de méthode** : les données ont été bruitées colonne par colonne pour protéger la confidentialité. L'écart moyen entre `HCT` mesuré et recalculé est de 0,76 point. On ne peut donc pas trancher sur une valeur individuelle au seul motif qu'elle s'écarte de son recalcul.

---

## Résultat 8 : des distributions à transformer

**34 variables sur 50 ont une asymétrie supérieure à 1 en valeur absolue**, donc une longue traîne. Les plus extrêmes : `PAMY` (75), `AMY` (52), `LYM` (52), `LIP` (47), `BASO` (43).

Leurs histogrammes sont illisibles en échelle normale.

**Ce qu'on en fait** : passage au logarithme pour les modèles linéaires seulement, les arbres découpant sur des seuils. Après nettoyage, 32 variables sont effectivement transformées. Détail dans [transformation.md](transformation.md).

---

## Résultat 9 : les variables qui séparent réellement les malades

L'AUC mesure la capacité d'une variable à distinguer les deux groupes : 0,50 correspond au hasard, 0,70 est déjà correct en biologie.

| Variable | Notre AUC | AUC publiée |
|---|---|---|
| `NEUR` (neutrophiles %) | **0,696** | 0,696 |
| `LYM` (lymphocytes) | 0,686 | 0,683 |
| `LYMR` (lymphocytes %) | 0,673 | 0,674 |
| `nb_anomalies` (variable construite) | 0,655 | — |
| `MONOR` (monocytes %) | 0,634 | 0,645 |
| `BUN` (urée) | 0,630 | 0,633 |
| `EOSR` (éosinophiles %) | 0,629 | 0,626 |
| `AGE` | 0,613 | 0,611 |
| `CRP` | 0,600 | 0,596 |

**Nos valeurs reproduisent celles de l'article d'origine** à moins de 0,015 près : Ratzinger F. et al., *A Risk Prediction Model for Screening Bacteremic Patients*, PLoS ONE 9(9), e106765, 2014. C'est une validation externe de notre analyse.

- **Le profil leucocytaire domine** : les trois meilleures variables sont des globules blancs.
- **`WBC` seul ne vaut rien** (0,512) alors que `NEUR` atteint 0,696 : c'est la composition qui compte, pas la quantité.
- **La CRP déçoit** (0,600), car 93 % des patients l'ont déjà élevée.
- **Aucune variable ne dépasse 0,70** : il faut les combiner.

Le test de Mann-Whitney confirme le classement : 44 variables sur 51 sont significatives. Sur les corrélations de Spearman entre les dix meilleures, deux paires seulement font double emploi, `NEUR` et `LYMR` (−0,91) et `EOS` et `EOSR` (0,96).

---

## Ce que l'analyse nous a appris pour la suite

1. Ne supprimer aucun patient.
2. Conserver l'information du manquant, qui reflète une décision médicale.
3. Corriger les valeurs impossibles, garder les valeurs extrêmes réelles.
4. Se servir des indices érythrocytaires pour reconstruire `RBC` et `HCT`, puis les retirer ; écarter les cinq pourcentages leucocytaires du seul modèle linéaire.
5. Transformer au logarithme les variables asymétriques à droite, pour les modèles linéaires seulement.
6. Ajouter le compte de défaillances d'organe et quatre rapports cliniques.
7. Partir du profil leucocytaire, qui rassemble les meilleurs prédicteurs.
8. Régler le seuil de décision sur le F1, et non le laisser à 0,5.

---

## Les documents du projet

| Fichier | Contenu |
|---|---|
| `notebook/1.EDA.ipynb` | L'analyse exploratoire, groupe par groupe |
| `notebook/2.MLFLOW-Prepro&Modeling.ipynb` | Pré-processing et modélisation, du CSV au modèle enregistré |
| `doc/transformation.md` | Nettoyage, réparation, variables construites et transformations |
| `doc/modelisation.md` | Les cinq modèles, le réglage du seuil et les résultats |
| `doc/cahierVariables.csv` | Dictionnaire des variables fourni avec les données |
| `Predicts.py` | Script de rendu : lit un CSV de test, écrit `ID` et `pred` |
