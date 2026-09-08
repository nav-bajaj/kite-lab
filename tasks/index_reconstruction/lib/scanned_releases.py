"""Changes read by eye from a press release that has no text layer.

ind_prs23082021.pdf is a 29-page scan: pdftotext returns 29 bytes for it, so
the parser sees nothing. The extraction pipeline now fails loudly on an empty
text dump rather than silently skipping the release (see fetch/extract step).

Its Nifty 500 section is superseded - the September 15, 2021 release restates
the same review with Gillette's exclusion dropped, and that one parses - so
only the Nifty 100 side is recorded here.

Nifty 100 = Nifty 50 + Nifty Next 50. This release changes Nifty Next 50 and
leaves Nifty 50 alone, so its Next 50 replacements ARE the Nifty 100
replacements for the September 2021 review. Read off pages 2-3.
"""

SCANNED_CHANGES = {
    "nifty100": [{
        "file": "ind_prs23082021",
        "pub": "2021-08-23",
        "title": "Revision in criteria and replacements in indices (scanned)",
        "eff": "2021-09-30",
        "excluded": [("Abbott India Ltd.", "ABBOTINDIA"),
                     ("Alkem Laboratories Ltd.", "ALKEM"),
                     ("MRF Ltd.", "MRF"),
                     ("Petronet LNG Ltd.", "PETRONET"),
                     ("United Breweries Ltd.", "UBL")],
        "included": [("Bank of Baroda", "BANKBARODA"),
                     ("Cholamandalam Investment and Finance Company Ltd.", "CHOLAFIN"),
                     ("Jindal Steel & Power Ltd.", "JINDALSTEL"),
                     ("PI Industries Ltd.", "PIIND"),
                     ("Steel Authority of India Ltd.", "SAIL")],
    }],
}
