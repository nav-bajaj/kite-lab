"""2022-vintage NSE tickers mapped to the ticker the same company uses today.

The reconstruction stores each company under its CURRENT symbol, because that
is what price files are keyed on. NSE's March 2022 factsheets naturally use
the symbol each company traded under then. Comparing the two therefore needs
this bridge; without it 19 correct constituents look like mismatches.

Every pair was confirmed by reading the company name off the March 2022
Nifty 500 factsheet and matching it to the company name the reconstruction
carries. All constituents of the Nifty 50 / 100 / LargeMidcap 250 are also
Nifty 500 constituents, so the same table serves all four indices.
"""

TICKER_2022_TO_TODAY = {
    "ADANITRANS": "ADANIENSOL",   # Adani Transmission -> Adani Energy Solutions
    "AEGISCHEM": "AEGISLOG",      # Aegis Logistics ticker change
    "AMARAJABAT": "ARE&M",        # Amara Raja Batteries -> Energy & Mobility
    "CENTURYTEX": "ABREL",        # Century Textile -> Aditya Birla Real Estate
    "IBULHSGFIN": "SAMMAANCAP",   # Indiabulls Housing -> Sammaan Capital
    "IIFLWAM": "360ONE",          # IIFL Wealth -> 360 ONE WAM
    "KALPATPOWR": "KPIL",         # Kalpataru Power -> Kalpataru Projects Intl
    "L&TFH": "LTF",               # L&T Finance Holdings -> L&T Finance
    "LTI": "LTM",                 # L&T Infotech -> LTIMindtree -> LTM
    "MAHINDCIE": "CIEINDIA",      # Mahindra CIE -> CIE Automotive India
    "MCDOWELL-N": "UNITDSPR",     # United Spirits ticker change
    "MINDAIND": "UNOMINDA",       # Minda Industries -> UNO Minda
    "PEL": "PIRAMALFIN",          # Piramal Enterprises -> Piramal Finance
    "PVR": "PVRINOX",             # PVR -> PVR INOX
    "RBA": "RBA",                 # Restaurant Brands Asia, unchanged
    "SRTRANSFIN": "SHRIRAMFIN",   # Shriram Transport -> Shriram Finance
    "SUVENPHAR": "COHANCE",       # Suven Pharma -> Cohance Lifesciences
    "TATAMOTORS": "TMPV",         # became Tata Motors Passenger Vehicles
    "WABCOINDIA": "ZFCVINDIA",    # WABCO India -> ZF Commercial Vehicle
    "WELSPUNIND": "WELSPUNLIV",   # Welspun India -> Welspun Living
    "ZOMATO": "ETERNAL",          # Zomato -> Eternal
}


def to_today(sym: str) -> str:
    return TICKER_2022_TO_TODAY.get(sym, sym)
