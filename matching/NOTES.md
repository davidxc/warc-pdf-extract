
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

=============================

Testing:

    mkdir -p test
    rm -f test/tokenized_crossref.sqlite
    ./tokenize_crossref_tsv.py test/crossref_examples.tsv  > test/tokenized_crossref.tsv
    sqlite3 test/tokenized_crossref.sqlite < token_doi_schema.sql
    sqlite3 test/tokenized_crossref.sqlite < test/import_test_data.sql

"Production":

    ./tokenize_crossref_tsv.py /fast/metadump/biblio/works_crossref.tsv | pv --line-mode -s 85000000 > tokenized_crossref.tsv
    sqlite3 test/tokenized_crossref.sqlite < import_full_data.sql

