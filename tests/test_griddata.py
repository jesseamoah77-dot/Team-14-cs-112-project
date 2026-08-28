"""
Tests for the shared grid data module.

Run from the repo root:  pytest tests/test_griddata.py -v

Most of these pin the known properties of the seed-42 dataset. That's deliberate: the
whole point of the seeded generator is that everyone's data is identical, so if a test
here fails, either the generator was modified or the cleaning code broke something.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "01-grid-analysis" / "src"))

import griddata  # noqa: E402


@pytest.fixture(scope="module")
def data():
    cleaned, _ = griddata.clean(griddata.load_raw())
    return cleaned


@pytest.fixture(scope="module")
def graph(data):
    return griddata.build_graph(data)


class TestLoadAndClean:
    def test_row_counts_match_brief(self, data):
        assert len(data["utilities"]) == 10
        assert len(data["substations"]) == 44
        assert len(data["lines"]) == 55

    def test_numeric_columns_are_numeric(self, data):
        subs = data["substations"]
        for col in ["Latitude", "Longitude", "Voltage (kV)", "Capacity (MVA)"]:
            assert subs[col].dtype.kind == "f" or subs[col].dtype.kind == "i", col

    def test_clean_is_idempotent(self, data):
        # Cleaning already-clean data must change nothing. If it does, the cleaning
        # steps are rewriting values rather than just normalising them.
        again, _ = griddata.clean(data)
        for name in data:
            assert data[name].equals(again[name]), name


class TestValidation:
    def test_no_errors_on_generated_data(self, data):
        findings = griddata.validate(data)
        errors = findings[findings["severity"] == "ERROR"]
        assert errors.empty, errors.to_string()

    def test_flags_the_two_isolated_substations(self, data):
        findings = griddata.validate(data)
        isolated = findings[findings["check"] == "Every substation has at least one line"]
        assert isolated.iloc[0]["severity"] == "WARN"
        assert isolated.iloc[0]["count"] == 2

    def test_catches_orphaned_line(self, data):
        # Break a copy on purpose: point one line at a substation that doesn't exist.
        broken = {k: v.copy() for k, v in data.items()}
        broken["lines"].loc[broken["lines"].index[0], "Source Substation ID"] = 99999
        findings = griddata.validate(broken)
        errors = findings[findings["severity"] == "ERROR"]
        assert not errors.empty

    def test_catches_bad_coordinates(self, data):
        broken = {k: v.copy() for k, v in data.items()}
        # Transpose lat/lon on one row - the classic data-entry mistake.
        i = broken["substations"].index[0]
        lat = broken["substations"].loc[i, "Latitude"]
        lon = broken["substations"].loc[i, "Longitude"]
        broken["substations"].loc[i, "Latitude"] = lon
        broken["substations"].loc[i, "Longitude"] = lat
        findings = griddata.validate(broken)
        geo = findings[findings["check"] == "Coordinates inside West Africa"]
        assert geo.iloc[0]["severity"] == "ERROR"


class TestMaster:
    def test_no_rows_lost_or_gained(self, data):
        master = griddata.build_master(data)
        assert len(master) == len(data["lines"])

    def test_both_ends_resolved(self, data):
        master = griddata.build_master(data)
        assert master["Region_src"].notna().all()
        assert master["Region_dst"].notna().all()

    def test_interregional_flag(self, data):
        master = griddata.build_master(data)
        # The backbone lines connect region hubs, so there must be some of each.
        assert master["Inter-regional"].any()
        assert (~master["Inter-regional"]).any()


class TestGraph:
    def test_all_substations_present(self, graph):
        # 44, not 42: the two substations with no lines must still be nodes.
        assert graph.number_of_nodes() == 44
        assert graph.number_of_edges() == 55

    def test_isolated_nodes_are_the_expected_ones(self, graph):
        import networkx as nx
        isolated = set(nx.isolates(graph))
        assert isolated == {"Conakry Transmission Hub", "Savelugu Substation"}

    def test_main_component_holds_everything_else(self, graph):
        import networkx as nx
        components = sorted(nx.connected_components(graph), key=len, reverse=True)
        # 42 connected substations + 2 isolates = 3 components in the strict sense.
        assert len(components[0]) == 42
        assert len(components) == 3

    def test_node_attributes_carried(self, graph):
        attrs = graph.nodes["Tema Substation"]
        assert attrs["region"] == "Greater Accra"
        assert attrs["voltage"] in {11, 33, 69, 161, 330}
        assert "capacity" in attrs and "commissioned" in attrs

    def test_edge_attributes_carried(self, graph):
        _, _, attrs = next(iter(graph.edges(data=True)))
        for key in ["line_id", "utility_id", "voltage", "length_km", "status"]:
            assert key in attrs

    def test_active_only_is_smaller(self, data):
        full = griddata.build_graph(data)
        active = griddata.build_graph(data, active_only=True)
        assert active.number_of_nodes() < full.number_of_nodes()
        assert active.number_of_edges() < full.number_of_edges()
