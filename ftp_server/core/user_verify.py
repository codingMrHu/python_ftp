#!/usr/bin/env python3
import os
import hashlib, json
from conf import setting
class User_login(object):
    def verify(sefl, login_info):
        list_info = login_info.split(":")
        login_name = list_info[0]
        login_pwd = sefl.to_md5(list_info[1])
        # print("login_info",login_info)
        user_db_path = os.path.join(setting.DATABASE_DIRECTORY, "%s.db"%(login_name))
        if os.path.isfile(user_db_path):
            # read the database and verify
            f = open(user_db_path, "r")
            read_data = json.loads(f.read())
            read_name = read_data["username"]
            read_pwd = read_data["password"]
            # print("read_data",read_data)
            if login_name == read_name and login_pwd == read_pwd:
                return read_data

    def to_md5(self, strs):
        m = hashlib.md5()
        m.update(strs.encode())
        return m.hexdigest()