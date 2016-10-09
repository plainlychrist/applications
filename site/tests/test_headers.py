import requests

def test_http_status_ok(site_with_empty_bootstrap):
    r = requests.get('https://localhost:10443', verify=False)
    assert r.status_code == 200

def test_strict_transport_security_enabled(site_with_empty_bootstrap):
    r = requests.get('https://localhost:10443', verify=False)
    assert r.headers['Strict-Transport-Security'] == 'max-age=63072000; includeSubdomains;'

def test_clickjacking_stopped(site_with_empty_bootstrap):
    r = requests.get('https://localhost:10443', verify=False)
    assert r.headers['X-Frame-Options'] == 'SAMEORIGIN'

def test_no_cookies_for_anonymous_users(site_with_empty_bootstrap):
    r = requests.get('https://localhost:10443', verify=False)
    assert not r.cookies
