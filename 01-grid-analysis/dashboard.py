"""
Interactive dashboard for the grid analysis.

Run from this folder:

    streamlit run dashboard.py

Reads the cleaned CSVs and the metric exports the notebooks write into data/, so run
notebooks 01 and 04 first (or just `python scripts/generate_grid_data.py` followed by
the notebooks) if data/ is empty.
"""

from pathlib import Path

import networkx as nx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import sys

sys.path.append(str(Path(__file__).resolve().parent / "src"))
import griddata

st.set_page_config(page_title="Grid Network Analysis", layout="wide")


@st.cache_data
def load():
    data, _ = griddata.clean(griddata.load_raw())
    master = griddata.build_master(data)
    metrics_path = griddata.DATA_DIR / "network_metrics.csv"
    metrics = pd.read_csv(metrics_path, index_col=0) if metrics_path.exists() else None
    n1_path = griddata.DATA_DIR / "n1_contingency.csv"
    n1 = pd.read_csv(n1_path) if n1_path.exists() else None
    return data, master, metrics, n1


data, master, metrics, n1 = load()
substations, lines, utilities = data["substations"], data["lines"], data["utilities"]

st.title("National Electricity Grid Network Analysis")
st.caption(
    "Synthetic dataset grounded in Ghanaian geography and utility names (seed 42). "
    "Capacities, connections and statuses are generated, not real measurements — "
    "nothing here describes Ghana's actual grid."
)

overview, network, geography, reliability = st.tabs(
    ["Overview", "Network", "Geography", "Reliability"]
)

# ---------------------------------------------------------------- Overview
with overview:
    left, mid1, mid2, right = st.columns(4)
    left.metric("Substations", len(substations))
    mid1.metric("Lines", len(lines))
    mid2.metric("Regions", substations["Region"].nunique())
    right.metric("Total capacity (MVA)", f"{substations['Capacity (MVA)'].sum():,.0f}")

    st.subheader("Substations by region")
    region_counts = substations["Region"].value_counts().reset_index()
    region_counts.columns = ["Region", "Substations"]
    st.plotly_chart(
        px.bar(region_counts, x="Substations", y="Region", orientation="h",
               color_discrete_sequence=["#2b6cb0"]),
        use_container_width=True,
    )

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Voltage levels")
        v = substations["Voltage (kV)"].value_counts().sort_index().reset_index()
        v.columns = ["Voltage (kV)", "Substations"]
        v["Voltage (kV)"] = v["Voltage (kV)"].astype(str) + " kV"
        st.plotly_chart(px.bar(v, x="Voltage (kV)", y="Substations",
                               color_discrete_sequence=["#2b6cb0"]),
                        use_container_width=True)
    with col_b:
        st.subheader("Lines per utility")
        u = master["Code"].value_counts().reset_index()
        u.columns = ["Utility", "Lines"]
        st.plotly_chart(px.bar(u, x="Utility", y="Lines",
                               color_discrete_sequence=["#2b6cb0"]),
                        use_container_width=True)

# ---------------------------------------------------------------- Network
with network:
    st.subheader("The grid as a graph")

    regions = ["All"] + sorted(substations["Region"].unique())
    chosen = st.selectbox("Filter to region", regions)

    G = griddata.build_graph(data)
    if chosen != "All":
        keep = [n for n, d in G.nodes(data=True) if d["region"] == chosen]
        G = G.subgraph(keep)

    edge_x, edge_y = [], []
    for a, b in G.edges():
        edge_x += [G.nodes[a]["lon"], G.nodes[b]["lon"], None]
        edge_y += [G.nodes[a]["lat"], G.nodes[b]["lat"], None]

    degree = dict(G.degree())
    node_trace = go.Scatter(
        x=[G.nodes[n]["lon"] for n in G.nodes],
        y=[G.nodes[n]["lat"] for n in G.nodes],
        mode="markers",
        marker=dict(
            size=[8 + 4 * degree[n] for n in G.nodes],
            color=[degree[n] for n in G.nodes],
            colorscale="Blues", showscale=True,
            colorbar=dict(title="Degree"), line=dict(width=1, color="#333"),
        ),
        text=[f"{n}<br>degree {degree[n]}<br>{G.nodes[n]['voltage']} kV, "
              f"{G.nodes[n]['capacity']} MVA" for n in G.nodes],
        hoverinfo="text",
    )
    fig = go.Figure([
        go.Scatter(x=edge_x, y=edge_y, mode="lines",
                   line=dict(width=0.7, color="#aaa"), hoverinfo="none"),
        node_trace,
    ])
    fig.update_layout(showlegend=False, height=560, margin=dict(l=10, r=10, t=10, b=10),
                      xaxis_title="Longitude", yaxis_title="Latitude")
    st.plotly_chart(fig, use_container_width=True)

    if metrics is not None:
        st.subheader("Centrality rankings (main component)")
        st.dataframe(metrics.head(15), use_container_width=True)
    else:
        st.info("Run notebook 04 to generate network_metrics.csv")

# ---------------------------------------------------------------- Geography
with geography:
    st.subheader("Substation map")
    st.caption("Marker size = capacity. The full layered map with lines is in outputs/grid_map.html (notebook 05).")

    map_df = substations.rename(columns={"Latitude": "lat", "Longitude": "lon"})
    fig = px.scatter_map(
        map_df, lat="lat", lon="lon",
        size="Capacity (MVA)", color="Voltage (kV)",
        hover_name="Name",
        hover_data={"Region": True, "Status": True, "lat": False, "lon": False},
        zoom=5.3, height=560, map_style="carto-positron",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Line lengths")
    st.plotly_chart(
        px.box(master, x="Voltage (kV)", y="Length (km)", color_discrete_sequence=["#2b6cb0"]),
        use_container_width=True,
    )

# ---------------------------------------------------------------- Reliability
with reliability:
    st.subheader("N-1 contingency: what breaks if one substation is lost?")
    if n1 is not None:
        worst = n1.sort_values("Nodes cut off", ascending=False).head(12)
        st.plotly_chart(
            px.bar(worst, x="Nodes cut off", y="Removed", orientation="h",
                   color="Nodes cut off", color_continuous_scale="Reds")
            .update_layout(yaxis=dict(autorange="reversed")),
            use_container_width=True,
        )
        st.caption(
            "Removing Cape Coast strands half the network; removing Mallam — same degree — "
            "strands nobody. Redundancy, not connection count, is what protects the grid."
        )
    else:
        st.info("Run notebook 04 to generate n1_contingency.csv")

    st.subheader("Assets needing attention")
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("**Lines under maintenance**")
        st.dataframe(
            master.loc[master["Status"] == "Under Maintenance",
                       ["Source Substation", "Destination Substation", "Region_src", "Voltage (kV)"]],
            use_container_width=True, hide_index=True,
        )
    with col_b:
        st.write("**Oldest substations (top 8)**")
        st.dataframe(
            substations.nsmallest(8, "Commissioning Year")[
                ["Short Name", "Region", "Commissioning Year", "Capacity (MVA)", "Status"]],
            use_container_width=True, hide_index=True,
        )
