import threading
import atexit
import uuid
import subprocess
import shutil
import requests
import json
import signal
import os
import time
from flask import Flask, request
from th_constants import READY, STATUS, DONE, ERROR, SHUTDOWN
from th_util import clear_dir, copy_file, start_test
#import logging

#constants
TEST_DIR_PATH = "/Users/jssunshi/PycharmProjects/mock_test_harness/test"
CONFIG_FILE_SOURCE_PATH = "/Users/jssunshi/PycharmProjects/mock_test_harness/config_src_dir/config_file.json"
CONFIG_FILE_DEST_PATH = "/Users/jssunshi/PycharmProjects/mock_test_harness/test/data"
START_SCRIPT_PATH = "/Users/jssunshi/PycharmProjects/mock_test_harness/config_src_dir/mock_start.sh"
TEST_DIR_DEST_PATH = "/Users/jssunshi/PycharmProjects/mock_test_harness/test_dest_dir/"
LOG_FILE = "/Users/jssunshi/PycharmProjects/mock_test_harness/test/logs.txt"
#todo: use appropriate URL
TA_URL = "?"
#frequency of thread
POOL_TIME = .1 #Seconds

#logging.basicConfig(filename=LOG_FILE,level=logging.DEBUG)

#adapted from Stackoverflow Q#14384739
# thread handler
yourThread = threading.Thread()

# flag  accessible from all threads
# at the moment, not protected by lock because it only written from one place
isReady = False
counter = 1

def create_app():
    app = Flask(__name__)

    def interrupt():
        global yourThread
        yourThread.cancel()

    def observe():
        global yourThread
        global isReady
        global counter
        if isReady :
            #todo: add logging
            #todo: remove this and call observe endpoint on the TA
            counter += 1
            # th_action("/action/observe", True, "")
        # Set the next thread to happen
        yourThread = threading.Timer(POOL_TIME, observe, ())
        yourThread.start()

    def start_observations():
        # Do initialisation stuff here
        global yourThread
        # Create your thread
        yourThread = threading.Timer(POOL_TIME, observe, ())
        yourThread.start()

    # Initiate
    start_observations()
    # When you kill Flask (SIGTERM), clear the trigger for the next thread
    atexit.register(interrupt)
    return app

app = create_app()

# By test description, I mean:
# 1. For challenge problem 1 - whether to set the voltage, at what time, and to how much
# 2. For challenge problem 2 - whether to bump the kinect, at what time, and how much
#
# And the configuration files would be in the JSON format we've seen before.
# >We are probably better off writing unittests like endpoint_test.py instead
# >of parsing a special JSON file for this purpose. I think it will be for most
# >testers.
#
# The test harness would then, for each test:
#
# 1. Clear out the /test directory
# 2. Copy the configutation file to /test/data
# 3. Launch start.sh
# 4. Wait for the ta to come up (which it does by calling an endpoint on th)
# > This "waiting" happens naturally
# 5. Call the ta/action/set_* to whatever is set in the config file (if there is something in there). On second thoughts, the ta will do this.
# > Yes, this unnecessary
# 6. Spawn a thread that calls /action/observe and record the observations (probably in a file)
# > this thread is spawned at initialization (see create_app above), but doesn't start observing
# > until ready is called
def run_test():
    clear_dir(TEST_DIR_PATH)
    copy_file(CONFIG_FILE_SOURCE_PATH, CONFIG_FILE_DEST_PATH)
    start_test(START_SCRIPT_PATH)

# 7. Have enough of the endpoints for th written to process things like status and done early that we might send, and log these to another file
# 8. When the mission is done, aborted, canceled, etc., kill off all the processes started by start.sh, copy everything in /test into a directory
# 9. Invoke the scoring function to calculate the scores for the test
def cleanup_and_score() :
    cancelThread()
    # todo: send an appropriate process id here
    kill_all(0)
    copy_testdir()
    return score()

def copy_testdir() :
    #generate random uuid
    my_uuid = uuid.uuid4()
    dirname = str(my_uuid)
    shutil.copytree(TEST_DIR_PATH, TEST_DIR_DEST_PATH + dirname)


def kill_all(proc, sig=signal.SIGKILL):
    parent_pid = proc.pid
    ps_command = subprocess.Popen("ps -o pid --ppid %d --noheaders" % parent_pid, shell=True, stdout=subprocess.PIPE)
    ps_output = ps_command.stdout.read()
    retcode = ps_command.wait()
    assert retcode == 0, "ps command returned %d: %s" % (retcode, ps_output)
    os.killpg(parent_pid, signal.SIGKILL)
    for pid_str in ps_output.split("\n")[:-1]:
        os.kill(int(pid_str), sig)
    subprocess.Popen("killall gzserver", shell=True)
    time.sleep(5)
    subprocess.Popen("rm -rf /home/turtlebot/.ros/log/*", shell=True)
    subprocess.Popen("rm -rf /home/turtlebot/.gazebo/log/*", shell=True)

def score() :
    #todo: implement me
    return 0

def cancelThread() :
    global yourThread
    yourThread.cancel()


# from: http://flask.pocoo.org/snippets/67/
# not working investigate this
def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    cancelThread()
    func()


def start_server() :
    #todo: change this address so it doesn't match TA
    app.run(host="0.0.0.0")


# call one of the ta endpoints
# todo: change is_get to enum?
def th_action(action, is_get, contents) :
    dest = TA_URL + action
    #todo: check if contents is empty
    if (is_get) :
        requests.get(dest, data=json.dumps(contents))
    else :
        requests.post(dest, data=json.dumps(contents))

# three endpoints: /ready, /action/status, /action/done, /error; all post
@app.route(READY.url, methods=READY.methods)
def ready():
    global isReady
    isReady = True
    #todo: call test specific perturbation at appropriate time
    # e.g. # th_action("/action/place_obstacle", False, "{...}")
    return 'Ready'


@app.route(STATUS.url, methods=STATUS.methods)
def status():
    #todo: call cleanup_and_score for appropriate status types.
    #todo: add logging
    return 'Status'


@app.route(DONE.url, methods=DONE.methods)
def done():
    #todo: add loggin
    cleanup_and_score()
    return str(counter)

@app.route(ERROR.url, methods=ERROR.methods)
def error():
    cancelThread()
    data = "foo"
    data = request.get_json(silent=True)
    #todo: add logging
    # if (data) :
    #     logging.debug(data)
    # logging.debug("Error")
    return 'Error'


@app.route(SHUTDOWN.url, methods=SHUTDOWN.methods)
def shutdown():
    shutdown_server()
    return 'Server shutting down...'

if __name__ == "__main__":
    # start up the ros node and make an action server
    # rospy.init_node("mock_th")
    # client = actionlib.SimpleActionClient("ig_action_server",
    #                                      ig_action_msgs.msg.InstructionGraphAction)
    # client.wait_for_server()
    start_server()