#!/usr/bin/env python3
"""
healthTracket.py (robust plotting)
- Filters blank rows from CSV
- Robust date parsing for plotting
- Diagnostics printed to terminal
"""

import csv
import os
import sys
from datetime import datetime, date
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from typing import List, Dict
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

CSV_FILENAME = "health_data.csv"
FIELDNAMES = [
    "date",
    "weight_kg",
    "fat_kg",
    "muscle_mass_kg",
    "calories_kcal",
    "metabolic_age",
    "visceral_fat",
]

def get_csv_path() -> str:
    """Return path to CSV next to the .exe (or script if running in dev)."""
    if getattr(sys, 'frozen', False):
        # Running in a PyInstaller bundle
        base_dir = os.path.dirname(sys.executable)
    else:
        # Running as normal Python script
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, CSV_FILENAME)

def ensure_csv_schema():
    path = get_csv_path()
    if not os.path.exists(path):
        with open(path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
        return
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        current_fields = reader.fieldnames or []
        if current_fields == FIELDNAMES:
            return
        rows = list(reader)
    upgraded_rows = []
    for r in rows:
        new_row = {k: r.get(k, "") for k in FIELDNAMES}
        upgraded_rows.append(new_row)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(upgraded_rows)

def is_blank_row(r: Dict[str, str]) -> bool:
    return all(r.get(k, "").strip() == "" for k in FIELDNAMES)

def read_rows() -> List[Dict[str, str]]:
    path = get_csv_path()
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if not is_blank_row(r):
                rows.append(r)
    return rows

def parse_date_str(s: str) -> datetime:
    s = (s or "").strip()
    fmts = ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d %H:%M:%S")
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s)
    except Exception:
        raise ValueError(f"Unrecognized date: {s!r}")

def sort_rows_by_date(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    def _key(r):
        try:
            return parse_date_str(r.get("date", ""))
        except Exception:
            return datetime.max
    return sorted(rows, key=_key)

class HealthTracketApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Health Tracker")
        self.geometry("560x500")
        self.resizable(False, False)
        self.iconbitmap("health.ico")

        ensure_csv_schema()

        try:
            self.style = ttk.Style(self)
            if "clam" in self.style.theme_names():
                self.style.theme_use("clam")
        except Exception:
            pass

        self._build_ui()
    
    def _convert_to_kg(self, weight, percentage):
        return float(weight) * float(percentage) / 100

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}
        frm = ttk.Frame(self)
        frm.pack(fill="both", expand=True, **pad)

        ttk.Label(frm, text="Date (YYYY-MM-DD):").grid(row=0, column=0, sticky="e", **pad)
        self.date_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        ttk.Entry(frm, textvariable=self.date_var, width=20).grid(row=0, column=1, sticky="w", **pad)

        ttk.Label(frm, text="Weight (kg):").grid(row=1, column=0, sticky="e", **pad)
        self.weight_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.weight_var, width=20).grid(row=1, column=1, sticky="w", **pad)

        ttk.Label(frm, text="Fat mass %:").grid(row=2, column=0, sticky="e", **pad)
        self.fat_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.fat_var, width=20).grid(row=2, column=1, sticky="w", **pad)

        ttk.Label(frm, text="Muscle mass (kg):").grid(row=3, column=0, sticky="e", **pad)
        self.muscle_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.muscle_var, width=20).grid(row=3, column=1, sticky="w", **pad)

        ttk.Label(frm, text="Daily calories (kcal):").grid(row=4, column=0, sticky="e", **pad)
        self.calories_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.calories_var, width=20).grid(row=4, column=1, sticky="w", **pad)

        ttk.Label(frm, text="Metabolic age:").grid(row=5, column=0, sticky="e", **pad)
        self.meta_age_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.meta_age_var, width=20).grid(row=5, column=1, sticky="w", **pad)

        ttk.Label(frm, text="Visceral fat:").grid(row=6, column=0, sticky="e", **pad)
        self.vfat_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.vfat_var, width=20).grid(row=6, column=1, sticky="w", **pad)

        self.plot_vars = {
            "weight_kg": tk.BooleanVar(value=True),
            "fat_kg": tk.BooleanVar(value=True),
            "muscle_mass_kg": tk.BooleanVar(value=False),
            "calories_kcal": tk.BooleanVar(value=False),
            "metabolic_age": tk.BooleanVar(value=False),
            "visceral_fat": tk.BooleanVar(value=False),
        }
        cb_frame = ttk.LabelFrame(frm, text="Plot metrics")
        cb_frame.grid(row=0, column=2, rowspan=7, sticky="nsw", **pad)
        row = 0
        for key, text in [
            ("weight_kg", "Weight (kg)"),
            ("fat_kg", "Fat (kg)"),
            ("muscle_mass_kg", "Muscle mass (kg)"),
            ("calories_kcal", "Calories (kcal)"),
            ("metabolic_age", "Metabolic age"),
            ("visceral_fat", "Visceral fat"),
        ]:
            ttk.Checkbutton(cb_frame, text=text, variable=self.plot_vars[key]).grid(row=row, column=0, sticky="w")
            row += 1

        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=7, column=0, columnspan=3, sticky="ew", **pad)
        btn_frame.columnconfigure((0,1,2), weight=1)

        ttk.Button(btn_frame, text="Save Entry", command=self.save_entry).grid(row=0, column=0, sticky="ew", **pad)
        ttk.Button(btn_frame, text="Plot Selected", command=self.plot_selected).grid(row=0, column=1, sticky="ew", **pad)
        ttk.Button(btn_frame, text="Open CSV Location", command=self.open_csv_location).grid(row=0, column=2, sticky="ew", **pad)

        self.status_var = tk.StringVar(value=f"CSV: {get_csv_path()}")
        ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w").pack(fill="x", side="bottom")

    def save_entry(self):
        try:
            raw = {
                "date": self.date_var.get().strip(),
                "weight_kg": self.weight_var.get().strip(),
                "fat_kg": self.fat_var.get().strip(),
                "muscle_mass_kg": self.muscle_var.get().strip(),
                "calories_kcal": self.calories_var.get().strip(),
                "metabolic_age": self.meta_age_var.get().strip(),
                "visceral_fat": self.vfat_var.get().strip(),
            }
            missing = [k for k, v in raw.items() if v == ""]
            if missing:
                raise ValueError(f"Please fill all fields: {', '.join(missing)}")

            dval = raw["date"]
            try:
                dobj = datetime.strptime(dval, "%Y-%m-%d")
                dval = dobj.strftime("%Y-%m-%d")
            except ValueError:
                for fmt in ("%d/%m/%Y", "%Y/%m/%d"):
                    try:
                        dobj = datetime.strptime(dval, fmt)
                        dval = dobj.strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        continue
                else:
                    raise ValueError("Date must be in YYYY-MM-DD format (or DD/MM/YYYY, YYYY/MM/DD).")

            weight = float(raw["weight_kg"])
            fat = self._convert_to_kg(float(raw["fat_kg"]), weight)
            muscle = float(raw["muscle_mass_kg"])
            calories = float(raw["calories_kcal"])
            meta_age = int(float(raw["metabolic_age"]))
            vfat = int(float(raw["visceral_fat"]))

            ensure_csv_schema()
            path = get_csv_path()
            record = {
                "date": dval,
                "weight_kg": f"{weight:.3f}",
                "fat_kg": f"{fat:.3f}",
                "muscle_mass_kg": f"{muscle:.3f}",
                "calories_kcal": f"{calories:.0f}",
                "metabolic_age": f"{meta_age}",
                "visceral_fat": f"{vfat}",
            }
            with open(path, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
                writer.writerow(record)

            print("[healthTracket] appended:", record, "->", path)
            messagebox.showinfo("Saved", "Entry saved to CSV.")

            self.weight_var.set("")
            self.fat_var.set("")
            self.muscle_var.set("")
            self.calories_var.set("")
            self.meta_age_var.set("")
            self.vfat_var.set("")
        except Exception as e:
            messagebox.showerror("Validation error", str(e))

    def plot_selected(self):
        rows = sort_rows_by_date(read_rows())
        if not rows:
            messagebox.showwarning("No data", "No data to plot yet. Save an entry first.")
            return

        xs = []
        series = {key: [] for key in FIELDNAMES if key != "date"}
        skipped = 0
        for r in rows:
            try:
                dt = parse_date_str(r.get("date", ""))
            except Exception:
                skipped += 1
                continue
            xs.append(dt)
            for key in series.keys():
                val = (r.get(key, "") or "").strip()
                try:
                    series[key].append(float(val))
                except Exception:
                    series[key].append(float("nan"))

        metrics_to_plot = [k for k, v in self.plot_vars.items() if v.get()]
        if not metrics_to_plot:
            messagebox.showwarning("No metrics selected", "Select at least one metric to plot.")
            return

        if len(xs) <= 1:
            messagebox.showwarning("Too few points", "Only 1 usable row found. Check your CSV dates and values.")
        print(f"[healthTracket] plotting {len(xs)} points; skipped {skipped} rows due to bad dates.")

        plt.figure(figsize=(9, 5))
        for key in metrics_to_plot:
            plt.plot(xs, series[key], marker="o", label=key.replace("_", " ").title())

        plt.xlabel("Date")
        plt.ylabel("Value")
        plt.title("Health Metrics Over Time")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        ax = plt.gca()
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(mdates.AutoDateLocator()))
        plt.gcf().autofmt_xdate()

        plt.show()

    def open_csv_location(self):
        path = get_csv_path()
        folder = os.path.dirname(path)
        self.status_var.set(f"CSV: {path}")
        try:
            if os.name == "nt":
                os.startfile(folder)  # type: ignore
            elif os.name == "posix":
                opener = "open" if sys.platform == "darwin" else "xdg-open"
                import subprocess
                subprocess.Popen([opener, folder], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                messagebox.showinfo("Location", f"CSV folder:\\n{folder}")
        except Exception:
            messagebox.showinfo("Location", f"CSV folder:\\n{folder}")

if __name__ == "__main__":
    app = HealthTracketApp()
    app.mainloop()
