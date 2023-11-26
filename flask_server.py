#!/usr/bin/env python  
# -*- coding:utf-8 _*-

""" 

@Author: Haomin Cheng
@File Name: flask_server.py 
@Time: 2023/11/24
@Contact: haomin.cheng@outlook.com

"""
import re
import sys
import socket
import threading

from flask import Flask, json, request, jsonify
from werkzeug.utils import secure_filename

import config
from supernode import init_server, bootstrap_join_func
from utils import common, endpoints
from utils.colorfy import *
from chord import hash, node_update_neighbours_func, node_replic_nodes_list, node_redistribute_data, \
    node_update_finger_table_func, insert_file_to_chord

app = Flask(__name__)


@app.route('/', methods=['GET'])
def home():
    return json.dumps(
        {"ip": common.my_ip, "port": common.my_port, "id": common.my_uid,
         "supernode": common.is_bootstrap,
         "mids": common.mids,
         "nids": common.nids}
    )


@app.route(endpoints.ping, methods=['GET'])
def ping():
    """
    Return "pong" if the node is alive.
    """
    return "pong"


@app.route(endpoints.node_join_bootstrap, methods=['POST'])  # join(nodeID)
def boot_join():
    if common.is_bootstrap:
        new_node = request.form.to_dict()
        return bootstrap_join_func(new_node)
    else:
        print(red(f"This is not the bootstrap node and not allowed for {endpoints.node_join_bootstrap}."))


@app.route(endpoints.node_join_procedure, methods=['POST'])
def join_procedure():
    print(red("Chord join procedure Start!"))
    if config.NDEBUG:
        print("chord_join_procedure is staring...")
    res = request.get_json()

    prev = res["prev"]
    next = res["next"]
    node_number = res["length"]
    node_list = []

    common.nids.append({"uid": prev["uid"], "ip": prev["ip"], "port": prev["port"]})
    common.nids.append({"uid": next["uid"], "ip": next["ip"], "port": next["port"]})
    if config.NDEBUG:
        print(yellow("Previous Node:"))
        print(common.nids[0])
        print(yellow("Next Node:"))
        print(common.nids[1])

    if common.k <= node_number:
        if config.NDEBUG:
            print("Node list creation is starting...")
        data = {"node_list": node_list, "k": common.k, "new_id": common.my_uid}
        node_list_json = node_replic_nodes_list(data)
        node_list = node_list_json["node_list"]
        if config.NDEBUG:
            print("i am the new node, i should get replica from these nodes: ", node_list)

        data = {"node_list": node_list, "new_id": common.my_uid}
        node_redistribute_data(data)

    if config.NDEBUG:
        print("Join of node completed - Overlay to check")

    return "Join Completed"


@app.route(endpoints.replic_nodes_list, methods=['POST'])
def get_response_chain():
    res = request.get_json()
    data = res["data"]
    return node_replic_nodes_list(data)


@app.route(endpoints.node_update_replicate, methods=['POST'])
def update_replicate():
    """
    Update the replicate nodes of the node.
    """
    if config.NDEBUG:
        print("Updating replicate nodes...")
    res = request.get_json()
    node_list = res["node_list"]
    common.mids = node_list
    if config.NDEBUG:
        print("Replicate nodes updated")
    return "Replicate nodes updated"


@app.route(endpoints.node_update_neighbours, methods=['POST'])  # update(nodeID)
def chord_update_neighbours():
    new_neighbours = request.get_json()
    return node_update_neighbours_func(new_neighbours)


@app.route(endpoints.node_update_finger_table, methods=['POST'])
def update_finger_table():
    """
    Update the finger table of the node.
    """
    res = request.get_json()
    if 'finger_table' not in res or 'timestamp' not in res:
        return "Invalid request format: 'timestamp' or'finger_table' key missing", 400

    if config.NDEBUG:
        print(red("Updating finger table..."))
        print(str(res))

    return node_update_finger_table_func(res)


@app.route(endpoints.node_new_file, methods=['POST'])
def upload_file():
    if 'file' not in request.files or 'name' not in request.form:
        return 'Please provide a file and a course title', 400

    file = request.files['file']
    filename = request.form.get('name', '')

    # Check if the file format is correct (PDF)
    if not allowed_file(file.filename):
        return jsonify(message='File type not allowed, only PDFs are accepted'), 400

    # Check if the filename matches the required format (4 letters and numbers)
    if not re.match(r'^[A-Za-z]{4}\d+$', filename):
        return jsonify(message='Filename format is incorrect'), 400

    common.is_data_uploading = True

    filename = secure_filename(filename)
    filepath = common.node_upload_file_dir + filename + '.pdf'
    file.save(filepath)

    if config.NDEBUG:
        print(yellow("[node_new_file] File is saved in node: " + filepath))
        print(yellow("[node_new_file] starting storing file in chord..."))

    t = threading.Thread(target=upload_file_thread, args=(filepath, filename))
    t.start()

    if common.

    # Handle file storage in Chord DHT
    # TODO: implement this
    # store_file_in_chord(filepath, filename)

    return jsonify(message='File successfully uploaded'), 200


def upload_file_thread(filepath, filename):
    return insert_file_to_chord({"who_uploads": {"uid": common.my_id, "ip": common.my_ip, "port": common.my_port},
                                 "filepath": filepath, "filename": filename})


@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    # Retrieve file path from Chord DHT
    filepath = get_file_from_chord(filename)

    if filepath and os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    else:
        return 'File not found', 404


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
    common.my_uid = hash(common.my_ip + ":" + common.my_port)
    common.node_file_dir = config.FILE_DIR + common.my_uid + "/"
    common.node_my_file_dir = common.node_file_dir + "my_files/"
    common.node_replicate_file_dir = common.node_file_dir + "replicate_files/"
    common.node_upload_file_dir = common.node_file_dir + "upload_files/"
    if len(sys.argv) == 4 and sys.argv[3] in ("-b", "-B"):
        print("I am the Bootstrap Node with ip: " + yellow(
            common.my_ip) + " about to run a Flask server on port " + yellow(common.my_port))
        print("and my unique id is: " + green(common.my_uid))
        print("and my file directory is: " + green(common.node_file_dir))
        common.is_bootstrap = True
        init_server()

    else:
        common.is_bootstrap = False
        print("I am a normal Node with ip: " + yellow(common.my_ip) + " about to run a Flask server on port " + yellow(
            common.my_port))
        print("and my unique id is: " + green(common.my_uid))
        print("and my file directory is: " + green(common.node_file_dir))
        # x = threading.Thread(target=node_initial_join, args=[])
        # x.start()

    app.run(host=common.my_ip, port=int(common.my_port), debug=True, use_reloader=False)


def wrong_input_format():
    print(red("Argument passing error!"))
    print(underline("Usage:"))
    print(cyan(
        "-p port_to_open\n -k replication_factor (<= number of nodes)\n -c consistency_type ((linear,l) or (eventual,"
        "e))\n -b for bootstrap node only"))
    exit(0)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ['pdf']


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
