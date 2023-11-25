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


def node_join_list(data):
    """

    :param data: {"node_list": node_list, "k": common.k, "new_id": common.my_id}
    :return:
    """
    node_list = data["node_list"]
    k = data["k"]
    new_id = data["new_id"]




def node_update_neighbours_func(data):
    common.nids[0] = data["prev"]
    common.nids[1] = data["next"]
    if config.NDEBUG:
        print(red("[node_update_neighbours_func] Updated neighbours:"))
        print(yellow("NEW Previous Node:"))
        print(common.nids[0])
        print(yellow("NEW Next Node:"))
        print(common.nids[1])
    return "new neighbours set"



# ----------------------Syllabus Function---------------------------------------
def hash(key):
    return hashlib.sha1(key.encode('utf-8')).hexdigest()
