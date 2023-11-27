#!/usr/bin/env python  
# -*- coding:utf-8 _*-

""" 

@Author: Haomin Cheng
@File Name: flask_server.py 
@Time: 2023/11/24
@Contact: haomin.cheng@outlook.com

"""
import os
import re
import sys
import socket
import threading
import time

from flask import Flask, json, request, jsonify, send_file
from werkzeug.utils import secure_filename

import config
from supernode import init_server, bootstrap_join_func
from utils import common, endpoints
from utils.colorfy import *
from chord import hash, node_update_neighbours_func, node_replic_nodes_list, node_redistribute_data, \
    node_update_finger_table_func, insert_file_to_chord, send_upload_file_to_node, node_initial_join, \
    query_file_in_the_chord

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
    """
    Update the neighbours of the node.
    :return:
    """
    while common.node_updating_neighbor:
        print(red("i am updating neighbours, wait..."))
        time.sleep(0.3)
    common.node_updating_neighbor = True
    new_neighbours = request.get_json()
    response = node_update_neighbours_func(new_neighbours)
    common.node_updating_neighbor = False
    return response


@app.route(endpoints.node_update_finger_table, methods=['POST'])
def update_finger_table():
    """
    Update the finger table of the node.
    """
    res = request.get_json()
    if 'finger_table' not in res or 'timestamp' not in res:
        return "Invalid request format: 'timestamp' or'finger_table' key missing", 400

    if config.NDEBUG:
        print(yellow("Updating finger table..."))
        print(str(res))

    return node_update_finger_table_func(res)


@app.route(endpoints.user_add_new_file, methods=['POST'])
def upload_file():
    if 'file' not in request.files or 'course_name' not in request.form:
        return 'Please provide a file and a course_name', 400

    file = request.files['file']
    filename = request.form.get('course_name', '')

    # Check if the file format is correct (PDF)
    if not allowed_file(file.filename):
        return jsonify(message='File type not allowed, only PDFs are accepted'), 400

    filename = secure_filename(filename)

    # Check if the filename matches the required format (4 letters and numbers)
    if not is_valid_course_id(filename):
        return jsonify(message='Filename format is incorrect'), 400

    common.is_data_uploading = True

    hashed_filename = hash(filename)
    filepath = common.node_upload_file_dir + hashed_filename + '.pdf'
    file.save(filepath)

    if config.NDEBUG:
        print(yellow(
            f"[node_add_new_file] Upload File is saved in my upload folder: {filename}, hashed {hashed_filename}"))
        print(yellow("[node_add_new_file] starting storing file in chord..."))

    t = threading.Thread(target=upload_file_thread, args=(hashed_filename,))
    t.start()

    while not common.already_upload_to_chord:
        print(yellow("waiting for a node in the chord to request my uploaded file to host..."))
        time.sleep(0.3)

    common.already_upload_to_chord = False
    # Handle file storage in Chord DHT
    # TODO: implement this
    # store_file_in_chord(filepath, filename)

    return jsonify(message='File successfully uploaded'), 200


def upload_file_thread(filename):
    return insert_file_to_chord({"who_uploads": {"uid": common.my_uid, "ip": common.my_ip, "port": common.my_port},
                                 "filename": filename})


@app.route(endpoints.request_upload_file_to_host, methods=['POST'])
def request_upload_file():
    """
    Request a file upload to the node.
    """
    if 'filename' not in request.form:
        print(red(f"[endpoints.request_upload_file_to_host] the params are: {str(request.form)}, return 400"))
        return 'Please provide a filename', 400

    if 'request_node' not in request.form:
        print(red(f"[endpoints.request_upload_file_to_host] the params are: {str(request.form)}, return 400"))
        return 'Please provide a request node', 400
    # filename should be hashed already
    filename = request.form.get('filename', '')
    filename = secure_filename(filename)

    # check file exist in my upload folder
    filepath = common.node_upload_file_dir + filename + '.pdf'
    if not os.path.exists(filepath):
        return 'File not found', 404

    request_node = json.loads(request.form.get('request_node', ''))
    print(red(f"The node {request_node['ip']}:{request_node['port']} in chord host the file {filename} "
              f"in my upload folder"))

    if config.NDEBUG:
        print(yellow(f"[request_upload_file] Requested file: {filename} from {str(request_node)}"))

    # send file to the node
    response = send_upload_file_to_node(request_node, filepath, filename)

    if config.NDEBUG:
        print(yellow(f"[request_upload_file] Response from node: {str(response)}"))

    # the file is sent to the chord, i can continue to upload other files
    common.already_upload_to_chord = True
    if response == 'File sent to the node':
        return 'File sent to the node', 200
    else:
        return 'File not sent to the node', 400


@app.route(endpoints.file_from_upload_node, methods=['POST'])
def file_from_upload_node():
    """
    a file send from upload node, i am responsible for it.
    """
    if 'file' not in request.files or 'filename' not in request.form:
        return 'Please provide a file and a filename', 400

    filename = request.form.get('filename', '')
    filename = secure_filename(filename)

    if config.NDEBUG:
        print(yellow(f"[file_from_upload_node] Requested file: {filename}"))

    # save the file in my host folder
    filepath = common.node_host_file_dir + filename + '.pdf'
    file = request.files['file']
    file.save(filepath)

    # update host file list
    common.host_file_list.append(filename)

    return 'File saved', 200


@app.route(endpoints.find_file_host_node, methods=['POST'])
def find_file_host_node():
    """
    a node is not responsible for a file, and i was the closest node he found, so i will find
    the node who is responsible
    """

    if 'filename' not in request.form or 'who_uploads' not in request.form:
        return 'Please provide a filename', 400

    filename = request.form.get('filename', '')
    filename = secure_filename(filename)

    who_uploads = json.loads(request.form.get('who_uploads', ''))

    if config.NDEBUG:
        print(yellow(f"[find_file_host_node] Requested file: {filename}"))

    # find the node who is responsible for the file in a new thread
    t = threading.Thread(target=insert_file_to_chord, args=({"filename": filename, "who_uploads": who_uploads},))
    t.start()

    return "I am finding the responsible node", 200


@app.route(endpoints.file_from_redistribute, methods=['POST'])
def file_from_redistribute():
    """
    as a new node joined the chord, a file send from my neighbor node claiming i am responsible for it.
    """
    if 'file' not in request.files or 'filename' not in request.form:
        return 'Please provide a file and a filename', 400

    filename = request.form.get('filename', '')
    filename = secure_filename(filename)
    print(red(f"i am responsible for a file from my neighbor node {filename}"))

    # save the file in my host folder
    filepath = common.node_host_file_dir + filename + '.pdf'
    file = request.files['file']
    file.save(filepath)

    # update host file list
    common.host_file_list.append(filename)

    return 'i have host the file', 200


@app.route(endpoints.user_query_file, methods=['GET'])
def query_file():
    """
    Query a file from the node.
    """
    if 'filename' not in request.args:
        return 'Please provide a filename', 400

    filename = request.args.get('filename', '')
    filename = secure_filename(filename)

    # check if the filename legal
    if not is_valid_course_id(filename):
        return 'input should be course id, department code + digits, like CSEN317', 400

    print(red(f"user query file, with name {filename}"))

    hashed_filename = hash(filename)

    # run the query in a new thread
    t = threading.Thread(target=query_file_in_the_chord_thread, args=(hashed_filename,))
    t.start()

    # Define a timeout (e.g., 30 seconds)
    timeout = 15  # seconds
    start_time = time.time()

    # if a node hosted the file got my request, it will send his info{uid, ip, port} to me, and i will
    # store it in common.query_file_result
    while True:
        if hashed_filename in common.query_file_result and common.query_file_result[hashed_filename] is not None:
            hosted_node = common.query_file_result[hashed_filename]

            if hosted_node == 'File not found in chord':
                # delete the query file result
                del common.query_file_result[hashed_filename]
                print(red("file not found in chord"))
                return 'File not found in chord', 404

            print(red(f"the file is hosted by {str(hosted_node)}, i will return the url to the user"))

            # Return the file URL
            return config.ADDR + hosted_node['ip'] + ':' + str(hosted_node['port']) + \
                   endpoints.user_get_file + '?filename=' + hashed_filename, 200

        # Check if the timeout has been reached
        if time.time() - start_time > timeout:
            print(red("Query timed out"))
            return 'Query timed out', 408  # 408 Request Timeout

        print(red("Asking the chord to give me file, waiting for query result"))
        time.sleep(1)


def query_file_in_the_chord_thread(filename):
    query_file_in_the_chord({"uid": common.my_uid, "ip": common.my_ip, "port": common.my_port}, filename)


@app.route(endpoints.node_chain_query_file, methods=['POST'])
def chain_query_file():
    # should be a form has filename, and  node info{uid, ip, port}
    if 'filename' not in request.form or 'request_node' not in request.form:
        if config.vNDEBUG:
            print(blue(f"[node_chain_query_file] Requested file: {request.form.to_dict()}"))
        return 'Please provide a filename or request_node', 400

    filename = request.form.get('filename', '')
    filename = secure_filename(filename)

    request_node = json.loads(request.form.get('request_node', ''))

    print(red(f"chain query file start, filename is {filename}, request_node is {request_node}"))

    threading.Thread(target=query_file_in_the_chord, args=(request_node, filename,)).start()

    return "success", 200


@app.route(endpoints.user_get_file, methods=['GET'])
def get_file():
    """
    Get a file from the node.
    """
    if 'filename' not in request.args:
        return 'Please provide a filename', 400

    print(red(f"user get file {request.args.get('filename', '')}"))

    filename = request.args.get('filename', '')
    filename = secure_filename(filename)

    # check file exist in my host folder
    filepath = common.node_host_file_dir + filename + '.pdf'

    # if there is a optional param type
    if 'type' in request.args:
        print(red(f"user get file, with the type is {request.args.get('type', '')}"))
        if request.args.get('type', '') == 'replica':
            # check file exist in my host folder
            filepath = common.node_replicate_file_dir + filename + '.pdf'

    if not os.path.exists(filepath):
        return 'File not found', 404

    return send_file(filepath, as_attachment=True)


@app.route(endpoints.node_query_result, methods=['POST'])
def node_query_result():
    """
    the node who hosted the file will send the file url to the node who query the file
    """
    if 'filename' not in request.form or 'res' not in request.form:
        return 'Please provide a filename or res', 400

    filename = request.form.get('filename', '')
    filename = secure_filename(filename)

    res = request.form.get('res', '')
    if res != 'File not found in chord':
        hosted_node = json.loads(res)
    else:
        hosted_node = res

    print(red(f"i am going to store the hosted node info {hosted_node}"))

    # store the hosted node info
    common.query_file_result[filename] = hosted_node

    return "success", 200


# @app.route('/download/<filename>', methods=['GET'])
# def download_file(filename):
#     # Retrieve file path from Chord DHT
#     filepath = get_file_from_chord(filename)
#
#     if filepath and os.path.exists(filepath):
#         return send_file(filepath, as_attachment=True)
#     else:
#         return 'File not found', 404


def server_start():
    """
    Entry point of the flask server.
    :return:
    """
    common.server_starting = True
    if len(sys.argv) < 3:  # should be -p port
        wrong_input_format()
    if sys.argv[1] in ("-p", "-P"):
        common.my_port = sys.argv[2]
    else:
        wrong_input_format()
    common.my_ip = get_my_ip()
    common.my_uid = hash(common.my_ip + ":" + common.my_port)
    common.node_file_dir = config.FILE_DIR + common.my_uid + "/"
    common.node_host_file_dir = common.node_file_dir + "host_files/"
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
        # create the directory for the node
        create_node_dir()
        print(red("I have created the file directory for me, now i will join the chord"))
        x = threading.Thread(target=node_initial_join, args=())
        x.start()

    app.run(host=common.my_ip, port=int(common.my_port), debug=True, use_reloader=False)


def create_node_dir():
    """
    Create the directory for the node
    :return:
    """
    if not os.path.exists(common.node_file_dir):
        os.makedirs(common.node_file_dir)
        if config.NDEBUG:
            print(yellow(f"[create_node_dir] Directory {common.node_file_dir} created"))
    if not os.path.exists(common.node_host_file_dir):
        os.makedirs(common.node_host_file_dir)
        if config.NDEBUG:
            print(yellow(f"[create_node_dir] Directory {common.node_host_file_dir} created"))
    if not os.path.exists(common.node_replicate_file_dir):
        os.makedirs(common.node_replicate_file_dir)
        if config.NDEBUG:
            print(yellow(f"[create_node_dir] Directory {common.node_replicate_file_dir} created"))
    if not os.path.exists(common.node_upload_file_dir):
        os.makedirs(common.node_upload_file_dir)
        if config.NDEBUG:
            print(yellow(f"[create_node_dir] Directory {common.node_upload_file_dir} created"))


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
    if config.LOCAL_SERVER:
        return '127.0.0.1'

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


def is_valid_course_id(course_id):
    """
    Check if the course id is valid
    :param course_id: 4letters+digits(CSEN317)
    :return:
    """
    return re.match(r'^[A-Za-z]{4}\d+$', course_id)


if __name__ == '__main__':
    server_start()
