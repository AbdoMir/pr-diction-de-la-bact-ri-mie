"""Genere les predictions de bacteriemie a partir d'un fichier de test.

    python Predicts.py chemin/vers/test.csv predictions.csv

Le fichier produit contient deux colonnes, ID et pred, avec des 0 et des 1.
Les fonctions de preparation sont identiques a la section 3 du notebook.
"""

import argparse
from pathlib import Path

import joblib
import polars as pl

RACINE = Path(__file__).parent
MODELE = RACINE / "models" / "modele_bacteriemie.joblib"

# Derivees exactes de HGB, HCT et RBC : elles servent a reparer leurs sources,
# puis sont retirees. Elles ne figurent donc pas dans les colonnes du modele,
# mais le fichier de test doit quand meme les contenir.
DERIVEES = ["MCV", "MCH", "MCHC"]


def nettoyer(df: pl.DataFrame) -> pl.DataFrame:
    """Remplace les valeurs physiologiquement impossibles par des valeurs manquantes."""
    return df.with_columns(
        HCT=pl.when(pl.col("HCT") <= 1).then(None).otherwise(pl.col("HCT")),
        PLT=pl.when(pl.col("PLT") == 0).then(None).otherwise(pl.col("PLT")),
        WBC=pl.when(pl.col("WBC") == 0).then(None).otherwise(pl.col("WBC")),
        POTASS=pl.when(pl.col("POTASS") > 10).then(None).otherwise(pl.col("POTASS")),
    )


def reparer_sources(df: pl.DataFrame) -> pl.DataFrame:
    """Reconstruit RBC et HCT depuis les indices erythrocytaires, avant leur retrait.

    MCH  = HGB / RBC x 10   ->  RBC = HGB / MCH x 10
    MCHC = HGB / HCT x 100  ->  HCT = HGB / MCHC x 100
    """
    return df.with_columns(
        RBC=pl.coalesce(pl.col("RBC"), pl.col("HGB") / pl.col("MCH") * 10),
        HCT=pl.coalesce(pl.col("HCT"), pl.col("HGB") / pl.col("MCHC") * 100),
    )


def _ratio(num: str, den: str) -> pl.Expr:
    """Rapport num/den, laisse null si le denominateur est nul ou absent."""
    return pl.when(pl.col(den) > 0).then(pl.col(num) / pl.col(den)).otherwise(None)


def ajouter_variables(df: pl.DataFrame) -> pl.DataFrame:
    """Compte de defaillances d'organe et rapports cliniques."""
    return df.with_columns(
        nb_anomalies=pl.sum_horizontal([
            (pl.col("PLT") < 150).cast(pl.Int8),        # plaquettes
            (pl.col("CREA") > 1.3).cast(pl.Int8),       # rein
            (pl.col("GBIL") > 1.2).cast(pl.Int8),       # foie
            (pl.col("NT") < 70).cast(pl.Int8),          # coagulation
            (pl.col("ALB") < 35).cast(pl.Int8),         # inflammation
            (pl.col("LYM") < 1).cast(pl.Int8),          # immunite
        ]),
        ratio_neu_lym=_ratio("NEU", "LYM"),      # marqueur d'infection bacterienne
        ratio_plt_lym=_ratio("PLT", "LYM"),      # inflammation systemique
        ratio_crp_alb=_ratio("CRP", "ALB"),      # inflammation contre denutrition
        ratio_bun_crea=_ratio("BUN", "CREA"),    # origine renale ou pre-renale
    )


def preparer(df: pl.DataFrame) -> pl.DataFrame:
    """Nettoyage, reparation des sources, retrait des derivees, variables construites.

    L'ordre est impose : reparer_sources a besoin des derivees, donc le retrait
    vient apres. Et nettoyer vient avant tout, car pl.coalesce ne remplit que les
    null : sans nettoyage, un HCT aberrant resterait une valeur presente.

    Aucun calcul appris sur les donnees.
    """
    return ajouter_variables(reparer_sources(nettoyer(df)).drop(DERIVEES))


def predire(entree: Path, sortie: Path, chemin_modele: Path) -> None:
    df = pl.read_csv(entree, null_values="NA")
    if "ID" not in df.columns:
        raise SystemExit(f"{entree} : colonne ID absente")

    ids = df["ID"]
    df = df.drop([c for c in ("ID", "BloodCulture") if c in df.columns])

    paquet = joblib.load(chemin_modele)

    # Les colonnes construites par preparer() portent le prefixe nb_ ou ratio_ :
    # les autres doivent deja etre dans le fichier, sinon la preparation echoue.
    # Les derivees s'y ajoutent : absentes du modele, mais indispensables a
    # reparer_sources(), donc exigees en entree.
    construites = ("nb_", "ratio_")
    attendues = [c for c in paquet["colonnes"] if not c.startswith(construites)] + DERIVEES
    absentes = [c for c in attendues if c not in df.columns]
    if absentes:
        raise SystemExit(f"{entree} : colonnes manquantes -> {absentes}")

    prepare = preparer(df)

    # Le seuil de decision est deja dans le modele : predict suffit.
    pred = paquet["modele"].predict(prepare.select(paquet["colonnes"]))

    resultat = pl.DataFrame({"ID": ids, "pred": pl.Series(pred).cast(pl.Int8)})
    resultat.write_csv(sortie)

    part = resultat["pred"].mean()
    print(f"{sortie} ecrit : {resultat.height} lignes, {part:.1%} predits positifs")


if __name__ == "__main__":
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("entree", type=Path, help="fichier de test au format CSV")
    parseur.add_argument("sortie", type=Path, nargs="?", default=Path("predictions.csv"))
    parseur.add_argument("--modele", type=Path, default=MODELE)
    args = parseur.parse_args()

    predire(args.entree, args.sortie, args.modele)
