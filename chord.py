#!/usr/bin/env python  
# -*- coding:utf-8 _*-

""" 

@Author: Haomin Cheng
@File Name: chord.py 
@Time: 2023/11/24
@Contact: haomin.cheng@outlook.com

"""
import hashlib

import requests

import config
from utils import common, endpoints
from utils.colorfy import *


# ----------------------Node Function---------------------------------------
def node_initial_join():
    if common.still_on_chord:
        if not common.boot:
            if config.NDEBUG:
                print(yellow("\nattempting to join the Chord..."))
            try:
                response = requests.post(
                    config.ADDR + config.BOOTSTRAP_IP + ":" + config.BOOTSTRAP_PORT + endpoints.join_bootstrap,
                    data={"uid": common.my_id, "ip": common.my_ip, "port": common.my_port})
                if response.status_code == 200:
                    res = response.text.split(" ")
                    common.nids.append({"uid": res[0], "ip": res[1], "port": res[2]})
                    common.nids.append({"uid": res[3], "ip": res[4], "port": res[5]})
                    if config.NDEBUG:
                        print(yellow("Joined Chord successfully!!"))
                        print(yellow("Previous Node:"))
                        print(common.nids[0])
                        print(yellow("Next Node:"))
                        print(common.nids[1])
                else:
                    print("Something went wrong!!  status code: " + red(response.status.code))
                    print(red("\nexiting..."))
                    exit(0)
            except:
                print(red("\nSomething went wrong!! (check if bootstrap is up and running)"))
                print(red("\nexiting..."))
                exit(0)


def bootstrap_join_func(new_node):
    """
    This function is called by bootstrap node when a node wants to join the Chord.
    :param new_node:
    :return:
    """
    candidate_id = new_node["uid"]
    if config.BDEBUG:
        print(blue(candidate_id) + " wants to join the Chord with ip:port " + blue(
            new_node["ip"] + ":" + new_node["port"]))
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

    response_p = requests.post(config.ADDR + prev["ip"] + ":" + prev["port"] + endpoints.n_update_peers,
                               json={"prev": prev_of_prev, "next": new_node})
    if response_p.status_code == 200 and response_p.text == "new neighbours set":
        if config.BDEBUG:
            print(blue("Updated previous neighbour successfully"))
    else:
        print(RED("Something went wrong while updating previous node list"))
    print(config.ADDR, next["ip"], ":", next["port"], endpoints.n_update_peers)
    response_n = requests.post(config.ADDR + next["ip"] + ":" + next["port"] + endpoints.n_update_peers,
                               json={"prev": new_node, "next": next_of_next})
    if response_n.status_code == 200 and response_n.text == "new neighbours set":
        if config.BDEBUG:
            print(blue("Updated next neighbour successfully"))
    else:
        print(RED("Something went wrong while updating next node list"))

    if config.NDEBUG:
        print("Master completed join of the node")
    try:
        response = requests.post(config.ADDR + new_node["ip"] + ":" + new_node["port"] + endpoints.chord_join_procedure,
                                 json={"prev": {"uid": prev["uid"], "ip": prev["ip"], "port": prev["port"]},
                                       "next": {"uid": next["uid"], "ip": next["ip"], "port": next["port"]},
                                       "length": len(common.mids) - 1})
        print(response.text)
    except:
        print("Something went wrong with join procedure")

    return prev["uid"] + " " + prev["ip"] + " " + prev["port"] + " " + next["uid"] + " " + next["ip"] + " " + next[
        "port"]


# ----------------------Syllabus Function---------------------------------------
def hash(key):
    return hashlib.sha1(key.encode('utf-8')).hexdigest()
