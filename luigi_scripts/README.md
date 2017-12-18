
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
- `jq`
- `gluish` (extensions to luigi)
- `GROBID`
- `time` (GNU program, not the bash builtin)
- `ia-mine` tool
- `ia` python library (and appropriate upload credentials)

Run:

    sudo apt install unzip time python3-pip python3-setuptools python3-wheel jq
    sudo pip3 install luigi gluish iamine

Have switched to GROBID 0.5.x. To download and build:

    wget https://github.com/kermitt2/grobid/archive/0.5.0.zip
    unzip 0.5.0.zip
    cd grobid-0.5.0
    ./gradlew clean install

If on a cluster machine (eg, NFS homedir), and you get an IDLE hange on the
last command, replace with:

    ./gradlew clean install --gradle-user-home .

Configure TMPDIR and restart user session.

## Run

You need an IA item manifest for the crawl or the jobs will refuse to run. Use
metamgr to export item lists (one item identifier per line) of all items in the
crawl. Put this file at `download/items_{crawl}.tsv`.

Run GROBID as a local service (from the GROBID root directory):

    ./gradlew run
    # or: ./gradlew run --gradle-user-home .

Then, run Luigi from this directory, three workers, local scheduling:

    PYTHONPATH='luigi_scripts' luigi --module warc_extract ExtractCrawl --crawl citeseerx_crawl_2017 --workers 3

In actual use you'll probably want more workers, and maybe even distributed
scheduling (multiple machines, one collection or set of items each).

