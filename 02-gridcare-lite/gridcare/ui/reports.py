"""Reports tab: headline figures plus an open-outages-by-region chart.

The chart is matplotlib embedded in Tkinter via FigureCanvasTkAgg, per the brief's
suggestion. Everything reloads from the database on Refresh, so a demo can resolve an
outage in one tab and immediately show the numbers moving here.
"""

from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from .. import services


class ReportsTab(ttk.Frame):
    def __init__(self, parent, conn, user):
        super().__init__(parent)
        self.conn = conn
        self.user = user

        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=8, pady=6)
        ttk.Label(bar, text="Operational summary", font=("", 10, "bold")).pack(side="left")
        ttk.Button(bar, text="Refresh", command=self.load).pack(side="right")

        self.stats = ttk.Frame(self)
        self.stats.pack(fill="x", padx=8)

        self.figure = Figure(figsize=(7, 3.4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)

        self.load()

    def load(self):
        summary = services.report_summary(self.conn, self.user)

        for child in self.stats.winfo_children():
            child.destroy()

        by_status = summary["by_status"]
        avg = summary["avg_resolution_hours"]

        cells = [
            ("Open", by_status.get("Open", 0)),
            ("In Progress", by_status.get("In Progress", 0)),
            ("Resolved", by_status.get("Resolved", 0)),
            ("Avg resolution (h)", avg if avg is not None else "n/a"),
            ("Complaints", summary["complaints_total"]),
            ("Linked to outages", summary["complaints_linked"]),
        ]

        for i, (label, value) in enumerate(cells):
            box = ttk.LabelFrame(self.stats, text=label)
            box.grid(
                row=0,
                column=i,
                padx=4,
                pady=4,
                sticky="nsew"
            )
            ttk.Label(
                box,
                text=str(value),
                font=("", 14, "bold")
            ).pack(
                padx=12,
                pady=6
            )

        severity = summary["open_by_severity"]

        if severity:
            order = [
                s for s in services.SEVERITIES
                if s in severity
            ]
            text = "   ".join(
                f"{s}: {severity[s]}"
                for s in order
            )
        else:
            text = "none"

        ttk.Label(
            self.stats,
            text=f"Unresolved by severity:  {text}"
        ).grid(
            row=1,
            column=0,
            columnspan=6,
            sticky="w",
            padx=6,
            pady=(2, 6)
        )

        self.figure.clear()

        regions = summary["open_by_region"]

        if regions:
            ax1 = self.figure.add_subplot(121)

            names = [r for r, _ in regions]
            counts = [n for _, n in regions]

            ax1.barh(
                names,
                counts,
                color="#2b6cb0"
            )

            ax1.invert_yaxis()
            ax1.set_xlabel("Unresolved outages")
            ax1.set_title("By region")
            ax1.xaxis.get_major_locator().set_params(
                integer=True
            )
        else:
            ax1 = self.figure.add_subplot(121)
            ax1.text(
                0.5,
                0.5,
                "No unresolved outages",
                ha="center",
                va="center"
            )
            ax1.set_axis_off()

        ax2 = self.figure.add_subplot(122)

        severity_order = [
            s for s in services.SEVERITIES
            if s in severity
        ]

        severity_counts = [
            severity[s]
            for s in severity_order
        ]

        if severity_order:
            ax2.bar(
                severity_order,
                severity_counts,
                color="#c53030"
            )
            ax2.set_xlabel("Severity")
            ax2.set_ylabel("Unresolved outages")
            ax2.set_title("By severity")
            ax2.yaxis.get_major_locator().set_params(
                integer=True
            )
        else:
            ax2.text(
                0.5,
                0.5,
                "No unresolved outages",
                ha="center",
                va="center"
            )
            ax2.set_axis_off()

        self.figure.tight_layout()
        self.canvas.draw()
