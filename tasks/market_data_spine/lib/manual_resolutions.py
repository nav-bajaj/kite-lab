"""Hand-confirmed name -> ISIN mappings for reconstruction leftovers whose
filing name differs from the name NSE used in the index sheet.

Each entry was confirmed 2026-09-10 against data/master/isin_names.csv: the
ISIN exists, its filing name is the renamed or re-spelt company, and its
filing window overlaps the index spell. The strict matcher refuses these on
purpose (it scored Dena Bank onto D B Corp at 1.0 once), so they are
encoded rather than fuzzed. The comment is the evidence; do not add an entry
without one.

SYMBOL_HINTS are for companies that filed under no matching name at all
(delisted early, or the API carries only a later name). They are resolved
by looking the expected symbol up in the bhavcopy, which yields the ISIN,
and are only accepted if that ISIN traded throughout the spell.
"""

BY_NAME = {
    # index-sheet name                                  ISIN            filing name / symbol seen
    "AstraZenca Pharma India Ltd.":                    "INE203A01020",  # AstraZeneca Pharma India Limited / ASTRAZEN (sheet typo)
    "Adlabs Entertainment Ltd.":                       "INE172N01012",  # Imagicaaworld Entertainment Limited / IMAGICAA (renamed)
    "Amtek India Ltd.":                                "INE068D01021",  # Castex Technologies Limited / CASTEXTECH (renamed 2015)
    "Bajaj Hindusthan Ltd.":                           "INE306A01021",  # Bajaj Hindusthan Sugar Limited / BAJAJHIND
    "Ballarpur Industries Ltd.":                       "INE294A01037",  # Ballarpur Industries Limited / BALLARPUR (post-2008 ISIN)
    "Bhushan Steel Ltd.":                              "INE824B01021",  # Tata Steel Bsl Limited / TATASTLBSL (renamed after IBC)
    "D B Realty Ltd.":                                 "INE879I01012",  # Valor Estate Limited / DBREALTY
    "Eros Intl Media Ltd.":                            "INE416L01017",  # Eros International Media Limited / EROSMEDIA
    "Financial Technologies (India) Ltd.":             "INE111B01023",  # 63 moons technologies limited / 63MOONS
    "Flexituff International Ltd.":                    "INE060J01017",  # Flexituff Ventures International Limited / FLEXITUFF
    "Gati Ltd.":                                       "INE152B01027",  # Allcargo Gati Limited / ACLGATI (earlier GATI)
    "Geojit BNP Paribas Financial Services Ltd.":      "INE007B01023",  # Geojit Financial Services Limited / GEOJITFSL
    "IIFL Holdings Ltd.":                              "INE530B01024",  # IIFL Finance Limited / IIFL
    "India Infoline Ltd.":                             "INE530B01024",  # IIFL Finance Limited / IIFL (same entity, earlier name)
    "Indiabulls Securities Ltd.":                      "INE274G01010",  # Dhani Services Limited / DHANI
    "International Paper APPM Ltd.":                   "INE435A01028",  # ANDHRA PAPER LIMITED / ANDHRAPAP
    "KSB Pumps Ltd.":                                  "INE999A01015",  # Ksb Limited / KSB
    "Magma Fincorp Ltd.":                              "INE511C01022",  # Poonawalla Fincorp Limited / POONAWALLA
    "Nava Bharat Ventures Ltd.":                       "INE725A01022",  # NAVA LIMITED / NAVA
    "Pipavav Defence and Offshore Engineering Company Ltd.": "INE542F01012",  # Reliance Naval and Engineering / RNAVAL
    "Puravankara Projects Ltd.":                       "INE323I01011",  # Puravankara Limited / PURVA
    "SKS Microfinance Ltd.":                           "INE180K01011",  # Bharat Financial Inclusion Limited / BHARATFIN
    "SML Isuzu Ltd.":                                  "INE294B01019",  # SML Mahindra Limited / SMLMAH (earlier SMLISUZU)
    "Sequent Scientific Ltd.":                         "INE807F01027",  # Viyash Scientific Limited / VIYASH (earlier SEQUENT)
    "Shilpi Cable Tech Ltd.":                          "INE510K01019",  # Shilpi Cable Technologies Limited / SHILPI
    "Strides Arcolab Ltd.":                            "INE939A01011",  # Strides Pharma Science Limited / STAR
    "Strides Shasun Ltd.":                             "INE939A01011",  # same entity, 2015-2018 name
    "Tata Sponge Iron Ltd.":                           "INE674A01014",  # Tata Steel Long Products Limited / TATASTLLP
    "Techno Elt & Eng Co. Ltd.":                       "INE286K01024",  # Techno Electric & Engineering / TECHNO (pre-2019 entity)
    "Tata Motors Ltd DVR":                             "IN9155A01012",  # Tata Motors Limited (DVR line) / TATAMTRDVR
    "Mahindra CIE Automotive Ltd.":                    "INE536H01010",  # CIE Automotive India Limited / CIEINDIA
    "Smithkline Beecham Consumer Healthcare Ltd.":     "INE264A01014",  # GlaxoSmithKline Consumer Healthcare / GSKCONS
    "Tube Investments of India Ltd.-Old":              "INE149A01025",  # Tube Investments of India Limited / TUBEINVEST (pre-demerger)
    "Bajaj Corp Ltd.":                                 "INE933K01021",  # Bajaj Consumer Care Limited / BAJAJCON
    "Jyothy Laboratories Ltd.":                        "INE668F01031",  # Jyothy Labs Limited / JYOTHYLAB
    "Videsh Sanchar Nigam Ltd.":                       "INE151A01013",  # Tata Communications Limited / TATACOMM
}

# name -> expected NSE symbol(s) during the spell; resolved via bhavcopy ISIN
SYMBOL_HINTS = {
    "8K Miles Soft Services Ltd.":                     ["8KMILES"],
    "Agro Tech Foods Ltd.":                            ["ATFL"],
    "Clariant Chemicals (India) Ltd.":                 ["CLNINDIA"],
    "Gammon Infrastructure Projects Ltd.":             ["GAMMNINFRA"],
    "HSIL Ltd.":                                       ["HSIL"],
    "Hitachi Home & Life Solutions (India) Ltd.":      ["HITACHIHOM", "JCHAC"],
    "Hotel Leela Venture Ltd.":                        ["HOTELEELA"],
    "ITD Cementation India Ltd.":                      ["ITDCEM"],
    "Indiabulls Integrated Services Ltd.":             ["IBULISL", "YAARII"],
    "Indiabulls Real Estate Ltd.":                     ["IBREALEST"],
    "Oswal Chemicals & Fertilizers Ltd.":              ["BINDALAGRO", "OSWALCHEM"],
    "Sona Koyo Steering Systems Ltd.":                 ["SONAKOYO", "JTEKTINDIA"],
    "Styrolution ABS (India) Ltd.":                    ["INEOSSTYRO", "STYROLUTION"],
    "Tide Water Oil (India) Ltd.":                     ["TIDEWATER"],
    # 2006-era members whose filing name is a later corporate name; the symbol
    # is what the bhavcopy shows in the spell and is checked against it
    "AGC Networks Ltd.":                               ["AGCNET", "AGCNETWRK", "TATATELE", "BLACKBOX"],
    "Accelya Kale Solutions Ltd.":                     ["KALE", "ACCELYA", "KALECONSUL"],
    "Birla Ericsson Optical Ltd.":                     ["BIRLAERIC", "BIRLACABLE"],
    "Central India Polyesters Ltd.":                   ["CIPL", "CENTRALPOL"],
    "Cosmo Films Ltd.":                                ["COSMOFILMS", "COSMOFIRST"],
    "Dwarikesh Sugar Industrial Ltd.":                 ["DWARKESH"],
    "Future Retail Ltd.":                              ["PANTALOONR", "FRETAIL", "FUTURERET"],
    "GSL Nova Petrochemicals Ltd.":                    ["GSLNOVA", "NOVAPETRO"],
    "Himachal Fut Com Ltd.- Old":                      ["HFCL", "HIMACHLFUT"],
    "Hinduja Ventures Ltd.":                           ["HINDUJAVEN", "HINDUJATMT", "NXTDIGITAL"],
    "Jubilant Life Sciences Ltd.":                     ["JUBILANT", "JUBLPHARMA"],
    "MRO-TEK Ltd.":                                    ["MRO-TEK", "MROTEK"],
    "Nagarjuna Fertilizers & Chemicals Ltd.":          ["NAGARFERT", "NAGAFERT"],
    "Narmada Chematur Petrochemicals Ltd.":            ["NARMADACHE", "NCPL"],
    "Orchid Chemicals & Pharmaceuticals Ltd.":         ["ORCHIDCHEM", "ORCHIDPHAR"],
    "Orient Information Technologies Ltd.":            ["ORIENTINFO"],
    "Paper Products Ltd.":                             ["PAPERPROD", "HUHTAMAKI"],
    "Pudumjee Pulp & Paper Mills Ltd.":                ["PUDUMJEEPU", "PDPL"],
    "Rane Brake Linings Ltd. -old":                    ["RANEBRAKE", "RBL"],
    "Rane Engine Valves Ltd. -old":                    ["RANEENGINE", "REVL"],
    "Sri Adhikari Brothers Television Network Ltd.":   ["SABTN", "SABTNL"],
    "Summit Securities Ltd.- Old":                     ["SUMMITSEC"],
    "Sundaram Clayton Ltd.- OLD":                      ["SUNCLAYTON", "SUNCLAYLTD"],
    "UCAL Fuel Systems Ltd.":                          ["UCALFUEL", "UCAL"],
    "Zenith Computer Ltd.":                            ["ZENITHCOMP"],
    "Zuari Global Ltd.":                               ["ZUARIAGRO", "ZUARIGLOB", "ZUARI"],
    "Television Eighteen India Ltd.":                  ["TV-18", "TV18"],
    "Gujarat NRE Coke Ltd.":                           ["GUJNRECOKE"],
    "Gujarat Gas Co. Ltd.":                            ["GUJRATGAS", "GUJGAS", "GUJGASLTD"],
    "Essar Steel Ltd.":                                ["ESSARSTEEL"],
    "Eicher Ltd.":                                     ["EICHERLTD", "EICHERMOT"],
}
