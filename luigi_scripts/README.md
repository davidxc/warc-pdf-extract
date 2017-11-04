
Code for extracting PDF metadata from all the WARCs in a targeted crawl.

These scripts will:
- create a task for each petabox item in a (crawl) collection
- download warc files to local disk
- extract all PDF files from the WARC into a directory
- run GROBID on the directory
- convert to concatonated JSON
- create a manifest of processed files and status
- zip everything up and move to output dir

## Setup

Requires:

- `luigi`
- `gluish` (extensions to luigi)
- `GROBID`
- `ia-mine` tooL
- `ia` python library (and appropriate upload credentials)

Configure TMPDIR and restart user session.

## Run

You need an IA item manifest for the crawl or the jobs will refuse to run. Use
metamgr to export item lists (one item identifier per line) of all items in the
crawl. Put this file at `download/items_{crawl}.tsv`.

Then, run Luigi from this directory, single worker, local scheduling:

    PYTHONPATH='luigi_scripts' luigi --module warc_extract ExtractCrawl --crawl CITESEERX-CRAWL-2017 --local-scheduler --workers 3

In actual use you'll probably want more workers, and maybe even distributed
scheduling (multiple machines).

## Upload Results

    # XXX:
    ia upload <crawl>-extract-grobid work/<crawl> --checksum

    # XXX: version xyz
    ia metadata <crawl>-extract-grobid
        -m title:"<crawl> PDF Extraction"
        -m mediatype:data
        -m description:"This item contains PDF paper metadata and extracted fulltext for all files in this crawl.\nExtraction was performed using GROBID"
        -m collection:<crawl-collection>

