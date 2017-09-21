#!/usr/bin/env python3
import os,sys

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, BASE_PATH)

DATABASE_DIRECTORY = os.path.join(BASE_PATH, "userdb")

USERS_HOME = os.path.join(BASE_PATH, "home")

#磁盘配额   1000M
LIMIT_SIZE = 10*1000*1024

#ftp服务端口
IP_PORT = ("0.0.0.0",9999)

USERS_PWD = {"huge":"123456","huge2":"123456","huge3":"123456"}
