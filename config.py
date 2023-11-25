#!/usr/bin/env python  
# -*- coding:utf-8 _*-

""" 

@Author: Haomin Cheng
@File Name: config.py 
@Time: 2023/11/24
@Contact: haomin.cheng@outlook.com

"""
import os

cwd = os.getcwd()  # Get the current working directory (cwd)

BOOTSTRAP_IP = "127.0.0.1"  # TODO fix this
BASE_DIR = cwd + '/'
BOOTSTRAP_PORT = "5000"
ADDR = 'http://'
BDEBUG = True  # debug information for bootstrap operations
NDEBUG = True  # debug information for node operations
TDEBUG = False  # debug information fot test operations
vBDEBUG = False  # extra verbose debug information for bootstrap operations
vNDEBUG = False  # extra verbose debug information for node operations

FILE_DIR = BASE_DIR + 'files/'