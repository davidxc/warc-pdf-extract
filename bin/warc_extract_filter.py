#!/usr/bin/env python3
"""
Extracts a subset of files from a WARC, based on filter parameters (for now,
just mimetype). Use like:

    ./warc_extract_filter.py --mimetype pdf . crawl_stuff.warc.gz

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
import warcat.model

def do_file(outdir, flo, size, out_suffix):
    out_suffix = out_suffix or ""
    h = hashlib.sha1()
    tmpname = tempfile.mktemp(dir=outdir, prefix="TEMP")
    with open(tmpname, 'bw') as outfile:
        while True:
            data = flo.read(2**20)
            if not data:
                break
            h.update(data)
            outfile.write(data)
    assert(os.path.getsize(tmpname) == size)
    flo.close()
    os.rename(tmpname, "{}/{}{}".format(outdir, h.hexdigest().lower(), out_suffix))

def do_warc(outdir, filename, mimefilter=None, minsize=None, maxsize=None, ignore_invalid=False, out_suffix=None):

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
        print("Dumping: %s" % uri)
        flo = content.payload.get_file(safe=True)
        # Sometimes content payload size "changes"
        size = content.payload.length
        try:
            do_file(outdir, flo, size, out_suffix)
        except Exception as e:
            if ignore_invalid:
                sys.stderr.write("Failed to dump file: %s\n" % uri)
                continue
            else:
                raise e

def main():
    parser = argparse.ArgumentParser(
        description="WARC extract with filtering",
        usage="%(prog)s [options] <dir> <warc>...")
    parser.add_argument("--mimetype",
        action="store",
        help="mimetype (lowercased) must contain this string")
    parser.add_argument("--min-size",
        action="store",
        help="files must be at least this size (bytes)")
    parser.add_argument("--max-size",
        action="store",
        help="files must be less than or equal to this size (bytes)")
    parser.add_argument("--ignore-invalid",
        action="store_true",
        help="ignore errors loading individual WARC files")
    parser.add_argument("--out-suffix",
        action="store",
        help="name all output files with the given suffix")
    parser.add_argument("outdir")
    parser.add_argument("warcfiles", nargs='+')

    args = parser.parse_args()

    outdir = args.outdir

    if not os.path.isdir(outdir):
        print("{} doesn't look like a directory".format(outdir))
        return

    minsize = args.min_size and int(args.min_size)
    maxsize = args.max_size and int(args.max_size)

    for filename in args.warcfiles:
        do_warc(outdir,
                filename,
                mimefilter=args.mimetype,
                minsize=minsize,
                maxsize=maxsize,
                ignore_invalid=args.ignore_invalid,
                out_suffix=args.out_suffix)

if __name__=='__main__':
    main()
