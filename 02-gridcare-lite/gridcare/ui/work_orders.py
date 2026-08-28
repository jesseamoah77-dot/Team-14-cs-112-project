"""
Work-order tab. The same screen serves two roles differently:

- admin: sees every order, can create one for an open outage and assign a technician
- technician: sees only their own queue, can start work and complete with notes

The buttons differ by role, but every action still goes through the services layer,
which re-checks the role and the status transition.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from .. import services
from .widgets import fill_table, labelled_combo, labelled_entry, labelled_text, make_table, selected_id

COLUMNS = [
    ("work_order_id", "WO"), ("outage_id", "Outage"), ("substation", "Substation"),
    ("severity", "Severity"), ("status", "Status"), ("scheduled_date", "Scheduled"),
    ("technician", "Technician"),
]
KEYS = [k for k, _ in COLUMNS]


class WorkOrdersTab(ttk.Frame):
    def __init__(self, parent, conn, user):
        super().__init__(parent)
        self.conn = conn
        self.user = user

        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=8, pady=6)
        title = "My work orders" if user["role"] == "technician" else "All work orders"
        ttk.Label(bar, text=title, font=("", 10, "bold")).pack(side="left")
        ttk.Button(bar, text="Refresh", command=self.load).pack(side="right")

        if user["role"] == "admin":
            ttk.Button(bar, text="Create for outage...", command=self.create_wo).pack(side="right", padx=4)
            ttk.Button(bar, text="Assign...", command=self.assign).pack(side="right", padx=4)
        if user["role"] in ("technician", "admin"):
            ttk.Button(bar, text="Start work", command=self.start).pack(side="right", padx=4)
            ttk.Button(bar, text="Complete...", command=self.complete).pack(side="right", padx=4)

        self.table = make_table(self, COLUMNS, widths=[40, 55, 190, 80, 90, 100, 130])
        self.load()

    def load(self):
        rows = services.list_work_orders(self.conn, self.user)
        fill_table(self.table, rows, KEYS)

    def _selected_wo(self):
        wo_id = selected_id(self.table)
        if wo_id is None:
            messagebox.showinfo("Work orders", "Select a work order first.")
        return wo_id

    def create_wo(self):
        open_outages = [o for o in services.list_outages(self.conn, self.user, status="Open")]
        if not open_outages:
            messagebox.showinfo("Create work order", "There are no open outages.")
            return
        dialog = tk.Toplevel(self)
        dialog.title("Create work order")
        dialog.grab_set()
        form = ttk.Frame(dialog, padding=10)
        form.pack(fill="both", expand=True)

        labels = [f"{o['outage_id']} - {o['substation']} [{o['severity']}]" for o in open_outages]
        combo = labelled_combo(form, 0, "Open outage:", labels, width=44)

        def submit():
            if not combo.get():
                messagebox.showerror("Missing field", "Choose an outage.", parent=dialog)
                return
            outage_id = int(combo.get().split(" - ")[0])
            try:
                wo_id = services.create_work_order(self.conn, self.user, outage_id)
            except (services.ValidationError, PermissionError) as e:
                messagebox.showerror("Cannot create", str(e), parent=dialog)
                return
            dialog.destroy()
            self.load()
            messagebox.showinfo("Created", f"Work order #{wo_id} created (Pending). Now assign it.")

        ttk.Button(form, text="Create", command=submit).grid(row=1, column=1, sticky="e", pady=8)

    def assign(self):
        wo_id = self._selected_wo()
        if wo_id is None:
            return
        techs = services.list_technicians(self.conn)
        if not techs:
            messagebox.showerror("Assign", "No technician accounts exist yet.")
            return
        dialog = tk.Toplevel(self)
        dialog.title(f"Assign work order #{wo_id}")
        dialog.grab_set()
        form = ttk.Frame(dialog, padding=10)
        form.pack(fill="both", expand=True)

        labels = [f"{t['user_id']} - {t['full_name']}" for t in techs]
        tech_combo = labelled_combo(form, 0, "Technician:", labels)
        date_entry = labelled_entry(form, 1, "Scheduled date (YYYY-MM-DD):")

        def submit():
            if not tech_combo.get():
                messagebox.showerror("Missing field", "Choose a technician.", parent=dialog)
                return
            technician_id = int(tech_combo.get().split(" - ")[0])
            try:
                services.assign_work_order(self.conn, self.user, wo_id,
                                           technician_id, date_entry.get())
            except (services.ValidationError, PermissionError) as e:
                messagebox.showerror("Cannot assign", str(e), parent=dialog)
                return
            dialog.destroy()
            self.load()

        ttk.Button(form, text="Assign", command=submit).grid(row=2, column=1, sticky="e", pady=8)

    def start(self):
        wo_id = self._selected_wo()
        if wo_id is None:
            return
        try:
            services.start_work(self.conn, self.user, wo_id)
        except (services.ValidationError, PermissionError) as e:
            messagebox.showerror("Cannot start", str(e))
            return
        self.load()
        messagebox.showinfo("Started", f"Work order #{wo_id} started - outage now In Progress.")

    def complete(self):
        wo_id = self._selected_wo()
        if wo_id is None:
            return
        dialog = tk.Toplevel(self)
        dialog.title(f"Complete work order #{wo_id}")
        dialog.grab_set()
        form = ttk.Frame(dialog, padding=10)
        form.pack(fill="both", expand=True)

        notes = labelled_text(form, 0, "Work performed:", height=6)

        def submit():
            try:
                services.complete_work(self.conn, self.user, wo_id, notes.get("1.0", "end"))
            except (services.ValidationError, PermissionError) as e:
                messagebox.showerror("Cannot complete", str(e), parent=dialog)
                return
            dialog.destroy()
            self.load()
            messagebox.showinfo("Completed", "Work order completed and outage resolved.")

        ttk.Button(form, text="Complete + resolve outage", command=submit).grid(
            row=1, column=1, sticky="e", pady=8)
