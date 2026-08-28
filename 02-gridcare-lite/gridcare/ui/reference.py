"""Reference tab: the imported substation register, searchable. Read-only by design."""

from tkinter import ttk

from .. import services
from .widgets import fill_table, make_table

COLUMNS = [
    ("substation_id", "ID"), ("name", "Name"), ("region", "Region"),
    ("voltage_kv", "kV"), ("status", "Status"),
]
KEYS = [k for k, _ in COLUMNS]


class ReferenceTab(ttk.Frame):
    def __init__(self, parent, conn, user):
        super().__init__(parent)
        self.conn = conn

        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=8, pady=6)
        ttk.Label(bar, text="Search:").pack(side="left")
        self.search = ttk.Entry(bar, width=30)
        self.search.pack(side="left", padx=6)
        self.search.bind("<KeyRelease>", lambda e: self.load())

        self.count = ttk.Label(bar, text="")
        self.count.pack(side="right")

        self.table = make_table(self, COLUMNS, widths=[50, 240, 150, 60, 90])
        self.load()

    def load(self):
        needle = self.search.get().strip().lower()
        rows = services.list_substations(self.conn)
        if needle:
            rows = [r for r in rows
                    if needle in r["name"].lower() or needle in r["region"].lower()]
        fill_table(self.table, rows, KEYS)
        self.count.config(text=f"{len(rows)} substation(s)")
