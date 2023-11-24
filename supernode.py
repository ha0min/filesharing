#!/usr/bin/env python  
# -*- coding:utf-8 _*-

""" 

@Author: Haomin Cheng
@File Name: supernode.py 
@Time: 2023/11/24
@Contact: haomin.cheng@outlook.com

"""
from utils import common
import os
import random
import socket
import threading
import signal
import sys
import json
import boto3
import time

BUCKET_NAME = "file-share-1"
LEADER_FILE = "leader_config.txt"
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
ip_log_file = 'ip_addresses.txt'
HEARTBEAT_TIMEOUT = 10

lock = threading.Lock()
heartbeat_lock = threading.Lock()
connected_clients_lock = threading.Lock()
leader_lock = threading.Lock()
s3_client = boto3.client('s3')


def is_leader_alive(leader_ip):
    try:
        # Use a temporary socket to check if the leader is alive
        if leader_ip == common.my_ip:
            return True

    except (socket.timeout, ConnectionRefusedError):
        return False


def initiate_leader_election():
    """
    This function initiates the leader election process.
    :return:
    """
    own_ip = common.my_ip

    if own_ip is None:
        print("Cannot determine own IP. Exiting.")
        return

    own_node_id = ip_to_node_id.get(own_ip)

    if own_node_id is None:
        print(f"Own IP {own_ip} is not in the node list. Exiting.")
        return

    s3_key = f'node_{own_node_id}.alive'

    while True:
        create_alive_file(own_node_id)
        global current_leader
        create_alive_file(own_node_id)
        current_leader = read_leader_config()
        print("Current Leader", current_leader)
        if current_leader.strip():  # Check if current_leader is not blank or only whitespace
            leader_alive = is_leader_alive(current_leader)

            if leader_alive:
                print(f"Leader {current_leader} is alive.")
            else:
                print(f"Leader {current_leader} is not alive. Re-electing a new leader.")
                current_leader = None
        else:
            print("No current leader information available. No action needed.")
            current_leader = None

        # Check if the S3 object (file) exists
        if current_leader is None or not does_s3_object_exist(BUCKET_NAME, s3_key):
            # If no leader or the current leader is not alive, elect a new leader
            available_nodes = [ip_to_node_id[node['ip']] for node in nodes if
                               does_s3_object_exist(BUCKET_NAME, f'node_{ip_to_node_id[node["ip"]]}.alive')]
            print(available_nodes)
            if available_nodes:
                new_node_id = min(available_nodes)
                new_leader = get_ip_from_node_id(new_node_id)
                print('current_leader')
                print(new_leader)
                if new_leader is not None:
                    print(f"The IP address for node {new_node_id} is {new_leader}")
                else:
                    print(f"Node {new_node_id} not found in the list.")
                write_leader_config(str(new_leader))
                print(f"[LEADER ELECTION] Node {new_leader} elected as the new leader.")
                current_leader = new_leader

        time.sleep(LEADER_CHECK_INTERVAL)
