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

global join_bootstrap  # POST: adds node to the Chord {node uid, ip, port}
join_bootstrap = '/boot/join'

global b_leave  # POST: removes node from the Chord {node uid}
b_leave = '/boot/leave'

global b_list  # GET: returns list of nodes in the Chord
b_list = '/boot/list'

global ping # GET: check if the node alive, returns "pong"
ping = '/ping'