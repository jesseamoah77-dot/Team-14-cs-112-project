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

overview, network, geography, reliability, search = st.tabs(
    ["Overview", "Network", "Geography", "Reliability", "Search"]
)

with overview:
    left, mid1, mid2, right = st.columns(4)
    left.metric("Substations", len(substations))
    mid1.metric("Lines", len(lines))
    mid2.metric("Regions", substations["Region"].nunique())
    right.metric(
        "Total capacity (MVA)",
        f"{substations['Capacity (MVA)'].sum():,.0f}"
    )

    st.subheader("Substations by region")
    region_counts = substations["Region"].value_counts().reset_index()
    region_counts.columns = ["Region", "Substations"]

    st.plotly_chart(
        px.bar(
            region_counts,
            x="Substations",
            y="Region",
            orientation="h",
            color_discrete_sequence=["#2b6cb0"]
        ),
        use_container_width=True,
    )

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Voltage levels")

        v = (
            substations["Voltage (kV)"]
            .value_counts()
            .sort_index()
            .reset_index()
        )

        v.columns = ["Voltage (kV)", "Substations"]
        v["Voltage (kV)"] = v["Voltage (kV)"].astype(str) + " kV"

        st.plotly_chart(
            px.bar(
                v,
                x="Voltage (kV)",
                y="Substations",
                color_discrete_sequence=["#2b6cb0"]
            ),
            use_container_width=True
        )

    with col_b:
        st.subheader("Lines per utility")

        u = master["Code"].value_counts().reset_index()
        u.columns = ["Utility", "Lines"]

        st.plotly_chart(
            px.bar(
                u,
                x="Utility",
                y="Lines",
                color_discrete_sequence=["#2b6cb0"]
            ),
            use_container_width=True
        )

with network:
    st.subheader("The grid as a graph")

    regions = ["All"] + sorted(substations["Region"].unique())
    chosen = st.selectbox("Filter to region", regions)

    G = griddata.build_graph(data)

    if chosen != "All":
        keep = [
            n
            for n, d in G.nodes(data=True)
            if d["region"] == chosen
        ]
        G = G.subgraph(keep)

    edge_x, edge_y = [], []

    for a, b in G.edges():
        edge_x += [
            G.nodes[a]["lon"],
            G.nodes[b]["lon"],
            None
        ]

        edge_y += [
            G.nodes[a]["lat"],
            G.nodes[b]["lat"],
            None
        ]

    degree = dict(G.degree())

    node_trace = go.Scatter(
        x=[G.nodes[n]["lon"] for n in G.nodes],
        y=[G.nodes[n]["lat"] for n in G.nodes],
        mode="markers",
        marker=dict(
            size=[8 + 4 * degree[n] for n in G.nodes],
            color=[degree[n] for n in G.nodes],
            colorscale="Blues",
            showscale=True,
            colorbar=dict(title="Degree"),
            line=dict(width=1, color="#333"),
        ),
        text=[
            f"{n}<br>"
            f"degree {degree[n]}<br>"
            f"{G.nodes[n]['voltage']} kV, "
            f"{G.nodes[n]['capacity']} MVA"
            for n in G.nodes
        ],
        hoverinfo="text",
    )

    fig = go.Figure(
        [
            go.Scatter(
                x=edge_x,
                y=edge_y,
                mode="lines",
                line=dict(width=0.7, color="#aaa"),
                hoverinfo="none"
            ),
            node_trace,
        ]
    )

    fig.update_layout(
        showlegend=False,
        height=560,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title="Longitude",
        yaxis_title="Latitude"
    )

    st.plotly_chart(fig, use_container_width=True)

    if metrics is not None:
        st.subheader("Centrality rankings (main component)")
        st.dataframe(
            metrics.head(15),
            use_container_width=True
        )
    else:
        st.info(
            "Run notebook 04 to generate network_metrics.csv"
        )

    st.subheader("3D Network Visualisation")

    G3 = griddata.build_graph(data)

    nodes_3d = list(G3.nodes())

    x_3d = [
        G3.nodes[n]["lon"]
        for n in nodes_3d
    ]

    y_3d = [
        G3.nodes[n]["lat"]
        for n in nodes_3d
    ]

    z_3d = [
        G3.nodes[n]["capacity"]
        for n in nodes_3d
    ]

    edge_x_3d = []
    edge_y_3d = []
    edge_z_3d = []

    for a, b in G3.edges():
        edge_x_3d.extend([
            G3.nodes[a]["lon"],
            G3.nodes[b]["lon"],
            None
        ])

        edge_y_3d.extend([
            G3.nodes[a]["lat"],
            G3.nodes[b]["lat"],
            None
        ])

        edge_z_3d.extend([
            G3.nodes[a]["capacity"],
            G3.nodes[b]["capacity"],
            None
        ])

    edge_trace_3d = go.Scatter3d(
        x=edge_x_3d,
        y=edge_y_3d,
        z=edge_z_3d,
        mode="lines",
        line=dict(
            width=2,
            color="#999999"
        ),
        hoverinfo="none"
    )

    degree_3d = dict(G3.degree())

    node_trace_3d = go.Scatter3d(
        x=x_3d,
        y=y_3d,
        z=z_3d,
        mode="markers",
        marker=dict(
            size=[
                5 + degree_3d[n]
                for n in nodes_3d
            ],
            color=z_3d,
            colorscale="Blues",
            showscale=True,
            colorbar=dict(
                title="Capacity (MVA)"
            )
        ),
        text=[
            f"{n}<br>"
            f"Degree: {degree_3d[n]}<br>"
            f"Voltage: {G3.nodes[n]['voltage']} kV<br>"
            f"Capacity: {G3.nodes[n]['capacity']} MVA<br>"
            f"Region: {G3.nodes[n]['region']}"
            for n in nodes_3d
        ],
        hoverinfo="text"
    )

    fig_3d = go.Figure(
        data=[
            edge_trace_3d,
            node_trace_3d
        ]
    )

    fig_3d.update_layout(
        title="3D Electricity Grid Network",
        scene=dict(
            xaxis_title="Longitude",
            yaxis_title="Latitude",
            zaxis_title="Capacity (MVA)"
        ),
        height=700,
        margin=dict(
            l=0,
            r=0,
            t=50,
            b=0
        ),
        showlegend=False
    )

    st.plotly_chart(
        fig_3d,
        use_container_width=True
    )

with geography:
    st.subheader("Substation map")

    st.caption(
        "Marker size = capacity. The full layered map with lines is in "
        "outputs/grid_map.html (notebook 05)."
    )

    map_df = substations.rename(
        columns={
            "Latitude": "lat",
            "Longitude": "lon"
        }
    )

    fig = px.scatter_map(
        map_df,
        lat="lat",
        lon="lon",
        size="Capacity (MVA)",
        color="Voltage (kV)",
        hover_name="Name",
        hover_data={
            "Region": True,
            "Status": True,
            "lat": False,
            "lon": False
        },
        zoom=5.3,
        height=560,
        map_style="carto-positron",
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.subheader("Grid Expansion by Commissioning Year")

    animation_df = substations.copy()

    animation_df["Commissioning Year"] = pd.to_numeric(
        animation_df["Commissioning Year"],
        errors="coerce"
    )

    animation_df = animation_df.dropna(
        subset=["Commissioning Year"]
    )

    animation_df["Commissioning Year"] = animation_df[
        "Commissioning Year"
    ].astype(int)

    animation_df = animation_df.sort_values(
        "Commissioning Year"
    )

    animated_fig = px.scatter_map(
        animation_df,
        lat="Latitude",
        lon="Longitude",
        size="Capacity (MVA)",
        color="Voltage (kV)",
        animation_frame="Commissioning Year",
        hover_name="Name",
        hover_data={
            "Region": True,
            "Country": True,
            "Status": True,
            "Capacity (MVA)": True,
            "Commissioning Year": True,
            "Latitude": False,
            "Longitude": False
        },
        zoom=5.3,
        height=600,
        map_style="carto-positron"
    )

    animated_fig.update_layout(
        title="Substation Development Over Time",
        margin=dict(
            l=10,
            r=10,
            t=50,
            b=10
        )
    )

    st.plotly_chart(
        animated_fig,
        use_container_width=True
    )

    st.subheader("Line lengths")

    st.plotly_chart(
        px.box(
            master,
            x="Voltage (kV)",
            y="Length (km)",
            color_discrete_sequence=["#2b6cb0"]
        ),
        use_container_width=True,
    )

with reliability:
    st.subheader(
        "N-1 contingency: what breaks if one substation is lost?"
    )

    if n1 is not None:
        worst = n1.sort_values(
            "Nodes cut off",
            ascending=False
        ).head(12)

        st.plotly_chart(
            px.bar(
                worst,
                x="Nodes cut off",
                y="Removed",
                orientation="h",
                color="Nodes cut off",
                color_continuous_scale="Reds"
            ).update_layout(
                yaxis=dict(
                    autorange="reversed"
                )
            ),
            use_container_width=True,
        )

        st.caption(
            "Removing Cape Coast strands half the network; removing Mallam — same degree — "
            "strands nobody. Redundancy, not connection count, is what protects the grid."
        )

    else:
        st.info(
            "Run notebook 04 to generate n1_contingency.csv"
        )

    st.subheader("Assets needing attention")

    col_a, col_b = st.columns(2)

    with col_a:
        st.write("**Lines under maintenance**")

        st.dataframe(
            master.loc[
                master["Status"] == "Under Maintenance",
                [
                    "Source Substation",
                    "Destination Substation",
                    "Region_src",
                    "Voltage (kV)"
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

    with col_b:
        st.write("**Oldest substations (top 8)**")

        st.dataframe(
            substations.nsmallest(
                8,
                "Commissioning Year"
            )[
                [
                    "Short Name",
                    "Region",
                    "Commissioning Year",
                    "Capacity (MVA)",
                    "Status"
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

with search:
    st.subheader("Substation Finder")

    search_term = st.text_input(
        "Search by substation name, short name, or ID"
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        search_regions = [
            "All"
        ] + sorted(
            substations["Region"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        selected_region = st.selectbox(
            "Region",
            search_regions,
            key="search_region"
        )

    with c2:
        search_voltages = [
            "All"
        ] + sorted(
            substations["Voltage (kV)"]
            .dropna()
            .unique()
            .tolist()
        )

        selected_voltage = st.selectbox(
            "Voltage (kV)",
            search_voltages,
            key="search_voltage"
        )

    with c3:
        search_statuses = [
            "All"
        ] + sorted(
            substations["Status"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        selected_status = st.selectbox(
            "Status",
            search_statuses,
            key="search_status"
        )

    results = substations.copy()

    if search_term:
        term = search_term.strip().lower()

        results = results[
            results["Name"]
            .astype(str)
            .str.lower()
            .str.contains(term, na=False)
            |
            results["Short Name"]
            .astype(str)
            .str.lower()
            .str.contains(term, na=False)
            |
            results["Substation ID"]
            .astype(str)
            .str.contains(term, na=False)
        ]

    if selected_region != "All":
        results = results[
            results["Region"].astype(str)
            == selected_region
        ]

    if selected_voltage != "All":
        results = results[
            results["Voltage (kV)"]
            == selected_voltage
        ]

    if selected_status != "All":
        results = results[
            results["Status"].astype(str)
            == selected_status
        ]

    st.write(
        f"Results found: {len(results)}"
    )

    display_columns = [
        "Substation ID",
        "Name",
        "Short Name",
        "Region",
        "Country",
        "Latitude",
        "Longitude",
        "Voltage (kV)",
        "Capacity (MVA)",
        "Commissioning Year",
        "Type",
        "Status"
    ]

    st.dataframe(
        results[display_columns],
        use_container_width=True,
        hide_index=True
    )

    if not results.empty:
        st.subheader("Substation Details")

        selected_name = st.selectbox(
            "Select a substation",
            results["Name"].tolist(),
            key="selected_substation"
        )

        selected_row = results[
            results["Name"] == selected_name
        ].iloc[0]

        d1, d2, d3, d4 = st.columns(4)

        d1.metric(
            "Voltage",
            f"{selected_row['Voltage (kV)']} kV"
        )

        d2.metric(
            "Capacity",
            f"{selected_row['Capacity (MVA)']} MVA"
        )

        d3.metric(
            "Region",
            str(selected_row["Region"])
        )

        d4.metric(
            "Status",
            str(selected_row["Status"])
        )

    st.divider()

    st.subheader("Utility Comparison")

    utility_names = sorted(
        utilities["Name"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    if len(utility_names) >= 2:
        u1, u2 = st.columns(2)

        with u1:
            utility_a = st.selectbox(
                "Utility A",
                utility_names,
                key="utility_a"
            )

        with u2:
            utility_b = st.selectbox(
                "Utility B",
                utility_names,
                index=1,
                key="utility_b"
            )

        id_a = utilities.loc[
            utilities["Name"] == utility_a,
            "Utility ID"
        ].iloc[0]

        id_b = utilities.loc[
            utilities["Name"] == utility_b,
            "Utility ID"
        ].iloc[0]

        lines_a = lines[
            lines["Utility ID"] == id_a
        ]

        lines_b = lines[
            lines["Utility ID"] == id_b
        ]

        connected_a = set(
            lines_a["Source Substation ID"]
            .dropna()
            .tolist()
        ) | set(
            lines_a["Destination Substation ID"]
            .dropna()
            .tolist()
        )

        connected_b = set(
            lines_b["Source Substation ID"]
            .dropna()
            .tolist()
        ) | set(
            lines_b["Destination Substation ID"]
            .dropna()
            .tolist()
        )

        substations_a = substations[
            substations["Substation ID"]
            .isin(connected_a)
        ]

        substations_b = substations[
            substations["Substation ID"]
            .isin(connected_b)
        ]

        maintenance_a = (
            lines_a["Status"]
            == "Under Maintenance"
        ).sum()

        maintenance_b = (
            lines_b["Status"]
            == "Under Maintenance"
        ).sum()

        comparison = pd.DataFrame({
            "Metric": [
                "Lines Operated",
                "Substations Connected",
                "Total Line Length (km)",
                "Average Line Capacity (MVA)",
                "Lines Under Maintenance"
            ],
            utility_a: [
                len(lines_a),
                len(substations_a),
                round(
                    lines_a["Length (km)"].sum(),
                    2
                ),
                round(
                    lines_a["Capacity (MVA)"].mean(),
                    2
                ),
                int(maintenance_a)
            ],
            utility_b: [
                len(lines_b),
                len(substations_b),
                round(
                    lines_b["Length (km)"].sum(),
                    2
                ),
                round(
                    lines_b["Capacity (MVA)"].mean(),
                    2
                ),
                int(maintenance_b)
            ]
        })

        st.dataframe(
            comparison,
            use_container_width=True,
            hide_index=True
        )

        chart_data = pd.DataFrame({
            "Utility": [
                utility_a,
                utility_b
            ],
            "Lines Operated": [
                len(lines_a),
                len(lines_b)
            ],
            "Substations Connected": [
                len(substations_a),
                len(substations_b)
            ],
            "Maintenance Lines": [
                int(maintenance_a),
                int(maintenance_b)
            ]
        })

        comparison_fig = px.bar(
            chart_data,
            x="Utility",
            y=[
                "Lines Operated",
                "Substations Connected",
                "Maintenance Lines"
            ],
            barmode="group",
            title="Utility Infrastructure Comparison"
        )

        st.plotly_chart(
            comparison_fig,
            use_container_width=True
        )

    else:
        st.warning(
            "At least two utilities are required for comparison."
        )
