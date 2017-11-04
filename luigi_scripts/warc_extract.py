
import subprocess
import tempfile
import datetime
import time
import json
import os

import luigi
from gluish.common import Executable
from gluish.utils import shellout
from gluish.format import TSV
import requests

# XXX: config values somewhere?
GROBID_JAR="/home/bnewbold/src/grobid/grobid-grobid-parent-0.4.4/grobid-core/target/grobid-core-0.4.4-SNAPSHOT.one-jar.jar"
GROBID_HOME="/home/bnewbold/src/grobid/grobid-grobid-parent-0.4.4/grobid-home/"


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
            shellout("mv {saved} new_path",
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

        warc_list = [l.strip() for l in input_manifest.readlines()]
        downloaded_warcs = ["work/{}/{}/{}".format(self.crawl, self.item, w) for w in warc_manifest]

        pdfdir = "work/{}/{}/pdfs".format(self.crawl, self.item)
        shellout("mkdir -p {pdfdir}", pdfdir)

        shellout("""
            warc_extract_filter.py {pdfdir} {infiles}
                --min-size 512
                --max-size 268435456
                --mimetype pdf
                --out-suffix .pdf""",
            outdir=outdir,
            infiles=" ".join(downloaded_warcs))

        output = shellout("echo 'done > {output}")
        luigi.LocalTarget(output).move(self.output().path)

    def output(self):
        return luigi.LocalTarget('work/{}/{}/pdfs.STAMP'.format(self.crawl, self.item))


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
        shellout("mkdir -p {grobid_dir}", grobid_dir)

        # XXX: set GROBID path
        output = shellout("""
            /usr/bin/time -v -o {output}
            java
                -Xmx6G
                -jar {GROBID_JAR}
                -gH {GROBID_HOME}
                -dIn {pdf_dir}
                -r
                -dOut {grobid_dir}
                -exe processFulltext""",
            pdf_dir=pdf_dir,
            grobid_dir=grobid_dir,
            GROBID_JAR=GROBID_JAR,
            GROBID_HOME=GROBID_HOME)

        luigi.LocalTarget(output).move(self.output().path)

    def output(self):
        return luigi.LocalTarget('work/{}/{}/grobid.timing'.format(self.crawl, self.item))


class ItemGrobidJson(luigi.Task):

    crawl = luigi.Parameter()
    item = luigi.Parameter()

    # Don't keep trying over and over!
    retry_count = 1

    def requires(self):
        return [(Executable(name='bin/grobid2json.py'),
                 Executable(name='jq')),
                ItemGrobidExtract(crawl=self.crawl, item=self.item)]

    def run(self):

        grobid_dir = "work/{}/{}/grobid_tei".format(self.crawl, self.item)
        json_dir = "work/{}/{}/grobid_json".format(self.crawl, self.item)
        shellout("mkdir -p {json_dir}", json_dir)

        # XXX: GROBID JSON fulltext (for file in ...)

        # Just the header info
        # jq in the pipeline ensures valid JSON
        shellout("""
            ls {grobid_dir}/*tei.xml
                | parallel -j 4 bin/grobid2json.py --no-encumbered {}
                | jq .
                > {output}""",
            grobid_dir=grobid_dir,
            GROBID_JAR=GROBID_JAR,
            GROBID_HOME=GROBID_HOME)
        luigi.LocalTarget(output).move(self.output().path)

    def output(self):
        return luigi.LocalTarget('work/{}/{}/grobid_metadata.json'.format(self.crawl, self.item))


# XXX: tarball things up
# XXX: upload and cleanup (delete PDFs, WARCs)


class ItemGrobidTarballs(luigi.Task):

    crawl = luigi.Parameter()
    item = luigi.Parameter()

    # Don't keep trying over and over!
    retry_count = 1

    def requires(self):
        return [(Executable(name='bin/grobid2json.py'),
                 Executable(name='jq')),
                ItemGrobidExtract(crawl=self.crawl, item=self.item)]

    def run(self):

        # NB: NO trailing slashes in the below
        base_dir = "work/{}/{}/".format(self.crawl, self.item)
        pdf_dir = "work/{}/{}/pdfs".format(self.crawl, self.item)
        grobid_dir = "work/{}/{}/grobid_tei".format(self.crawl, self.item)
        json_dir = "work/{}/{}/grobid_json".format(self.crawl, self.item)

        manifest_tmp = shellout("""
            sha1sum {pdf_dir} {grobid_dir} {json_dir} {json_dir}/../grobid_metadata.json
                > {output}""",
            pdf_dir=pdf_dir,
            grobid_dir=grobid_dir,
            json_dir=json_dir)

        shellout("tar czf {json_dir}.tar.gz {json_dir}", json_dir)
        shellout("tar czf {grobid_dir}.tar.gz {grobid_dir}", grobid_dir)

        # Move the manifest file over
        luigi.LocalTarget(manifest_tmp).move(self.output().path)

    def output(self):
        return luigi.LocalTarget('work/{}/{}/grobid.sha1sum'.format(self.crawl, self.item))


class ItemGrobidUpload(luigi.Task):

    crawl = luigi.Parameter()
    item = luigi.Parameter()
    cleanup = luigi.BoolParameter(default=False)

    # Don't keep trying over and over!
    retry_count = 1

    def requires(self):
        return [(Executable(name='bin/grobid2json.py'),
                 Executable(name='jq')),
                ItemGrobidTarballs(crawl=self.crawl, item=self.item)]

    def run(self):

        base_dir = "work/{}/{}/".format(self.crawl, self.item)

        upload_list = [
            base_dir + "grobid_tei.tar.gz",
            base_dir + "grobid_json.tar.gz",
            base_dir + "grobid_metadata.json",
            base_dir + "grobid.log",
            base_dir + "grobid.sha1sum",
        ]

        # upload result to item
        shellout("""ia upload --no-derive --checksum {item} {files}""",
            item=self.item,
            files=" ".join(upload_list))

        if self.cleanup:
            shellout("rm {json_dir}/*.json", json_dir)
            shellout("rm {grobid_dir}/*.json", grobid_dir)
            shellout("rm {base_dir}/*arg.gz", base_dir)

        output = shellout("echo 'done > {output}")
        luigi.LocalTarget(output).move(self.output().path)

    def output(self):
        return luigi.LocalTarget('work/{}/{}/uploaded.STAMP'.format(self.crawl, self.item))


class ExtractCrawl(luigi.Task):
    """Reads CrawlItemsList, creates a ItemPdfExtract for each"""

    crawl = luigi.Parameter()

    def requires(self):
        return CrawlItemsList(self.crawl)

    def run(self):
        todo_file = self.input()
        all_jobs = list()
        with todo_file.open() as handle:
            for row in handle:
                row = row.strip()
                all_jobs.append(
                    ItemGrobidUpload(
                        crawl=self.crawl,
                        item=row))

        yield all_jobs

        # Combine all metadata
        output = shellout("""
            cat work/{crawl}/*/grobid_metadata.json
                > {output}""",
            crawl=self.crawl)
        luigi.LocalTarget(output).move(self.output().path)

    def output(self):
        return luigi.LocalTarget('work/%s.metadata.json' % (self.crawl))

