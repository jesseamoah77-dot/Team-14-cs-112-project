"""
Import the cleaned substation and line data from the grid-analysis component.

Run the analysis cleaning notebook first (it writes clean_substations.csv and
clean_lines.csv), then:

    python import_grid_data.py

Safe to re-run: imports are keyed on the asset ids, so re-importing updates in place.
This is the bridge between the two components - outages in GridCare-Lite can only be
logged against substations that exist in the analysed dataset.
"""

from pathlib import Path

from gridcare import db

ANALYSIS_DATA = Path(__file__).resolve().parent.parent / "01-grid-analysis" / "data"


def main():
    subs_csv = ANALYSIS_DATA / "clean_substations.csv"
    lines_csv = ANALYSIS_DATA / "clean_lines.csv"

    missing = [p.name for p in (subs_csv, lines_csv) if not p.exists()]
    if missing:
        print(f"Missing {', '.join(missing)} in {ANALYSIS_DATA}")
        print("Run the 01-data-cleaning notebook in 01-grid-analysis first.")
        return 1

    conn = db.connect()
    db.init_db(conn)
    n_subs = db.import_substations(conn, subs_csv)
    n_lines = db.import_lines(conn, lines_csv)
    print(f"Imported {n_subs} substations and {n_lines} lines into {db.DEFAULT_DB.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
