# P2P File Sharing System Based on Chord 🗂️

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Introduction

> This is a project for the course CSEN317 Distributed System @Santa Clara University.

This repository contains the code for a file sharing system, designed to manage and facilitate the sharing of
course-related files. The system is implemented using Flask and handles file uploads, queries, and other operations.

The repository already contains a frontend web interface as a submodule. For the latest code, please refer
to [this repository](https://github.com/ha0min/filesharingweb).

## Features 🌟

- 📤 **File Upload and Storage Management**: Handle the uploading and storage of files securely.
- 🔍 **Query System**: Locate and retrieve files efficiently.
- xia **Leader Election**: Server would elect a leader to handle join and leave operations from chord.
- 📁 **Resource Discovery**: Server would join the chord and handle the operations from chord.
- 📝 **Replication & Consistency**: Node would replicate files and ensure consistency. 

## Getting Started 🚀

These instructions will get you a copy of the project up and running on your local machine for development and testing
purposes.

### Prerequisites 📋

#### Before you begin. 

Ensure your machine is publicly accessible via ip. 
 
Otherwise, you should run all the nodes including server in the same network.

#### Add `.env` file to the root directory of the project.

The file should contain the following environment variables:

   ```bash
   AWS_ACCESS_KEY=
   AWS_SECRET_KEY=
   REGION_NAME=
   ```

The AWS credentials should have access to S3 and could perform all operations on S3, including delete object.

### Change variables.

Add the two bucket in your S3 instance. 

Then update `BUCKET_NAME` and `SERVER_BUCKET_NAME`  in `supernode.py` to your own bucket name.

   

### Installation 🔧

1. Clone the repository:
   ```bash
   git clone https://github.com/ha0min/filesharing.git
   ```

2. Install dependencies:
   ```bash
    pip install -r requirements.txt
    ```

3. Install dependencies for the frontend:
   ```bash
    cd filesharingweb
    yarn install
    ```

## Usage 💡

There is two types of nodes in the system: **supernode(server)** and **normal node**.

Normal node could only initiate when there is a supernode running.

### Start a supernode

```bash
python3 flask_server.py -p port_number -b true -k replication_factor
```

A flask server should be running on the `port_number` of your machine's ip. 

Visiting the ip and port number should give you the info stored in that node.

### Start a normal node

```bash
python3 flask_server.py -p port_number
```

A flask server should be running on the `port_number` of your machine's ip. 

The node should get the info supernode and ask to join the chord.

Visiting the ip and port number should give you the info stored in that node.

### Start a web interface

```bash
cd filesharingweb
yarn start
```

A web interface should be running on `localhost:3000`.

## Development 🛠️

### Code Structure 📚

A file tree of the project is:

```
.
├── README.md                
├── chord.py                  # Module for normal node
├── config.py                 # Configuration settings and parameters for the application
├── filesharingweb            # React/Next.js frontend application submodule
├── flask_server.py           # Main entry point for the backend application
├── requirements.txt          
├── supernode.py              # Module for supernode functionalities in the system
└── utils                     
    ├── colorfy.py            # Utility for colorizing terminal output
    ├── common.py             # Global constants and variables
    ├── endpoints.py          # Definitions of API endpoints
    └── util.py               # General utility functions
```

## License 📄

[MIT](https://choosealicense.com/licenses/mit/)


   