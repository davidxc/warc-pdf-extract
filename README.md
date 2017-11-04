
This repo contains research, tools, and pipeline stuff for extracting metadata
from scholarly publication PDFs (eg, title, author) and matching against 
databases of bibliographic identifiers.

See `./notes/comparison_summary.md` for summary and conclusions.

See `./luigi_scripts/README.md` for summary and conclusions.

### Big Picture

Want to identify our tens of millions of crawled papers to identifiers
(specifically, DOI).

"While we're at it", should collect other extracted information, even including
fulltext.

Need to select the best tools for this task, and have an idea of the resource
consumption (aka, throughput) and accuracy involved.

### Run Tests

    nosetests3
