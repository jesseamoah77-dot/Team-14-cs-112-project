"""
Shared loading, cleaning and validation code for the grid analysis.

Everything that touches the raw CSVs lives here rather than in the notebooks, so that
all six notebooks start from the same cleaned data and we're not copy-pasting the same
twenty lines of pd.read_csv into each one. Import it from a notebook like this:

    import sys; sys.path.append('../src')
    import griddata

    raw = griddata.load_raw()
    data, report = griddata.clean(raw)
"""

from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# West African bounding box, generous on purpose. Anything outside this is definitely a
# typo (transposed lat/lon, dropped minus sign) rather than a real cross-border node.
LAT_BOUNDS = (3.0, 16.0)
LON_BOUNDS = (-18.0, 5.0)

# The generator only ever emits these. Anything else means the file was hand-edited.
VALID_VOLTAGES = {11, 33, 69, 161, 330}
VALID_SUBSTATION_TYPES = {"Distribution", "Bulk Supply Point", "Transmission"}
VALID_SUBSTATION_STATUS = {"Active", "Inactive"}
VALID_LINE_STATUS = {"Active", "Under Maintenance"}

NUMERIC_COLUMNS = {
    "substations": ["Latitude", "Longitude", "Voltage (kV)", "Capacity (MVA)", "Commissioning Year"],
    "lines": ["Voltage (kV)", "Length (km)", "Capacity (MVA)"],
    "utilities": [],
}

# Strings that mean "missing" but aren't NaN yet. '\N' is the OpenFlights convention the
# brief's dataset is modelled on, so it's worth handling even though our generator is clean.
MISSING_TOKENS = [r"\N", "NULL", "null", "N/A", "n/a", "-", "", " "]


def load_raw():
    """Read the three CSVs exactly as they come off disk, no cleaning."""
    missing = [n for n in ("utilities", "substations", "lines") if not (DATA_DIR / f"{n}.csv").exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing {', '.join(n + '.csv' for n in missing)} in {DATA_DIR}. "
            "Run: python 01-grid-analysis/scripts/generate_grid_data.py"
        )
    return {
        "utilities": pd.read_csv(DATA_DIR / "utilities.csv"),
        "substations": pd.read_csv(DATA_DIR / "substations.csv"),
        "lines": pd.read_csv(DATA_DIR / "lines.csv"),
    }


def clean(raw):
    """
    Clean all three tables and record what changed.

    Returns (cleaned_dict, report_df). The report is the evidence for the cleaning
    section of the write-up, so every step logs a row whether or not it found anything.
    A step that found nothing is still a step we checked.
    """
    steps = []
    out = {}

    for name, df in raw.items():
        df = df.copy()
        before = len(df)

        # 1. Normalise the "missing" placeholders into real NaN first, so that the numeric
        #    coercion below actually sees them as missing instead of as unparseable text.
        df = df.replace(MISSING_TOKENS, np.nan)

        # 2. Strip stray whitespace from every text column. Asset registers maintained by
        #    hand are full of trailing spaces, and " Tema" != "Tema" when you group by region.
        text_cols = df.select_dtypes(include=["object", "str"]).columns
        stripped = 0
        for col in text_cols:
            original = df[col]
            df[col] = original.str.strip()
            stripped += int((original != df[col]).sum())
        steps.append((name, "Strip whitespace from text columns", f"{stripped} value(s) changed"))

        # 3. Force the numeric columns to be numeric. errors='coerce' turns anything
        #    unparseable into NaN rather than blowing up, and we count those below.
        coerced = 0
        for col in NUMERIC_COLUMNS[name]:
            if col in df.columns:
                before_na = df[col].isna().sum()
                df[col] = pd.to_numeric(df[col], errors="coerce")
                coerced += int(df[col].isna().sum() - before_na)
        steps.append((name, "Coerce numeric columns", f"{coerced} value(s) became NaN"))

        # 4. Drop exact duplicate rows.
        df = df.drop_duplicates()
        steps.append((name, "Drop duplicate rows", f"{before - len(df)} removed"))

        # 5. Report remaining missing values per column. We don't impute anything: the
        #    generated data is complete, and inventing a capacity for a substation that
        #    doesn't have one would be worse than leaving the gap visible.
        na_total = int(df.isna().sum().sum())
        steps.append((name, "Remaining missing values", f"{na_total} cell(s)"))

        out[name] = df

    report = pd.DataFrame(steps, columns=["Table", "Step", "Result"])
    return out, report


def validate(data):
    """
    Check the things that would quietly break the analysis if they were wrong.

    Returns a DataFrame of findings. 'severity' is ERROR for anything that would produce
    a wrong answer downstream, WARN for anything worth a sentence in the report.
    """
    utilities, substations, lines = data["utilities"], data["substations"], data["lines"]
    findings = []

    def add(severity, check, detail, count):
        findings.append({"severity": severity, "check": check, "detail": detail, "count": count})

    # --- Primary keys ---
    for name, df, key in [
        ("utilities", utilities, "Utility ID"),
        ("substations", substations, "Substation ID"),
        ("lines", lines, "Line ID"),
    ]:
        dupes = int(df[key].duplicated().sum())
        add("ERROR" if dupes else "OK", f"{name}.{key} unique", f"{dupes} duplicate id(s)", dupes)

    # --- Foreign keys. An orphaned line is a line to nowhere: it would silently create a
    #     phantom node in the graph and inflate every centrality score. ---
    sub_ids = set(substations["Substation ID"])
    util_ids = set(utilities["Utility ID"])

    for col in ["Source Substation ID", "Destination Substation ID"]:
        orphans = lines.loc[~lines[col].isin(sub_ids), col]
        add(
            "ERROR" if len(orphans) else "OK",
            f"lines.{col} resolves to a substation",
            f"{len(orphans)} orphaned reference(s)",
            len(orphans),
        )

    bad_util = lines.loc[~lines["Utility ID"].isin(util_ids), "Utility ID"]
    add(
        "ERROR" if len(bad_util) else "OK",
        "lines.Utility ID resolves to a utility",
        f"{len(bad_util)} orphaned reference(s)",
        len(bad_util),
    )

    # --- Geography. A transposed lat/lon puts a Ghanaian substation in the Indian Ocean
    #     and wrecks every distance calculation and map. ---
    off_map = substations[
        ~substations["Latitude"].between(*LAT_BOUNDS) | ~substations["Longitude"].between(*LON_BOUNDS)
    ]
    add(
        "ERROR" if len(off_map) else "OK",
        "Coordinates inside West Africa",
        f"{len(off_map)} substation(s) outside {LAT_BOUNDS} / {LON_BOUNDS}",
        len(off_map),
    )

    # --- Categorical domains ---
    for label, series, allowed in [
        ("substations.Voltage (kV)", substations["Voltage (kV)"], VALID_VOLTAGES),
        ("substations.Type", substations["Type"], VALID_SUBSTATION_TYPES),
        ("substations.Status", substations["Status"], VALID_SUBSTATION_STATUS),
        ("lines.Status", lines["Status"], VALID_LINE_STATUS),
    ]:
        unexpected = sorted(set(series.dropna().unique()) - allowed)
        add(
            "ERROR" if unexpected else "OK",
            f"{label} in expected set",
            f"unexpected: {unexpected}" if unexpected else "all values expected",
            len(unexpected),
        )

    # --- Sanity checks on the numbers themselves ---
    future = substations[substations["Commissioning Year"] > 2026]
    add("ERROR" if len(future) else "OK", "No future commissioning years",
        f"{len(future)} substation(s) commissioned after 2026", len(future))

    nonpositive = lines[lines["Length (km)"] <= 0]
    add("ERROR" if len(nonpositive) else "OK", "Line lengths positive",
        f"{len(nonpositive)} line(s) with length <= 0", len(nonpositive))

    self_loops = lines[lines["Source Substation ID"] == lines["Destination Substation ID"]]
    add("ERROR" if len(self_loops) else "OK", "No self-connected lines",
        f"{len(self_loops)} line(s) from a substation to itself", len(self_loops))

    # --- Structural things that are fine but need mentioning in the report ---
    connected = set(lines["Source Substation ID"]) | set(lines["Destination Substation ID"])
    isolated = substations[~substations["Substation ID"].isin(connected)]
    add(
        "WARN" if len(isolated) else "OK",
        "Every substation has at least one line",
        f"{len(isolated)} isolated: {', '.join(isolated['Name'])}" if len(isolated) else "none isolated",
        len(isolated),
    )

    # Both directions of the same pair would double-count an edge.
    pairs = lines.apply(
        lambda r: tuple(sorted((r["Source Substation ID"], r["Destination Substation ID"]))), axis=1
    )
    dup_pairs = int(pairs.duplicated().sum())
    add("WARN" if dup_pairs else "OK", "No duplicated substation pairs",
        f"{dup_pairs} pair(s) appear more than once", dup_pairs)

    return pd.DataFrame(findings)


def build_master(data):
    """
    One wide table: every line with its two substations and its owning utility attached.

    This is the table almost every later question gets answered from, so it's built once
    here rather than re-merged in each notebook. Suffixes are explicit because pandas'
    defaults produce a column called 'Name' twice over and it becomes impossible to tell
    which end of the line you're looking at.
    """
    utilities, substations, lines = data["utilities"], data["substations"], data["lines"]

    sub_cols = ["Substation ID", "Region", "Country", "Latitude", "Longitude",
                "Voltage (kV)", "Capacity (MVA)", "Commissioning Year", "Type", "Status"]

    src = substations[sub_cols].add_suffix("_src")
    dst = substations[sub_cols].add_suffix("_dst")

    master = (
        lines
        .merge(src, left_on="Source Substation ID", right_on="Substation ID_src", how="left")
        .merge(dst, left_on="Destination Substation ID", right_on="Substation ID_dst", how="left")
        .merge(
            utilities[["Utility ID", "Name", "Alias", "Code", "Type", "Country"]]
            .rename(columns={"Name": "Utility Name", "Type": "Utility Type", "Country": "Utility Country"}),
            on="Utility ID",
            how="left",
        )
        .drop(columns=["Substation ID_src", "Substation ID_dst"])
    )

    # Left joins keep every line even when a lookup fails, so an orphaned reference shows
    # up as NaN rather than a silently dropped row. Check for that here instead of
    # discovering it three notebooks later.
    lost = master["Region_src"].isna().sum() + master["Region_dst"].isna().sum()
    if lost:
        raise ValueError(f"{lost} line end(s) did not resolve to a substation - run validate() first")
    if len(master) != len(lines):
        raise ValueError(f"Merge changed row count: {len(lines)} lines in, {len(master)} out")

    # True where the two ends sit in different regions. Used all over the BI notebook.
    master["Inter-regional"] = master["Region_src"] != master["Region_dst"]
    master["Cross-border"] = master["Country_src"] != master["Country_dst"]

    return master


def build_graph(data, active_only=False):
    """
    Model the grid as an undirected NetworkX graph.

    Undirected because AC power flows either way along a line depending on system
    conditions - unlike a scheduled flight, a transmission line has no fixed direction.

    Nodes are substation names (not IDs) so that plots and printed rankings are readable.
    Node and edge attributes are carried over so the graph can be filtered later without
    going back to the DataFrames.

    active_only=True drops inactive substations and lines under maintenance, which is the
    version to use when asking "what does the network look like right now" rather than
    "what has been built".
    """
    import networkx as nx

    substations, lines = data["substations"], data["lines"]

    if active_only:
        substations = substations[substations["Status"] == "Active"]
        lines = lines[lines["Status"] == "Active"]

    G = nx.Graph()

    # Add every substation first, so nodes with no lines still appear. Building straight
    # from the edge list would silently drop them, which is how you end up reporting 42
    # nodes for a 44-substation network without noticing.
    for _, row in substations.iterrows():
        G.add_node(
            row["Name"],
            substation_id=row["Substation ID"],
            short_name=row["Short Name"],
            region=row["Region"],
            country=row["Country"],
            lat=row["Latitude"],
            lon=row["Longitude"],
            voltage=row["Voltage (kV)"],
            capacity=row["Capacity (MVA)"],
            commissioned=row["Commissioning Year"],
            sub_type=row["Type"],
            status=row["Status"],
        )

    valid = set(G.nodes)
    for _, row in lines.iterrows():
        src, dst = row["Source Substation"], row["Destination Substation"]
        # When active_only drops a substation, skip its lines too instead of letting
        # add_edge quietly resurrect it as a bare node with no attributes.
        if src in valid and dst in valid:
            G.add_edge(
                src, dst,
                line_id=row["Line ID"],
                utility_id=row["Utility ID"],
                voltage=row["Voltage (kV)"],
                length_km=row["Length (km)"],
                capacity=row["Capacity (MVA)"],
                status=row["Status"],
                line_type=row["Line Type"],
            )

    return G


def summarise(data):
    """Row counts and the handful of headline numbers, for the top of a notebook."""
    substations, lines = data["substations"], data["lines"]
    return pd.Series({
        "Utilities": len(data["utilities"]),
        "Substations": len(substations),
        "Lines": len(lines),
        "Regions": substations["Region"].nunique(),
        "Countries": substations["Country"].nunique(),
        "Active substations": int((substations["Status"] == "Active").sum()),
        "Lines under maintenance": int((lines["Status"] == "Under Maintenance").sum()),
        "Total capacity (MVA)": round(substations["Capacity (MVA)"].sum(), 1),
        "Total line length (km)": round(lines["Length (km)"].sum(), 1),
        "Oldest substation": int(substations["Commissioning Year"].min()),
        "Newest substation": int(substations["Commissioning Year"].max()),
    })
