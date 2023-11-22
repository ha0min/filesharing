#!/usr/bin/env python  
# -*- coding:utf-8 _*-

""" 

@Author: Haomin Cheng
@File Name: network_communication.py 
@Time: 2023/11/19
@Contact: haomin.cheng@outlook.com

"""

import socket
import select
from socket import error as SocketError
from type import MessageType, BLOCK_SIZE
from pocket_utils import create_pickled_packet
import threading

HOST = "0.0.0.0"
HOST_PORT = 0
BT_PORT = 4
CLOSED_SOCKET = 1

class NetworkCommunication:
    def __init__(self):
        self.PORT = None
        self.neighbors_sock = {}  # maps IP to sock
        self.neighbors_ip = {}  # maps sock to IP
        self.sock = None

    def join(self, ip, port, is_bt=False):
        print('-------------')
        print('Joining network', ip, port)
        if is_bt:
            s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        else:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print('Socket created')
        s.connect((ip, port))
        print('Socket connected')
        self.neighbors_ip[s] = ip
        self.neighbors_sock[ip] = s
        self.routes[ip] = ip
        print('-------------')

    def list_neighbors(self):
        neighbors = []
        for n in self.neighbors_sock.keys():
            neighbors.append(n)
        return neighbors

    def send_packet(self, ip, packet):
        if ip not in self.routes or self.routes[ip] not in self.neighbors_sock:
            print(f'Given IP is unknown ({ip})')
            return

        s = self.neighbors_sock[self.routes[ip]]
        print(f'sending {MessageType.to_str(packet.type)} to {ip} (using {self.routes[ip]})')
        _, pickled_packet = create_pickled_packet(packet, None)
        s.sendall(pickled_packet)

    def remove_neighbor(self, conn):
        self.neighbors_sock.pop(self.neighbors_ip[conn])
        self.routes.pop(self.neighbors_ip[conn])
        self.neighbors_ip.pop(conn)

    def handle_incoming_data(self, sock, callback):
        data = b''
        try:
            for _ in range(BLOCK_SIZE):
                temp = sock.recv(1)
                if not temp:
                    data = b''
                    break
                data += temp
        except ConnectionResetError:
            print('Connection Reset Error')
        if not data:  # EOF
            print(self.neighbors_ip[sock], 'disconnected!')
            self.remove_neighbor(sock)
            sock.close()
            return CLOSED_SOCKET
        callback(data, sock)

    def update_routes(self, packet, conn):
        self.routes[packet.sender] = self.neighbors_ip[conn]

    def send_data(self, route_ip, packet):
        if route_ip in self.neighbors_sock:
            s = self.neighbors_sock[route_ip]
            try:
                s.sendall(packet)
            except OSError:
                print('Other node probably got disconnected')
        else:
            print(f'Route IP not found in neighbors: {route_ip}')

    def run_socket(self, bt_name=None, incoming_data_callback=None):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((HOST, HOST_PORT))
        self.sock.listen()
        bt_sock = None
        if bt_name:
            bt_sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            bt_sock.bind((bt_name, BT_PORT))
            bt_sock.listen()
            print('Bluetooth socket is running')

        while True:
            listening_socks = [self.sock]
            if bt_name:
                listening_socks.append(bt_sock)
            listening_socks.extend(self.neighbors_ip.keys())
            ready_socks, _, _ = select.select(listening_socks, [], [], 0.5)
            for sock in ready_socks:
                if sock == self.sock or sock == bt_sock:  # new connection
                    conn, addr = sock.accept()
                    self.neighbors_sock[addr[0]] = conn
                    self.neighbors_ip[conn] = addr[0]
                    listening_socks.append(conn)
                    print(f"Connected by {addr}")
                else:
                    ret = self.handle_incoming_data(sock, incoming_data_callback)
                    if ret == CLOSED_SOCKET:
                        listening_socks.remove(sock)
