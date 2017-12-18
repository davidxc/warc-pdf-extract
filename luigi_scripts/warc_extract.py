
import subprocess
import tempfile
import datetime
import time
import json
import glob
import os

import luigi
from gluish.common import Executable
from gluish.utils import shellout
from gluish.format import TSV
import requests

from grobid_server import GrobidServer

# TODO: proper config values somewhere?
GROBID_JAR="./grobid-grobid-parent-0.4.4/grobid-core/target/grobid-core-0.4.4-SNAPSHOT.one-jar.jar"
GROBID_HOME="./grobid-grobid-parent-0.4.4/grobid-home/"


class CrawlItemsList(luigi.Task):
    """This represents an item list (eg, metamgr output) of items holding WARCs
    for a given crawl.
    """

    crawl = luigi.Parameter()

    def requires(self):
        return [Executable(name='ia-mine')]

    def run(self):
        output = shellout("""
            LC_ALL=C
            ia-mine --itemlist -s collection:"{crawl}"
                | grep -v "\-warcsum"
                | grep -v "\-CRL"
                | sort -u
            > {output}""",
            crawl=self.crawl)
        luigi.LocalTarget(output).move(self.output().path)

    def output(self):
        return luigi.LocalTarget('work/items_%s.tsv' % (self.crawl))


class ItemWarcDownload(luigi.Task):

    crawl = luigi.Parameter()
    item = luigi.Parameter()

    # Don't keep trying over and over!
    retry_count = 1

    def requires(self):
        return [Executable(name='ia')]

    def run(self):

        # get list of WARC files in item using ia metadata
        # parse and filter the json output
        #   ia metadata <item>
        cmd_out = subprocess.check_output(['ia', 'metadata', self.item])
        cmd_out = cmd_out.decode('utf-8')
        if cmd_out.strip() == "{}":
            raise Exception("Item not found! " + self.item)
        item_info = json.loads(cmd_out)
        file_list = [f['name'] for f in item_info['files']]

        # filter to just WARC files (.warc or .warc.gz)
        file_list = [f for f in file_list if f.endswith('.warc') or f.endswith('.warc.gz')]

        # create output dir for this item
        shellout("mkdir -p work/{}/{}".format(self.crawl, self.item))

        # for each file, download with ia download
        #   ia download <item> <file> --stdout > {warc_file}
        for fname in file_list:
            saved = shellout("""
                ia download {item} {fname} --stdout > {output}""",
                item=self.item,
                fname=fname)

            # move to local directory
            # warcsum's warcat requires .warc.gz extension
            new_path = "work/{crawl}/{item}/{fname}".format(
                crawl=self.crawl,
                item=self.item,
                fname=fname)
            shellout("mv {saved} {new_path}",
                saved=saved,
                new_path=new_path)

        # write out TSV of WARC names (and hashes?)
        with self.output().open('w') as out_fd:
            for fn in file_list:
                out_fd.write_tsv(fn)

    def output(self):
        return luigi.LocalTarget('work/{}/{}/warcs.tsv'.format(self.crawl, self.item),
            format=TSV)


class ItemPdfs(luigi.Task):

    crawl = luigi.Parameter()
    item = luigi.Parameter()

    # Don't keep trying over and over!
    retry_count = 1

    def requires(self):
        return [Executable(name='bin/warc_extract_filter.py'),
                ItemWarcDownload(crawl=self.crawl, item=self.item)]

    def run(self):

        (_, input_manifest) = self.input()

        with open(input_manifest.path, 'r') as mf:
            warc_list = [l.strip() for l in mf.readlines()]
        downloaded_warcs = ["work/{}/{}/{}".format(self.crawl, self.item, w) for w in warc_list]

        pdf_dir = "work/{}/{}/pdfs".format(self.crawl, self.item)
        shellout("mkdir -p {pdf_dir}", pdf_dir=pdf_dir)

        shellout("""
            bin/warc_extract_filter.py {pdf_dir} {infiles}
                --ignore-invalid
                --min-size 512
                --max-size 268435456
                --mimetype pdf
                --out-suffix .pdf""",
            pdf_dir=pdf_dir,
            infiles=" ".join(downloaded_warcs))

        output = shellout("echo done > {output}")
        luigi.LocalTarget(output).move(self.output().path)

    def output(self):
        return luigi.LocalTarget('work/{}/{}/pdfs.STAMP'.format(self.crawl, self.item))

def glob_count(g):
    return len(glob.glob(g))

class ItemGrobidExtract(luigi.Task):

    crawl = luigi.Parameter()
    item = luigi.Parameter()

    # Don't keep trying over and over!
    retry_count = 1

    def requires(self):
        return [(Executable(name='java'),
                 Executable(name='/usr/bin/time')),
                ItemPdfs(crawl=self.crawl, item=self.item)]

    def run(self):

        pdf_dir = "work/{}/{}/pdfs".format(self.crawl, self.item)
        grobid_dir = "work/{}/{}/grobid_tei".format(self.crawl, self.item)
        shellout("mkdir -p {grobid_dir}", grobid_dir=grobid_dir)

        output = shellout("""
            /usr/bin/time -v -o {output}
            java
                -Xmx6G
                -jar {GROBID_JAR}
                -gH {GROBID_HOME}
                -dIn {pdf_dir}
                -r
                -dOut {grobid_dir}
                -exe processFullText""",
            pdf_dir=pdf_dir,
            grobid_dir=grobid_dir,
            GROBID_JAR=GROBID_JAR,
            GROBID_HOME=GROBID_HOME)

        # java/GROBID doesn't error when it runs. One way to check that it ran
        # is that there should be a TEI file for every file in PDF dir.
        #assert(glob_count(pdf_dir + "/*.pdf") == glob_count(grobid_dir + "/*.tei.xml"))

        luigi.LocalTarget(output).move(self.output().path)

    def output(self):
        return luigi.LocalTarget('work/{}/{}/grobid.timing'.format(self.crawl, self.item))

class ItemGrobidServiceExtract(luigi.Task):

    crawl = luigi.Parameter()
    item = luigi.Parameter()

    # Don't keep trying over and over!
    retry_count = 1

    def requires(self):
        return [ItemWarcDownload(crawl=self.crawl, item=self.item)]

    def run(self):
        input_manifest = self.input()[0]

        warc_list = [l.strip() for l in open(input_manifest.path, 'r').readlines()]
        yield [WarcGrobidServiceExtract(self.crawl, self.item, w) for w in warc_list]

        output = shellout("echo 'done' > {output}")
        luigi.LocalTarget(output).move(self.output().path)

    def output(self):
        return luigi.LocalTarget('work/{}/{}/grobid_service.STAMP'.format(self.crawl, self.item))


class WarcGrobidServiceExtract(luigi.Task):

    crawl = luigi.Parameter()
    item = luigi.Parameter()
    warc = luigi.Parameter()

    # Don't keep trying over and over!
    retry_count = 1

    def requires(self):
        return [GrobidServer(),
                ItemWarcDownload(crawl=self.crawl, item=self.item)]

    def run(self):

        warc_path = "work/{}/{}/{}".format(self.crawl, self.item, self.warc)
        grobid_server = "http://localhost:8070"
        grobid_dir = "work/{}/{}/grobid_tei".format(self.crawl, self.item)
        shellout("mkdir -p {grobid_dir}", grobid_dir=grobid_dir)

        shellout("""
            bin/warc_pdf_grobid_client.py {grobid_dir} {warc_path}
                --min-size 512
                --max-size 268435456
                --mimetype pdf
                --grobid-server {grobid_server}""",
            grobid_dir=grobid_dir,
            grobid_server=grobid_server,
            warc_path=warc_path)

        output = shellout("echo 'done' > {output}")
        luigi.LocalTarget(output).move(self.output().path)


    def output(self):
        return luigi.LocalTarget('work/{}/{}/{}.grobid.STAMP'.format(self.crawl, self.item, self.warc))


class ItemGrobidJson(luigi.Task):

    crawl = luigi.Parameter()
    item = luigi.Parameter()

    # Don't keep trying over and over!
    retry_count = 1

    def requires(self):
        return [(Executable(name='bin/grobid2json.py'),
                 Executable(name='jq')),
                ItemGrobidServiceExtract(crawl=self.crawl, item=self.item)]

    def run(self):

        grobid_dir = "work/{}/{}/grobid_tei".format(self.crawl, self.item)
        json_dir = "work/{}/{}/grobid_json".format(self.crawl, self.item)
        shellout("mkdir -p {json_dir}", json_dir=json_dir)

        # Generate fulltext json (one file per PDF)
        for tei_path in glob.glob(grobid_dir + "/*.tei.xml"):
            json_path = tei_path.replace('/grobid_tei/', '/grobid_json/')\
                                .replace('.tei.xml', '.json')
            # jq in the pipeline validates JSON
            shellout("""
                bin/grobid2json.py {tei_path}
                    | jq -c .
                    > {json_path}""",
                tei_path=tei_path,
                json_path=json_path)

        # Just the header info (one json file for the whole item)
        # jq in the pipeline validates JSON
        output = shellout("""
            cd {grobid_dir}
            && find . -name "*.tei.xml"
                | parallel -j 4 ../../../../bin/grobid2json.py --no-encumbered {{}}
                | jq -c .
                > {output}""",
            grobid_dir=grobid_dir)

        luigi.LocalTarget(output).move(self.output().path)

    def output(self):
        return luigi.LocalTarget('work/{crawl}/{item}/{item}_grobid_metadata.json'.format(crawl=self.crawl, item=self.item))


class ItemGrobidTarballs(luigi.Task):

    crawl = luigi.Parameter()
    item = luigi.Parameter()

    # Don't keep trying over and over!
    retry_count = 1

    def requires(self):
        return [(Executable(name='bin/grobid2json.py'),
                 Executable(name='jq')),
                ItemGrobidJson(crawl=self.crawl, item=self.item)]

    def run(self):

        base_dir = "work/{}/{}".format(self.crawl, self.item)

        manifest_tmp = shellout("""
            cd {base_dir}
            && find . \( -path "./pdfs/*.pdf" -o -path "./grobid_tei/*.tei.xml" -o -path "./grobid_json/*.json" -o -path "./*grobid_metadata.json" \)
            | parallel -j3 sha1sum {{}}
                > {output}""",
            base_dir=base_dir)

        shellout("tar -C {base_dir} -czf {item}_grobid_json.tar.gz grobid_json", base_dir=base_dir, item=self.item)
        shellout("tar -C {base_dir} -czf {item}_grobid_tei.tar.gz grobid_tei", base_dir=base_dir, item=self.item)
        shellout("gzip --keep {base_dir}/{item}_grobid_metadata.json", base_dir=base_dir, item=self.item)

        # Move the manifest file over
        luigi.LocalTarget(manifest_tmp).move(self.output().path)

    def output(self):
        return luigi.LocalTarget('work/{crawl}/{item}/{item}_grobid.sha1sum'.format(
            crawl=self.crawl, item=self.item))


class ItemGrobidUpload(luigi.Task):

    crawl = luigi.Parameter()
    item = luigi.Parameter()

    # Don't keep trying over and over!
    retry_count = 1

    def requires(self):
        return [(Executable(name='bin/grobid2json.py'),
                 Executable(name='jq')),
                ItemGrobidTarballs(crawl=self.crawl, item=self.item)]

    def run(self):

        base_dir = "work/{}/{}/".format(self.crawl, self.item)

        upload_list = [
            base_dir + "{}_grobid_tei.tar.gz".format(self.item),
            base_dir + "{}_grobid_json.tar.gz".format(self.item),
            base_dir + "{}_grobid_metadata.json.gz".format(self.item),
            base_dir + "{}_grobid.sha1sum".format(self.item),
            #base_dir + "{}_grobid.timing".format(self.item), # not in service extract
        ]

        # upload result to item
        shellout("""ia upload --no-derive --checksum {item} {files}""",
            item=self.item,
            files=" ".join(upload_list))

        output = shellout("echo done > {output}")
        luigi.LocalTarget(output).move(self.output().path)

    def output(self):
        return luigi.LocalTarget('work/{}/{}/uploaded.STAMP'.format(self.crawl, self.item))


class ItemGrobidCleanup(luigi.Task):

    crawl = luigi.Parameter()
    item = luigi.Parameter()

    # Don't keep trying over and over!
    retry_count = 1

    def requires(self):
        return [ItemGrobidUpload(crawl=self.crawl, item=self.item)]

    def run(self):

        base_dir = "work/{}/{}/".format(self.crawl, self.item)
        pdf_dir = "work/{}/{}/pdfs".format(self.crawl, self.item)
        grobid_dir = "work/{}/{}/grobid_tei".format(self.crawl, self.item)
        json_dir = "work/{}/{}/grobid_json".format(self.crawl, self.item)

        shellout("rm -f {json_dir}/*.json", json_dir=json_dir)
        shellout("rm -f {grobid_dir}/*.xml", grobid_dir=grobid_dir)
        shellout("rm -f {base_dir}/*arc.gz", base_dir=base_dir)
        shellout("rm -f {pdf_dir}/*pdf", pdf_dir=pdf_dir)

        output = shellout("echo done > {output}")
        luigi.LocalTarget(output).move(self.output().path)

    def output(self):
        return luigi.LocalTarget('work/{}/{}/cleanup.STAMP'.format(self.crawl, self.item))


class ExtractCrawl(luigi.Task):
    """Reads CrawlItemsList, creates a ItemPdfExtract for each"""

    crawl = luigi.Parameter()
    cleanup = luigi.BoolParameter(default=False)

    def requires(self):
        return CrawlItemsList(self.crawl)

    def run(self):
        todo_file = self.input()
        all_jobs = list()
        with todo_file.open() as handle:
            for row in handle:
                row = row.strip()
                if self.cleanup:
                    all_jobs.append(
                        ItemGrobidCleanup(crawl=self.crawl, item=row))
                else:
                    all_jobs.append(
                        ItemGrobidUpload(crawl=self.crawl, item=row))

        yield all_jobs

        # Combine all metadata
        output = shellout("""
            cat work/{crawl}/*/grobid_metadata.json
                > {output}""",
            crawl=self.crawl)
        luigi.LocalTarget(output).move(self.output().path)

    def output(self):
        return luigi.LocalTarget('work/%s.metadata.json' % (self.crawl))

