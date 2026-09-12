"""Company identity over time.

A company is a connected component over (isin, symbol) trading windows,
joined by (a) a shared ISIN, (b) a dated rename edge old->new from NSE's
symbol-change master, the PREVCLOSE detector, or the hand list below. ISIN
alone is not enough: a rename that coincides with a face-value change gives
the old and new ticker different ISINs (COLGATE INE259A01014 -> COLPAL
INE259A01022), and a symbol alone is not enough because tickers get reused.

LINE_OVERRIDES fix the reconstruction where it attached a historical member
to the wrong listed line after a demerger: the 2006 "Bajaj Auto" is the
company that trades today as BAJAJHLDNG, not the 2008 spin-off BAJAJ-AUTO.
Before the cutover date the member is resolved to the override symbol.
"""
from __future__ import annotations

import pandas as pd

from data_pipeline.master_store import MASTER  # noqa: E402

# (old, new, date) renames neither NSE's master nor the detector carries;
# each verified 2026-09-10 against symbol_master.csv windows
HAND_RENAMES = [
    ("CEAT", "CEATLTD", "2008-02-01"),          # ISIN ...012 -> ...020, 5-week gap, face-value change
    ("MANALIPET", "MANALIPETC", "2006-12-06"),  # ISIN ...016 -> ...024
    ("PRICOL", "PRICOLLTD", "2017-02-10"),      # scheme of arrangement, new ISIN INE726V01018
    ("GESHIPPING", "GESHIP", "2006-11-27"),     # demerger of Great Offshore, new ISIN ...032
    ("ELGIRUBBER", "ELGIRUBCO", "2011-08-10"),  # detector has ELGITYRE->ELGIRUBBER; this closes the chain
    ("SUPPETRO", "SPLPETRO", "2022-05-24"),     # ISIN ...017 -> ...025
    ("GUJFLUORO", "GFLLIMITED", "2019-07-25"),  # detector already has it; kept explicit
    ("KIRLOSOIL", "KIRLOSIND", "2010-04-21"),   # Kirloskar Oil Engines -> Kirloskar Industries (renamed line)
    ("LGBROS", "LGBBROSLTD", "2010-03-15"),
    ("GTNIND", "GTNINDS", "2021-03-15"),
    ("NAHARSPG", "NAHARSPING", "2007-01-24"),
    ("NAHAREXP", "NAHARPOLY", "2007-01-24"),    # Nahar Exports -> Nahar Poly Films
    ("SHYAMTELE", "SHYAMTEL", "2006-07-25"),
    ("RAMANEWSPR", "RAMANEWS", "2006-07-21"),
    ("CHEMPLAST", "CHEMPLASTS", "2021-08-24"),  # delisted 2012, re-IPO 2021 as Chemplast Sanmar; same business, see note
    # NOT ("MAX","MAXIND"): MAX became MFSL in 2016 (NSE master has it); MAXIND is a new line.
    # Encoding that edge merged two live companies and interleaved their rows.
    # NOT ("KBL","KIRLOSBROS"): one company, but the two windows are six weeks and
    # +29% apart (KBL 2010-03-08 at 260.55, KIRLOSBROS 2010-04-20 at 337.35), so
    # joining them would write a phantom return into the series. The pre-2010
    # membership spells are repointed at KBL through LINE_OVERRIDES instead.
    # NOT ("HEXAWARE","HEXT"): same company, but taken private in 2020 and re-listed
    # in 2025 — a four-year hole that the panel loader would forward-fill across for
    # a name both books can hold today. Repointed through LINE_OVERRIDES.
]

# (symbol, date) where one ticker's ISIN changed mid-life with no rename to
# follow, so ISIN cannot join the two windows and neither can a rename edge.
# Each verified against isin_names.csv: the same filing name on both ISINs and
# contiguous trading sessions across the date.
ISIN_CHANGES = [
    ("GUJGASLTD", "2019-01-16"),   # INE844O01022 -> INE844O01030, no gap; without this the
                                   # 2015-2019 half is a separate company and the canonical
                                   # GUJENERGY series starts in 2019
]

# membership symbol -> [(before_date, historical symbol)]; the member before
# `before_date` is the line that trades as `historical symbol` (or its chain)
LINE_OVERRIDES = {
    "BAJAJ-AUTO": [("2008-05-26", "BAJAJHLDNG")],   # pre-demerger Bajaj Auto = today's Bajaj Holdings (INE118A01012)
    "TIINDIA":    [("2017-11-02", "TUBEINVEST")],   # pre-2017 Tube Investments -> TIFIN -> CHOLAHLDNG
    "KPITTECH":   [("2019-04-22", "KPIT")],         # pre-2019 KPIT (Cummins) = today's BSOFT line
    "PIRAMALFIN": [("2025-11-07", "PEL")],          # Piramal Enterprises line: NICOLASPIR -> PIRHEALTH -> PEL
    "FLUOROCHEM": [("2019-10-16", "GUJFLUORO")],    # pre-demerger Gujarat Fluorochemicals = GFLLIMITED line
    "GATEWAY":    [("2022-03-22", "GDL")],          # Gateway Distriparks, new ISIN on the 2022 merger
    "MAXIND":     [("2016-02-26", "MAX")],          # pre-2016 Max India = the MAX line
    "GUJGASLTD":  [("2015-09-15", "GUJRATGAS")],    # old Gujarat Gas (INE374A01029) merged into GSPC Distribution; new line listed 2015-09-15
    "GUJENERGY":  [("2015-09-15", "GUJRATGAS")],    # same company, renamed Gujarat Energy 2026-07
    "DALBHARAT":  [("2019-01-22", "DALMIABHA")],    # old Dalmia Bharat merged into Odisha Cement, relisted 2019 as DALBHARAT (INE00R701025)
    "HEXT":       [("2025-02-19", "HEXAWARE")],     # Hexaware delisted 2020-10-30 (INE093A01033), re-listed 2025-02-19 (INE093A01041); nse500 already carries the old spell as HEXAWARE
    "ORCHPHARMA": [("2020-11-03", "ORCHIDCHEM")],   # Orchid Chemicals -> Orchid Pharma (INE191A01019), relisted after IBC 2020-11-03 (INE191A01027); nse500 carries the old spell as ORCHIDPHAR
    "KIRLOSBROS": [("2010-04-20", "KBL")],          # Kirloskar Brothers traded as KBL until 2010-03-08 (INE732A01028); the KIRLOSBROS line (INE732A01036) starts 2010-04-20
}


class Identity:
    def __init__(self, windows: pd.DataFrame | None = None, renames: pd.DataFrame | None = None,
                 detected: pd.DataFrame | None = None):
        w = windows if windows is not None else pd.read_csv(f"{MASTER}/symbol_master.csv", parse_dates=["first_seen", "last_seen"])
        w = w.reset_index(drop=True)
        self.w = w
        n = len(w)
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]; x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra
        # (a) shared real ISIN
        for _, g in w[~w["isin"].str.startswith("SYM:")].groupby("isin"):
            idx = list(g.index)
            for j in idx[1:]:
                union(idx[0], j)
        # (b) rename edges: old's last window before the date <-> new's first window after
        by_sym = {s: g.sort_values("first_seen") for s, g in w.groupby("symbol")}
        edges = []
        chg = renames if renames is not None else pd.read_csv(f"{MASTER}/symbol_changes.csv", parse_dates=["date"])
        edges += [(r.old, r.new, r.date) for r in chg.itertuples()]
        det = detected if detected is not None else pd.read_csv(f"{MASTER}/symbol_renames_detected.csv", parse_dates=["t1"])
        edges += [(r.old, r.new, r.t1) for r in det.itertuples()]
        edges += [(o, nw, pd.Timestamp(d)) for o, nw, d in HAND_RENAMES]
        edges += [(s, s, pd.Timestamp(d)) for s, d in ISIN_CHANGES]   # old and new window of one ticker
        self.n_edges = 0
        for old, new, d in edges:
            if old not in by_sym or new not in by_sym:
                continue
            a = by_sym[old]; a = a[a["first_seen"] <= d + pd.Timedelta(days=45)]
            b = by_sym[new]; b = b[b["last_seen"] >= d - pd.Timedelta(days=45)]
            if a.empty or b.empty:
                continue
            union(a.index[-1], b.index[0]); self.n_edges += 1
        self.comp = [find(i) for i in range(n)]
        w["company"] = self.comp
        # audit: two different tickers of one company trading on the same days
        # means a wrong merge (a reused symbol, a bad edge); log, do not hide
        self.overlaps = []
        for c, g in w.groupby("company"):
            if g["symbol"].nunique() < 2:
                continue
            g = g.sort_values("first_seen")
            for i in range(1, len(g)):
                prev = g.iloc[:i]
                cur = g.iloc[i]
                ov = prev[(prev["last_seen"] - cur["first_seen"]).dt.days > 5]
                ov = ov[ov["symbol"] != cur["symbol"]]
                for o in ov.itertuples():
                    self.overlaps.append((o.symbol, cur["symbol"], str(max(o.first_seen, cur["first_seen"]).date()),
                                          str(min(o.last_seen, cur["last_seen"]).date())))
        self.by_company = {c: g for c, g in w.groupby("company")}
        self.company_of_symbol = {}
        for r in w.itertuples():
            self.company_of_symbol.setdefault(r.symbol, set()).add(r.company)

    def companies(self, symbol: str) -> set:
        return self.company_of_symbol.get(symbol, set())

    def symbols_on(self, symbol: str, day) -> list:
        """Symbols any of `symbol`'s companies traded under on `day`."""
        out = []
        for c in self.companies(symbol):
            g = self.by_company[c]
            out += list(g[(g["first_seen"] <= day) & (g["last_seen"] >= day)]["symbol"])
        return out

    def canonical(self, symbol: str) -> str:
        """The symbol the company trades under most recently (price-file key)."""
        best = None
        for c in self.companies(symbol):
            g = self.by_company[c].sort_values("last_seen")
            cand = g.iloc[-1]
            if best is None or cand["last_seen"] > best["last_seen"]:
                best = cand
        return best["symbol"] if best is not None else symbol

    @staticmethod
    def override(symbol: str, day) -> str:
        for before, hist in LINE_OVERRIDES.get(symbol, []):
            if day < pd.Timestamp(before):
                return hist
        return symbol
