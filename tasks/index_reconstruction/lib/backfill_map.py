"""Symbols recovered for ex-members after the first resolution pass.

Two mechanisms, both auditable:

  rename-chase - the company was renamed while OUT of scope of the first
    pass; following renames.py forward from the old name reaches a name that
    today's constituent file or the Kite dump does know.

  name-match - strict token matching against the NSE and BSE cash rows of the
    Kite instruments dump. BSE carries full company names where NSE truncates
    them, which is what makes the match possible. Strict means every token on
    both sides must be accounted for and abbreviations must be >=4 characters:
    a looser rule mapped "Corporation Bank" onto Indian Bank and "Dena Bank"
    onto D B Corp before it was tightened.

"have_prices" marks symbols with a daily price file already on disk. The rest
would need a backfill before they can be used in a backtest.

Everything here was eyeballed against the dump name shown in the comment.
Companies still missing after this are overwhelmingly pre-2010 delistings
that no live instrument master carries.
"""

BACKFILL_SYMBOLS = {
    'ATV Projects India Ltd.': 'ATVPR',                                   # name-match | ATV PROJECTS INDIA
    'Allied Digital Services Ltd.': 'ADSL',                               # name-match | ALLIED DIGITAL SERV.
    'Alstom T&D India Ltd.': 'GVT&D',                                     # rename-chase have_prices | GE VERNOVA T&D INDIA
    'Ansal Properties & Infrastructure Ltd.': 'ANSALAPI',                 # name-match | ANSAL PROP & INFRA
    'B L Kashyap & Sons Ltd.': 'BLKASHYAP',                               # name-match | B.L.KASHYAP & SON
    'Banco Products (India) Ltd.': 'BANCOINDIA',                          # name-match have_prices | BANCO PRODUCTS (I)
    'Baroda Rayon Corporation Ltd.': 'BARODARY',                          # name-match | BARODA RAYON CORPORATION
    'Bhansali Engineering Polymers Ltd.': 'BEPL',                         # name-match | BHANSALI ENG. POLYMERS LT
    'Caprihans India Ltd.': 'CAPRIHANS',                                  # name-match | CAPRIHANS INDIA
    'Chowgule Steamships Ltd.': 'CHOWGULSTM',                             # name-match | CHOWGULE STEAMSHIPS
    'Coffee Day Enterprises Ltd.': 'COFFEEDAY',                           # name-match | COFFEE DAY ENTERPRISE
    'Crompton Greaves Ltd.': 'CGPOWER',                                   # rename-chase have_prices | CG POWER AND IND SOL
    'Cybertech Systems & Software Ltd.': 'CYBERTECH',                     # name-match | CYBERTECH SYSTEMS & SOFTW
    'D.S. Kulkarni Developers Ltd.': 'DSKULKARNI',                        # name-match | DS KULKARNI DEVELOPERS L
    'Dalmia Bharat Sugar and Industries Ltd.': 'DALMIASUG',               # name-match | DALMIA BHARAT SUG IN
    'Donear Industries Ltd.': 'DONEAR',                                   # name-match | DONEAR IND.
    'Entertainment Network India Ltd.': 'ENIL',                           # name-match | ENTERTAIN NET. IND.
    'Essel Propack Ltd.': 'EPL',                                          # rename-chase have_prices | EPL
    'Eveready Industries India Ltd.': 'EVEREADY',                         # name-match | EVEREADY INDS. IND.
    'Everest Kanto Cylinder Ltd.': 'EKC',                                 # name-match | EVEREST KANTO CYLINDERLTD
    'FGP Ltd.': 'FGP',                                                    # name-match | FGP
    'Future Lifestyle Fashions Ltd.': 'FLFL',                             # name-match | FUT LIFESTYLE FASH
    'GTL Infrastructure Ltd.': 'GTLINFRA',                                # name-match | GTL INFRA.LTD
    'GTN Industries Ltd.': 'GTNINDS',                                     # name-match | GTN INDUSTRIES
    'GVK Power & Infrastructures Ltd.': 'GVKPIL',                         # name-match | GVK POW. & INFRA
    'Goodricke Group Ltd.': 'GOODRICKE',                                  # name-match | GOODRICKE GROUP
    'Gujarat Alkalies & Chemicals Ltd.': 'GUJALKALI',                     # name-match | GUJARAT ALKALIES & CHEM
    'Gujarat Ambuja Exports Ltd.': 'GAEL',                                # name-match have_prices | GUJARAT AMBUJA EXPORTS LT
    'Gujarat Lease Financing Ltd.': 'GLFL',                               # name-match | GUJARAT LEASE FINANCING L
    'Gulf Oil Lubricants India Ltd.': 'GULFOILLUB',                       # name-match | GULF OIL LUB. IND.
    'Harrisons Malayalam Ltd.': 'HARRMALAYA',                             # name-match | HARRISON MALAYALAM
    'HeidelbergCement India Ltd.': 'HEIDELBERG',                          # name-match | HEIDELBERGCEMENT (I)
    'Hindustan Motors Ltd.': 'HINDMOTORS',                                # name-match | HINDUSTAN MOTORS
    'Housing Development and Infrastructure Ltd.': 'HDIL',                # name-match | HOUSING DEV & INFRA
    'IL&FS Transportation Networks Ltd.': 'IL&FSTRANS',                   # name-match | IL&FS TRANS NET
    'Ind-Swift Laboratories Ltd.': 'INDSWFTLAB',                          # name-match | IND SWIFT LABORATORIES LT
    'India Nippon Electricals Ltd.': 'INDNIPPON',                         # name-match | INDIA NIPPON ELECT
    'Indiabulls Power Ltd.': 'RTNPOWER',                                  # rename-chase have_prices | RATTANINDIA POWER
    'International Travel House Ltd.': 'ITHL',                            # name-match | INTERNATIONAL TRAVEL HOUSE
    'J.Kumar Infraprojects Ltd.': 'JKIL',                                 # name-match | JKUMAR INFR.LTD.
    'KNR Constructions Ltd.': 'KNRCON',                                   # name-match have_prices | KNR CONSTRU
    'Kakatiya Cement Sugar & Industries Ltd.': 'KAKATCEM',                # name-match | KAKATIYA CEM SUGAR &IND L
    'Kinetic Engineering Ltd.': 'KINETICENG',                             # name-match | KINETIC ENGINEERING
    'MBL Infrastructures Ltd.': 'MBLINFRA',                               # name-match | MBL INFRASTRUCTURE
    'Madras Fertilizers Ltd.': 'MADRASFERT',                              # name-match | MADRAS FERTILISERS
    'Mahindra Lifespace Developers Ltd.': 'MAHLIFE',                      # name-match | MAHINDRA LIFESPACE DEVLTD
    'Man Industries (India) Ltd.': 'MANINDS',                             # name-match | MAN INDUSTRIES (I)
    'Man Infraconstruction Ltd.': 'MANINFRA',                             # name-match | MAN INFRA
    'Manali Petrochemicals Ltd.': 'MANALIPETC',                           # name-match | MANALI PETROCHEMICALS LT
    'Mirza International Ltd.': 'MIRZAINT',                               # name-match | MIRZA INTERNATIONAL LIMIT
    'Morepen Laboratories Ltd.': 'MOREPENLAB',                            # name-match | MOREPEN LAB.
    'Munjal Auto Industries Ltd.': 'MUNJALAU',                            # name-match | MUNJAL AUTO IND.
    'NRB Bearings Ltd.': 'NRBBEARING',                                    # name-match | NRB BEARING
    'National Fertilizers Ltd.': 'NFL',                                   # name-match have_prices | NATIONAL FERT.
    'National Peroxide Ltd.': 'NPL',                                      # name-match | NATIONAL PEROXIDE
    'Network18 Media & Investments Ltd.': 'NETWORK18',                    # name-match have_prices | NETWORK18 MEDIA & INV
    'Onelife Capital Advisors Ltd.': 'ONELIFECAP',                        # name-match | ONELIFE CAP ADVISORS
    'Orient Paper & Industries Ltd.': 'ORIENTPPR',                        # name-match | ORIENT PAPER AND INDS
    'Oriental Hotels Ltd.': 'ORIENTHOT',                                  # name-match | ORIENT HOTELS
    'Patspin India Ltd.': 'PATSPINLTD',                                   # name-match | PATSPIN INDIA
    'Prism Cement Ltd.': 'PRSMJOHNSN',                                    # rename-chase have_prices | PRISM JOHNSON
    'Pritish Nandy Communications Ltd.': 'PNC',                           # name-match | PRITISH NANDY COMMUNICATI
    'Punjab Chemicals & Crop Protection Ltd.': 'PUNJABCHEM',              # name-match | PUNJAB CHEM & CROP PROT L
    'Punjab Communications Ltd.': 'PUNJCOMMU',                            # name-match | PUNJAB COMMUNICATIONS
    'R. S. Software (India) Ltd.': 'RSSOFTWARE',                          # name-match | R. S. SOFTWARE (INDIA) LI
    'Raj Television Network Ltd.': 'RAJTV',                               # name-match | RAJ TV NETWORK
    'Ratnamani Metals & Tubes Ltd.': 'RATNAMANI',                         # name-match have_prices | RATNAMANI MET & TUB
    'Relaxo Footwears Ltd.': 'RELAXO',                                    # name-match have_prices | RELAXO FOOT
    'Reliance Communications Ltd.': 'RCOM',                               # name-match | RELIANCE COMMUNICATIONS L
    'Reliance Industrial Infrastructure Ltd.': 'RIIL',                    # name-match | RELIANCE INDUSTRIAL INFRA
    'Reliance Infrastructure Ltd.': 'RELINFRA',                           # name-match have_prices | RELIANCE INFRASTRUCTU
    'Religare Enterprises Ltd.': 'RELIGARE',                              # name-match have_prices | RELIGARE ENTER.
    'Sadbhav Infrastructure Project Ltd.': 'SADBHIN',                     # name-match | SADBHAV INFRA PROJ
    'Salora International Ltd.': 'SALORAINTL',                            # name-match | SALORA INTERNATIONAL
    'Sesa Sterlite Ltd.': 'VEDL',                                         # rename-chase have_prices | VEDANTA
    'Shree Precoated Steels Ltd.': 'SPSL',                                # name-match | SHREE PRECOATED STEELS
    'Simplex Infrastructures Ltd.': 'SIMPLEXINF',                         # name-match | SIMPLEX INFRASTRUCTURES L
    'Siti Cable Network Ltd.': 'SITINET',                                 # rename-chase | SITI NETWORKS
    'Sudarshan Chemical Industries Ltd.': 'SUDARSCHEM',                   # name-match have_prices | SUDARSHAN CHEMICAL INDS L
    'Suryalakshmi Cotton Mills Ltd.': 'SURYALAXMI',                       # name-match | SURYALAKSHMI COT MIL
    'TCI Industries Ltd.': 'TCIIND',                                      # name-match | TCI INDUSTRIES
    'Tamil Nadu Newsprint & Papers Ltd.': 'TNPL',                         # name-match | TAMILNADU NEWSPRT & PAPER
    'Tamilnadu Petroproducts Ltd.': 'TNPETRO',                            # name-match | TAMILNADU PETROPRODUCTS L
    'Tamilnadu Telecommunications Ltd.': 'TNTELE',                        # name-match | TAMILNADU TELECOMMUNICATI
    'Transpek Industry Ltd.': 'TRANSPEK',                                 # name-match | TRANSPEK INDUSTRIES
    'Transport Corporation of India Ltd.': 'TCI',                         # name-match | TRANSPORT CORPN OF INDIA
    'Tree House Education & Accessories Ltd.': 'TREEHOUSE',               # name-match | TREE HOUSE EDU
    'Tribhovandas Bhimji Zaveri Ltd.': 'TBZ',                             # name-match | TRIB BHIMJI ZAVERI
    'Triveni Engineering & Industries Ltd.': 'TRIVENI',                   # name-match have_prices | TRIVENI ENGG. & INDS.
    'Vikas WSP Ltd.': 'VIKASWSP',                                         # name-match | VIKAS WSP
    'Vinyl Chemicals (India) Ltd.': 'VINYLINDIA',                         # name-match | VINYL CHEMICALS (I)
    'Warren Tea Ltd.': 'WARRENTEA',                                       # name-match | WARREN TEA
    'West Coast Paper Mills Ltd.': 'WSTCSTPAPR',                          # name-match | WEST COAST PAPER MILLS LT
}
