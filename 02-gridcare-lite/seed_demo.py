"""
Create the demo accounts and a little sample history so the app doesn't start empty.

    python seed_demo.py

Accounts (username / password / role):

    admin1   / admin123   / admin
    kwame.e  / engineer1  / engineer
    ama.t    / techpass1  / technician
    yaw.t    / techpass2  / technician
    efua.cs  / service1   / customer_service

Demo credentials for coursework only, obviously - a real deployment would never ship
predictable passwords. 


The sample records include one fully resolved outage (so average resolution time has
a value), one in progress, and one still open with a linked complaint - enough for
every screen and the reports chart to show something on first login.
"""

import random
from datetime import datetime, timedelta

from gridcare import auth, db, services


def backdate(conn, table, id_column, row_id, column, days_ago, hours_ago=0):
    """Shift a timestamp into the past so the demo data looks lived-in.

    Seeding runs the whole workflow in one second, which makes 'average resolution
    time' read 0.0 on the reports screen. Real records accumulate over days.
    """
    stamp = (datetime.now() - timedelta(days=days_ago, hours=hours_ago)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(f"UPDATE {table} SET {column} = ? WHERE {id_column} = ?", (stamp, row_id))
    conn.commit()

DEMO_USERS = [
    ("admin1", "admin123", "Abena Owusu", "admin"),
    ("kwame.e", "engineer1", "Kwame Adjei", "engineer"),
    ("ama.t", "techpass1", "Ama Tetteh", "technician"),
    ("yaw.t", "techpass2", "Yaw Darko", "technician"),
    ("efua.cs", "service1", "Efua Mensimah", "customer_service"),
]


def main():
    conn = db.connect()
    db.init_db(conn)

    if conn.execute("SELECT COUNT(*) FROM substations").fetchone()[0] == 0:
        print("No substations - run  python import_grid_data.py  first.")
        return 1
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
        print("Users already exist - not seeding twice.")
        return 1

    for username, password, full_name, role in DEMO_USERS:
        auth.create_user(conn, username, password, full_name, role)
    print(f"Created {len(DEMO_USERS)} demo accounts.")

    admin = auth.authenticate(conn, "admin1", "admin123")
    engineer = auth.authenticate(conn, "kwame.e", "engineer1")
    tech = auth.authenticate(conn, "ama.t", "techpass1")
    cs = auth.authenticate(conn, "efua.cs", "service1")

    subs = [s["substation_id"] for s in services.list_substations(conn)]
    random.seed(7)  # same sample data on every fresh seed, for comparable demos
    a, b, c = random.sample(subs, 3)

    # 1: full lifecycle, so resolution stats exist. Backdated to look like it was
    # reported four days ago and fixed ~27 hours later.
    o1 = services.log_outage(conn, engineer, a, "Transformer overheating alarm, load shed.", "High")
    w1 = services.create_work_order(conn, admin, o1)
    services.assign_work_order(conn, admin, w1, tech["user_id"], "2030-01-10")
    services.start_work(conn, tech, w1)
    services.complete_work(conn, tech, w1, "Replaced cooling fan, cleared alarm, load restored.")
    backdate(conn, "outages", "outage_id", o1, "reported_at", days_ago=4)
    backdate(conn, "outages", "outage_id", o1, "resolved_at", days_ago=2, hours_ago=21)
    backdate(conn, "work_orders", "work_order_id", w1, "created_at", days_ago=3, hours_ago=22)
    backdate(conn, "work_orders", "work_order_id", w1, "completed_at", days_ago=2, hours_ago=21)

    # 2: mid-workflow, reported yesterday.
    o2 = services.log_outage(conn, engineer, b, "Feeder breaker tripping repeatedly.", "Critical")
    w2 = services.create_work_order(conn, admin, o2)
    services.assign_work_order(conn, admin, w2, tech["user_id"], "2030-01-20")
    services.start_work(conn, tech, w2)
    backdate(conn, "outages", "outage_id", o2, "reported_at", days_ago=1)

    # 3: freshly reported this morning, with the complaint that came in about it.
    o3 = services.log_outage(conn, engineer, c, "Area outage reported, cause not yet known.", "Medium")
    backdate(conn, "outages", "outage_id", o3, "reported_at", days_ago=0, hours_ago=3)
    services.log_complaint(conn, cs, "Kojo Antwi", "No power since 6am, whole street affected.",
                           contact="024-555-0199", outage_id=o3)
    services.log_complaint(conn, cs, "Adwoa Boakye", "Fridge damaged by power fluctuations last week.")

    print("Seeded 3 outages (1 resolved, 1 in progress, 1 open) and 2 complaints.")
    print("Log in as admin1/admin123 to see everything.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
