import csv
import json
import re
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

APP_NAME = "WG-Kassenabrechnung"
SAVE_FILE = Path.home() / ".wg_abrechnung.json"
MAX_EXACT = 16  # bis zu so vielen offenen Salden wird die Überweisungszahl exakt minimiert


# --------------------------------------------------------------------------
# Rechenlogik (ohne Oberfläche, gut testbar)
# --------------------------------------------------------------------------

def euro_to_cents(text):
    """Wandelt '12,50', '1.234,56', '1,234.56' oder '12.5' in Cent um.
    Mehrdeutige Eingaben wie '1.234' werden abgelehnt statt falsch gelesen."""
    value = text.strip().replace("€", "").replace(" ", "").replace("\u00a0", "")
    if not value:
        raise ValueError("Bitte einen Betrag eingeben.")
    if value.startswith("-"):
        raise ValueError("Beträge dürfen nicht negativ sein.")
    if "," in value and "." in value:
        # Das zuletzt stehende Zeichen ist das Dezimaltrennzeichen
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif "," in value:
        value = value.replace(",", ".")
    if not re.fullmatch(r"\d+(\.\d{1,2})?", value):
        raise ValueError(
            f"Ungültiger Geldbetrag: „{text.strip()}“.\n"
            "Bitte mit Komma und höchstens zwei Nachkommastellen eingeben, z. B. 1234,50."
        )
    whole, _, frac = value.partition(".")
    return int(whole) * 100 + int((frac + "00")[:2])


def money(cents):
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}{cents // 100:,}".replace(",", ".") + f",{cents % 100:02d} €"


def money_plain(cents):
    """Für CSV/Excel: 1234,50 ohne Tausenderpunkt und ohne €."""
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}{cents // 100},{cents % 100:02d}"


def _zero_sum_groups(items):
    """Zerlegt die Salden in die maximale Anzahl Gruppen, deren Summe jeweils 0 ist.
    Eine Gruppe mit k Personen braucht k-1 Überweisungen; je mehr Gruppen,
    desto weniger Überweisungen insgesamt (n - Gruppen)."""
    n = len(items)
    if n == 0:
        return []
    size = 1 << n
    sums = [0] * size
    for mask in range(1, size):
        low = mask & -mask
        sums[mask] = sums[mask ^ low] + items[low.bit_length() - 1][1]

    dp = [0] * size
    prev = [0] * size
    for mask in range(1, size):
        best, best_bit = -1, 0
        m = mask
        while m:
            low = m & -m
            m ^= low
            if dp[mask ^ low] > best:
                best, best_bit = dp[mask ^ low], low
        dp[mask] = best + (1 if sums[mask] == 0 else 0)
        prev[mask] = best_bit

    order = []
    mask = size - 1
    while mask:
        low = prev[mask]
        order.append(low.bit_length() - 1)
        mask ^= low
    order.reverse()

    groups, current, running = [], [], 0
    for idx in order:
        current.append(items[idx])
        running += items[idx][1]
        if running == 0:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups


def _settle_group(items):
    debtors = sorted(([n, b] for n, b in items if b > 0), key=lambda x: -x[1])
    creditors = sorted(([n, -b] for n, b in items if b < 0), key=lambda x: -x[1])
    transfers = []
    i = j = 0
    while i < len(debtors) and j < len(creditors):
        amount = min(debtors[i][1], creditors[j][1])
        if amount:
            transfers.append((debtors[i][0], creditors[j][0], amount))
        debtors[i][1] -= amount
        creditors[j][1] -= amount
        if debtors[i][1] == 0:
            i += 1
        if creditors[j][1] == 0:
            j += 1
    return transfers


def settle(balances):
    """balances: Liste (Name, Saldo in Cent); Summe muss 0 sein."""
    items = [(n, b) for n, b in balances if b != 0]
    groups = _zero_sum_groups(items) if len(items) <= MAX_EXACT else [items]
    transfers = []
    for group in groups:
        transfers.extend(_settle_group(group))
    return transfers


def calculate(rows):
    people = []
    total_spent = 0
    total_days = 0

    for name, amount_text, days_text in rows:
        name = name.strip()
        amount_text = amount_text.strip()
        days_text = days_text.strip()
        if not name:
            if amount_text and euro_to_cents(amount_text) != 0:
                raise ValueError("Bei einem Betrag fehlt der Name.")
            continue
        amount = euro_to_cents(amount_text)
        try:
            days = int(days_text)
        except ValueError:
            raise ValueError(f"Ungültige Tagesanzahl bei {name}.")
        if days < 0:
            raise ValueError(f"Die Tagesanzahl bei {name} darf nicht negativ sein.")
        people.append({"name": name, "spent": amount, "days": days})
        total_spent += amount
        total_days += days

    if len(people) < 2:
        raise ValueError("Bitte mindestens zwei Personen eintragen.")
    names = [p["name"].casefold() for p in people]
    if len(names) != len(set(names)):
        raise ValueError("Jeder Name darf nur einmal vorkommen.")
    if total_days <= 0:
        raise ValueError("Die Summe der Personentage muss größer als 0 sein.")

    # Anteile in Cent; größte Nachkommareste zuerst aufrunden, damit die Summe exakt stimmt.
    raw = [total_spent * p["days"] for p in people]
    shares = [v // total_days for v in raw]
    remainder = total_spent - sum(shares)
    order = sorted(range(len(people)), key=lambda i: raw[i] % total_days, reverse=True)
    for i in order[:remainder]:
        shares[i] += 1

    for p, share in zip(people, shares):
        p["share"] = share
        p["balance"] = share - p["spent"]  # positiv: muss zahlen, negativ: bekommt Geld

    transfers = settle([(p["name"], p["balance"]) for p in people])
    return people, total_spent, total_days, transfers


# --------------------------------------------------------------------------
# Oberfläche
# --------------------------------------------------------------------------

def balance_text(bal):
    if bal > 0:
        return f"muss zahlen: {money(bal)}"
    if bal < 0:
        return f"bekommt: {money(-bal)}"
    return "ausgeglichen"


def csv_safe(text):
    # Schutz vor Formel-Interpretation in Excel
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text


class App:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("880x760")
        self.root.minsize(760, 640)
        self.rows = []  # Liste von (name_var, amount_var, days_var)
        self.last_result = None

        title_font = tkfont.nametofont("TkDefaultFont").copy()
        title_font.configure(size=18, weight="bold")
        bold_font = tkfont.nametofont("TkDefaultFont").copy()
        bold_font.configure(weight="bold")

        main = ttk.Frame(root, padding=12)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text=APP_NAME, font=title_font).pack(anchor="w")
        ttk.Label(main, text="Name, persönliche Ausgaben und Anzahl der Tage eintragen.").pack(
            anchor="w", pady=(2, 10))

        input_frame = ttk.LabelFrame(main, text="Personen", padding=8)
        input_frame.pack(fill="x")
        canvas = tk.Canvas(input_frame, height=190, highlightthickness=0)
        scrollbar = ttk.Scrollbar(input_frame, orient="vertical", command=canvas.yview)
        self.rows_frame = ttk.Frame(canvas)
        self.rows_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.rows_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="x", expand=True)
        scrollbar.pack(side="right", fill="y")

        controls = ttk.Frame(main)
        controls.pack(fill="x", pady=8)
        ttk.Button(controls, text="+ Person hinzufügen", command=self.add_row).pack(side="left")
        ttk.Button(controls, text="Berechnen", command=self.run_calculation).pack(side="left", padx=8)
        ttk.Button(controls, text="CSV exportieren", command=self.export_csv).pack(side="left")
        ttk.Button(controls, text="Ergebnis kopieren", command=self.copy_result).pack(side="left", padx=8)

        self.summary = ttk.Label(main, text="Noch keine Berechnung durchgeführt.", font=bold_font)
        self.summary.pack(anchor="w", pady=(8, 6))

        result_frame = ttk.LabelFrame(main, text="Abrechnung pro Person", padding=8)
        result_frame.pack(fill="both", expand=True, pady=(0, 8))
        cols = ("name", "spent", "days", "share", "balance")
        self.tree = ttk.Treeview(result_frame, columns=cols, show="headings", height=7)
        headings = [("name", "Person"), ("spent", "Ausgegeben"), ("days", "Tage"),
                    ("share", "Fairer Anteil"), ("balance", "Saldo")]
        widths = [170, 110, 60, 120, 170]
        for (col, title), width in zip(headings, widths):
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor="w" if col == "name" else "e")
        self.tree.pack(fill="both", expand=True)

        transfer_frame = ttk.LabelFrame(
            main, text="Wer muss wem wie viel überweisen? (kleinstmögliche Anzahl an Überweisungen)", padding=8)
        transfer_frame.pack(fill="both", expand=True)
        self.transfer_list = tk.Listbox(transfer_frame, height=7)
        self.transfer_list.pack(fill="both", expand=True)

        self.load_state()
        if not self.rows:
            self.add_row("Person 1", "0,00", "30")
            self.add_row("Person 2", "0,00", "30")
        self.render_rows()

        root.bind("<Return>", lambda e: self.run_calculation())
        root.protocol("WM_DELETE_WINDOW", self.on_close)

    # --- Eingabezeilen ---------------------------------------------------
    def add_row(self, name="", amount="0,00", days="30"):
        self.rows.append((tk.StringVar(value=name), tk.StringVar(value=amount), tk.StringVar(value=days)))
        self.render_rows()

    def remove_row(self, index):
        if len(self.rows) <= 2:
            messagebox.showinfo("Hinweis", "Mindestens zwei Personen werden gebraucht.")
            return
        del self.rows[index]
        self.render_rows()

    def render_rows(self):
        for w in self.rows_frame.winfo_children():
            w.destroy()
        for col, text in enumerate(("Name", "Ausgaben (€)", "Tage")):
            ttk.Label(self.rows_frame, text=text).grid(row=0, column=col, sticky="w", padx=4)
        for r, (name, amount, days) in enumerate(self.rows, start=1):
            ttk.Entry(self.rows_frame, textvariable=name, width=26).grid(row=r, column=0, padx=4, pady=2)
            ttk.Entry(self.rows_frame, textvariable=amount, width=16).grid(row=r, column=1, padx=4, pady=2)
            ttk.Entry(self.rows_frame, textvariable=days, width=8).grid(row=r, column=2, padx=4, pady=2)
            ttk.Button(self.rows_frame, text="Entfernen",
                       command=lambda i=r - 1: self.remove_row(i)).grid(row=r, column=3, padx=4)

    # --- Speichern der letzten Eingaben -----------------------------------
    def load_state(self):
        try:
            data = json.loads(SAVE_FILE.read_text(encoding="utf-8"))
            for name, amount, days in data["rows"]:
                self.rows.append((tk.StringVar(value=str(name)), tk.StringVar(value=str(amount)),
                                  tk.StringVar(value=str(days))))
        except Exception:
            self.rows = []

    def save_state(self):
        try:
            data = {"rows": [[n.get(), a.get(), d.get()] for n, a, d in self.rows]}
            SAVE_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def on_close(self):
        self.save_state()
        self.root.destroy()

    # --- Berechnung -------------------------------------------------------
    def run_calculation(self):
        try:
            rows = [(n.get(), a.get(), d.get()) for n, a, d in self.rows]
            people, total, days, transfers = calculate(rows)
        except ValueError as exc:
            messagebox.showerror("Eingabefehler", str(exc))
            return

        self.save_state()
        self.last_result = (people, total, days, transfers)
        for item in self.tree.get_children():
            self.tree.delete(item)
        for p in people:
            self.tree.insert("", "end", values=(p["name"], money(p["spent"]), p["days"],
                                                money(p["share"]), balance_text(p["balance"])))
        per_day = (2 * total + days) // (2 * days)  # kaufmännisch gerundet
        self.summary.config(
            text=f"Gesamtausgaben: {money(total)}    |    Personentage: {days}    |    "
                 f"Ø pro Personentag: {money(per_day)}")
        self.transfer_list.delete(0, "end")
        if transfers:
            for debtor, creditor, amount in transfers:
                self.transfer_list.insert("end", f"{debtor}  →  {creditor}:  {money(amount)}")
            self.transfer_list.insert("end", "")
            self.transfer_list.insert("end", f"Anzahl der Überweisungen: {len(transfers)}")
        else:
            self.transfer_list.insert("end", "Es sind keine Überweisungen nötig.")

    def result_text(self):
        if not self.last_result:
            return ""
        people, total, days, transfers = self.last_result
        lines = [f"Gesamtausgaben: {money(total)} | Personentage: {days}", "", "Abrechnung:"]
        for p in people:
            lines.append(f"{p['name']}: ausgegeben {money(p['spent'])}, "
                         f"fairer Anteil {money(p['share'])}, {balance_text(p['balance'])}")
        lines += ["", "Überweisungen:"]
        lines += [f"{a} -> {b}: {money(v)}" for a, b, v in transfers] or ["Keine Überweisungen nötig."]
        lines.append(f"Anzahl der Überweisungen: {len(transfers)}")
        return "\n".join(lines)

    def copy_result(self):
        text = self.result_text()
        if not text:
            messagebox.showinfo("Hinweis", "Bitte zuerst berechnen.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        messagebox.showinfo("Kopiert", "Die Abrechnung wurde in die Zwischenablage kopiert.")

    def export_csv(self):
        if not self.last_result:
            messagebox.showinfo("Hinweis", "Bitte zuerst berechnen.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV-Datei", "*.csv")],
                                            initialfile="wg_abrechnung.csv")
        if not path:
            return
        people, total, days, transfers = self.last_result
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(["Person", "Ausgegeben (€)", "Tage", "Fairer Anteil (€)", "Saldo (€)"])
                for p in people:
                    writer.writerow([csv_safe(p["name"]), money_plain(p["spent"]), p["days"],
                                     money_plain(p["share"]), money_plain(p["balance"])])
                writer.writerow([])
                writer.writerow(["Überweisungen"])
                writer.writerow(["Von", "An", "Betrag (€)"])
                for a, b, amount in transfers:
                    writer.writerow([csv_safe(a), csv_safe(b), money_plain(amount)])
        except OSError as exc:
            messagebox.showerror("Export fehlgeschlagen", str(exc))
            return
        messagebox.showinfo("Export", "CSV-Datei wurde gespeichert.")


def main():
    if sys.platform == "win32":
        try:  # scharfe Darstellung auf hochauflösenden Displays
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
