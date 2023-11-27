#!/usr/bin/env python  
# -*- coding:utf-8 _*-

""" 

@Author: Haomin Cheng
@File Name: endpoints.py
@Time: 2023/11/24
@Contact: haomin.cheng@outlook.com

"""

global node_info # GET: returns node info
node_info = '/node/info'

global node_join_bootstrap  # POST: adds node to the Chord {node uid, ip, port}
node_join_bootstrap = '/boot/join'

global b_leave  # POST: removes node from the Chord {node uid}
b_leave = '/boot/leave'

global b_list  # GET: returns list of nodes in the Chord
b_list = '/boot/list'

global ping # GET: check if the node alive, returns "pong"
ping = '/ping'

global node_join_procedure # POST: adds node to the Chord {node uid, ip, port}
node_join_procedure = '/node/procedure'

global node_update_replicate # POST: updates the replicate nodes of the node {node uid, ip, port}
node_update_replicate = '/node/update_replicate'

global node_update_neighbours
node_update_neighbours = '/node/update_neighbours'

global replic_nodes_list # POST: returns list of replicate nodes of the node
replic_nodes_list = '/node/replic_nodes_list'

global node_update_finger_table # POST: updates the finger table of the node {node uid, ip, port}
node_update_finger_table = '/node/update_finger_table'

global user_add_new_file # POST: adds a new file to the node {file name, file content}
user_add_new_file = '/user/new_file'

global request_upload_file_to_host # POST: request to upload a file to the node {file name, file content}
request_upload_file_to_host = '/node/request_upload_file'

global file_from_upload_node # POST: adds a new file to the node {file name, file content}
file_from_upload_node = '/node/file_from_upload'

global find_file_host_node # POST: find the host node of the file {file name}
find_file_host_node = '/node/find_file_host_node'

global file_from_redistribute # POST: adds a new file to the node {file name, file content}
file_from_redistribute = '/node/file_from_redistribute'