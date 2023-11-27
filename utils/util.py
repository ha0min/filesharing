#!/usr/bin/env python  
# -*- coding:utf-8 _*-

""" 

@Author: Haomin Cheng
@File Name: util.py 
@Time: 2023/11/24
@Contact: haomin.cheng@outlook.com

"""

import hashlib


def hash_str(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def get_identifier(uid, ip, port):
    return uid+'_'+ip+'_'+str(port)

def get_info_from_identifier(file):
    """
    This function returns the node_id, ip and port from the alive file name.
    :param file:
    :return:  A dictionary with the node_id, ip and port
    """
    return {
        'uid': file.split('_')[0],
        'ip': file.split('_')[1],
        'port': file.split('_')[2]
    }
