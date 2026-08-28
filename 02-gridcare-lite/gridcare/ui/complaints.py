"""Customer-complaint tab: log a complaint, optionally linked to a known outage."""

import tkinter as tk
from tkinter import ttk, messagebox

from .. import services
from .widgets import fill_table, labelled_combo, labelled_entry, labelled_text, make_table

COLUMNS = [
    ("complaint_id", "ID"), ("customer_name", "Customer"), ("contact", "Contact"),
    ("description", "Complaint"), ("outage_id", "Outage"), ("substation", "Substation"),
    ("created_at", "Logged"),
]
KEYS = [k for k, _ in COLUMNS]


class ComplaintsTab(ttk.Frame):
    def __init__(self, parent, conn, user):
        super().__init__(parent)
        self.conn = conn
        self.user = user

        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=8, pady=6)
        ttk.Button(bar, text="Refresh", command=self.load).pack(side="right")
        if user["role"] in ("customer_service", "admin"):
            ttk.Button(bar, text="Log complaint...", command=self.new_complaint).pack(side="right", padx=4)

        self.table = make_table(self, COLUMNS, widths=[40, 130, 110, 260, 55, 160, 140])
        self.load()

    def load(self):
        fill_table(self.table, services.list_complaints(self.conn, self.user), KEYS)

    def new_complaint(self):
        dialog = tk.Toplevel(self)
        dialog.title("Log customer complaint")
        dialog.grab_set()
        form = ttk.Frame(dialog, padding=10)
        form.pack(fill="both", expand=True)

        name = labelled_entry(form, 0, "Customer name:")
        contact = labelled_entry(form, 1, "Contact (phone/email):")
        description = labelled_text(form, 2, "Complaint:")

        # Linking is optional: the caller may be reporting something already known.
        unresolved = [o for o in services.list_outages(self.conn, self.user)
                      if o["status"] != "Resolved"]
        labels = ["(not linked)"] + [
            f"{o['outage_id']} - {o['substation']} [{o['status']}]" for o in unresolved]
        link = labelled_combo(form, 3, "Related outage:", labels, width=44)
        link.set("(not linked)")

        def submit():
            outage_id = None
            if link.get() != "(not linked)":
                outage_id = int(link.get().split(" - ")[0])
            try:
                services.log_complaint(self.conn, self.user, name.get(),
                                       description.get("1.0", "end"),
                                       contact=contact.get(), outage_id=outage_id)
            except (services.ValidationError, PermissionError) as e:
                messagebox.showerror("Cannot log complaint", str(e), parent=dialog)
                return
            dialog.destroy()
            self.load()

        ttk.Button(form, text="Log complaint", command=submit).grid(row=4, column=1, sticky="e", pady=8)
