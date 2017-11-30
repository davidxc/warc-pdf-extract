#!/usr/bin/env python3
"""
Extracts a subset of files from a WARC, based on filter parameters (for now,
just mimetype). Use like:

    ./warc_pdf_grobid_client.py --mimetype pdf . crawl_stuff.warc.gz

Output file name will be just the (lower-case base16/hex) sha1 hash of the
content.

Requires the warcat library:

    sudo pip3 install warcat
"""

import os
import sys
import hashlib
import argparse
import tempfile
import requests
import warcat.model


def check_server(grobid_server):
    r = requests.get(grobid_server + "/api/isalive")
    assert r.status_code == 200
    assert b"true" in r.content


def do_file(outdir, flo, size, grobid_server):
    h = hashlib.sha1()
    tmpname = tempfile.mktemp(dir=outdir, prefix="TEMP")
    
    r = requests.post(grobid_server + "/api/processFulltextDocument",
        files={'input': flo})
    if r.status_code is not 200:
        # TODO: log failure somewhere?
        print("\tFailed to parse: " + r.content.decode('utf8'))
        return

    with open(tmpname, 'bw') as outfile:
        data = r.content
        h.update(data)
        outfile.write(data)
    flo.close()
    os.rename(tmpname, "{}/{}.tei.xml".format(outdir, h.hexdigest().lower()))


def do_warc(outdir, filename, grobid_server, mimefilter=None, minsize=None, maxsize=None, ignore_invalid=False):

    print("Parsing WARC: %s" % filename)
    warc = warcat.model.WARC()
    try:
        warc.load(filename)
    except Exception as e:
        if ignore_invalid:
            sys.stderr.write("Failed to load WARC: %s\n" % filename)
            return
        else:
            raise e

    for record in warc.records:
        if record.header.fields['WARC-Type'].lower() != 'response':
            continue
        if not "application/http" in record.header.fields.get('Content-Type'):
            continue

        content = record.content_block
        try:
            size = content.payload.length
            mimetype = content.fields['Content-Type'].lower().split(';')[0]
        except Exception as e:
            #raise e
            continue

        if (minsize is not None and size < minsize):
            continue
        if (maxsize is not None and size > maxsize):
            continue
        if (mimefilter is not None and mimefilter not in mimetype):
            continue

        uri = record.header.fields.get("WARC-Target-URI")
        print("Parsing: %s" % uri)
        flo = content.payload.get_file(safe=True)
        # Sometimes content payload size "changes"
        size = content.payload.length
        try:
            do_file(outdir, flo, size, grobid_server)
        except Exception as e:
            if ignore_invalid:
                sys.stderr.write("Failed to dump file: %s\n" % uri)
                continue
            else:
                raise e

def main():
    parser = argparse.ArgumentParser(
        description="WARC extract, process with GROBID, save XML",
        usage="%(prog)s [options] <dir> <warc>...")
    parser.add_argument("--mimetype",
        action="store",
        default="pdf",
        help="mimetype (lowercased) must contain this string")
    parser.add_argument("--min-size",
        action="store",
        help="files must be at least this size (bytes)")
    parser.add_argument("--max-size",
        action="store",
        default=1024*1000*200, # ~200MB
        type=int,
        help="files must be less than or equal to this size (bytes)")
    parser.add_argument("--ignore-invalid",
        action="store_true",
        help="ignore errors loading individual WARC files")
    parser.add_argument("--grobid-server",
        action="store",
        default="localhost:8070",
        help="host:port of GROBID server to connect to")
    parser.add_argument("outdir")
    parser.add_argument("warcfiles", nargs='+')

    args = parser.parse_args()

    outdir = args.outdir

    if not os.path.isdir(outdir):
        print("{} doesn't look like a directory".format(outdir))
        return

    minsize = args.min_size and int(args.min_size)
    maxsize = args.max_size and int(args.max_size)

    check_server(args.grobid_server)

    for filename in args.warcfiles:
        do_warc(outdir,
                filename,
                grobid_server=args.grobid_server,
                mimefilter=args.mimetype,
                minsize=minsize,
                maxsize=maxsize,
                ignore_invalid=args.ignore_invalid)

if __name__=='__main__':
    main()
