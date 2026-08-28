"""
Start GridCare-Lite.

    python run.py

First run on a fresh machine:

    python import_grid_data.py   # load the substation/line reference data
    python seed_demo.py          # create the demo accounts and sample records
    python run.py
"""

from gridcare import db
from gridcare.ui.app import run_app


def main():
    conn = db.connect()
    db.init_db(conn)

    substations = conn.execute("SELECT COUNT(*) FROM substations").fetchone()[0]
    users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if substations == 0 or users == 0:
        print("Database is empty. Run these first:")
        if substations == 0:
            print("  python import_grid_data.py")
        if users == 0:
            print("  python seed_demo.py")
        return

    run_app(conn)


if __name__ == "__main__":
    main()
