---
confluence-page-title: "PDF Metadata Extraction Tooling"
confluence-page-id: 199720961
...

Motivation is to select a PDF parsing and metadata extraction tool to run over
potentially huge numbers of crawled PDFs. The primary goal is to get enough
metadata about the file (title, author) to match against existing catalogs and
resolve a persistant identifier (aka, DOI) for the file.

But, "while we're at it", a strong secondary goal is to extract as much
metadata (including citations) and fulltext as possible to enable later
fulltext search, machine learning, fingerprinting (simhash), analytics, and
discovery tools.

## Comparison Summary

Based on parsing approximately 1000 previously-identified PDFs, and measuring
success in matching against the "known-good" metadata from Crossref...

<table>
 <tr>
  <th>Tool</th>
  <th>Max CPU (of 400%)</th>
  <th>Max RAM</th>
  <th>CPU Sec/file</th>
  <th>Token Match frac</th>
  <th>Fuzzy Match frac</th>
  <th>DOI Match frac</th>
 </tr>
 <tr>
  <td>CERMINE</td>
  <td>106%</td>
  <td>2.8 GB</td>
  <td>7.8</td>
  <td>72.3%</td>
  <td>76.3%</td>
  <td>34.3% (4.3% false)</td>
 </tr>
 <tr>
  <td>GROBID</td>
  <td>56%</td>
  <td>4.9 GB</td>
  <td>0.26</td>
  <td>77.3%</td>
  <td>81.2%</td>
  <td>40.0% (4.7% false)</td>
 </tr>
 <tr>
  <td>Science Parse</td>
  <td>335%</td>
  <td>6.8 GB</td>
  <td>1.2</td>
  <td>75.5%</td>
  <td>85.1%</td>
  <td>N/A</td>
 </tr>
</table>

Note that GROBID does *not* extract fulltext, references, etc by default, while
the other tools do, which probably explains the performance difference. GROBID
can do these extractions. Without being able to compare against GROBID, CERMINE
seems to do a subjectively better job extracting references than Science Parse.

I think the selection is basically between Science Parse and GROBID. I am
leaning towards GROBID.

A back-of-the-envelope estimate (probably accurate within a factor of two, but
many caveats apply) of the time and CPU cost to parse 100 million PDF files
using 12 nodes is two weeks, which would cost about $1000 using cloud services.
Using GROBID (just for identification) could be less than half of that.

## Extractor Tools

Ended up comparing 3 tools:

**CERMINE** (version 1.13, active, Java, GPL3), first released around 2015 by a
team at University of Warsaw. Run as a pulic service at
[http://cermine.ceon.pl](). This "Center for Open Science" group (CeON) should
not be confused with COS (the US non-profit). Outputs JATS XML, which works
with many other tools.

**GROBID** (version 0.4.4, active, Java, Apache), developed since 2008 by a
small team in Europe which now seem to be doing a "science mining" company.
Outputs XML in "TEI" format. Specifically supports hitting the Crossref live
API and exporting in OpenURL format (?). Claims to support internationalization
(CJK and Arabic, probably many more). Seems to be used by ResearchGate (based
on credits file).

**Science Parse** (version v1.3.0, active, Scala, Apache), developed since 2015
by Semantic Scholar (AI2). Outputs JSON. Does not detect DOI of the work.

I did not compare the following other tools:

**RefExtract** (python, CERN, GPL2), which is very focused on just extracting
references.

**ParsCit** (perl), used by CiteseerX, seems clunky and out of date.
**biblicit**, a forked version, now explicitly recommends GROBID in the README.

I broadly researched other tools, particularly simple targeted tools to find
the DOI of a paper. Many of these seemed to be total junk, work only with PDFs
from particular publishing software, use the PDF title only, or use non-public
online databases (eg, searching for a random sentance in Google Scholar).

## Resource Consumption

All extractors use the Java VM and had their heaps capped at 6 GB of RAM
(`-Xmx6g`). The extractors varied in how aggressively they were able to consume
CPU resources; I used the number of CPU seconds consumed, not the "wall time",
on the assumption that we can tune or run extractors in parallel to ensure they
are utilizing CPU as efficiently as possible.

Each second of CPU processing time per file requires about 12 days of CPU core
time, or 2 days node time with a 6 core machine for 1 million files. This is a
lower bound; network transfer and other inefficiency will slow actual things
down. As an order of magnitude estimate though, if we need 1 sec/file, 100
million PDFs could be processed by a 12 node cluster (72 cores total) in about
two weeks. That would cost ~$2000 on AWS, or ~$1000 on DigitalOcean; presumably
our operating costs are even lower. Great!

Testing was on bnewbold's laptop, which was "lightly" in use turing testing:

- Thinkpad X1
- CPU: 2.9 GHz i5-5300U, "4" cores, 2 physical
- 8 GB RAM
- fast SSD

## Methodology

Started with a 1000 file list. 2 files failed to download at all, and another
11 are not detected by `file` as PDF for other reasons. One file seems to be a
PDF but `file` doesn't detect it as such. Will use the number 988 as the number
of PDF files to attempt extraction from, and 998 as the number of files parsed
(in terms of seconds-per-file). All tools were directed to parse all files, and
none crashed from invalid or corrupt data.

These files came from an intermediate step of manifest processing, so we only
ended up with valid crossref metadata for 964 (to compare accuracy against).

Output from each tool was normalized into a JSON format (one line per input
file). The extracted metadata for each input file was matched against the known 
crossref metadata in a relatively conservative fashion (eg, both title and
author last names have to match pretty closely) using arbitrary algorithms I
came up with on the spot. Note that this last stage is different from what we
would do in production, where we would need to search or join metadata against
the huge catalog (a big O(n^2) process, 100 million by 100 million) to get a
small set of potential matches, then run the match tool plus other logic to
confirm an identification. DOI identification/extraction could significantly
speed up this process (by first attempting a match against the detected DOI,
then falling back to fuzzy matching).

For each tool, I used the default configuration, meaning I didn't re-train
against this particular data set. Most extractors seem to be trained/tuned
against PubMed or Arxiv works in English by default; it might be worth training
against a more diverse corpus later.

## Future Work

One could imagine extending this comparison with:

- full end-to-end analysis of accuracy (including false positive matches)
- larger sample set
- comparing other extracted info of interest (references, fulltext, abstracts,
  affiliations)
- faceted analysis (eg, better or worse matching for particular fields)
- focus on scanned/OCR'd works (majority here are born-digital)
- re-training extractors

## Reading / References

For more detailed resources (eg, scripts and installation instructions), see
the `bnewbold/pdf-extraction` repo on git.archive.org.

Background reading:

- [Arxiv's recent experimentation with PDF extraction][arxiv] from Sept 2017,
  very similar to this analysis, and similar conclusions.
- Google Scholar tech notes
  - [https://scholar.google.com/intl/en/scholar/inclusion.html#crawl]()
  - [https://scholar.google.com/intl/en/scholar/inclusion.html#indexing]()
- [Docear’s PDF Inspector: Title Extraction from PDF files][docear]

[arxiv]: https://blogs.cornell.edu/arxiv/2017/09/27/development-update-reference-extraction-linking/
[docear]: https://pdfs.semanticscholar.org/753d/9c1d2c1f7e4fb7e474236f9409d2e2590142.pdf
