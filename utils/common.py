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
