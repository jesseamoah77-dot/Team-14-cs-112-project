"""Small shared building blocks so the tab modules don't each reinvent a table."""

import tkinter as tk
from tkinter import ttk


def make_table(parent, columns, widths=None):
    """
    A Treeview in 'headings' mode with a vertical scrollbar, packed to fill.

    columns: list of (key, heading) pairs. Returns the tree; callers insert rows with
    tree.insert("", "end", values=(...)) in the same column order.
    """
    frame = ttk.Frame(parent)
    frame.pack(fill="both", expand=True, padx=8, pady=(4, 8))

    keys = [key for key, _ in columns]
    tree = ttk.Treeview(frame, columns=keys, show="headings", selectmode="browse")
    for i, (key, heading) in enumerate(columns):
        tree.heading(key, text=heading)
        tree.column(key, width=(widths[i] if widths else 120), anchor="w")

    scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    return tree


def fill_table(tree, rows, keys):
    """Replace a table's contents with fresh rows (list of sqlite3.Row)."""
    tree.delete(*tree.get_children())
    for row in rows:
        tree.insert("", "end", values=[row[k] if row[k] is not None else "" for k in keys])


def selected_id(tree, column_index=0):
    """The integer id in the given column of the selected row, or None."""
    selection = tree.selection()
    if not selection:
        return None
    return int(tree.item(selection[0], "values")[column_index])


def labelled_entry(parent, row, label, width=38, show=None):
    ttk.Label(parent, text=label).grid(row=row, column=0, sticky="e", padx=6, pady=4)
    entry = ttk.Entry(parent, width=width, show=show)
    entry.grid(row=row, column=1, sticky="w", padx=6, pady=4)
    return entry


def labelled_combo(parent, row, label, values, width=36):
    ttk.Label(parent, text=label).grid(row=row, column=0, sticky="e", padx=6, pady=4)
    combo = ttk.Combobox(parent, values=values, width=width, state="readonly")
    combo.grid(row=row, column=1, sticky="w", padx=6, pady=4)
    return combo


def labelled_text(parent, row, label, width=40, height=4):
    ttk.Label(parent, text=label).grid(row=row, column=0, sticky="ne", padx=6, pady=4)
    text = tk.Text(parent, width=width, height=height)
    text.grid(row=row, column=1, sticky="w", padx=6, pady=4)
    return text
