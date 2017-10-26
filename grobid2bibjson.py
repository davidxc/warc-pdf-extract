#!/usr/bin/env python3

import sys
import json
import xml.etree.ElementTree as ET


def parse(p):
    sha = p.split('/')[-1].split('.')[0]
    assert(len(sha) == 40)
    info = dict(sha=sha)

    tree = ET.parse(p)
    tei = tree.getroot()
    ns = "http://www.tei-c.org/ns/1.0"
    info['title'] = tei.findtext('.//{%s}analytic/{%s}title' % (ns, ns))
    info['authors'] = [' '.join([e.findtext('./{%s}forename' % ns) or '', e.findtext('./{%s}surname' % ns) or '']).strip() for e in tei.findall('.//{%s}author/{%s}persName' % (ns, ns))]
    info['journal'] = tei.findtext('.//{%s}monogr/{%s}title' % (ns, ns))
    doi = [e.text for e in tei.findall('.//{%s}idno' % ns) if e.attrib['type'] == "DOI"]
    if len(doi):
        info['doi'] = doi[0]
    else:
        info['doi'] = None
    return info    

def run():
    for p in sys.argv[1:]:
        print(json.dumps(parse(p)))

if __name__=='__main__':
    run()
