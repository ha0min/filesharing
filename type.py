#!/usr/bin/env python  
# -*- coding:utf-8 _*-

""" 

@Author: Haomin Cheng
@File Name: Type.py
@Time: 2023/11/15
@Contact: haomin.cheng@outlook.com

"""

import pickle

BLOCK_SIZE = 2048
DEFAULT_TTL = 10


class MessageType:
    FILE_TRANFER = 0
    JOIN = 1
    FILE_SEARCH = 2
    HAS_FILE = 3
    TRANSFER_REQUEST = 4
    ACK = 5

    _msg_str = {
        FILE_TRANFER: 'File Transfer',
        JOIN: 'Join',
        FILE_SEARCH: 'File Search',
        HAS_FILE: 'Has File',
        TRANSFER_REQUEST: 'Transfer Request',
        ACK: 'ACK'
    }

    @staticmethod
    def to_str(msg):
        return MessageType._msg_str[msg]


class Data:
    def __init__(self, msg_type, sender, receiver):
        self.type = msg_type
        self.sender = sender
        self.receiver = receiver
        self.data = None
        self.file_name = ''
        self.is_last = False
        self.part_num = 0
        self.ttl = DEFAULT_TTL
