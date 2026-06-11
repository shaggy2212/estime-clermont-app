"""
build_dvf_local.py  (v2 - téléchargement ciblé par commune)

Télécharge les DVF géolocalisées d'Etalab UNIQUEMENT pour les 7 communes
du secteur, sur les années dispo (5 ans glissants), et génère le parquet
attendu par l'app ICOstim.

Usage:
    python build_dvf_local.py
    python build_dvf_local.py --output data/dvf_local.parquet --years 2021 2022 2023 2024 2025
"""

import argparse
import io
import sys
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://files.data.gouv.fr/geo-dvf/latest/csv/{year}/communes/{dep}/{insee}.csv"

# Code INSEE -> juste pour mémoire lisible
COMMUNES = {
    "60157": "Clermont",
    "60107": "Breuil-le-Vert",
    "60007": "Agnetz",
    "60234": "Fitz-James",
    "60106": "Breuil-le-Sec",
    "60451": "Neuilly-sous-Clermont",
    "60042": "Bailleval",
}
DEP = "60"

# Colonnes du format "geo-dvf par commune" (CSV non gzippé)
USECOLS = [
    "date_mutation",
    "valeur_fonciere",
    "type_local",
    "surface_reelle_bati",
    "nombre_pieces_principales",
    "code_commune",
    "nom_commune",
    "longitude",
    "latitude",
]

FINAL_COLS = [
    "date_mutation",
    "valeur_fonciere",
    "code_commune",
    "nom_commune",
    "type_local",
    "surface_reelle_bati",
    "nb_pieces",
    "longitude",
    "latitude",
]


def fetch_commune_year(insee: str, year: int, session: requests.Session) -> pd.DataFrame | None:
    url = BASE_URL.format(year=year, dep=DEP, insee=insee)
    try:
        r = session.get(url, timeout=60)
    except requests.RequestException as e:
        print(f"   ⚠️ {insee} {year} : erreur réseau ({e})")
        return None

    if r.status_code == 404:
        # pas de transaction cette année-là dans cette commune, c'est normal
        return None
    if r.status_code != 200:
        print(f"   ⚠️ {insee} {year} : HTTP {r.status_code}")
        return None

    df = pd.read_csv(io.StringIO(r.text), usecols=lambda c: c in USECOLS, low_memory=False)
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["code_commune"] = df["code_commune"].astype(str).str.zfill(5)
    df["date_mutation"] = pd.to_datetime(df["date_mutation"], errors="coerce")
    df["valeur_fonciere"] = pd.to_numeric(df["valeur_fonciere"], errors="coerce")
    df["surface_reelle_bati"] = pd.to_numeric(df["surface_reelle_bati"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")

    if "nombre_pieces_principales" in df.columns:
        df["nb_pieces"] = pd.to_numeric(df["nombre_pieces_principales"], errors="coerce")
    else:
        df["nb_pieces"] = pd.NA

    df = df.dropna(subset=["date_mutation", "valeur_fonciere", "surface_reelle_bati", "longitude", "latitude"])
    df = df[(df["valeur_fonciere"] > 1000) & (df["surface_reelle_bati"] >= 10)]
    df = df[df["type_local"].isin(["Maison", "Appartement"])]

    return df[FINAL_COLS]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="data/dvf_local.parquet")
    p.add_argument("--years", nargs="+", type=int, default=[2021, 2022, 2023, 2024, 2025])
    p.add_argument("--dedup", action="store_true", default=True,
                   help="Dédoublonne les ventes multi-lots (même date/prix/commune/surface)")
    args = p.parse_args()

    outp = Path(args.output)
    outp.parent.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({"User-Agent": "ICOstim-DVF-updater/1.0"})

    parts = []
    print("📦 Téléchargement par commune…")
    for insee, name in COMMUNES.items():
        kept = 0
        for year in args.years:
            df = fetch_commune_year(insee, year, session)
            if df is None or df.empty:
                continue
            df = clean(df)
            if not df.empty:
                parts.append(df)
                kept += len(df)
        print(f"   ✅ {name} ({insee}) : {kept} lignes gardées")

    if not parts:
        sys.exit("❌ Aucune donnée récupérée. Vérifie ta connexion ou les codes INSEE.")

    df = pd.concat(parts, ignore_index=True)

    # Dédoublonnage léger : une vente peut apparaître en plusieurs lignes (lots)
    if args.dedup:
        before = len(df)
        df = df.drop_duplicates(
            subset=["date_mutation", "valeur_fonciere", "code_commune",
                    "surface_reelle_bati", "longitude", "latitude"]
        )
        print(f"🧹 Dédoublonnage : {before} -> {len(df)} lignes")

    df = df.sort_values("date_mutation").reset_index(drop=True)
    df.to_parquet(outp, index=False)

    print(f"\n✅ Export OK : {outp} — {len(df):,} lignes")
    print(f"   Période : {df['date_mutation'].min().date()} -> {df['date_mutation'].max().date()}")
    print(f"   nb_pieces rempli : {df['nb_pieces'].notna().sum()}/{len(df)}")
    print("\n   Répartition par commune :")
    print(df['nom_commune'].value_counts().to_string())


if __name__ == "__main__":
    main()
