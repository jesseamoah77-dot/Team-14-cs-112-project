"""
Synthetic dataset generator for the National Electricity Grid Network Analysis project.

Produces three CSVs in the same spirit as the OpenFlights airlines/airports/routes trio:
    utilities.csv    (like airlines.csv)
    substations.csv  (like airports.csv)
    lines.csv        (like routes.csv)

Grounded in Ghana's grid (ECG, NEDCo, GRIDCo, VRA) with cross-border interconnections
reflecting the real West African Power Pool (WAPP).

Reproduced verbatim from the CS 112 project brief. The only change is OUT_DIR below,
which writes the CSVs into 01-grid-analysis/data/ instead of the current directory.
The random sequence is untouched, so the output is byte-identical to the brief's.

Run from anywhere:  python 01-grid-analysis/scripts/generate_grid_data.py
"""

import csv
import math
import random
from pathlib import Path

# Write CSVs into 01-grid-analysis/data/ regardless of where this is run from.
OUT_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

random.seed(42)

# ---------------------------------------------------------------------------
# Utilities (analogous to airlines.csv)
# ---------------------------------------------------------------------------
utilities = [
    # utility_id, name, alias, code, type, country, active
    (1, "Electricity Company of Ghana", "ECG", "ECG", "Distribution", "Ghana", "Y"),
    (2, "Northern Electricity Distribution Company", "NEDCo", "NED", "Distribution", "Ghana", "Y"),
    (3, "Ghana Grid Company", "GRIDCo", "GRD", "Transmission", "Ghana", "Y"),
    (4, "Volta River Authority", "VRA", "VRA", "Generation", "Ghana", "Y"),
    (5, "Compagnie Ivoirienne d'Electricite", "CIE", "CIE", "Distribution", "Cote d'Ivoire", "Y"),
    (6, "Communaute Electrique du Benin", "CEB", "CEB", "Transmission", "Togo/Benin", "Y"),
    (7, "Societe Beninoise d'Energie Electrique", "SBEE", "SBE", "Distribution", "Benin", "Y"),
    (8, "Electricite de Guinee", "EDG", "EDG", "Distribution", "Guinea", "N"),
    (9, "Sonabel", "SONABEL", "SNB", "Distribution", "Burkina Faso", "Y"),
    (10, "Enclave Power Company", "EPC", "EPC", "Generation", "Ghana", "N"),
]

# ---------------------------------------------------------------------------
# Substations (analogous to airports.csv) — coordinates are approximate/illustrative
# ---------------------------------------------------------------------------
ghana_regions = {
    "Greater Accra": [("Achimota", 5.614, -0.224), ("Tema", 5.669, -0.017),
                       ("Mallam", 5.560, -0.298), ("Legon", 5.650, -0.186),
                       ("Kaneshie", 5.560, -0.238), ("Aboadze Junction", 5.590, -0.150)],
    "Ashanti": [("Kumasi Central", 6.688, -1.624), ("Ejisu", 6.719, -1.463),
                ("Obuasi", 6.202, -1.663), ("Mampong", 7.062, -1.400), ("Konongo", 6.618, -1.219)],
    "Western": [("Takoradi", 4.895, -1.759), ("Aboadze", 4.985, -1.766),
                ("Tarkwa", 5.301, -1.994), ("Axim", 4.867, -2.241)],
    "Central": [("Cape Coast", 5.106, -1.246), ("Winneba", 5.352, -0.622),
                ("Kasoa", 5.533, -0.416), ("Assin Fosu", 5.699, -1.492)],
    "Eastern": [("Koforidua", 6.094, -0.259), ("Akosombo", 6.300, 0.055),
                ("Nkawkaw", 6.550, -0.767), ("Suhum", 6.041, -0.451)],
    "Volta": [("Ho", 6.611, 0.471), ("Kpong", 6.150, 0.100),
              ("Hohoe", 7.152, 0.472), ("Sogakope", 6.007, 0.573)],
    "Bono": [("Sunyani", 7.339, -2.326), ("Techiman", 7.590, -1.938), ("Berekum", 7.453, -2.585)],
    "Northern": [("Tamale", 9.403, -0.842), ("Yendi", 9.442, -0.011), ("Savelugu", 9.625, -0.826)],
    "Upper East": [("Bolgatanga", 10.787, -0.851), ("Bawku", 11.058, -0.243)],
    "Upper West": [("Wa", 10.061, -2.501)],
}

cross_border = [
    ("Bolgatanga Interconnection", "Burkina Faso border", 11.20, -0.75),
    ("Elubo Border Station", "Cote d'Ivoire border", 5.20, -2.85),
    ("Aflao Border Station", "Togo border", 6.12, 1.19),
    ("Lome Transmission Hub", "Togo", 6.13, 1.22),
    ("Cotonou Transmission Hub", "Benin", 6.37, 2.43),
    ("Abidjan Transmission Hub", "Cote d'Ivoire", 5.35, -4.00),
    ("Bobo-Dioulasso Hub", "Burkina Faso", 11.18, -4.30),
    ("Conakry Transmission Hub", "Guinea", 9.64, -13.58),
]

voltage_levels = [11, 33, 69, 161, 330]

substations = []
sid = 1
name_to_id = {}
for region, places in ghana_regions.items():
    for name, lat, lon in places:
        voltage = random.choice(voltage_levels)
        sub_type = ("Transmission" if voltage >= 161 else
                    "Bulk Supply Point" if voltage == 69 else "Distribution")
        capacity = round(random.uniform(15, 400) if sub_type != "Distribution"
                          else random.uniform(5, 60), 1)
        status = "Active" if random.random() > 0.05 else "Inactive"
        substations.append([
            sid, f"{name} Substation", name, region, "Ghana",
            round(lat + random.uniform(-0.01, 0.01), 4), round(lon + random.uniform(-0.01, 0.01), 4),
            voltage, capacity, random.randint(1965, 2023), sub_type, status,
        ])
        name_to_id[name] = sid
        sid += 1

for name, country, lat, lon in cross_border:
    voltage = random.choice([161, 330])
    capacity = round(random.uniform(100, 500), 1)
    substations.append([
        sid, f"{name}", name, country, country.split()[0],
        round(lat, 4), round(lon, 4), voltage, capacity,
        random.randint(1980, 2020), "Transmission", "Active",
    ])
    name_to_id[name] = sid
    sid += 1

# ---------------------------------------------------------------------------
# Transmission/Distribution lines (analogous to routes.csv)
# ---------------------------------------------------------------------------
def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))

sub_by_id = {row[0]: row for row in substations}

lines = []
lid = 1
seen_pairs = set()

# Connect substations within each region into a loosely meshed network
for region, places in ghana_regions.items():
    ids_in_region = [name_to_id[n] for n, _, _ in places]
    for i, a in enumerate(ids_in_region):
        for b in ids_in_region[i + 1:]:
            if random.random() < 0.55:
                pair = tuple(sorted((a, b)))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                utility_id = random.choice([1, 2, 3])
                sub_a, sub_b = sub_by_id[a], sub_by_id[b]
                dist = round(haversine_km(sub_a[5], sub_a[6], sub_b[5], sub_b[6])
                             * random.uniform(1.05, 1.3), 1)
                voltage = min(sub_a[7], sub_b[7])
                lines.append([
                    lid, utility_id, a, sub_a[1], b, sub_b[1],
                    voltage, dist, round(random.uniform(20, 300), 1),
                    "Active" if random.random() > 0.08 else "Under Maintenance",
                    random.choice(["Overhead", "Underground"]),
                ])
                lid += 1

# A handful of inter-regional backbone lines (transmission-level, GRIDCo)
region_hub = {r: name_to_id[places[0][0]] for r, places in ghana_regions.items()}
region_names = list(region_hub.keys())
for i in range(len(region_names) - 1):
    a = region_hub[region_names[i]]
    b = region_hub[region_names[i + 1]]
    sub_a, sub_b = sub_by_id[a], sub_by_id[b]
    dist = round(haversine_km(sub_a[5], sub_a[6], sub_b[5], sub_b[6]) * 1.15, 1)
    lines.append([
        lid, 3, a, sub_a[1], b, sub_b[1], 330, dist,
        round(random.uniform(200, 600), 1), "Active", "Overhead",
    ])
    lid += 1

# Cross-border interconnections (WAPP-style)
border_links = [
    ("Bolgatanga", "Bolgatanga Interconnection", 9),
    ("Bolgatanga Interconnection", "Bobo-Dioulasso Hub", 9),
    ("Elubo Border Station", "Kumasi Central", 5),
    ("Elubo Border Station", "Abidjan Transmission Hub", 5),
    ("Aflao Border Station", "Tema", 6),
    ("Aflao Border Station", "Lome Transmission Hub", 6),
    ("Lome Transmission Hub", "Cotonou Transmission Hub", 6),
]
for src_name, dst_name, utility_id in border_links:
    if src_name not in name_to_id or dst_name not in name_to_id:
        continue
    a, b = name_to_id[src_name], name_to_id[dst_name]
    sub_a, sub_b = sub_by_id[a], sub_by_id[b]
    dist = round(haversine_km(sub_a[5], sub_a[6], sub_b[5], sub_b[6]) * 1.1, 1)
    lines.append([
        lid, utility_id, a, sub_a[1], b, sub_b[1], 330, dist,
        round(random.uniform(150, 400), 1), "Active", "Overhead",
    ])
    lid += 1

# ---------------------------------------------------------------------------
# Write CSVs
# ---------------------------------------------------------------------------
with open(OUT_DIR / "utilities.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Utility ID", "Name", "Alias", "Code", "Type", "Country", "Active"])
    w.writerows(utilities)

with open(OUT_DIR / "substations.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Substation ID", "Name", "Short Name", "Region", "Country", "Latitude", "Longitude",
                "Voltage (kV)", "Capacity (MVA)", "Commissioning Year", "Type", "Status"])
    w.writerows(substations)

with open(OUT_DIR / "lines.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Line ID", "Utility ID", "Source Substation ID", "Source Substation",
                "Destination Substation ID", "Destination Substation", "Voltage (kV)",
                "Length (km)", "Capacity (MVA)", "Status", "Line Type"])
    w.writerows(lines)

print(f"utilities: {len(utilities)} rows")
print(f"substations: {len(substations)} rows")
print(f"lines: {len(lines)} rows")
print(f"written to: {OUT_DIR}")
