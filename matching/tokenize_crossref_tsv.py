#!/usr/bin/env python3

"""
Reads in crossref-works.tsv:

    <doi>  <title>  <authors> ...

Writes out (TSV):

    <title_token> <doi> <title> <authors>

Filters out lines with very short title or author strings (which are unlikely
to match easily).

Output can be fed into sqlite.
"""

import sys


def tokenize(s, remove_whitespace=True):

    if not s:
        return None

    # Remove non-alphanumeric characters
    s = ''.join([c for c in s.lower() if c.isalnum() or c.isspace()])

    if remove_whitespace:
        s = ''.join(s.split())

    # Encode as dumb ASCII (TODO: this is horrible)
    return s.encode('ascii', 'replace').replace(b'?', b'').decode()

def run(infile):
    for line in infile:
        line = line.split('\t')
        if len(line) != 8:
            sys.stderr.write("invalid input line (len={}): {}".format(len(line), line))
            continue
        doi = line[0]
        title = line[1]
        authors = line[2]
        assert(doi.startswith("10."))
        if len(title) <= 5 or len(authors) <= 3:
            continue
        title_token = tokenize(title)[:64]
        print("\t".join((title_token, doi, title, authors)))

if __name__=='__main__':
    if len(sys.argv) > 1:
        run(open(sys.argv[1], 'r'))
    else:
        run(sys.stdin)
