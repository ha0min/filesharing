"""

@Author: Sana Pathan
@File Name: supernode_server.py
@Time: 2023/11/20
@Contact: sanapathan28@gmail.com

"""

import socket
import json
from datetime import time

import boto3

HOST = "0.0.0.0"
HOST_PORT = 0
BT_PORT = 4

ACK_LIMIT = 20  # seconds
SIMILARITY_MIN_THRESHOLD = 0.8

CLOSED_SOCKET = 1
known_servers = ['3.144.165.8']
SERVER_HOST = '3.144.165.8'
SERVER_PORT = 5551
DEFAULT_LEADER = '3.18.107.63'

LEADER_RECONNECT_INTERVAL = 30  # Adjust this interval as needed
BUCKET_NAME = "file-share-1"
LEADER_FILE = "leader_config.txt"

def read_leader_config():
    s3 = boto3.client("s3")
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=LEADER_FILE)
        return response["Body"].read().decode("utf-8")
    except s3.exceptions.NoSuchKey:
        return None

def is_leader_alive(leader_ip):
    try:
        # Use a temporary socket to check if the leader is alive
        with socket.create_connection((leader_ip, SERVER_PORT), timeout=1):
            return True
    except (socket.timeout, ConnectionRefusedError):
        return False


def check_leader_status():
    while True:
        global current_leader
        leader_alive = is_leader_alive(current_leader)

        if not leader_alive:
            print(f"Leader {current_leader} is not alive. Reconnecting to the current leader.")
            current_leader = read_leader_config()

            print(f"Reconnected to the current leader: {current_leader}")

        # Perform any other leader-related tasks here

        time.sleep(LEADER_RECONNECT_INTERVAL)


def start_client(self, client):
    client.connect((SERVER_HOST, SERVER_PORT))
    print("Connected to the server.")


def print_connected_clients(connected_clients):
    print("Connected clients:")
    for ip in connected_clients:
        print(ip)


def receive_connected_clients(self):
    try:
        connected_clients = receive_data(self)
        return connected_clients
    except Exception as e:
        print(f"Error receiving connected clients: {e}")
        return []


def receive_data(self):
    try:
        data = self.client.recv(1024).decode('utf-8')
        if not data:
            print("Error: Received empty data.")
            return []
        print(f"Received data: {data}")
        return json.loads(data)
    except Exception as e:
        print(f"Error receiving data: {e}")
        return []


def request_leader(self):
    for server_host in known_servers:
        try:
            self.leader_client.connect((server_host, SERVER_PORT))
            self.leader_client.sendall('LEADER_REQUEST'.encode('utf-8'))
            SERVER_HOST = self.supernode_client.receive_leader_information(self)
            if not SERVER_HOST:
                SERVER_HOST = DEFAULT_LEADER

        except socket.error as e:
            print(f"Error connecting to {server_host}: {e}")

        except Exception as e:
            print(f"Error in request_leader: {e}")

        finally:
            # Close the socket connection
            self.leader_client.close()


def receive_leader_information(self):
    try:
        leader_server = receive_leader_data(self)
        return leader_server
    except Exception as e:
        print(f"Error receiving connected clients: {e}")
        return []


def receive_leader_data(self):
    try:
        data = self.leader_client.recv(1024).decode('utf-8')
        if not data:
            print("Error: Received empty data.")
            return []
        print(f"Received Leader: {data}")
        return json.loads(data)
    except Exception as e:
        print(f"Error receiving data: {e}")
        return []