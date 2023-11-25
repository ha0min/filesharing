#!/usr/bin/env python  
# -*- coding:utf-8 _*-

""" 

@Author: Haomin Cheng
@File Name: common.py
@Time: 2023/11/24
@Contact: haomin.cheng@outlook.com
@Description: This file is used to store the global variables that are used in the whole project.

"""

# --------------------------------------------------------
# The system global variable

global k # number of replicas
k = 1



# --------------------------------------------------------
# The node's global variable
global is_bootstrap		# true if node is bootstrap
global is_leader # true if the bootstrap node is leader
global my_uid   # my unique identifier, hash of my_ip:my_port
global my_port
global my_ip

global still_on_chord	# flag that becomes (and stays) false when a node departs (used to prevent unwanted operations from a departed node)
still_on_chord = True

# --------------------------------------------------------
# The DHT global variable
mids = []		# list of dicts, descending uids
global nids
nids = []		# list of dicts, first element is the previous node and second element is the next node

global my_finger_table
my_finger_table = []	# list of dicts, each dict is a finger table

global my_finger_table_timestamp


# Supernode variables
global finger_tables
finger_tables = []	# list of dicts, each dict is a finger table

# --------------------------------------------------------
# The File global variable
global replica_file_list
replica_file_list = []
global my_file_list
my_file_list = []

global node_file_dir
global node_my_file_dir
global node_replica_file_dir


# --------------------------------------------------------
# variables for async function
global server_starting
server_starting = False

global server_node_joining
server_node_joining = False

global server_updating_finger_table
server_updating_finger_table = False

global node_updating_finger_table
node_updating_finger_table = False
