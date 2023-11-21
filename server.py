#!/usr/bin/env python  
# -*- coding:utf-8 _*-

""" 

@Author: Haomin Cheng
@File Name: server.py 
@Time: 2023/11/20
@Contact: haomin.cheng@outlook.com

"""
from flask import Flask

from command_handler import CommandHandler
from node import Node

app = Flask(__name__)

command_handler = CommandHandler()

@app.route('/')
def home():
    return "Node is running!"

@app.route('/list_neighbors')
def list_neighbors():
    return str(command_handler.list_neighbors())

# Add other routes as needed


if __name__ == '__main__':
    app.run(debug=False, port=5000)  # Run on port 5000
