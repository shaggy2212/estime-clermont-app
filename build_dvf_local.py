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

# Colonnes indispensables (doivent exister)
REQUIRED_COLS = [
    "date_mutation",
    "valeur_fonciere",
    "type_local",
    "surface_reelle_bati",
    "code_commune",
    "nom_commune",
    "longitude",
    "latitude",
]

# Colonnes optionnelles pour le nombre de pièces selon les variantes d’export DVF
PIECES_CANDIDATES = [
    "nombre_pieces_principales",          # le plus courant DVF
    "nombre_pieces_principale",           # typo/variante rencontrée parfois
    "nb_pieces_principales",              # autre variante
    "nb_pieces",                          # export custom
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

    print("🔎 Vérification des colonnes (entête)…")
    head = pd.read_csv(inp, compression="gzip", nrows=1, low_memory=False)
    cols = set(head.columns)

    missing_required = [c for c in REQUIRED_COLS if c not in cols]
    if missing_required:
        raise ValueError(
            f"Colonnes indispensables manquantes: {missing_required}\n"
            f"Colonnes trouvées (extrait): {list(head.columns)[:80]}"
        )

    # On garde la 1ère colonne “pièces” disponible
    pieces_col = next((c for c in PIECES_CANDIDATES if c in cols), None)
    if pieces_col:
        print(f"✅ Colonne pièces détectée : {pieces_col} (sera exportée en 'nb_pieces')")
    else:
        print("⚠️ Aucune colonne 'pièces' trouvée dans ce DVF. "
              "Le parquet sera généré sans 'nb_pieces' (donc l’app affichera 'p. ?').")

    usecols = REQUIRED_COLS + ([pieces_col] if pieces_col else [])

    total_kept = 0
    parts = []

    print("📦 Lecture en morceaux (chunks)…")
    it = pd.read_csv(
        inp,
        compression="gzip",
        usecols=usecols,
        chunksize=args.chunksize,
        low_memory=False,
    )

    for i, chunk in enumerate(it, start=1):
        # code_commune: string 5 chars
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

        # pièces (si présent)
        if pieces_col:
            chunk["nb_pieces"] = pd.to_numeric(chunk[pieces_col], errors="coerce")
        else:
            chunk["nb_pieces"] = pd.NA

        # nettoyage
        chunk = chunk.dropna(subset=["date_mutation", "valeur_fonciere", "surface_reelle_bati", "longitude", "latitude"])
        chunk = chunk[(chunk["valeur_fonciere"] > 1000) & (chunk["surface_reelle_bati"] >= 10)]
        chunk = chunk[chunk["type_local"].isin(["Maison", "Appartement"])]

        # garde uniquement colonnes finales (on standardise)
        final_cols = [
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
        chunk = chunk[final_cols].copy()

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
    print(f"ℹ️ Colonnes exportées: {list(df.columns)}")

if __name__ == "__main__":
    main()
