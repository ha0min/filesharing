#!/usr/bin/env python  
# -*- coding:utf-8 _*-

""" 

@Author: Haomin Cheng
@File Name: flask_server.py 
@Time: 2023/11/24
@Contact: haomin.cheng@outlook.com

"""
import sys
import socket

from flask import Flask, json, request

from supernode import init_server
from utils import common, endpoints
from utils.colorfy import *
from chord import hash

app = Flask(__name__)


@app.route('/', methods=['GET'])
def home():
    return "Hello, world, flask server is running!"


@app.route(endpoints.node_info, methods=['GET'])
def info():
    """
    Return the information of the node.
    """
    return json.dumps(
        {"ip": common.my_ip, "port": common.my_port, "id": common.my_id, "boot": common.boot, "mids": common.mids,
         "nids": common.nids})


@app.route(endpoints.ping, methods=['GET'])
def ping():
    """
    Return "pong" if the node is alive.
    """
    return "pong"


@app.route(endpoints.join_bootstrap , methods = ['POST'])										# join(nodeID)
def boot_join():
	if common.boot:
		new_node = request.form.to_dict()
		return bootstrap_join_func(new_node)
	else:
		print(red("This is not the bootstrap node..."))


def server_start():
    """
    Entry point of the flask server.
    :return:
    """
    common.server_starting = True
    if len(sys.argv) < 4:
        wrong_input_format()
    if sys.argv[1] in ("-p", "-P"):
        common.my_port = sys.argv[2]
    else:
        wrong_input_format()
    common.my_ip = get_my_ip()
    if len(sys.argv) == 4 and sys.argv[3] in ("-b", "-B"):
        print("I am the Bootstrap Node with ip: " + yellow(
            common.my_ip) + " about to run a Flask server on port " + yellow(common.my_port))
        common.my_id = hash(common.my_ip + ":" + common.my_port)
        print("and my unique id is: " + green(common.my_id))
        common.is_bootstrap = True
        init_server()

    else:
        common.is_bootstrap = False
        print("I am a normal Node with ip: " + yellow(common.my_ip) + " about to run a Flask server on port " + yellow(
            common.my_port))
        common.my_id = hash(common.my_ip + ":" + common.my_port)
        print("and my unique id is: " + green(common.my_id))
        # x = threading.Thread(target=node_initial_join, args=[])
        # x.start()

    app.run(host=common.my_ip, port=common.my_port, debug=True, use_reloader=False)


def wrong_input_format():
    print(red("Argument passing error!"))
    print(underline("Usage:"))
    print(cyan(
        "-p port_to_open\n -k replication_factor (<= number of nodes)\n -c consistency_type ((linear,l) or (eventual,"
        "e))\n -b for bootstrap node only"))
    exit(0)


def get_my_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


if __name__ == '__main__':
    server_start()
