
PLAN
- create sqlite lookup index with:
    partial title token (indexed)
    DOI (indexed)
    full title
    full authors
- for each input JSON:
    try exact DOI lookup
        if a match, verify with fuzzy
    tokenize title and do lookup
    for each match (up to N):
        try exact token match
        try fuzzy match
    if a match, report "why" (eg, "grobid-crossref-fuzzy-0.74"), output JSON:
        sha1, why, doi
- save this as json somewhere
- also save progeny metadata?
    grobid version
    crossref
    this repo revision


    sqlite3 tokenized_crossref.sqlite < token_doi_schema.sql
