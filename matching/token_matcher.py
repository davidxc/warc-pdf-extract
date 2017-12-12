#!/usr/bin/env python3

"""
Reads in PDF metadata (one json per line) and tries to match against a sqlite
database of tokenized metadata.

Outputs:

    <fulltext-sha1>  <doi>  <why>

Or, if a match isn't found:

    <fulltext-sha1>  -  -
"""

import sys
import json
from fuzzywuzzy import fuzz
import sqlite3
import argparse


def tokenize(s, remove_whitespace=True):

    if not s:
        return None

    # Remove non-alphanumeric characters
    s = ''.join([c for c in s.lower() if c.isalnum() or c.isspace()])

    if remove_whitespace:
        s = ''.join(s.split())

    # Encode as dumb ASCII (TODO: this is horrible)
    return s.encode('ascii', 'replace').replace(b'?', b'').decode()


def score_match(obj, row):
    """Does a fuzzywuzzy ratio comparison between 
    """
    author_names = ";".join([a['name'] for a in obj['authors']])
    left = "{} {}".format(obj['title'], author_names).lower()
    row_token, row_doi, row_title, row_authors = row
    right = "{} {}".format(row_title, row_authors).lower()
    return fuzz.ratio(left, right)


def try_doi(db, obj):
    doi = obj.get('doi')
    if not doi or not doi.startswith("10."):
        return False
    # probably redundant, but make sure DOI is lower-cased
    doi = doi.lower()
    c = db.execute('SELECT * FROM token_doi WHERE doi=? LIMIT 10', (doi, ))
    rows = c.fetchall()
    assert len(rows) <= 1, "DOI column should be unique"
    if len(rows) == 1:
        score = score_match(obj, rows[0])
        if score > 90:
            return (doi, 'grobid-crossref-exact_doi-{}'.format(score))
    else:
        return False


def try_title_author(db, obj):
    title = obj['title']
    title_token = tokenize(title)[:64]
    rows = db.execute('SELECT * from token_doi WHERE title_token=? LIMIT 20', (title_token, ))
    for row in rows:
        score = score_match(obj, row)
        if score > 90:
            doi = row[1].lower()
            return (doi, 'grobid-crossref-title_token-{}'.format(score))
    return False


def run(db, infile):

    for line in infile:
        if len(line) <= 2:
            # skip ~blank lines
            continue
        obj = json.loads(line)

        # skip totally bogus objects
        if not obj.get('title') or len(obj['title']) < 5:
            continue
        if not obj.get('authors') or len(obj['authors']) == 0:
            continue

        fulltext_hash = obj['filename'].split('.')[0]
        match = try_doi(db, obj)
        if not match:
            match = try_title_author(db, obj)
        if not match:
            match = ("-", "-")
        match_doi, match_why = match
        print("\t".join((fulltext_hash, match_doi, match_why)))


def main():
    parser = argparse.ArgumentParser(
        description="token matcher!",
        usage="%(prog)s [options] <token_db.sqlite> <metadata.json>...")
    parser.add_argument("db_path",
        help="token-to-DOI database path (sqlite3)")
    parser.add_argument("metadata_file",
        help="path to metadata file")

    args = parser.parse_args()

    db = sqlite3.connect(args.db_path)

    run(db, open(args.metadata_file, 'r'))

if __name__=='__main__':
    main()
