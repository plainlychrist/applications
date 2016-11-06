# vim: smarttab tabstop=4 shiftwidth=4 expandtab softtabstop=4 filetype=python
# vim: set syntax=python:
import requests

def test_http_status_ok(site_with_empty_bootstrap):
    s = site_with_empty_bootstrap
    r = requests.get(s.url, verify=False)
    assert r.status_code == 200

def test_strict_transport_security_enabled(site_with_empty_bootstrap):
    s = site_with_empty_bootstrap
    r = requests.get(s.url, verify=False)
    assert r.headers['Strict-Transport-Security'] == 'max-age=2592000; includeSubdomains'

def test_clickjacking_stopped(site_with_empty_bootstrap):
    s = site_with_empty_bootstrap
    r = requests.get(s.url, verify=False)
    assert r.headers['X-Frame-Options'] == 'SAMEORIGIN'

def test_cross_site_scripting_filtered(site_with_empty_bootstrap):
    s = site_with_empty_bootstrap
    r = requests.get(s.url, verify=False)
    assert r.headers['X-XSS-Protection'] == '1; mode=block'

def test_strict_content_type(site_with_empty_bootstrap):
    s = site_with_empty_bootstrap
    r = requests.get(s.url, verify=False)
    assert r.headers['X-Content-Type-Options'] == 'nosniff'

def test_content_security_policy(site_with_empty_bootstrap):
    s = site_with_empty_bootstrap
    r = requests.get(s.url, verify=False)
    assert r.headers['Content-Security-Policy'] == "script-src 'self'"

def test_no_permitted_cross_domain_policies(site_with_empty_bootstrap):
    s = site_with_empty_bootstrap
    r = requests.get(s.url, verify=False)
    assert r.headers['X-Permitted-Cross-Domain-Policies'] == 'none'

def test_no_cookies_for_anonymous_users(site_with_empty_bootstrap):
    s = site_with_empty_bootstrap
    r = requests.get(s.url, verify=False)
    assert not r.cookies
