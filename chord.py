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
