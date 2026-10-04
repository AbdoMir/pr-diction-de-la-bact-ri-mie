# Transformations et variables construites

Ce que fait la préparation des données, dans l'ordre. Tout est réuni dans la fonction `preparer()` du notebook, recopiée à l'identique dans `Predicts.py`.

---

## L'ordre des étapes

| Étape | Colonnes |
|---|---|
| 1. Nettoyer les valeurs impossibles | inchangé |
| 2. Réparer `RBC` et `HCT` | inchangé |
| 3. Retirer `MCV`, `MCH`, `MCHC` | −3 |
| 4. Ajouter les variables construites | +5 |

De 53 colonnes au départ à 55 à l'arrivée, soit 53 variables explicatives sans `ID` ni `BloodCulture`.

L'ordre ne peut pas changer. Le nettoyage doit passer en premier, sinon la réparation ne voit pas les valeurs à corriger. Le retrait des indices doit passer en dernier, parce que la réparation s'en sert.

---

## 1. Nettoyer les valeurs impossibles

| Règle | Pourquoi |
|---|---|
| `HCT` ≤ 1 → manquant | Un hématocrite nul est incompatible avec la vie |
| `PLT` = 0 → manquant | Aucune plaquette signifierait une hémorragie massive |
| `WBC` = 0 → manquant | Aucun globule blanc est impossible |
| `POTASS` > 10 mmol/L → manquant | Au-delà, le prélèvement est hémolysé |

**On ne touche à rien d'autre.** Les zéros de `BASO`, `EOS`, `MONO`, `NEU` et `LYM` sont réels : un patient peut n'avoir aucun basophile. Et les valeurs très élevées sont des pathologies, pas des erreurs — une lipase à 45 000 est une pancréatite, des CK à 98 000 une rhabdomyolyse.

Règle à retenir : on supprime une valeur **physiologiquement impossible**, jamais une valeur simplement extrême.

---

## 2. Réparer `RBC` et `HCT`

Les indices érythrocytaires sont calculés par l'automate. On inverse les formules pour retrouver une mesure manquante :

- `RBC` = `HGB` / `MCH` × 10
- `HCT` = `HGB` / `MCHC` × 100

| Variable | Manquants avant | Manquants après |
|---|---|---|
| `RBC` | 375 | 37 |
| `HCT` | 58 | 37 |

359 valeurs récupérées. Les 37 restantes sont des hémogrammes entièrement absents : pas de source, rien à reconstruire.

---

## 3. Retirer `MCV`, `MCH`, `MCHC`

Ces trois variables sont des fonctions exactes de `HGB`, `HCT` et `RBC`. Une fois qu'elles ont servi à la réparation, elles n'apportent plus rien et sont supprimées.

---

## 4. Les variables construites

### `nb_anomalies` — compte de défaillances d'organe

Un critère par système, note de 0 à 6.

| Critère | Système |
|---|---|
| `PLT` < 150 G/L | Plaquettes |
| `CREA` > 1,3 mg/dl | Rein |
| `GBIL` > 1,2 mg/dl | Foie |
| `NT` < 70 % | Coagulation |
| `ALB` < 35 g/L | Inflammation, nutrition |
| `LYM` < 1 G/L | Immunité |

Une infection localisée touche un organe, une bactériémie en touche plusieurs. Le compte capte cette dimension générale.

À savoir : une analyse manquante compte comme normale, donc un patient peu exploré est sous-noté.

### Quatre rapports cliniques

| Rapport | Lecture |
|---|---|
| `NEU` / `LYM` | Infection bactérienne |
| `PLT` / `LYM` | Inflammation systémique |
| `CRP` / `ALB` | Inflammation contre dénutrition |
| `BUN` / `CREA` | Origine rénale ou pré-rénale |

Le rapport reste manquant quand le dénominateur est nul ou absent — `LYM` vaut zéro chez 90 patients, une division donnerait un infini.

---

## 5. Transformation logarithmique

**Critère** : asymétrie strictement supérieure à 1. Pas en valeur absolue — le logarithme corrige une queue à droite, il aggraverait une queue à gauche.

**Transformation** : `log(1 + x)` partout, jamais `log(x)`. La différence est négligeable, mais `log(1 + x)` supporte les zéros, et le fichier de test peut en contenir.

**Pour qui** : les modèles linéaires seulement. Les arbres découpent sur des seuils, une transformation monotone ne change rien pour eux.

### Les 32 variables transformées

`ALAT`, `AMY`, `AP`, `APTT`, `ASAT`, `BASO`, `BUN`, `CHOL`, `CK`, `CREA`, `CRP`, `EOS`, `GBIL`, `GGT`, `GLU`, `HS`, `LDH`, `LIP`, `LYM`, `MONO`, `NEU`, `PAMY`, `PDW`, `PHOS`, `PLT`, `RDW`, `TRIG`, `WBC`, et les quatre rapports construits.

### Les 16 laissées telles quelles

`AGE`, `ALB`, `CA`, `CHE`, `FIB`, `HCT`, `HGB`, `MG`, `MPV`, `NT`, `POTASS`, `RBC`, `SEX`, `SODIUM`, `TP`, `nb_anomalies`.

Deux cas méritent un mot. `POTASS` sort de la liste tout seul : son asymétrie tombe sous le seuil dès que les valeurs impossibles sont nettoyées. Et `NEUR` est asymétrique **à gauche**, donc le logarithme ne s'applique pas.

---

## 6. Mise à l'échelle

`RobustScaler`, qui centre sur la médiane et divise par l'écart interquartile.

`StandardScaler` utilise la moyenne et l'écart-type, tous deux tirés par les valeurs extrêmes — nombreuses ici, puisqu'elles correspondent à de vraies pathologies. La médiane et l'écart interquartile les ignorent.

---

## 7. Variables écartées du modèle linéaire

`BASOR`, `EOSR`, `LYMR`, `MONOR`, `NEUR`.

Leur somme vaut exactement 100 : le cinquième se déduit des quatre autres. Les donner tous à une régression rend ses coefficients arbitraires. Les modèles à base d'arbres les gardent, la colinéarité ne les gêne pas.

La régression ne perd rien pour autant : `NEU` et `WBC` lui sont fournis au logarithme, et la différence de leurs logarithmes vaut celui de `NEUR`.
