#!/usr/bin/env python3.5
import os,json
from conf import setting
from core import user_verify
from core import server as main_server

def create_userdb_homedir():
    user_db = {}
    limitsize = setting.LIMIT_SIZE
    for key, value in setting.USERS_PWD.items():
        username = key
        password = user_verify.User_login().to_md5(value)
        user_db_path = os.path.join(setting.DATABASE_DIRECTORY, "%s.db"%(username))
        user_home_path = os.path.join(setting.USERS_HOME, username)
        create_dir(user_home_path)
        user_db["username"] = username
        user_db["password"] = password
        user_db["limitsize"] = limitsize
        user_db["homepath"] = user_home_path
        # print(user_db_path)
        # print(user_home_path)
        # if not os.path.isfile(user_db_path):
        f = open(user_db_path,"w")
        f.write(json.dumps(user_db))
        f.close()

def create_dir(path):
    if not os.path.isdir(path):
        os.popen("mkdir %s"%(path))

if __name__ =="__main__":
    create_userdb_homedir()
    HOST, PORT = "localhost", 9999
    # Create the server, binding to localhost on port 9999
    server = main_server.socketserver.ThreadingTCPServer((HOST, PORT), main_server.MyTCPHandler)
    server.serve_forever()