import argparse
import pandas as pd
from pathlib import Path

KEEP_INSEE = {
    "60157",  # Clermont
    "60107",  # Breuil-le-Vert
    "60007",  # Agnetz
    "60234",  # Fitz-James
    "60106",  # Breuil-le-Sec
    "60451",  # Neuilly-sous-Clermont
    "60042",  # Bailleval
}

KEEP_COLS = [
    "date_mutation",
    "valeur_fonciere",
    "type_local",
    "surface_reelle_bati",
    "code_commune",
    "nom_commune",
    "longitude",
    "latitude",
]

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output", default="data/dvf_local.parquet")
    p.add_argument("--chunksize", type=int, default=250_000)
    args = p.parse_args()

    inp = Path(args.input)
    outp = Path(args.output)
    outp.parent.mkdir(parents=True, exist_ok=True)

    print("🔎 Vérification des colonnes…")
    # On lit juste l'entête pour vérifier les colonnes sans charger tout le fichier
    head = pd.read_csv(inp, compression="gzip", nrows=1, low_memory=False)
    missing = [c for c in KEEP_COLS if c not in head.columns]
    if missing:
        raise ValueError(
            f"Colonnes manquantes: {missing}\n"
            f"Colonnes trouvées (extrait): {list(head.columns)[:60]}"
        )

    total_kept = 0
    parts = []

    print("📦 Lecture en morceaux (chunks)…")
    it = pd.read_csv(
        inp,
        compression="gzip",
        usecols=KEEP_COLS,
        chunksize=args.chunksize,
        low_memory=False,
    )

    for i, chunk in enumerate(it, start=1):
        chunk["code_commune"] = chunk["code_commune"].astype(str).str.zfill(5)
        chunk = chunk[chunk["code_commune"].isin(KEEP_INSEE)].copy()
        if chunk.empty:
            if i % 10 == 0:
                print(f"… chunk {i} (0 gardé)")
            continue

        # conversions
        chunk["date_mutation"] = pd.to_datetime(chunk["date_mutation"], errors="coerce")
        chunk["valeur_fonciere"] = pd.to_numeric(chunk["valeur_fonciere"], errors="coerce")
        chunk["surface_reelle_bati"] = pd.to_numeric(chunk["surface_reelle_bati"], errors="coerce")
        chunk["longitude"] = pd.to_numeric(chunk["longitude"], errors="coerce")
        chunk["latitude"] = pd.to_numeric(chunk["latitude"], errors="coerce")

        # nettoyage
        chunk = chunk.dropna(subset=["date_mutation", "valeur_fonciere", "surface_reelle_bati", "longitude", "latitude"])
        chunk = chunk[(chunk["valeur_fonciere"] > 1000) & (chunk["surface_reelle_bati"] >= 10)]
        chunk = chunk[chunk["type_local"].isin(["Maison", "Appartement"])]

        if not chunk.empty:
            parts.append(chunk)
            total_kept += len(chunk)

        if i % 5 == 0:
            print(f"… chunk {i} (gardés cumulés: {total_kept:,})")

    if not parts:
        raise RuntimeError("Aucune ligne conservée après filtrage (vérifie les codes INSEE / fichier).")

    print("🧩 Assemblage final…")
    df = pd.concat(parts, ignore_index=True)

    print("💾 Export parquet…")
    df.to_parquet(outp, index=False)

    print(f"✅ Export OK: {outp} — {len(df):,} lignes")

if __name__ == "__main__":
    main()