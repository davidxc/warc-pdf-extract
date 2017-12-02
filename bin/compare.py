#!/usr/bin/env python3

"""
This script takes a TSV file path (with upstream metadata):

  <doi> <title> <authors> <year> <journal> <publisher> <subject> <type> <sha1>

and a path to a file with bibjson-per-line (plus a 'sha1' field).

It checks if the sha1 lines match up using title/author matching, and prints
result stats.

TODO: should be doing this in jupyter/pandas
"""

import sys
import json
from fuzzywuzzy import fuzz

def tokenize(s, remove_whitespace=False):

    if not s:
        return None

    # Remove non-alphanumeric characters
    s = ''.join([c for c in s.lower() if c.isalnum() or c.isspace()])

    if remove_whitespace:
        s = ''.join(s.split())

    # Encode as dumb ASCII (TODO: this is horrible)
    return s.encode('ascii', 'replace').replace(b'?', b'')

def tokenize_name(s):

    s = s.strip()
    if not s:
        return None

    # Remove non-alphanumeric characters
    s = ''.join([c for c in s.lower() if c.isalnum() or c.isspace()])

    if len(s) < 1:
        return None

    # Take last word
    return s.split()[-1]

def is_token_match(left, right):

    try:
        left_title = tokenize(left['title'], True)
        right_title = tokenize(right['title'], True)
        left_authors = list(map(tokenize_name, left['authors']))
        right_authors = list(map(tokenize_name, left['authors']))
        print(left_title)
        print(right_title)
        print(left_authors)
        print(right_authors)
        return left_title == right_title and left_authors == right_authors
    except Exception as e:
        raise e
        print("Error: {}".format(e))

    return False

def is_fuzzy_match(left, right):

    try:
        left_title = tokenize(left['title'])
        right_title = tokenize(right['title'])
        left_authors = list(map(tokenize_name, left['authors']))
        right_authors = list(map(tokenize_name, left['authors']))
        if not (left_title and right_title and left_authors and right_authors):
            return False
        left = left_title.decode() + " ".join([a or "" for a in left_authors])
        right = right_title.decode() + " ".join([a or "" for a in right_authors])
        # cut-off chosen somewhat randomly
        return fuzz.ratio(left, right) > 90
    except Exception as e:
        raise e
        print("Error: {}".format(e))

    return False

def read_crossref(p):
    papers = dict()
    with open(p, 'r') as f:
        for line in f:
            line = line.strip().split('\t')
            if len(line) != 9:
                continue
            paper = dict(
                doi=line[0],
                title=line[1],
                authors=line[2].split(';'),
                year=line[3],
                journal=line[4],
                subject=line[6],
                media=line[7],
                sha1=line[8])
            assert(len(paper['sha1']) == 40)
            papers[paper['sha1']] = paper
    return papers

def read_extracted(p):
    papers = dict()
    with open(p, 'r') as f:
        for line in f:
            line = json.loads(line)
            paper = dict(
                sha1=line['sha'],
                doi=line.get('doi'),
                title=line['title'],
                authors=line['authors'])
            papers[paper['sha1']] = paper
    return papers

def run():
    
    crossref_papers = read_crossref(sys.argv[1])
    extracted_papers = read_extracted(sys.argv[2])
    total = len(crossref_papers)
    matched = 0
    missed = 0
    fuzzy_matched = 0
    fuzzy_missed = 0
    doi_matched = 0
    doi_missed = 0
    for extracted in extracted_papers.values():
        print()
        if not extracted['sha1'] in crossref_papers.keys():
            print("=> SKIPPING No metadata: " + extracted['sha1'])
            continue
        crossref = crossref_papers[extracted['sha1']]
        r = is_token_match(crossref, extracted)
        if r:
            print("=> TITLE+AUTHOR MATCHED: " + extracted['sha1'])
            matched = matched + 1
        else:
            print("=> TITLE+AUTHOR FAIL: " + extracted['sha1'])
            missed = missed + 1
        fr = is_fuzzy_match(crossref, extracted)
        if fr:
            print("=> FUZZY MATCHED: " + extracted['sha1'])
            fuzzy_matched = fuzzy_matched + 1
        else:
            print("=> FUZZY FAIL: " + extracted['sha1'])
            fuzzy_missed = fuzzy_missed + 1
        if extracted.get('doi'):
            if extracted['doi'].lower() == crossref['doi'].lower():
                print("=> DOI MATCHED")
                doi_matched = doi_matched + 1
            else:
                print("=> DOI FAIL")
                doi_missed = doi_missed + 1

    print("Title and author tokens:")
    print("  total={} tried={} ({}) matched={} ({}) missed={} ({})".format(
        total, matched+missed, (matched+missed)/total,
        matched, matched/total,
        missed, missed/total))
    print("Fuzzy:")
    print("  total={} tried={} ({}) matched={} ({}) missed={} ({})".format(
        total, fuzzy_matched+fuzzy_missed, (fuzzy_matched+fuzzy_missed)/total,
        fuzzy_matched, fuzzy_matched/total,
        fuzzy_missed, fuzzy_missed/total))
    print("DOI:")
    print("  total={} tried={} ({}) matched={} ({}) missed={} ({})".format(
        total, doi_matched+doi_missed, (doi_matched+doi_missed)/total,
        doi_matched, doi_matched/total,
        doi_missed, doi_missed/total))

if __name__=='__main__':
    run()
