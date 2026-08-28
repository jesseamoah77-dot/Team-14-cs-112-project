# National Electricity Grid Network Analysis — Project Report

CS 112 Final Course Project, Component 1 · Summer 2026

---

## 1. Dataset

The project uses a synthetic dataset produced by the seeded generator supplied in the
brief (`01-grid-analysis/scripts/generate_grid_data.py`, `random.seed(42)`), so every
team and every run gets byte-identical files. Three CSVs, modelled on the OpenFlights
airlines/airports/routes structure:

| file | rows | one row is |
|---|---|---|
| utilities.csv | 10 | a power company (ECG, NEDCo, GRIDCo, VRA, plus WAPP neighbours) |
| substations.csv | 44 | a substation: location, region, voltage, capacity, commissioning year, status |
| lines.csv | 55 | a line between two substations: voltage, length, capacity, status, owner |

The geography and utility names are real; every number is generated. Nothing in this
report describes Ghana's actual grid, and none of the findings below should be read
as claims about it. The dataset totals 6,946 MVA of substation capacity and
5,462 km of lines, with commissioning years spanning 1967–2022.

## 2. Cleaning and validation

The pipeline (shared module `01-grid-analysis/src/griddata.py`, walked through in
notebook 01) treats the generated files the way it would treat a real utility's
asset register export:

1. normalise missing-value placeholders (`\N`, `NULL`, blanks) to NaN;
2. strip stray whitespace from every text value;
3. coerce numeric columns with `errors='coerce'`;
4. drop exact duplicates;
5. validate: primary-key uniqueness, foreign keys in both directions, coordinates
   inside a West-African bounding box, categorical fields against their expected
   sets, no negative lengths, no self-loops, no future commissioning years.

On the generated data every check passes with zero corrections — verified rather
than assumed, and the same pipeline would catch each of those defects in a real file
(the test suite plants an orphaned line and transposed coordinates and confirms the
validators flag both).

**The one substantive data-quality finding:** two of the 44 substations — Conakry
Transmission Hub and Savelugu Substation — have no lines at all. Building the graph
naively from the edge list (as the brief's own sample code does) silently drops
them, which is why the brief reports "42 nodes". We add all 44 substations as nodes
explicitly and treat the two isolates as a finding about coverage, not noise:
dropping them would misstate per-region substation counts, capacity totals and
asset-age statistics.

We deliberately impute nothing. There is nothing missing to impute, and invented
capacities would contaminate every capacity statistic downstream.

## 3. Exploratory findings (notebook 02)

- **Greater Accra has the most substations (6)**; the northern third of the country
  (Northern, Upper East, Upper West) is thinnest on both substation count and total
  capacity — and Savelugu's missing lines make the north's *effective* connectivity
  worse than the raw counts suggest.
- **Voltage levels are near-uniform across the five tiers** (11/33/69/161/330 kV)
  for Ghanaian substations. Real registers skew heavily toward low-voltage
  distribution assets, so this flatness is a generator artefact and is flagged as a
  realism limitation rather than a finding. Cross-border hubs are exclusively
  161/330 kV, which *is* realistic for interconnectors.
- **GRIDCo operates the most lines (24 of 55)** — structurally sensible, since the
  generator gives the transmission operator every inter-regional backbone line.
- **Capacity is strongly right-skewed**: many small distribution substations under
  60 MVA, a tail of transmission assets up to ~500 MVA. Mean capacity is therefore a
  misleading summary; medians per substation type are reported instead.
- **96.4% of lines are active** (53/55; two under maintenance, both intra-regional),
  and 43/44 substations are active (Axim inactive). With n=2 maintenance lines, no
  regional maintenance pattern can honestly be claimed.
- **Most-connected substations: Mallam, Kumasi Central and Cape Coast, tied at 5
  lines each** — computed by counting both endpoints, since counting only the
  "source" column undercounts stations that mostly appear as destinations.
- Line lengths verify against coordinates: recomputed geodesic distances give
  routing factors of 1.05–1.30 for every line, matching the generator's design and
  confirming internal consistency (a stated length *below* geodesic distance is
  physically impossible and would indicate a data error).

## 4. Network analysis (notebook 04)

The grid is modelled as an **undirected** NetworkX graph (AC power has no fixed
flow direction, unlike a scheduled flight). Whole-network measures for the 42-node
main component:

| measure | value |
|---|---|
| density | 0.064 |
| diameter | 14 hops |
| average shortest path | 5.41 hops |
| average clustering coefficient | 0.384 |
| global efficiency | 0.268 |
| communities (greedy modularity) | 8, modularity 0.730 |
| bridges | 21 (16 of them inter-regional) |
| articulation points | 17 |

A sparse network with strong community structure: the detected communities are
unions of adjacent administrative regions, with the cross-border stations folding
into whichever Ghanaian cluster they attach to. The merged-data analysis (notebook
03) found that **every inter-regional pair is joined by exactly one line**, and the
bridge analysis confirms the consequence: all 16 inter-regional corridors are
bridges. Redundancy exists inside regions and nowhere between them.

### N-1 contingency

Rather than removing only the busiest node, we removed every substation in turn and
measured fragmentation. The headline is a controlled comparison the degree ranking
cannot see:

> **Mallam and Cape Coast both have degree 5 — the joint highest in the network.
> Removing Mallam disconnects nobody. Removing Cape Coast cuts off 21 of the
> remaining 41 substations — half the country.**

Mallam's five lines are redundant local links inside a well-meshed Greater Accra;
Cape Coast's five make it a link in the only west–east backbone chain. Connection
count does not measure criticality — betweenness and articulation-point analysis do.
The 17 articulation points are dominated by the backbone chain (Takoradi cuts off
19, Koforidua 17, Kumasi Central 15, Ho 13). The brute-force removal results were
cross-checked against `nx.articulation_points` and agree exactly.

Interpretation caveat, per the brief: these are structural measures on synthetic
data. They say nothing about electrical load, voltage stability or protection
behaviour, and are offered as reliability *proxies* — indicators of where a real
analysis with power-flow data would look first.

## 5. Visualisation and dashboard

Every EDA question has a saved chart (`01-grid-analysis/outputs/`); the network map
positions nodes by real coordinates, sizes them by betweenness, colours by community
and rings articulation points in red — one figure carrying the main finding. A
three-layer interactive Folium map (`outputs/grid_map.html`) toggles substations by
voltage, lines by status and lines by utility. The Streamlit dashboard
(`streamlit run dashboard.py`) provides the overview, filterable network view,
capacity map and the N-1 ranking.

## 6. Challenges and decisions

- **The 42-vs-44 node discrepancy** (isolated substations silently dropped by
  edge-list construction) — resolved by adding nodes before edges; kept as both a
  data-quality lesson and a coverage finding.
- **Check-your-claims discipline**: an early draft of a notebook stated 13
  inter-regional lines; the computed figure is 16. The correction is a reminder that
  every number in prose must come from the code, not from memory.
- **Windows quirks**: pip's resolver stalls on Jupyter unless installed
  `--only-binary=:all:`; documented in the README so teammates don't lose an hour.
- **Honest nulls**: with ~4 substations per region drawn from a uniform 1965–2023
  range, regional "oldest infrastructure" differences are noise — the report says
  so instead of inventing a pattern (Q5 uses a strip plot precisely to avoid
  averaging three data points into a fake signal).

## 7. Limitations and future work

All numeric values are synthetic; utility assignment is uniform (NEDCo appears in
southern regions it does not really serve); voltage levels are unrealistically flat;
the dataset has no load, generation or time-series data, so no power-flow or outage
simulation is possible. With real data, the next steps would be: load-weighted
centrality, N-2 contingency screening, correlating asset age with recorded fault
history, and validating the graph-based "critical substation" list against
operational incident logs.
