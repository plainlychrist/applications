# vim: smarttab tabstop=4 shiftwidth=4 expandtab softtabstop=4 filetype=python
# vim: set syntax=python:
import subprocess

def test_no_broken_links(site_with_empty_bootstrap):
    """
    Tests that the site has 0 broken links.

    At the moment, this uses an empty (default bootstrap) site. There should be another test for a full bootstrap-from-live site.
    """

    s = site_with_empty_bootstrap
    # https://github.com/stevenvachon/broken-link-checker/issues/42 ... ignore self-signed certificate
    output = subprocess.check_output([
        "bash",
        "-c",
        "TERM=ansi NODE_TLS_REJECT_UNAUTHORIZED=0 ~/node_modules/broken-link-checker/bin/blc --verbose %s" % (s.url)
        ],
        stderr=subprocess.STDOUT)
    assert '. 0 broken.' in output
