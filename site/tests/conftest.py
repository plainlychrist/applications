# vim: smarttab tabstop=4 shiftwidth=4 expandtab softtabstop=4 filetype=python
# vim: set syntax=python:
import pytest
import Queue
import subprocess
import sys
import threading
import time

EMPTY_BOOTSTRAP = "setup/docker-compose-site-empty-bootstrap.yml"
TESTS_PROJECT = "plainlychristtests"
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

def enqueue_output(out, queue):
    """
    Read every line from 'out' and place into 'queue'

    This blocks until 'out' has no more lines, and then this will close 'out'.
    """
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()

@pytest.fixture(scope="session")
def site_with_empty_bootstrap(request):
    start_docker_compose(request, EMPTY_BOOTSTRAP)
    return Site('https://localhost:10443')

def start_docker_compose(request, docker_compose_file):
    # shutdown the container, if it is already running
    subprocess.call(["docker-compose", "-p", TESTS_PROJECT, "-f", docker_compose_file, "down"])

    # run the container in the background, which prints the docker container name
    p = subprocess.Popen(["docker-compose", "-p", TESTS_PROJECT, "-f", docker_compose_file, "up", "-d"], stdout=subprocess.PIPE)
    (output, err) = p.communicate()
    p_status = p.wait()
    if p_status != 0:
        raise TestError("exit code = %s" % (p_status))

    # on teardown, shutdown the container
    def fin():
        sys.stderr.write("\n\nShutting down the container ...\n\n")
        sys.stderr.flush()
        subprocess.call(["docker-compose", "-p", TESTS_PROJECT, "-f", docker_compose_file, "down"])
    request.addfinalizer(fin)

    # read the container logs in the background
    p = subprocess.Popen(["docker-compose", "-p", TESTS_PROJECT, "-f", docker_compose_file, "logs", "--follow", "--timestamps"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    q = Queue.Queue()
    t = threading.Thread(target=enqueue_output, args=(p.stdout, q))
    t.daemon = True # when the program exits, this thread will exit
    t.start() # start thread
    read_until = time.time() + READ_TIMEOUT_SECS # max READ_TIMEOUT_SECS seconds to start up
    success = False
    while time.time() < read_until:
        try:
            out = q.get_nowait()
            if out != '':
                sys.stderr.write(out)
                sys.stderr.flush()
            if 'apache2 entered RUNNING state' in out:
                success = True
                break
        except Queue.Empty: time.sleep(0.1)
    p.kill() # stop following the logs
    if not success: 
        raise TestError("The container did not start apache2 successfully in %s seconds" % (READ_TIMEOUT_SECS))

    # return the container name on setup
    return output
