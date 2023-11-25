#!/usr/bin/env python  
# -*- coding:utf-8 _*-

"""

@Author: Sana Pathan
@File Name: supernode_server.py
@Time: 2023/11/20
@Contact: sanapathan28@gmail.com

"""

import os
import random
import socket
import threading
import signal
import sys
import json
import boto3
import time

from utils.colorfy import red

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

def get_own_ip():
    try:
        # Use a temporary socket to determine the local IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        own_ip = s.getsockname()[0]
        s.close()
        return own_ip
    except Exception as e:
        print(f"Error getting own IP: {e}")
        return None


def remove_server_from_leader_config():
    try:
        current_leader = read_leader_config()
        print(red("Current Leader", current_leader))
        if current_leader is not None:
            print(f"Removing {current_leader} from leader_config.txt")
            # Read the content of the leader_config.txt file in S3
            file_content = get_object_from_s3(s3_client, BUCKET_NAME, LEADER_FILE)

            if current_leader in file_content:
                # Remove the current_leader from the file content
                new_content = file_content.replace(current_leader, "").strip()

                # Update the leader_config.txt file in S3 with the modified content
                s3_client.put_object(Body=new_content.encode("utf-8"), Bucket=BUCKET_NAME, Key=LEADER_FILE)

                print(f"{current_leader} removed from leader_config.txt")
            else:
                print(f"{current_leader} not found in leader_config.txt. No action needed.")
        else:
            print("No current leader information available. No action needed.")
    except Exception as e:
        print(f"Error removing server from leader_config.txt: {e}")


def get_ip_from_node_id(node_id):
    print("Node id",node_id)
    for node in nodes_to_ip:
        print(node)
        if node['id'] == node_id:
            return node['ip']
    return None  # Return None if node_id is not found in the list


def send_connected_clients(client_socket):
    with connected_clients_lock:
        print(f"sending connected data.")
        clients_message = json.dumps(list(connected_clients.keys()))
        client_socket.send(clients_message.encode('utf-8'))


def send_leader_information(client_socket):
    with leader_lock:
        print(f"sending leader data.", current_leader)
        clients_message = json.dumps(current_leader)
        client_socket.send(clients_message.encode('utf-8'))


def is_leader_alive(leader_ip):
    try:
        # Use a temporary socket to check if the leader is alive
        with socket.create_connection((leader_ip, SERVER_PORT), timeout=1):
            return True
    except (socket.timeout, ConnectionRefusedError):
        return False


def handle_client(client_socket, addr):
    try:
        while True:
            data = client_socket.recv(1024).decode('utf-8')
            if not data:
                break
            print(f"[{addr}] {data}")
            if data.startswith('PRIVATE_IP:'):
                private_ip = data.split(':')[1]
                print(f"[PRIVATE IP RECEIVED] {addr} private IP: {private_ip}")
                print(f"[NEW CONNECTION FOR SERVER] {addr} connected.")
                with lock:
                    connected_clients[private_ip] = client_socket
                    log_ip_address(addr)

            elif data.strip().lower() == 'get_connected_ips':
                send_connected_clients(client_socket)

            elif data.strip().lower() == 'leader_request':
                send_leader_information(client_socket)

    except Exception as e:
        print(f"Error in handle_client: {e}")

    finally:
        with lock:
            # Remove the client from the dictionary and log file when they disconnect
            if addr in connected_clients:
                del connected_clients[addr]
            remove_ip_address(addr)

        client_socket.close()
        print(f"[SERVER CONNECTION] {addr} disconnected.")

def remove_ip_address(addr):
    # Remove the IP address from the file
    with open(ip_log_file, 'r') as file:
        lines = file.readlines()
    with open(ip_log_file, 'w') as file:
        for line in lines:
            if line.strip() != addr[0]:
                file.write(line)

def log_ip_address(addr):
    # Log the IP address to the file
    with open(ip_log_file, 'a') as file:
        file.write(f"{addr[0]}\n")


def start_server():
    global server

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    SERVER_HOST=get_own_ip()
    server.bind((SERVER_HOST, SERVER_PORT))
    server.listen()

    print(f"[LISTENING] Server is listening on {SERVER_HOST}:{SERVER_PORT}")

    leader_election_thread = threading.Thread(target=initiate_leader_election, daemon=True)
    leader_election_thread.start()

    def signal_handler(sig, frame):
        print("\n[SERVER SHUTTING DOWN] Closing server...")
        for client_socket in connected_clients.values():
            client_socket.close()
        server.close()
        remove_alive_file()
        remove_server_from_leader_config()

        # Print a message indicating where the IP addresses are stored
        print(f"IP addresses are stored in {ip_log_file}")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    while True:
        client_socket, addr = server.accept()
        client_handler = threading.Thread(target=handle_client, args=(client_socket, addr), daemon=True)
        client_handler.start()


def read_leader_config():
    s3 = boto3.client("s3")
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=LEADER_FILE)
        return response["Body"].read().decode("utf-8")
    except s3.exceptions.NoSuchKey:
        return None


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


def create_alive_file(node_id):
    file_key = f'node_{node_id}.alive'

    # Check if the file already exists in the S3 bucket
    if not does_s3_object_exist(BUCKET_NAME, file_key):
        s3_client = boto3.client('s3')
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=file_key,
            Body="This file indicates that the server is alive."
        )
        print(f"Alive file created for node {node_id} in bucket {BUCKET_NAME} at {file_key}")
    else:
        print(f"Alive file for node {node_id} already exists in bucket {BUCKET_NAME} at {file_key}")


def remove_alive_file():
    own_ip = get_own_ip()

    if own_ip is None:
        print("Cannot determine own IP. Exiting.")
        return

    own_node_id = ip_to_node_id.get(own_ip)

    if own_node_id is None:
        print(f"Own IP {own_ip} is not in the node list. Exiting.")
        return
    file_path = f'node_{own_node_id}.alive'
    try:
        os.remove(file_path)
        print(f"Alive file for node {own_node_id} removed.")
    except FileNotFoundError:
        print(f"Alive file for node {own_node_id} not found.")


def remove_alive_file():
    own_ip = get_own_ip()

    if own_ip is None:
        print("Cannot determine own IP. Exiting.")
        return

    node_id = ip_to_node_id.get(own_ip)
    file_key = f'node_{node_id}.alive'
    s3_client = boto3.client('s3')

    # Check if the file exists in the S3 bucket before attempting to delete
    if does_s3_object_exist(BUCKET_NAME, file_key):
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=file_key)
        print(f"Alive file for node {node_id} removed from bucket {BUCKET_NAME} at {file_key}")
    else:
        print(f"Alive file for node {node_id} not found in bucket {BUCKET_NAME}")


def initiate_leader_election():
    own_ip = get_own_ip()

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
            available_nodes = [ip_to_node_id[node['ip']] for node in nodes if does_s3_object_exist(BUCKET_NAME, f'node_{ip_to_node_id[node["ip"]]}.alive')]
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

if __name__ == "__main__":
    start_server()