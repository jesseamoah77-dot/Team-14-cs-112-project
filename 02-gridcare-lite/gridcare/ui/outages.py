"""Outage dashboard tab: filterable list, new-outage form, per-outage history."""

import tkinter as tk
from tkinter import ttk, messagebox

from .. import services
from .widgets import fill_table, labelled_combo, labelled_text, make_table, selected_id

COLUMNS = [
    ("outage_id", "ID"), ("substation", "Substation"), ("region", "Region"),
    ("severity", "Severity"), ("status", "Status"), ("reported_at", "Reported"),
    ("reported_by", "Reported by"),
]
KEYS = [k for k, _ in COLUMNS]


class OutagesTab(ttk.Frame):
    def __init__(self, parent, conn, user):
        super().__init__(parent)
        self.conn = conn
        self.user = user

        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=8, pady=6)

        ttk.Label(bar, text="Status:").pack(side="left")
        self.status_filter = ttk.Combobox(
            bar, values=["All", "Open", "In Progress", "Resolved"], width=12, state="readonly")
        self.status_filter.set("All")
        self.status_filter.pack(side="left", padx=(4, 12))
        self.status_filter.bind("<<ComboboxSelected>>", lambda e: self.load())

        regions = sorted({s["region"] for s in services.list_substations(self.conn)})
        ttk.Label(bar, text="Region:").pack(side="left")
        self.region_filter = ttk.Combobox(bar, values=["All"] + regions, width=16, state="readonly")
        self.region_filter.set("All")
        self.region_filter.pack(side="left", padx=(4, 12))
        self.region_filter.bind("<<ComboboxSelected>>", lambda e: self.load())

        ttk.Button(bar, text="Refresh", command=self.load).pack(side="right")
        ttk.Button(bar, text="History", command=self.show_history).pack(side="right", padx=4)
        # Only roles that can actually log an outage get the button - and the service
        # layer checks again anyway, so this is presentation, not the security.
        if user["role"] in ("engineer", "admin"):
            ttk.Button(bar, text="New outage...", command=self.new_outage).pack(side="right", padx=4)

        self.table = make_table(self, COLUMNS, widths=[40, 190, 120, 80, 90, 140, 130])
        self.load()

    def load(self):
        status = self.status_filter.get()
        region = self.region_filter.get()
        rows = services.list_outages(
            self.conn, self.user,
            status=None if status == "All" else status,
            region=None if region == "All" else region,
        )
        fill_table(self.table, rows, KEYS)

    def show_history(self):
        outage_id = selected_id(self.table)
        if outage_id is None:
            messagebox.showinfo("History", "Select an outage first.")
            return
        rows = services.get_history(self.conn, "outage", outage_id)
        lines = [f"{r['changed_at']}  {r['old_status'] or '-'} -> {r['new_status']}"
                 f"  ({r['changed_by']})" + (f"  - {r['note']}" if r["note"] else "")
                 for r in rows]
        messagebox.showinfo(f"Outage #{outage_id} history", "\n".join(lines) or "No history.")

    def new_outage(self):
        dialog = tk.Toplevel(self)
        dialog.title("Log new outage")
        dialog.grab_set()
        form = ttk.Frame(dialog, padding=10)
        form.pack(fill="both", expand=True)

        subs = services.list_substations(self.conn)
        labels = [f"{s['substation_id']} - {s['name']} ({s['region']})" for s in subs]
        sub_combo = labelled_combo(form, 0, "Substation:", labels, width=44)
        severity = labelled_combo(form, 1, "Severity:", list(services.SEVERITIES))
        description = labelled_text(form, 2, "Description:")

        def submit():
            if not sub_combo.get():
                messagebox.showerror("Missing field", "Choose a substation.", parent=dialog)
                return
            substation_id = int(sub_combo.get().split(" - ")[0])
            desc = description.get("1.0", "end").strip()
            try:
                services.log_outage(self.conn, self.user, substation_id, desc, severity.get())
            except services.DuplicateOutageError as e:
                # Second report for the same substation: ask rather than refuse outright.
                if messagebox.askyesno("Possible duplicate", str(e), parent=dialog):
                    services.log_outage(self.conn, self.user, substation_id, desc,
                                        severity.get(), allow_duplicate=True)
                else:
                    return
            except (services.ValidationError, PermissionError) as e:
                messagebox.showerror("Cannot log outage", str(e), parent=dialog)
                return
            dialog.destroy()
            self.load()

        ttk.Button(form, text="Log outage", command=submit).grid(row=3, column=1, sticky="e", pady=8)
