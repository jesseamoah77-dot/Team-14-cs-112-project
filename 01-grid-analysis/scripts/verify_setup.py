"""
Environment smoke test. Run this after setting up, before writing any analysis code.

    python 01-grid-analysis/scripts/verify_setup.py

It loads the generated CSVs, builds the NetworkX graph, and checks the numbers against the
values the project brief reports for the seeded dataset. If every line says OK, your machine
is set up correctly and matches everyone else's.

If the CSVs are missing, run the generator first:

    python 01-grid-analysis/scripts/generate_grid_data.py
"""

import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Values the brief reports for the seed-42 dataset. If any of these drift, either the
# generator was edited or someone changed the seed -- both break comparability between teams.
EXPECTED = {
    "utilities": 10,
    "substations": 44,
    "lines": 55,
    "graph_nodes": 42,
    "graph_edges": 55,
    "components": 1,
    "top_degree": 5,
}

failures = []


def check(label, actual, expected):
    ok = actual == expected
    status = "OK  " if ok else "FAIL"
    print(f"  [{status}] {label}: {actual}" + ("" if ok else f"  (expected {expected})"))
    if not ok:
        failures.append(label)


print("1. Importing libraries")
try:
    import pandas as pd
    import networkx as nx
    print("  [OK  ] pandas", pd.__version__)
    print("  [OK  ] networkx", nx.__version__)
except ImportError as exc:
    print(f"  [FAIL] {exc}")
    print("\nInstall dependencies first:  pip install -r requirements.txt")
    sys.exit(1)

print("\n2. Loading the CSVs")
missing = [n for n in ("utilities", "substations", "lines") if not (DATA_DIR / f"{n}.csv").exists()]
if missing:
    print(f"  [FAIL] missing: {', '.join(n + '.csv' for n in missing)}")
    print("\nGenerate them first:  python 01-grid-analysis/scripts/generate_grid_data.py")
    sys.exit(1)

utilities = pd.read_csv(DATA_DIR / "utilities.csv")
substations = pd.read_csv(DATA_DIR / "substations.csv")
lines = pd.read_csv(DATA_DIR / "lines.csv")

check("utilities rows", len(utilities), EXPECTED["utilities"])
check("substations rows", len(substations), EXPECTED["substations"])
check("lines rows", len(lines), EXPECTED["lines"])

print("\n3. Building the network graph")
# Undirected: AC power can flow either way along a line depending on system conditions.
G = nx.from_pandas_edgelist(
    lines,
    source="Source Substation",
    target="Destination Substation",
    edge_attr=["Length (km)", "Voltage (kV)"],
    create_using=nx.Graph(),
)
check("nodes", G.number_of_nodes(), EXPECTED["graph_nodes"])
check("edges", G.number_of_edges(), EXPECTED["graph_edges"])
check("connected components", nx.number_connected_components(G), EXPECTED["components"])

# 44 substations but only 42 graph nodes: two substations have no lines attached, so
# from_pandas_edgelist never sees them. Worth writing up in the data-quality report.
orphans = sorted(set(substations["Name"]) - set(G.nodes))
print(f"  [INFO] substations with no lines: {', '.join(orphans)}")

print("\n4. Network metrics")
degree_centrality = nx.degree_centrality(G)
top = sorted(degree_centrality.items(), key=lambda kv: kv[1], reverse=True)[:5]
top_degree = G.degree(top[0][0])
check("highest node degree", top_degree, EXPECTED["top_degree"])
print("  [INFO] top 5 by degree centrality:")
for name, score in top:
    print(f"           {name:<34} {score:.4f}  (degree {G.degree(name)})")

print("\n5. N-1 contingency check")
hub = top[0][0]
reduced = G.copy()
reduced.remove_node(hub)
before = nx.number_connected_components(G)
after = nx.number_connected_components(reduced)
print(f"  [INFO] components before removing {hub}: {before}")
print(f"  [INFO] components after:  {after}")
if after > before:
    print("  [INFO] the network FRAGMENTS when its busiest substation is lost")
else:
    print("  [INFO] the network survives intact -- it is meshed enough to absorb the loss")

print()
if failures:
    print(f"FAILED: {len(failures)} check(s) did not match: {', '.join(failures)}")
    sys.exit(1)
print("All checks passed. Environment is set up correctly.")
