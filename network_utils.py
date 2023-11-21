#!/usr/bin/env python  
# -*- coding:utf-8 _*-

""" 

@Author: Haomin Cheng
@File Name: network_utils.py 
@Time: 2023/11/19
@Contact: haomin.cheng@outlook.com

"""
import socket

import requests

def get_public_ip():
    try:
        response = requests.get('https://ifconfig.me')
        ip = response.text
        print("External IP:", ip)
        return ip
    except requests.RequestException:
        return '127.0.0.1'

def get_my_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        s.connect(('ifconfig.me', 1))
        ip = s.getsockname()[0]
        print("External IP:", ip)
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip