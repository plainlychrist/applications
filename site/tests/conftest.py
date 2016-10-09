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
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()

@pytest.fixture(scope="session")
def site_with_empty_bootstrap(request):
    # shutdown the container, if it is already running
    subprocess.call(["docker-compose", "-p", TESTS_PROJECT, "-f", EMPTY_BOOTSTRAP, "down"])
     
    # run the container in the background, which prints the docker container name
    p = subprocess.Popen(["docker-compose", "-p", TESTS_PROJECT, "-f", EMPTY_BOOTSTRAP, "up", "-d"], stdout=subprocess.PIPE)
    (output, err) = p.communicate()
    p_status = p.wait()
    if p_status != 0:
        raise TestError("exit code = %s" % (p_status))
     
    # on teardown, shutdown the container
    def fin():
        subprocess.call(["docker-compose", "-p", TESTS_PROJECT, "-f", EMPTY_BOOTSTRAP, "down"])
    request.addfinalizer(fin)

    # read the container logs in the background
    p = subprocess.Popen(["docker-compose", "-p", TESTS_PROJECT, "-f", EMPTY_BOOTSTRAP, "logs", "--follow", "--timestamps"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
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
