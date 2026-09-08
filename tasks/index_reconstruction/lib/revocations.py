"""Announced Nifty 500 changes that NSE revoked before they took effect.

The Index Maintenance Sub-Committee occasionally cancels a change it has
already published - usually because the incoming stock breached SEBI's
portfolio-concentration/impact-cost rules between announcement and effective
date. Replaying the original review alone would move a stock that never
actually moved, so these cancellations have to be applied on top.

Only two of the four revocation notices in 2020-2026 touch the Nifty 500;
the others are Microcap 250 / Total Market only. Each entry below was read
off the revocation table and cross-checked against the parsed review it
cancels.
"""

# (effective_date, symbol, kind) tuples to DROP from the replayed events.
REVOKED = [
    # ind_prs19032024 - IREDA breached SEBI impact-cost norms after the
    # February 2024 review was published, so its inclusion and the matching
    # V-Guard exclusion were both called off.
    ("2024-03-28", "IREDA", "in"),
    ("2024-03-28", "VGUARD", "out"),
    # ind_prs25092024 - NSE recalculated Vodafone Idea's impact cost and
    # kept it in the index; Prism Johnson was excluded in its place.
    ("2024-09-30", "IDEA", "out"),
]

# Changes introduced BY a revocation notice, to keep the index at 500.
SUBSTITUTED = [
    # ind_prs25092024 - replaces the revoked Vodafone Idea exclusion.
    ("2024-09-30", "Prism Johnson Ltd.", "PRSMJOHNSN", "out", "ind_prs25092024"),
]


# Corporate-action releases announce their changes as a bare list of affected
# INDEX NAMES with no per-index company table, so the section parser cannot
# reach them. Both entries below were read off the release named in the note.
CORPORATE_ACTIONS = [
    # ind_prs23082024_1 - Tata Motors' 'A' Ordinary (DVR) shares were
    # cancelled under a scheme of arrangement and dropped from the index.
    ("2024-08-30", "Tata Motors Ltd DVR", "TATAMTRDVR", "out", "ind_prs23082024_1"),
    # ind_prs03092026 - HEG demerged its graphite business; NSE adds the
    # resulting company as a zero-price dummy until it lists properly. This
    # is why NSE's own constituent file currently carries 501 rows.
    ("2026-09-07", "HEG Graphite Ltd.", "DUMMYHEG", "in", "ind_prs03092026"),
]


# Revocations that hit the smaller indices. ind_prs25092024 revoked Central
# Bank of India's Nifty Midcap 150 inclusion and Vodafone Idea's exclusion;
# LargeMidcap 250 is Nifty 100 + Midcap 150, so both land there too.
INDEX_REVOKED = {
    "nifty250": [("2024-09-30", "CENTRALBK", "in"),
                 ("2024-09-30", "IDEA", "out")],
}


# Substitutions a revocation notice introduces so the index keeps its size.
# ind_prs19032024 group 6: with IREDA's LargeMidcap 250 inclusion revoked,
# BSE Ltd. was included in its place.
INDEX_SUBSTITUTED = {
    "nifty250": [("2024-03-28", "BSE Ltd.", "BSE", "in", "ind_prs19032024")],
}
