# vim: smarttab tabstop=4 shiftwidth=4 expandtab softtabstop=4 filetype=python
# vim: set syntax=python:
import pytest
import Queue
import subprocess
import sys
import threading
import time

EMPTY_A_BOOTSTRAP =       "setup/docker-compose-site-empty-a-bootstrap.yml"
SHARED_A_B_BOOTSTRAP =    "setup/docker-compose-site-shared-a-and-b-bootstrap.yml"
SEPARATED_A_B_BOOTSTRAP = "setup/docker-compose-site-separated-a-and-b-bootstrap.yml"
EMPTY_A_PROJECT =       "plainlychristtest_empty_a"
SHARED_A_B_PROJECT =    "plainlychristtest_shared_a_b"
SEPARATED_A_B_PROJECT = "plainlychristtest_separated_a_b"
READ_TIMEOUT_SECS = 120

class TestError(Exception):
    """
    TestError is an error raising during testing
    """

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class Site:
    """
    A Site represents a running website
    """

    def __init__(self, url):
        self.url = url

    def __str__(self):
        return "url=%s" % (self.url)

@pytest.fixture(scope="session")
def site_with_empty_bootstrap(request):
    start_docker_compose(request, EMPTY_A_PROJECT, EMPTY_A_BOOTSTRAP, 1)
    return Site('https://localhost:10443')

@pytest.fixture(scope="session")
def two_sites_separated(request):
    start_docker_compose(request, SEPARATED_A_B_PROJECT, SEPARATED_A_B_BOOTSTRAP, 2)
    return [Site('https://localhost:11443'), Site('https://localhost:11543')]

@pytest.fixture(scope="session")
def two_sites_shared(request):
    start_docker_compose(request, SHARED_A_B_PROJECT, SHARED_A_B_BOOTSTRAP, 2)
    return [Site('https://localhost:12443'), Site('https://localhost:12543')]

def enqueue_output(out, queue):
    """
    Read every line from 'out' and place into 'queue'

    This blocks until 'out' has no more lines, and then this will close 'out'.
    """
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()

def start_docker_compose(request, project_name, docker_compose_file, expected_web_instances):
    # shutdown the container, if it is already running
    subprocess.call(["docker-compose", "-p", project_name, "-f", docker_compose_file, "down"])

    # run the container in the background, which prints the docker container name
    p = subprocess.Popen(["docker-compose", "-p", project_name, "-f", docker_compose_file, "up", "-d"], stdout=subprocess.PIPE)
    (output, err) = p.communicate()
    p_status = p.poll()
    if p_status != 0:
        raise TestError("exit code = %s" % (p_status))

    # on teardown, shutdown the container
    def fin():
        sys.stderr.write("\n\nShutting down the container ...\n\n")
        sys.stderr.flush()
        subprocess.call(["docker-compose", "-p", project_name, "-f", docker_compose_file, "down"])
    request.addfinalizer(fin)

    # read the container logs in the background
    p = subprocess.Popen(["docker-compose", "-p", project_name, "-f", docker_compose_file, "logs", "--follow", "--timestamps"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    q = Queue.Queue()
    t = threading.Thread(target=enqueue_output, args=(p.stdout, q))
    t.daemon = True # when the program exits, this thread will exit
    t.start() # start thread
    read_until = time.time() + READ_TIMEOUT_SECS # max READ_TIMEOUT_SECS seconds to start up
    success_nginx = 0
    success_php_fm = 0
    while time.time() < read_until:
        try:
            out = q.get_nowait()
            if out != '':
                sys.stderr.write(out)
                sys.stderr.flush()
            if 'nginx entered RUNNING state' in out:
                success_nginx += 1
            if 'php-fpm entered RUNNING state' in out:
                success_php_fm += 1
            if success_nginx == expected_web_instances and success_php_fm == expected_web_instances:
                break
        except Queue.Empty: time.sleep(0.1)
    # stop following the logs
    p.terminate()
    time.sleep(1)
    try:
        p.kill()
    except: pass
    if success_nginx != expected_web_instances:
        raise TestError("The container did not start nginx successfully %s time(s) within %s seconds. Actual starts: %s" % (expected_web_instances, READ_TIMEOUT_SECS, success_nginx))
    if success_php_fm != expected_web_instances:
        raise TestError("The container did not start php-fpm successfully %s time(s) within %s seconds. Actual starts: %s" % (expected_web_instances, READ_TIMEOUT_SECS, success_php_fm))

    # return the container name on setup
    return output
