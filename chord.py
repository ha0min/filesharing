#!/usr/bin/env python  
# -*- coding:utf-8 _*-

""" 

@Author: Haomin Cheng
@File Name: chord.py 
@Time: 2023/11/24
@Contact: haomin.cheng@outlook.com

"""
import hashlib
import json
import os
import threading
import time
from threading import Thread

import requests

import config
from utils import common, endpoints
from utils.colorfy import *


# ----------------------Node Function---------------------------------------
def node_initial_join():
    if common.still_on_chord:
        if not common.is_bootstrap:
            if config.NDEBUG:
                print(yellow("\nattempting to join the Chord..."))
            try:
                response = requests.post(
                    config.ADDR + config.BOOTSTRAP_IP + ":" + config.BOOTSTRAP_PORT + endpoints.node_join_bootstrap,
                    data={"uid": common.my_uid, "ip": common.my_ip, "port": common.my_port})
                if response.status_code == 200:
                    data = response.json()

                    prev_node = data["prev"]
                    next_node = data["next"]

                    common.nids.append(prev_node)
                    common.nids.append(next_node)

                    if config.NDEBUG:
                        print(f"Joined Chord successfully!!")
                        print(f"Previous Node: {json.dumps(prev_node)}")
                        print(f"Next Node: {json.dumps(next_node)}")
                else:
                    print("Something went wrong!!  status code: " + red(response.status.code))
                    print(red("\nexiting..."))
                    exit(0)
            except:
                print(red("\nSomething went wrong!! (check if bootstrap is up and running)"))
                print(red("\nexiting..."))
                exit(0)


def node_replic_nodes_list(data):
    """
    list the nodes that the new node is responsible for replication
    :param data: {"node_list": node_list, "k": common.k, "new_id": common.my_id}
    :return:
    """
    node_list = data["node_list"]
    k = data["k"]  # k is the number of nodes that the new node should be responsible for replication
    new_id = data["new_id"]

    if common.my_uid != new_id:
        node_list.append(common.my_uid)

    if k >= 1:
        response = requests.post(
            config.ADDR + common.nids[0]["ip"] + ":" + common.nids[0]["port"] + endpoints.replic_nodes_list,
            json={"node_list": node_list, "k": k - 1, "new_id": new_id})
        print(yellow("Got request for new nodes wants to replicate, current list new node needs to handled is:"))
        print(response.json())
        return response.json()
    else:
        print(yellow("Got request for new nodes wants to replicate, i am the last one, current list it needs to "
                     "handled is:"))
        return {"node_list": node_list}


def node_redistribute_data(data):
    """
    redistribute the data to the new node, after the new node join the chord
    endpoint: endpoints.node_join_procedure
    :param data: {"node_list": node_list, "new_id": new added node id}
    :return:
    """
    print("Chord join update POST function is starting...")
    node_list = data["node_list"]
    new_id = data["new_id"]
    try:
        response = requests.post(
            config.ADDR + common.nids[1]["ip"] + ":" + common.nids[1]["port"] + endpoints.node_update_replicate,
            json={"node_list": node_list, "new_id": new_id})
        song_list_json = response.json()
        song_list = song_list_json["song_list"]
    except:
        print("Problem with join update song list operation")
        return "NOT OK"

    for item in song_list:
        common.songs.append(item)
    return "New node songs and replication updated"


def node_update_neighbours_func(data):
    """
    update the neighbours of the node
    :param data:
    :return:
    """
    common.nids[0] = data["prev"]
    common.nids[1] = data["next"]
    change_neighbor = data["change"]  # either "prev" or "next"
    if config.NDEBUG:
        print(red("[node_update_neighbours_func] i got new neighbours:"))
        print(yellow("NEW Previous Node:"))
        print(common.nids[0])
        print(yellow("NEW Next Node:"))
        print(common.nids[1])
    print(yellow("i got New neighbours and set"))

    print(yellow("i need to redistribute my data to my new neighbours"))
    node_redistribute_host_file_to_new_neighbour(change_neighbor)
    return "new neighbours set"


def node_update_finger_table_func(res):
    while common.node_updating_finger_table:
        print(red(["[node_update_finger_table_func] waiting for previous to be done..."]))
        time.sleep(1)

    common.node_updating_finger_table = True
    try:
        if "timestamp" not in res or "finger_table" not in res:
            return "Invalid data format", 400

        if common.my_finger_table is not None and common.my_finger_table_timestamp > res["timestamp"]:
            print(yellow("[node_update_finger_table_func] Received older finger table. Not updating."))
            return "Finger table update skipped due to older timestamp", 200

        common.my_finger_table_timestamp = res["timestamp"]
        common.my_finger_table = res["finger_table"]
        return "Finger table updated", 200

    finally:
        common.node_updating_finger_table = False


# ----------------------Syllabus Function---------------------------------------
def hash(key):
    return hashlib.sha1(key.encode('utf-8')).hexdigest()


def insert_file_to_chord(data):
    """
    insert file to the chord
    :param data: {"who_uploads": {"uid": common.my_id, "ip": common.my_ip, "port": common.my_port},
                                 "file", "file_name"}
    :return:
    """

    hashedname = data["filename"]
    who_uploads = data["who_uploads"]

    closest_node = determine_correct_node(hashedname, common.my_finger_table, common.my_uid)
    if closest_node['uid'] == common.my_uid:
        print("i am responsible for this file")
        # request the file from the node uploads the file
        response = requests.post(
            config.ADDR + who_uploads["ip"] + ":" + who_uploads["port"] + endpoints.request_upload_file_to_host,
            json={"filename": hashedname, "request_node": {"uid": common.my_uid, "ip": common.my_ip,
                                                           "port": common.my_port}})
        if response.status_code == 200 and response.text == "File sent to the node":
            print(red(f"i have send request to {who_uploads['ip']}:{who_uploads['port']} to host the file"))
    else:
        # Forward the file query to the responsible node to find the node in the chord that will host the file
        forward_file_host_query_to_node(hashedname, who_uploads, closest_node)


def forward_file_host_query_to_node(filename, who_uploads, closest_node):
    """
    Forward the file query to the responsible node to find the node in the chord that will host the file
    :param filename: hashed filename
    :param who_uploads: {"uid": common.my_id, "ip": common.my_ip, "port": common.my_port}
    :param closest_node: {"uid": common.my_id, "ip": common.my_ip, "port": common.my_port}
    :return:
    """
    # i am not responsible for this file, forward the request to my closet node to
    # determine the node that will host the file

    response = requests.post(
        config.ADDR + closest_node["ip"] + ":" + closest_node["port"] + endpoints.find_file_host_node,
        json={"filename": filename, "who_uploads": who_uploads})
    if response.status_code == 200 and response.text == "I am finding the responsible node":
        print(red(f"i have send request to {closest_node['ip']}:{closest_node['port']} to find the "
                  f"node that will host the file"))


def determine_correct_node(hashed_key, finger_table, self_ID):
    """
    Determine the correct node to store the file based on the hashed key using the finger table.
    :param hashed_key: Hashed key of the file name.
    :param finger_table: Finger table of the current node.
    :param self_ID: ID of the current node.
    :return: node: {uid, ip, port}
    """
    hashed_key_int = int(hashed_key, 16)
    closest_preceding_finger = {'uid': self_ID, 'ip': common.my_ip, 'port': common.my_port}

    # Check if the hashed key falls within the current node's responsibility
    next_node_ID = int(common.nids[1]['uid'], 16)
    if is_responsible_for_key(hashed_key_int, self_ID, next_node_ID):
        if config.NDEBUG:
            print(("[determine_correct_node] current node is responsible: " + blue(str(self_ID))))
        return closest_preceding_finger

    # Iterate through the finger table to find the responsible node
    for entry in finger_table:
        node_id = int(entry['node']['uid'], 16)
        if is_in_range(hashed_key_int, self_ID, node_id):
            if config.NDEBUG:
                print(("[determine_correct_node] responsible node found: " + blue(str(node_id))))
            return entry['node']

    # Fall back to the next neighbor if no suitable node is found in the finger table
    if config.NDEBUG:
        print(("[determine_correct_node] no responsible node found in finger table, returning next neighbor: " +
               blue(str(next_node_ID))))
    return finger_table[-1]['node']


def is_responsible_for_key(hashed_key_int, self_ID, next_node_ID):
    """
    Check if the current node is responsible for the given key in a circular ID space.
    """
    if self_ID < next_node_ID:
        return self_ID < hashed_key_int <= next_node_ID
    return self_ID < hashed_key_int or hashed_key_int <= next_node_ID


def is_in_range(key, self_ID, node_id):
    """
    Check if a key is in the range (self_ID, node_id) in a circular ID space.
    """
    if self_ID < node_id:
        return self_ID < key < node_id
    return self_ID < key or key < node_id


def send_upload_file_to_node(request_node, filepath, filename):
    while common.is_sending_file:
        print(red(["[send_upload_file_to_node] waiting for previous to be done..."]))
        time.sleep(1)

    common.is_sending_file = True
    if config.NDEBUG:
        print(f"[send_upload_file_to_node] sending file {filepath} to node: " + blue(str(request_node)))
    # get the node ip and port
    node_ip = request_node['ip']
    node_port = request_node['port']

    # send file to the node
    files = {'file': open(filepath, 'rb')}
    response = requests.post(config.ADDR + node_ip + ":" + node_port + endpoints.file_from_upload_node, files=files,
                             data={"filename": filename})

    if response.status_code == 200 and response.text == "File saved":
        print(red("File sent to the node"))
        res = 'File sent to the node'
    else:
        print(red("File sending failed"))
        res = 'File sending failed'
    common.is_sending_file = False

    return res


def node_redistribute_host_file_to_new_neighbour(change_position):
    """
    Redistribute files to the new node based on the hash keys.
    :param change_position: "prev" or "next"
    :return:
    """
    if change_position == "prev":
        print(red("[node_redistribute_host_file_to_new_neighbour] prev node changed, i dont have to redistribute"))
        return

    # Files to transfer to the new node
    files_to_transfer = files_need_to_be_redistributed(common.nids[1])

    if config.NDEBUG:
        print(f"[node_redistribute_host_file_to_new_neighbour] files to transfer: {files_to_transfer}")

    files_did_transfer = []
    # Transfer files to the new node
    for filename in files_to_transfer:
        res = redistribute_host_file_to_node(common.nids[1], filename)
        if res == "File sent to the node":
            files_did_transfer.append(filename)
        else:
            print(red(f"[node_redistribute_host_file_to_new_neighbour] file {filename} not transferred"))

    print(red("[node_redistribute_host_file_to_new_neighbour] files redistributed"))

    # Remove files that were transferred successfully
    for filename in files_did_transfer:
        common.host_file_list.remove(filename)
        os.remove(config.HOST_FILE_DIR + filename + ".pdf")





def files_need_to_be_redistributed(new_node):
    """
    Redistribute files to the new node based on the hash keys.
    :param new_node: {uid, ip, port} of the new node
    """
    new_node_id = int(new_node['uid'], 16)

    # Files to transfer to the new node
    files_to_transfer = []

    # Identify files that should be transferred to the new node
    for filename in common.host_file_list:
        hashed_name_int = int(filename, 16)

        if is_responsible_for_key(hashed_name_int, common.my_uid, new_node_id):
            files_to_transfer.append(filename)

    return files_to_transfer


def redistribute_host_file_to_node(request_node, filename):
    if config.NDEBUG:
        print(f"[redistribute_host_file_to_node] sending file {filename} to node: " + blue(str(request_node)))
    # get the node ip and port
    node_ip = request_node['ip']
    node_port = request_node['port']

    # get the file from the node
    filepath = common.node_host_file_dir + filename + ".pdf"
    with open(filepath, 'rb') as f:
        files = {'file': f}
        # send file to the node
        response = requests.post(config.ADDR + node_ip + ":" + node_port + endpoints.file_from_redistribute,
                                 files=files, data={"filename": filename})

        if response.status_code == 200 and response.text == "i have host the file":
            print(f"[redistribute_host_file_to_node] sending file {filename} to node ok: " + blue(str(request_node)))
            res = 'File sent to the node'
        else:
            print(f"[redistribute_host_file_to_node] sending file {filename} to node error: " + blue(str(request_node)))
            res = 'File sending failed'
            print(red("with response"), response.text, response.status_code)

    return res
