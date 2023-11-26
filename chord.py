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
import time
from threading import Thread

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


def node_update_finger_table_func(res):
    while common.node_updating_finger_table:
        print(red(["[node_update_finger_table_func] waiting for previous to be done..."]))
        time.sleep(1)

    common.node_updating_finger_table = True
    try:
        if "timestamp" not in res or "finger_table" not in res:
            return "Invalid data format", 400

        if common.my_finger_table is not None and common.my_finger_table_timestamp > res["timestamp"]:
            print(yellow("[node_update_finger_table_func] Received older finger table. Not updating."))
            return "Finger table update skipped due to older timestamp", 200

        common.my_finger_table_timestamp = res["timestamp"]
        common.my_finger_table = res["finger_table"]
        return "Finger table updated", 200

    finally:
        common.node_updating_finger_table = False


# ----------------------Syllabus Function---------------------------------------
def hash(key):
    return hashlib.sha1(key.encode('utf-8')).hexdigest()


def insert_file_to_chord(data):
    """
    insert file to the chord
    :param data: {"who_uploads": {"uid": common.my_id, "ip": common.my_ip, "port": common.my_port},
                                 "file_path", "file_name"}
    :return:
    """

    syllabus_file_path = data["file_path"]
    syllabus_file_name = data["file_name"]
    who_is = data["who_uploads"]
    if (who_is["uid"] != common.my_id and common.started_insert) or (
            common.started_insert and who_is["uid"] == common.my_id and common.last_replica_flag == True):
        # i am the node who requested the insertion of the song and i am here because the node who has the song sent it to me
        if config.NDEBUG:
            print(yellow("Got response directly from the source: ") + who_is["uid"])
            print(yellow("and it contains: ") + str(syllabus_file))
            print(yellow("sending confirmation to source node"))
        common.q_responder = who_is["uid"]
        common.q_response = syllabus_file["key"]
        common.started_insert = False
        common.got_insert_response = True

        common.last_replica_flag = False
        return common.my_id + " " + syllabus_file["key"]

    hashed_key = hash(syllabus_file["key"])
    if config.NDEBUG:
        print(yellow("Got request to insert song: {}").format(syllabus_file))
        print(yellow("From node: ") + who_is["uid"])
        print(yellow("Song Hash: ") + hashed_key)
    previous_ID = common.nids[0]["uid"]
    next_ID = common.nids[1]["uid"]
    self_ID = common.my_id
    who = 1
    if previous_ID > self_ID and next_ID > self_ID:
        who = 0  # i have the samallest id
    elif previous_ID < self_ID and next_ID < self_ID:
        who = 2  # i have the largest id

    if (hashed_key > previous_ID and hashed_key <= self_ID and who != 0) or (
            hashed_key > previous_ID and hashed_key > self_ID and who == 0) or (hashed_key <= self_ID and who == 0):
        # song goes in me
        song_to_be_inserted = found(syllabus_file["key"])
        if (song_to_be_inserted):
            common.songs.remove(song_to_be_inserted)
            if config.NDEBUG:
                print(yellow('Updating song: {}').format(song_to_be_inserted))
                print(yellow("To song: 	{}").format(syllabus_file))
                if config.vNDEBUG:
                    print(yellow("My songs are now:"))
                    print(common.songs)
        common.songs.append(
            {"key": syllabus_file["key"], "value": syllabus_file["value"]})  # inserts the (updated) pair of (key,value)
        if config.NDEBUG:
            print(yellow('Inserted song: {}').format(syllabus_file))
            if config.vNDEBUG:
                print(yellow("My songs are now:"))
                print(common.songs)

        if (common.replication == "eventual" and common.k != 1):
            ploads = {"who": {"uid": who_is["uid"], "ip": who_is["ip"], "port": who_is["port"]},
                      "song": {"key": syllabus_file["key"], "value": syllabus_file["value"]}, "chain_length": {"k": common.k - 1}}
            t = Thread(target=eventual_insert, args=[ploads])
            t.start()

        elif (common.replication == "linear" and common.k != 1):
            ploads = {"who": {"uid": who_is["uid"], "ip": who_is["ip"], "port": who_is["port"]},
                      "song": {"key": syllabus_file["key"], "value": syllabus_file["value"]}, "chain_length": {"k": common.k - 1}}
            linear_result = requests.post(
                config.ADDR + common.nids[1]["ip"] + ":" + common.nids[1]["port"] + ends.chain_insert, json=ploads)
            return "Right node insert song"

        if common.started_insert:  # it means i requested the insertion of the song, and i am responsible for it
            common.q_response = syllabus_file["key"]
            common.q_responder = who_is["uid"]
            common.started_insert = False
            common.got_insert_response = True
            if config.NDEBUG:
                print(cyan("Special case ") + "it was me who made the request and i also have the song")
                print(yellow("Returning to myself..."))
            return "sent it to myself"

        try:  # send the key of the song to the node who requested the insertion
            result = requests.post(config.ADDR + who_is["ip"] + ":" + who_is["port"] + ends.n_insert,
                                   json={"who": {"uid": common.my_id, "ip": common.my_ip, "port": common.my_port},
                                         "song": syllabus_file})
            if result.status_code == 200 and result.text.split(" ")[0] == who_is["uid"]:
                if config.NDEBUG:
                    print("Got response from the node who requested the insertion of the song: " + yellow(
                        result.text))
                return self_ID + syllabus_file["key"]
            else:
                print(
                    red("node who requested the insertion of the song respond incorrectly, or something went wrong with the satus code (if it is 200 in prev/next node, he probably responded incorrectly)"))
                return "Bad status code: " + result.status_code
        except:
            print(red("node who requested the insertion of the song dindnt respond at all"))
            return "Exception raised node who requested the insertion of the song dindnt respond"


    elif ((hashed_key > self_ID and who != 0) or (
            hashed_key > self_ID and hashed_key < previous_ID and who == 0) or (
                  hashed_key <= next_ID and who != 0) or (
                  hashed_key <= previous_ID and hashed_key > next_ID and who == 2)):
        # forward song to next
        if config.NDEBUG:
            print(yellow('forwarding to next..'))
        try:
            result = requests.post(config.ADDR + common.nids[1]["ip"] + ":" + common.nids[1]["port"] +
                                   endpoints.n_insert,
                                   json={"who": who_is, "song": syllabus_file})
            if result.status_code == 200:
                if config.NDEBUG:
                    print("Got response from next: " + yellow(result.text))
                return result.text
            else:
                print(red("Something went wrong while trying to forward insert to next"))
                return "Bad status code: " + result.status_code
        except:
            print(red("Next is not responding to my call..."))
            return "Exception raised while forwarding to next"
        return self_ID
    else:
        print(red("The key hash didnt match any node...consider thinking again about your skills"))
        return "Bad skills"


def eventual_insert(ploads):
    r = requests.post(config.ADDR + common.nids[1]["ip"] + ":" + common.nids[1]["port"] + ends.chain_insert,
                      json=ploads)
    return r.text
