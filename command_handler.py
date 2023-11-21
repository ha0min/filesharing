#!/usr/bin/env python  
# -*- coding:utf-8 _*-

""" 

@Author: Haomin Cheng
@File Name: command_handler.py 
@Time: 2023/11/20
@Contact: haomin.cheng@outlook.com

"""
import threading

from network_utils import get_my_ip
from node import Node, PORT, BT_PORT
from write_ahead import WriteAheadLog


class CommandHandler:
    def __init__(self, bt_addr=None):
        self.ip = get_my_ip()
        self.node = Node(self.ip, WriteAheadLog())
        t = threading.Thread(target=self.node.run_socket, args=(bt_addr,), daemon=True)
        t.start()
        t2 = threading.Thread(target=self.node.retransmit_packets_after_failure, daemon=True)
        t2.start()
        t3 = threading.Thread(target=self.node.check_for_time_out_acks, daemon=True)
        t3.start()

    def list_neighbors(self):
        return self.node.list_neighbors()



    def run(self):
        while 1:
            cmd = input('> ').split()
            if not cmd:
                continue
            elif cmd[0] == 'send':
                self.node.send_file(cmd[1], cmd[2])
            elif cmd[0] == 'join':
                if len(cmd) > 2:
                    self.node.network_communication.join(cmd[1], BT_PORT, True)
                else:
                    self.node.network_communication.join(cmd[1], PORT)
            elif cmd[0] == 'request':
                self.node.request_file(cmd[1])
            elif cmd[0] == 'list':
                self.node.network_communication.list_neighbors()
            elif cmd[0] == 'leave':
                pass
            elif cmd[0] == 'help':
                print('''join <ip>\nsend <ip>\nlist - lists neighbors\nhelp - shows this message\nrequest <file>''')
            else:
                print('Invalid command! use "help"')
