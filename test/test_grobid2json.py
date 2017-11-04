
from nose.tools import assert_equals
from bin.grobid2json import *


class TestConvert:

    def setup(self):
        self.test_file = "test/files/faca7e910d43d72609d32fb910a64623a6cee8e4.tei.xml"

    def test_header(self):
        extracted = do_tei(self.test_file)
        info = dict()
        info['title'] = "Exact and stable recovery of rotations for robust synchronization"
        info['authors'] = [
            dict(name="L Wang"),
            dict(name="A Singer"),
        ]
        info['journal'] = dict(
            name="Information and Inference",
            issn="2049-8764",
            eissn="2049-8772",
            publisher="Oxford University Press (OUP)",
            volume="2",
            issue="2")
        info['date'] = "2013"
        info['doi'] = "10.1093/imaiai/iat005"

        for field in ['title', 'authors', 'journal', 'date', 'doi']:
            assert_equals(info[field], extracted[field])

    def test_refs(self):
        extracted = do_tei(self.test_file)
        ref0 = dict()
        ref19 = dict()
        ref_count = 46

        ref0['index'] = 0
        ref0['id'] = 'b0'
        ref0['title'] = "On the concentration of eigenvalues of random symmetric matrices"
        ref0['authors'] = [
            dict(name="N Alon"),
            dict(name="M Krivelevich"),
            dict(name="V Vu"),
        ]
        ref0['journal'] = "Israel J. Math"
        ref0['publisher'] = None
        ref0['volume'] = "131"
        ref0['date'] = "2002"
        ref0['issue'] = None
        ref0['url'] = None

        ref19['index'] = 19
        ref19['id'] = 'b19'
        ref19['title'] = "Estimation and registration on graphs"
        ref19['authors'] = [
            dict(name="S Howard"),
            dict(name="D Cochran"),
            dict(name="W Moran"),
            dict(name="F Cohen"),
        ]
        ref19['journal'] = None
        ref19['publisher'] = None
        ref19['volume'] = None
        ref19['date'] = "2010-08-05"
        ref19['issue'] = None
        ref19['url'] = "http://arxiv.org/abs/1010.2983"

        assert_equals(ref0, extracted['citations'][0])
        assert_equals(ref19, extracted['citations'][19])

    def test_fulltext(self):
        """Checks that the body and other fulltext fields are extracted (fuzzy match)"""

        extracted = do_tei(self.test_file)

        ack_snip = "The authors thank Zaiwen Wen for many useful discussions regarding the ADM"
        abstract_snip = "The synchronization problem over the special orthogonal group SO(d)"
        body_snip = "The rotations obtained in this manner are uniquely determined up to a global rotation"

        assert ack_snip in extracted['acknowledgement']
        assert abstract_snip in extracted['abstract']
        assert body_snip in extracted['body']

    def test_excludes(self):
        """Test that copyright-encumbered stuff gets added if encumbered=False"""

        e = do_tei(self.test_file, encumbered=True)
        no_e = do_tei(self.test_file, encumbered=False)
        assert('title' in e.keys())
        assert('title' in no_e.keys())
        for field in 'body', 'acknowledgement', 'annex', 'abstract':
            assert field in e.keys()
            assert not field in no_e.keys()
