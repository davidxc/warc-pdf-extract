
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
- `time` (GNU program, not the bash builtin)
- `ia-mine` tool
- `ia` python library (and appropriate upload credentials)

Run:

    sudo pip3 install gluish iamine

Have switched to GROBID 0.5.x. To download and build:

    wget https://github.com/kermitt2/grobid/archive/0.5.0.zip
    unzip 0.5.0.zip
    cd grobid-0.5.0
    ./gradlew clean install

Configure TMPDIR and restart user session.

## Run

You need an IA item manifest for the crawl or the jobs will refuse to run. Use
metamgr to export item lists (one item identifier per line) of all items in the
crawl. Put this file at `download/items_{crawl}.tsv`.

Run GROBID as a local service (from the GROBID root directory):

    ./gradlew run

Then, run Luigi from this directory, three workers, local scheduling:

    PYTHONPATH='luigi_scripts' luigi --module warc_extract ExtractCrawl --crawl citeseerx_crawl_2017 --local-scheduler --workers 3

In actual use you'll probably want more workers, and maybe even distributed
scheduling (multiple machines, one collection or set of items each).

