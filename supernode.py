#!/usr/bin/env python  
# -*- coding:utf-8 _*-

""" 

@Author: Haomin Cheng
@File Name: supernode.py 
@Time: 2023/11/24
@Contact: haomin.cheng@outlook.com

"""
import requests
import config
import utils.util
from utils import common, endpoints
import os
import random
import socket
import threading
import signal
import sys
import json
import boto3
import time
from utils.colorfy import *
from utils.util import get_info_from_identifier

BUCKET_NAME = "file-share-1"
SERVER_BUCKET_NAME = "server-info"
LEADER_FILE = "leader_config.json"
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 5551
LEADER_PORT = 4447
NODE_ALIVE_PREFIX = 'node'
LEADER_CHECK_INTERVAL = 60

connected_clients = {}
nodes = [
    {'id': 2, 'ip': '172.31.5.165'},
    {'id': 1, 'ip': '172.31.40.112'}
]

nodes_to_ip = [
    {'id': 2, 'ip': '18.219.30.179'},
    {'id': 1, 'ip': '3.144.165.8'}
]
ip_to_node_id = {node['ip']: node['id'] for node in nodes}

current_leader = None
ip_log_file = 'node_info.json'
NODES_LIST_FILE = 'nodes.json'
HEARTBEAT_TIMEOUT = 10

lock = threading.Lock()
heartbeat_lock = threading.Lock()
connected_clients_lock = threading.Lock()
leader_lock = threading.Lock()
s3_client = boto3.client('s3')
s3_server_bucket = boto3.resource('s3').Bucket(SERVER_BUCKET_NAME)
s3_server = boto3.resource('s3')


def is_leader_alive(leader_ip):
    # Use a temporary socket to check if the leader is alive
    if leader_ip == common.my_ip:
        return True
    print(red("[Server]"), ("Checking if leader is alive..." + yellow(leader_ip + ":" + str(LEADER_PORT))))
    response = requests.post(config.ADDR + leader_ip + ":" + str(LEADER_PORT) + endpoints.ping)
    if response.status_code == 200 and response.text == "pong":
        return True
    else:
        return False


def create_alive_file():
    file_key = utils.util.get_identifier(common.my_uid, common.my_ip, common.my_port)

    # Check if the file already exists in the S3 bucket
    if not does_s3_object_exist(SERVER_BUCKET_NAME, file_key):
        s3_client = boto3.client('s3')
        s3_client.put_object(
            Bucket=SERVER_BUCKET_NAME,
            Key=file_key,
            Body="This file indicates that the server is alive."
        )
        print(f"Alive file created for node {common.my_uid} in bucket {SERVER_BUCKET_NAME} at {file_key}")
    else:
        print(f"Alive file for node {common.my_uid} already exists in bucket {SERVER_BUCKET_NAME} at {file_key}")


def read_leader_config():
    s3 = boto3.client("s3")
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=LEADER_FILE)
        content = response["Body"].read().decode("utf-8")

        print(red("[read_leader_config] response", response))
        if not content:
            # Handle empty file content
            return None
        return json.loads(content)
    except json.JSONDecodeError:
        # Handle invalid JSON content
        return None
    except s3.exceptions.NoSuchKey:
        # Handle file not found
        return None
    except Exception as e:
        print(f"An error occurred in read_leader_config: {e}")
        return None


def get_node_list_from_s3():
    s3 = boto3.client('s3')
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=NODES_LIST_FILE)
        node_list = json.loads(response['Body'].read().decode('utf-8'))
        return node_list
    except s3.exceptions.NoSuchKey:
        return []


def update_local_node_list():
    nodes = get_node_list_from_s3()
    common.mids = nodes


def save_node_list_to_s3(node_list):
    s3 = boto3.client('s3')
    s3.put_object(Bucket=BUCKET_NAME, Key=NODES_LIST_FILE, Body=json.dumps(node_list).encode('utf-8'))
    update_local_node_list()



def write_leader_config(data):
    s3 = boto3.client("s3")
    s3.put_object(Body=data.encode("utf-8"), Bucket=BUCKET_NAME, Key=LEADER_FILE)


def get_object_from_s3(s3_client, bucket_name, key):
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        return response['Body'].read().decode('utf-8')
    except Exception as e:
        print(f"Error getting object from S3: {e}")
        return None


def does_s3_object_exist(bucket, key):
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except Exception as e:
        return False


def remove_alive_file():
    """
    This function removes the 'alive' file of the current node from the S3 bucket.
    """
    file_key = f'{common.my_uid}_{common.my_ip}_{common.my_port}'
    s3_client = boto3.client('s3')

    try:
        s3_client.delete_object(Bucket=SERVER_BUCKET_NAME, Key=file_key)
        print(f"Alive file {file_key} successfully removed from bucket {SERVER_BUCKET_NAME}.")
    except s3_client.exceptions.NoSuchKey:
        print(f"Alive file {file_key} does not exist in bucket {SERVER_BUCKET_NAME}.")
    except Exception as e:
        print(f"An error occurred while removing the alive file: {e}")


def get_new_leader_from_list(server_list):
    """
    This function returns the file key with the minimum node ID.
    :param server_list: A list of server file objects
    :return: The file key with the minimum node ID
    """
    min_node_id = None
    min_file_key = None

    for file in server_list:
        # Extracting the file name
        file_key = file.key
        # Splitting the file name to get the node_id
        node_id = file_key.split('_')[0]

        if min_node_id is None or node_id < min_node_id:
            min_node_id = node_id
            min_file_key = file_key

    return min_file_key


def get_all_available_servers():
    """
    This function returns a list of all available servers.
    :return:
    """
    available_servers = s3_server_bucket.objects.all()
    print(cyan("Available servers" ), str(available_servers))
    return available_servers


def remove_server_from_leader_config():
    try:
        current_leader = read_leader_config()
        print(red("Current Leader"), str(current_leader))
        if current_leader is not None:
            print(red("[Update Leader Config]"), ("Try to remove myself as current leader from leader_config.txt..."))
            current_node_identifier = f'{common.my_uid}_{common.my_ip}_{common.my_port}'

            # Check if the current leader is the same as the current node
            if current_leader == current_node_identifier:
                # Remove the current_leader from the file content
                new_content = ''
                # Update the leader_config.txt file in S3 with the modified content
                s3_client.put_object(Body=new_content.encode("utf-8"), Bucket=BUCKET_NAME, Key=LEADER_FILE)

                print(f"{current_leader} removed from leader_config.txt")
            else:
                print(f"{current_leader} not found in leader_config.txt. No action needed.")
        else:
            print("No current leader information available. No action needed.")
    except Exception as e:
        print(f"Error removing server from leader_config.txt: {e}")


def initiate_leader_election():
    """
    This function initiates the leader election process.
    :return:
    """

    while True:
        create_alive_file()
        global current_leader
        current_leader = read_leader_config()
        if config.BDEBUG:
            print(red("[Leader Election]"), "Current Leader", current_leader)
        if current_leader.strip():  # Check if current_leader is not blank or only whitespace
            leader_alive = is_leader_alive(current_leader)

            if leader_alive:
                print(red("[Leader Election]"), f"Leader {current_leader} is alive.")
            else:
                print(red("[Leader Election]"), f"Leader {current_leader} is not alive. Re-electing a new leader.")
                current_leader = None
        else:
            print(red("[Leader Election]"), "No current leader information available. No action needed.")
            current_leader = None

        # Check if the S3 object (file) exists
        if current_leader is None:
            # If no leader or the current leader is not alive, elect a new leader
            available_nodes = get_all_available_servers()
            # choose the node with the lowest node_id as the new leader
            if available_nodes:
                new_leader_key = get_new_leader_from_list(available_nodes)
                new_leader = get_info_from_identifier(new_leader_key)
                if new_leader is not None:
                    print(red("[Leader Election]"), f"Node {new_leader['ip']} elected as the new leader.")
                    current_leader = new_leader
                    write_leader_config(current_leader)

        time.sleep(LEADER_CHECK_INTERVAL)


def init_server():
    print(red("[Init Server]"), f"Server is listening on {common.my_ip}:{common.my_port}")

    leader_election_thread = threading.Thread(target=initiate_leader_election, daemon=True)
    leader_election_thread.start()

    def signal_handler(sig, frame):
        print('\n')
        print(red("[SERVER SHUTTING DOWN]"), "Closing server...")
        remove_alive_file()
        remove_server_from_leader_config()

        # Print a message indicating where the IP addresses are stored
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

# -----------------------------------------------------
# functions for the chord ring
def bootstrap_join_func(new_node):
    """
    This function is called by bootstrap node when a node wants to join the Chord.
    :param new_node: {node uid, ip, port}
    :return:
    """
    while common.server_node_joining:
        print(red("[Bootstrap Join]"), "Other node has not finished joining the Chord. Waiting...")
        time.sleep(0.3)

    common.server_node_joining = True

    update_local_node_list()
    candidate_id = new_node["uid"]
    if config.BDEBUG:
        print(blue(candidate_id) + " wants to join the Chord with ip:port " + blue(
            new_node["ip"] + ":" + new_node["port"]))

    # if the new node is the first node in the Chord
    if len(common.mids) == 0:
        common.mids.append(new_node)
        response = {
            "prev": {
                "uid": new_node["uid"],
                "ip": new_node["ip"],
                "port": new_node["port"]
            },
            "next": {
                "uid": new_node["uid"],
                "ip": new_node["ip"],
                "port": new_node["port"]
            }
        }
        save_node_list_to_s3(common.mids)
        common.server_node_joining = False
        return response

    for idx, ids in enumerate(common.mids):
        if candidate_id < ids["uid"]:
            common.mids.insert(idx, new_node)
            break
        elif idx == len(common.mids) - 1:
            common.mids.append(new_node)
            break
    new_node_idx = common.mids.index(new_node)
    if config.vBDEBUG:
        print(blue(common.mids))
        print(blue("new node possition in common.mids: " + str(new_node_idx)))
    prev_of_prev = common.mids[new_node_idx - 2] if new_node_idx >= 2 else (
        common.mids[-1] if new_node_idx >= 1 else common.mids[-2])
    prev = common.mids[new_node_idx - 1] if new_node_idx >= 1 else common.mids[-1]
    next = common.mids[new_node_idx + 1] if new_node_idx < len(common.mids) - 1 else common.mids[0]
    next_of_next = common.mids[new_node_idx + 2] if new_node_idx < len(common.mids) - 2 else (
        common.mids[0] if new_node_idx < len(common.mids) - 1 else common.mids[1])

    response_p = requests.post(config.ADDR + prev["ip"] + ":" + prev["port"] + endpoints.node_update_neighbours,
                               json={"prev": prev_of_prev, "next": new_node})
    if response_p.status_code == 200 and response_p.text == "new neighbours set":
        if config.BDEBUG:
            print(blue("Updated previous neighbour successfully"))
    else:
        print(RED("Something went wrong while updating previous node list"))
    print(config.ADDR, next["ip"], ":", next["port"], endpoints.node_update_neighbours)
    response_n = requests.post(config.ADDR + next["ip"] + ":" + next["port"] + endpoints.node_update_neighbours,
                               json={"prev": new_node, "next": next_of_next})
    if response_n.status_code == 200 and response_n.text == "new neighbours set":
        if config.BDEBUG:
            print(blue("Updated next neighbour successfully"))
    else:
        print(RED("Something went wrong while updating next node list"))

    if config.NDEBUG:
        print("Master completed join of the node")
    #TODO add join procedure
    # try:
    #     response = requests.post(config.ADDR + new_node["ip"] + ":" + new_node["port"] + endpoints.chord_join_procedure,
    #                              json={"prev": {"uid": prev["uid"], "ip": prev["ip"], "port": prev["port"]},
    #                                    "next": {"uid": next["uid"], "ip": next["ip"], "port": next["port"]},
    #                                    "length": len(common.mids) - 1})
    #     print(response.text)
    # except:
    #     print("Something went wrong with join procedure")

    response = {
        "prev": {
            "uid": prev["uid"],
            "ip": prev["ip"],
            "port": prev["port"]
        },
        "next": {
            "uid": next["uid"],
            "ip": next["ip"],
            "port": next["port"]
        }
    }
    save_node_list_to_s3(common.mids)
    common.server_node_joining = False
    return json.dumps(response)