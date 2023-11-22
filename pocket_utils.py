#!/usr/bin/env python  
# -*- coding:utf-8 _*-

""" 

@Author: Haomin Cheng
@File Name: PocketUtils.py
@Time: 2023/11/15
@Contact: haomin.cheng@outlook.com

"""
import pickle

from type import BLOCK_SIZE, Data


def get_pickled_size(obj):
    p = pickle.dumps(obj)
    return len(p)


def insert_padding(pickled_data):
    initial_size = len(pickled_data)
    if initial_size > BLOCK_SIZE:
        print(initial_size)
        raise Exception('insert_padding: Packet is larger than BLOCK_SIZE')

    return pickled_data + b'0' * (BLOCK_SIZE - initial_size)


def create_pickled_packet(packet, data) -> (int, bytes):
    initial_size = get_pickled_size(packet)
    if data and initial_size >= BLOCK_SIZE - 5:
        print(initial_size)
        raise Exception('get_pickled_packet: Packet has no space for data')

    capacity = BLOCK_SIZE - initial_size - 5
    if data:
        packet.data = data[:capacity]
        if (len(data) <= capacity):
            packet.is_last = True
    return capacity, insert_padding(pickle.dumps(packet))


def create_data_packets(msg_type, sender, receiver, data, file_name=''):
    part_num = 0
    while len(data) > 0:
        packet = Data(msg_type, sender, receiver)
        packet.file_name = file_name
        packet.part_num = part_num
        serialized_size, pickled_packet = create_pickled_packet(packet, data)
        yield pickled_packet, part_num
        data = data[serialized_size:]
        part_num += 1
