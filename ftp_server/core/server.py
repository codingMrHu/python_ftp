#!/usr/bin/env python3
import socketserver
import  json
import os
import hashlib
from core import user_verify as user_pwd_verify
import threading
# ftp server:
class MyTCPHandler(socketserver.BaseRequestHandler):
    # 类MyTCPHandler的实例被创建 就会自动调用handle函数处理socket任务
    def handle(self): 
        while True:
            try:
                login_data = self.request.recv(1024)
                if not login_data:
                    print("client break........")
                    break
                login_msg = login_data.decode().strip()
                print("clien addr:", self.client_address[0])
                # print("server recv data:", login_msg)
                verify_result = self.user_verify(login_msg)
                status_code = verify_result[0]
                print("server status", status_code)
                print(threading.active_count())
                self.request.send(status_code.encode())
                if status_code == "400":
                    continue
                user_db = verify_result[1]
                self.home_path = user_db["homepath"]
                self.current_path = user_db["homepath"]
                self.limitsize = user_db["limitsize"]
                while True:
                    data = self.request.recv(1024)
                    if not data:
                        print("client break........")
                        break
                    msg_dic = json.loads(data.decode())
                    action = msg_dic["action"]
                    if hasattr(self, action):
                        func = getattr(self, action)
                        func(msg_dic)

            except ConnectionResetError as e:
                print(e)
        # 关闭socket应该在最外层循环，最外层循环执行结束就表示一个client连接断开
        self.request.close()

    def user_verify(self, login_msg):
        '''
        用户登录验证，返回两个数据：
        1）登录状态200表示登录成功
        2）登录用户的数据信息
        '''
        user_verify_db = user_pwd_verify.User_login().verify(login_msg)
        if user_verify_db:
            return "200",user_verify_db
        else:
            return "400",user_verify_db

    def ls(self, *args):
        cmd = args[0]
        ls_operation = "%s %s"%(''.join(cmd["cmd"]), self.current_path)
        # print("ls_operation:",ls_operation)
        cmd_result = os.popen(ls_operation).read()
        if cmd_result:
            self.request.send(cmd_result.encode())
        else:
            self.request.send("000".encode())
    
    def rm(self, *args):
        cmd = args[0]
        cmd_list = cmd["cmd"].split()
        if len(cmd_list) >1:
            file_path = os.path.join(self.current_path,cmd_list[1])
            if os.path.isfile(file_path):
                rm_operation = "rm %s"%file_path
                cmd_result = os.popen(rm_operation).read()
                self.request.send("000".encode())
            else:
                self.request.send(("The file [%s] not exist!"%str(cmd_list[1])).encode())
        else:
            self.request.send(("%s not right!"%cmd["cmd"]).encode())
        
    def pwd(self, *args):
        '''
        处理pwd命令将用户当前所在目录发送给client
        这里参照ubunut下的pwd命令 并没有对命令的正确与否进行判断
        只有client发送的命令action是pwd即发送
        '''
        # cmd = args[0]
        send_data = self.current_path
        # print("pwd:",send_data)
        self.request.send(send_data.encode())

    def mkdir(self, *args):
        cmd = args[0]
        strs_mkdir = cmd["cmd"].split()
        if len(strs_mkdir) ==2:
            self.request.send("201".encode())
            mkdir_operation = "mkdir %s"%(os.path.join(self.current_path, strs_mkdir[1]))
            # print("mkdir_operation:", mkdir_operation)
            os.popen(mkdir_operation)
        else:
            # cmd not exist!!
            self.request.send("401".encode())

    def cd(self, *args):
        '''
        处理client端发来的cd命令。
        client只允许在自己的用户目录下活动不可切换访问 home/username目录之外的内容
        '''
        cmd = args[0]
        strs_mkdir = cmd["cmd"].split()
        if len(strs_mkdir) ==2:
            self.request.send("201".encode())
            cd_dir = os.path.join(self.current_path, strs_mkdir[1])
            # cd_operation = "cd %s"%cd_dir
            # 在连续的两次recv之间插入一次send交互 防止粘包
            tmp = self.request.recv(1024).decode()
            send_msg =''
            if os.path.isdir(cd_dir):
                after_cdpath = self.__operate_dir(cd_dir)
                # print("after_cdpath",after_cdpath)
                # print("homepath",self.home_path)
                if len(after_cdpath) >= len(self.home_path):
                    self.current_path = after_cdpath
                    send_msg = self.current_path
                else:
                    send_msg = "cd %s has no permission !!!!"%(after_cdpath)
            else:
                send_msg = "%s is not a dir"%strs_mkdir[1]
            self.request.send(send_msg.encode())
        else:
            self.request.send("401".encode())

    def get(self, *args):
        '''
        server端对应client端的get命令，默认从用户的当前目录下寻找并发送数据
        可实现续传
        '''
        cmd_dic = args[0]
        filename = cmd_dic["filename"]
        client_exist_file = cmd_dic["client_exist_file"]
        file_path = os.path.join(self.current_path, filename)
        if os.path.isfile(file_path):
            # 向client发送表示server端文201表示文件件存在 
            self.request.send("201".encode())
           
            # 接受client发来的短线续传的相关信息
            continue_msg = json.loads(self.request.recv(1024).decode())

            filesize = os.stat(file_path).st_size
            # 向client发送文件大小
            self.request.send(str(filesize).encode())

            is_continued_send = continue_msg["status_code"]
            have_sendsize = continue_msg["get_size"]
            # print("is_continued_send*********:", is_continued_send)
            f = open(file_path,"rb")
            # f.seek 将文件游标移动到已经发送文件位置 这样便可进行续传
            f.seek(have_sendsize)
            for line in f:
                self.request.send(line)

        else:
            # server端文件不存在
            self.request.send("402".encode())
           

    def put(self, *args):
        '''
        处理client的put文件上传命令，上传的文件默认保存到用户的self.current_path当前目录下
        md5进行文件是否一致校验
        '''
        cmd_dic = args[0]
        filename = cmd_dic["filename"]
        filesize = cmd_dic["filesize"]
        save_file_path = os.path.join(self.current_path, filename)

        # juge the disk is engh
        limit_size = self.limitsize
        used_size = self.__getdirsize(self.home_path)
        if limit_size - used_size > filesize:
            status_code = "202"
        else:
            status_code = "402"
        self.request.send(status_code.encode())

        if status_code == "202":
            received_size = 0
            # 判断要上传的文件是否存在 如果存在则获取大小
            if os.path.isfile(save_file_path):
                received_size = os.stat(save_file_path).st_size
            # 接收client发送的数据000 防止粘包
            self.request.recv(1024)
            # 发送已经接收文件的大小
            self.request.send(str(received_size).encode())
            m = hashlib.md5()
            f = open(save_file_path, "ab")
            f.seek(received_size)
            while received_size < filesize:
                if(filesize - received_size >1024):
                    size = 1024
                else:
                    size = filesize - received_size 
                data = self.request.recv(size)
                f.write(data)
                m.update(data)
                received_size += len(data)
            f.close()
            print("server get file over")
            client_md5 = self.request.recv(1024).decode()
            server_md5 = m.hexdigest()
            if client_md5 == server_md5:
                self.request.send("203".encode())
            else:
                self.request.send("000".encode())

    def __operate_dir(self, strs_dir):
        '''
        处理 cd ../..命令执行后当前所在的目录
        '''
        if ".." in strs_dir:
            list_dir = strs_dir.split("/")
            count = 0
            for item in list_dir:
                if item =="..":
                    count+=1
            tmp = self.current_path
            for x in range(count):
                tmp = os.path.dirname(tmp)
            strs_dir = tmp

        return strs_dir

    def __getdirsize(self, dir_path):
        '''
        获取目录下文件占用的磁盘大小
        '''
        size = 0
        for root, dirs, files in os.walk(dir_path):
            size += sum([os.path.getsize(os.path.join(root, name)) for name in files])
        return size

if __name__=="__main__":
    HOST, PORT = "localhost", 9999
    # 调用socketserver的ThreadingTCPServer类创建实例，每个新的client请求时server就会自动创建一个新的线程来处理
    server = socketserver.ThreadingTCPServer((HOST, PORT), MyTCPHandler)
    server.serve_forever()