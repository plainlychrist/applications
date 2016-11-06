# vim: smarttab tabstop=4 shiftwidth=4 expandtab softtabstop=4 filetype=python
# vim: set syntax=python:
import pprint
import requests
from bs4 import BeautifulSoup
from urlparse import urlparse, urljoin

pp = pprint.PrettyPrinter(indent=4)

def visit_if_should_be_on_s2(s2, url):
    """
    Fails if the relative 'url' (if it is a relative url) on 's2' is not found.
    """

    if url.scheme == '': # only see if relative paths exist
        link_on_s2 = urljoin(s2.url, url.geturl())
        print("Fetching %s ..." % link_on_s2)
        r2 = requests.get(link_on_s2, verify=False)
        print(pp.pprint(r2.headers.items()))
        return r2.status_code
    return -1 # absolute path

def visit_and_assert_should_be_on_s2(s2, url):
    status_code = visit_if_should_be_on_s2(s2, url)
    assert status_code == 200 or status_code == -1
    return 1

def test_css_aggregation_across_two_separated_sites(two_sites_separated):
    """
    Tests that when a user accesses site "A", the links they receive DO NOT work on site "B", mimicking what a browser against a real load balancer would do
    if there were no sharing of sites/default/files.

    Why? Because CSS/JS Aggregation can generate unique files that are not present on other machines (unless it is configured correctly).
    """

    s1 = two_sites_separated[0]
    s2 = two_sites_separated[1]

    r1 = requests.get(s1.url, verify=False)

    soup = BeautifulSoup(r1.text, 'html.parser')
    links_404 = 0
    for link in soup.find_all('link'):
        url = urlparse(link.get('href'))
        status_code = visit_if_should_be_on_s2(s2, url)
        if status_code == 404: links_404 += 1
    for link in soup.find_all('script'):
        url = urlparse(link.get('src'))
        status_code = visit_if_should_be_on_s2(s2, url)
        if status_code == 404: links_404 += 1

    assert links_404 >= 1 # we expect at least one CSS or JS file not found

def test_css_aggregation_across_two_shared_sites(two_sites_shared):
    """
    Tests that when a user accesses site "A", the links they receive work on site "B", mimicking what a browser against a real load balancer would do.

    Why? Because CSS/JS Aggregation can generate unique files that are not present on other machines (unless it is configured correctly).
    """

    s1 = two_sites_shared[0]
    s2 = two_sites_shared[1]

    r1 = requests.get(s1.url, verify=False)

    soup = BeautifulSoup(r1.text, 'html.parser')
    links = 0
    for link in soup.find_all('link'):
        url = urlparse(link.get('href'))
        links += visit_and_assert_should_be_on_s2(s2, url)
    for link in soup.find_all('script'):
        url = urlparse(link.get('src'))
        links += visit_and_assert_should_be_on_s2(s2, url)

    assert links >= 3 # we expect at least a few CSS and JS files
