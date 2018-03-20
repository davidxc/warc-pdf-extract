#!/usr/bin/python

"""
Test this script:

    echo "uk,ac,warwick)/fac/sci/hri2/research/biodiseasecontrol/alliumwhiterot/2003clarksonwrposter.pdf 20050426054216 http://www2.warwick.ac.uk:80/fac/sci/hri2/research/biodiseasecontrol/alliumwhiterot/2003clarksonwrposter.pdf application/pdf 200 AAAAAAPUDWOG7X4VM4344VEXCSNMDIQ2 - - 563414 76545698 ED_binary1_crawl32.20050426045431-c/ED_binary1_crawl32.20050426054105.arc.gz\nde,vw-bus-t4)/getfile.php?d=sh&getfile=st_ra%20alte%20hydronic.pdf 20101201115907 http://vw-bus-t4.de/getfile.php?getfile=ST_RA%20alte%20Hydronic.pdf&d=sh application/pdf 200 AAAAADYZLKZ3NHCGNVCAYBW6CSNF2VJR - - 3296019 885491467 WIDE-20101201111236882-02365-02383-ia360903/WIDE-20101201115326213-02371-29762~ia360903.us.archive.org~9443.warc.gz\ninfo,olci)/(jnazoxi5ftorvw45ewninanp)/pdf/animalassistedtherapy.pdf 20061011044733 http://www.olci.info/(jnazoxi5ftorvw45ewninanp)/pdf/animalassistedtherapy.pdf application/pdf 200 AAAAAFLH52EXP666UOWKBILWHQK4ZQIJ - - 30169 21320631 ACC-20061011044024-08450-c07.ba.accelovation.com-c/ACC-20061011044317-09757-c05.ba.accelovation.com.arc.gz" | ./script.py
"""

import sys
import requests

GROBID_SERVER="http://wbgrp-svc096.us.archive.org:8070"

def do_line(line_split):
    dt = line_split[1]
    url = line_split[2]

    wb_url = "https://web.archive.org/{}/{}".format(dt, url)
    pdf_resp = requests.get(wb_url)
    if pdf_resp.status_code is not 200:
        # TODO: log failure somewhere?
        print("FAIL (download: {}): {}".format(pdf_resp.content.decode('utf8'), url))
        return

    r = requests.post(GROBID_SERVER + "/api/processFulltextDocument",
            files={'input': pdf_resp.content})
    if r.status_code is not 200:
        print("FAIL (Grobid: {}): {}".format(r.content.decode('utf8'), url))
    else:
        print("SUCCESS: " + url)

for line in sys.stdin:
    line_split = line.split()
    if len(line_split) < 10:
        # Doesn't seem like a CDX line, skip silently
        continue
    try:
        do_line(line_split)
    except:
        # TODO: catch keyboard interupt
        print("ERROR")
print("DONE")
