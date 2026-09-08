"""Company renames in the NSE inclusion/exclusion feed.

NSE's IndexInclExcl export records an exclusion under the company's name AT
THE TIME OF EXCLUSION, but the matching inclusion under the name it carried
when it entered. Where a company renamed itself mid-membership the two rows
never join, so a naive replay leaks a phantom member and the index count
drifts above 500. Mapping the post-rename name back to the pre-rename one
closes the window on the entity that actually holds it.

Keys are the name as it appears on the EXCLUSION row; values the name on the
earlier INCLUSION row.
"""

EXCL_NAME_TO_INCL_NAME = {
    "RattanIndia Power Ltd.": "Indiabulls Power Ltd.",
    "Indiabulls Ventures Ltd.": "Indiabulls Securities Ltd.",
    "Castex Technologies Ltd.": "Amtek India Ltd.",
    "INEOS Styrolution India Ltd.": "Styrolution ABS (India) Ltd.",
    "Siti Networks Ltd.": "Siti Cable Network Ltd.",
    "IIFL Holdings Ltd.": "India Infoline Ltd.",
    "Strides Shasun Ltd.": "Strides Arcolab Ltd.",
    "Arvind Ltd.": "Arvind Ltd",
    "Bajaj Hindusthan Sugar Ltd.": "Bajaj Hindusthan Ltd.",
    "Bharat Financial Inclusion Ltd.": "SKS Microfinance Ltd.",
    "Johnson Controls - Hitachi Air Conditioning India Ltd.":
        "Hitachi Home & Life Solutions (India) Ltd.",
    "Reliance Naval and Engineering Ltd.":
        "Pipavav Defence and Offshore Engineering Company Ltd.",
    "CG Power and Industrial Solutions Ltd.": "Crompton Greaves Ltd.",
    "Vedanta Ltd.": "Sesa Sterlite Ltd.",
}


# Renames that straddle the 2020-09-14 handoff: the pre-2020 CSV carries the
# old name, the press releases the new one. Same joining problem as above,
# plus punctuation and case drift in NSE's own spelling of unchanged names.
PR_ERA_RENAMES = {
    # genuine corporate renames
    "GE T&D India Ltd.": "Alstom T&D India Ltd.",
    "GE Power India Ltd.": "Alstom India Ltd.",
    "Infibeam Avenues Ltd.": "Infibeam Incorporation Ltd.",
    "CARE Ratings Ltd.": "CARE Ltd.",
    "Future Consumer Ltd.": "Future Consumer Enterprise Ltd.",
    "Huhtamaki India Ltd.": "Huhtamaki PPL Ltd.",
    "Bajaj Consumer Care Ltd.": "Bajaj Corp Ltd.",
    "DCB Bank Ltd.": "Development Credit Bank Ltd",
    "Vakrangee Ltd.": "Vakrangee Software Ltd.",
    "Dhani Services Ltd.": "Indiabulls Ventures Ltd.",
    "Procter & Gamble Health Ltd.": "Merck Ltd.",
    "SIS Ltd.": "Security and Intelligence Services (India) Ltd.",
    "Epigral Ltd.": "Meghmani Finechem Ltd.",
    "DCM Shriram Ltd.": "DCM Shriram Consolidated Ltd.",
    "EPL Ltd.": "Essel Propack Ltd.",
    "Restaurant Brands Asia Ltd.": "Burger King India Ltd.",
    "Vodafone Idea Ltd.": "Idea Cellular Ltd.",
    "CIE Automotive India Ltd.": "Mahindra CIE Automotive Ltd.",
    "Sterling and Wilson Renewable Energy Ltd.": "Sterling And Wilson Solar Ltd.",
    "Westlife Foodworld Ltd.": "Westlife Development Ltd.",
    "Jyothy Labs Ltd.": "Jyothy Laboratories Ltd.",
    "JSW Dulux Ltd.": "Akzo Nobel India Ltd.",
    "Leela Palaces Hotels & Resorts Ltd.": "Schloss Bangalore Ltd.",
    # NSE spelling drift for a company that never renamed
    "Sadbhav Engineering Ltd.": "Sadbhav Engineering Ltd",
    "JK Tyre & Industries Ltd.": "JK Tyre & Industries Ltd..",
    "Saregama India Ltd.": "Saregama India Ltd",
    "INOX Leisure Ltd.": "Inox Leisure Ltd.",
    "Bajaj Electricals Ltd.": "Bajaj Electricals Ltd",
    "Prism Johnson Ltd.": "Prism Cement Ltd.",
}


# Renames that must be applied ON A DATE rather than looked up at exclusion
# time, because the old name is reused by a DIFFERENT company afterwards.
#
# Tata Motors demerged its commercial-vehicle business on 2025-10-14: the
# entity that had been in the index since 1998 (ISIN INE155A01022) became
# Tata Motors Passenger Vehicles Ltd. (TMPV), and the name "Tata Motors Ltd."
# passed to the newly listed commercial-vehicle company (TMCV, INE1TAE01010),
# which the March 2026 review then included as a separate constituent. Without
# renaming the incumbent first, that inclusion collides with it.
DATED_ENTITY_RENAMES = [
    ("2025-10-14", "Tata Motors Ltd.", "Tata Motors Passenger Vehicles Ltd.", "TMPV"),
]


# Companies that were renamed while continuously in the index and never
# generated a post-rename event, so the replay still carries their old name.
# Mapping each to the symbol it trades under today is what lets the
# reconstruction be checked against NSE's current constituent file.
SURVIVOR_IDENTITY = {
    "Adani Gas Ltd.": "ATGL",
    "Adani Transmission Ltd.": "ADANIENSOL",
    "Affle (India) Ltd.": "AFFLE",
    "Akzo Nobel India Ltd.": "JSWDULUX",
    "Amara Raja Batteries Ltd.": "ARE&M",
    "Angel Broking Ltd.": "ANGELONE",
    "Apollo Hospitals Enterprises Ltd.": "APOLLOHOSP",
    "Aster DM Healthcare Ltd.": "ASTERDM",
    "Astral Poly Technik Ltd.": "ASTRAL",
    "Bharti Infratel Ltd.": "INDUSTOWER",
    "Cadila Healthcare Ltd.": "ZYDUSLIFE",
    "Century Textile & Industries Ltd.": "ABREL",
    "Escorts Ltd.": "ESCORTS",
    "Fag Bearings India Ltd.": "SCHAEFFLER",
    "GE T&D India Ltd.": "GVT&D",
    "GMR Infrastructure Ltd.": "GMRAIRPORT",
    "HBL Power Systems Ltd.": "HBLENGINE",
    "HDFC Standard Life Insurance Company Ltd.": "HDFCLIFE",
    "Himachal Fut Com Ltd.": "HFCL",
    "IDFC Bank Ltd.": "IDFCFIRSTB",
    "IIFL Wealth Management Ltd.": "360ONE",
    "Idea Cellular Ltd.": "IDEA",
    "Indiabulls Housing Finance Ltd.": "SAMMAANCAP",
    "Infotech Enterprises Ltd.": "CYIENT",
    "Jindal Steel & Power Ltd.": "JINDALSTEL",
    "Kalpataru Power Transmission Ltd.": "KPIL",
    "L&T Finance Holdings Ltd.": "LTF",
    "Larsen & Toubro Infotech Ltd.": "LTM",
    "Minda Industries Ltd.": "UNOMINDA",
    "NIIT Technologies Ltd.": "COFORGE",
    "National Buildings Construction Corporation Ltd.": "NBCC",
    "Neyveli Lignite Corporation Ltd.": "NLCINDIA",
    "Orient Refractories Ltd.": "RHIM",
    "PVR Ltd.": "PVRINOX",
    "Phillips Carbon Black Ltd.": "PCBL",
    "Redington (India) Ltd.": "REDINGTON",
    "Reliance Nippon Life Asset Management Ltd.": "NAM-INDIA",
    "Rural Electrification Corporation Ltd.": "RECLTD",
    "Shriram Transport Finance Co. Ltd.": "SHRIRAMFIN",
    "Sobha Developers Ltd.": "SOBHA",
    "Suven Pharmaceuticals Ltd.": "COHANCE",
    "Swan Energy Ltd.": "SWANCORP",
    "TI Financial Holdings Ltd.": "CHOLAHLDNG",
    "Tata Global Beverages Ltd.": "TATACONSUM",
    "Titan Industries Ltd.": "TITAN",
    "WABCO India Ltd.": "ZFCVINDIA",
    "Welspun India Ltd.": "WELSPUNLIV",
    "Zomato Ltd.": "ETERNAL",
}
