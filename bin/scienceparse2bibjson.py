#!/usr/bin/env python3

import sys
import json

def parse(p):
    sha = p.split('/')[-1].split('.')[0]
    assert(len(sha) == 40)
    info = dict(sha=sha)
    with open(p, 'r') as f:
        tree = json.loads(f.read())['metadata']
    info['title'] = tree['title']
    info['authors'] = tree['authors'] or []
    info['year'] = tree['year'] or None
    info['ref_count'] = len(tree['references'])
    info['_extract_mode'] = tree['source']
    info['_generator'] = tree['creator']
    return info    

def run():
    for p in sys.argv[1:]:
        print(json.dumps(parse(p)))

if __name__=='__main__':
    run()
