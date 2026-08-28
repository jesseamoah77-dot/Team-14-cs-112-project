"""
Login window and the role-routed main window.

Which tabs a user gets is decided here from their role; what those tabs are allowed
to do is decided again in the services layer. Both sides matter: the routing keeps
the interface uncluttered, the services checks keep it secure.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from .. import auth
from .complaints import ComplaintsTab
from .outages import OutagesTab
from .reference import ReferenceTab
from .reports import ReportsTab
from .work_orders import WorkOrdersTab

# role -> ordered list of (title, tab class)
TABS_BY_ROLE = {
    "admin": [("Outages", OutagesTab), ("Work orders", WorkOrdersTab),
              ("Complaints", ComplaintsTab), ("Reports", ReportsTab),
              ("Substations", ReferenceTab)],
    "engineer": [("Outages", OutagesTab), ("Work orders", WorkOrdersTab),
                 ("Reports", ReportsTab), ("Substations", ReferenceTab)],
    "technician": [("My work orders", WorkOrdersTab), ("Outages", OutagesTab),
                   ("Substations", ReferenceTab)],
    "customer_service": [("Complaints", ComplaintsTab), ("Outages", OutagesTab),
                         ("Reports", ReportsTab), ("Substations", ReferenceTab)],
}


class LoginFrame(ttk.Frame):
    def __init__(self, master, conn, on_success):
        super().__init__(master, padding=24)
        self.conn = conn
        self.on_success = on_success

        ttk.Label(self, text="GridCare-Lite", font=("", 16, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(0, 2))
        ttk.Label(self, text="Outage and maintenance management").grid(
            row=1, column=0, columnspan=2, pady=(0, 14))

        ttk.Label(self, text="Username:").grid(row=2, column=0, sticky="e", padx=6, pady=4)
        self.username = ttk.Entry(self, width=26)
        self.username.grid(row=2, column=1, pady=4)

        ttk.Label(self, text="Password:").grid(row=3, column=0, sticky="e", padx=6, pady=4)
        self.password = ttk.Entry(self, width=26, show="*")
        self.password.grid(row=3, column=1, pady=4)

        ttk.Button(self, text="Log in", command=self.attempt).grid(
            row=4, column=0, columnspan=2, pady=12)
        self.username.focus_set()
        # Enter submits from either field - people expect it on a login form.
        master.bind("<Return>", lambda e: self.attempt())

    def attempt(self):
        try:
            user = auth.authenticate(self.conn, self.username.get(), self.password.get())
        except auth.AuthError as e:
            messagebox.showerror("Login failed", str(e))
            self.password.delete(0, "end")
            return
        self.on_success(user)


class MainWindow(ttk.Frame):
    def __init__(self, master, conn, user, on_logout):
        super().__init__(master)
        self.pack(fill="both", expand=True)

        header = ttk.Frame(self, padding=(10, 6))
        header.pack(fill="x")
        role_label = user["role"].replace("_", " ").title()
        ttk.Label(header, text=f"GridCare-Lite - {user['full_name']} ({role_label})",
                  font=("", 11, "bold")).pack(side="left")
        ttk.Button(header, text="Log out", command=on_logout).pack(side="right")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)
        self._tabs = []
        for title, tab_class in TABS_BY_ROLE[user["role"]]:
            tab = tab_class(notebook, conn, user)
            notebook.add(tab, text=title)
            self._tabs.append(tab)

        # Reload a tab whenever it is brought to the front, so cross-tab changes
        # (resolve an outage -> reports move) appear without pressing Refresh.
        def on_change(_event):
            current = notebook.nametowidget(notebook.select())
            if hasattr(current, "load"):
                current.load()
        notebook.bind("<<NotebookTabChanged>>", on_change)


def run_app(conn):
    root = tk.Tk()
    root.title("GridCare-Lite")
    root.geometry("980x620")

    state = {"frame": None}

    def show_login():
        if state["frame"] is not None:
            state["frame"].destroy()
        root.geometry("360x300")
        frame = LoginFrame(root, conn, on_success=show_main)
        frame.pack(fill="both", expand=True)
        state["frame"] = frame

    def show_main(user):
        state["frame"].destroy()
        root.geometry("980x620")
        state["frame"] = MainWindow(root, conn, user, on_logout=show_login)

    show_login()
    root.mainloop()
