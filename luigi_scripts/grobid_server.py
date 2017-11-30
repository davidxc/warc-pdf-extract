
import luigi
import requests

__all__ = ['GrobidServer']

class GrobidServer(luigi.Task):
    """Helper to check that GROBID server is actually running and accessible
    """

    host_port = luigi.Parameter(default="http://localhost:8070")

    def run(self):
        raise RuntimeError("couldn't connect to GROBID server: %s" % host)

    def complete(self):
        r = requests.get(self.host_port + "/api/isalive")
        return r.status_code == 200 and b"true" in r.content

