#!/usr/bin/env python3

import sys
import json
import xml.etree.ElementTree as ET


def parse(p):
    sha = p.split('/')[-1].split('.')[0]
    assert(len(sha) == 40)
    info = dict(sha=sha)

    tree = ET.parse(p)
    article = tree.getroot()
    info['title'] = article.findtext('.//article-title')
    info['authors'] = [e.findtext('./string-name') for e in article.findall('.//contrib') if e.attrib['contrib-type'] == "author"]
    info['year'] = article.findtext('.//year')
    info['journal'] = article.findtext('.//journal-title')
    info['volume'] = article.findtext('.//volume')
    info['issue'] = article.findtext('.//issue')
    doi = [e.text for e in article.findall('.//article-id') if e.attrib['pub-id-type'] == "doi"]
    if len(doi):
        info['doi'] = doi[0]
    else:
        info['doi'] = None
    info['ref_count'] = len(article.findall('.//ref'))
    return info    

def run():
    for p in sys.argv[1:]:
        print(json.dumps(parse(p)))

if __name__=='__main__':
    run()
