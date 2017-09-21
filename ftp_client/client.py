#!/usr/bin/env python3
import socket
import os,json,sys
import hashlib
import getpass
import threading
# ftp 客户端
'''
ftp socetserver 状态码

    400 用户认证失败
    401 命令不正确
    402 文件不存在
    403 创建文件已经存在
    404 磁盘空间不够
    405 不续传

    200 用户认证成功
    201 命令可以执行
    202 磁盘空间够用
    203 文件具有一致性
    205 续传

    000 系统交互码
'''
class Myclient(object):
    def __init__(self,ip_port):
        self.ip_port = ip_port

    def help(self):
        msg = '''
command:
        ls
        rm filename
        pwd
        cd ../.. or filename
        get filename
        put filename
        '''
        print(msg)

    # 连接server服务器
    def connect(self):
        self.client = socket.socket()
        self.client.connect(self.ip_port)

    # 程序开始
    def start(self):
        self.connect()
        while True:
            username = input("\033[1;32;1minput user name:\033[0m").strip()
            password = getpass.getpass("\033[1;32;1minput your password:\033[0m").strip()
            login_info = ("%s:%s"%(username,password))
            # 向服务器发送登录信息
            # login_info = "huge:123456"
            self.client.send(login_info.encode())
            # 服务器返回登录状态
            status_code = self.client.recv(1024).decode()

            if status_code == "400":
                print("name or password wrong!!")
                continue
            else:
                print("login success!")
                self.interactive()

    def interactive(self):
        while True:
            command = input("\033[1;32;1m->>:\033[0m").strip()
            if not command:
                continue
            # 获取输入命令的首字符串 然后利用反射调用对应的函数执行相应的动作
            command_first_str = command.split()[0]
            if hasattr(self, command_first_str):
                func = getattr(self, command_first_str)
                func(command)
            else:
                print("%s command not exist!"%(command_first_str))
                self.help()

    def ls(self, *args):
        cmd = ''.join(args[0])
        msg_dic={
        "action":"ls",
        "cmd":cmd
        }
        self.__universal_method_havedata(msg_dic)
    
    def rm(self, *args):
        cmd = ''.join(args[0])
        msg_dic={
        "action":"rm",
        "cmd":cmd
        }
        self.__universal_method_havedata(msg_dic)

    def pwd(self, *args):
        cmd = ''.join(args[0])
        msg_dic={
        "action":"pwd",
        "cmd":cmd
        }
        if(len(cmd.split()) ==1):
            self.__universal_method_havedata(msg_dic)
        else:
            print("%s : not exist!"%cmd)

    def mkdir(self, *args):
        cmd = ''.join(args[0])
        msg_dic={
        "action":"mkdir",
        "cmd":cmd
        }
        self.__universal_method_nodata(msg_dic)

    def cd(self, *args):
        cmd = ''.join(args[0])
        msg_dic={
        "action":"cd",
        "cmd":cmd
        }
        self.__universal_method_nodata(msg_dic)

    def get(self, *args):
        '''
        get命令，默认从用户在server的当前目录下寻找并发送数据
        可实现续传
        '''
        command = args[0].split()
        if len(command) >1:
            filename = command[1]
            client_exist_file = os.path.isfile(filename)
            # client和server端命令交互统一以字典的形式 便于扩展
            msg_dic={
            "action":"get",
            "filename":filename,
            "client_exist_file":client_exist_file
            }
            self.client.send(json.dumps(msg_dic).encode())
            # 接收server端返回的文件状态（server端是否存在该文件）
            status_code = self.client.recv(1024).decode()
            # server exist file
            if status_code =="201":
                # 判断client是否存在文件 是否进行续传
                if client_exist_file:
                    status_code = "205"
                    get_size = os.stat(filename).st_size
                else:
                    status_code = "405"
                    get_size = 0
                continue_msg={
                "status_code":status_code,
                "get_size":get_size
                }
                # 是否续传的信息发送至server，状态 及已经收到的文件大小
                self.client.send(json.dumps(continue_msg).encode())
                file_size = int(self.client.recv(1024).decode())
                if get_size == file_size:
                    print_strs = "%s already exists!!"%filename
                else:
                    print_strs = "loading over!"
                # 以追加的方式打开文件，即可实现续传
                f = open(filename, "ab")
                while get_size< file_size:
                    if file_size - get_size>1024:
                        size = 1024
                    else:
                        size = file_size- get_size
                    data = self.client.recv(size)
                    f.write(data)
                    get_size +=len(data)
                    self.__progress(get_size, file_size, "loading.........")
                print(print_strs)
                f.close()
            else:
                print("%s not exist!"%filename)
        else:
            print("%s not right!"%command)
            self.help()



    def put(self, *args):
        '''
        put文件上传命令，上传的文件默认保存到用户在server上的self.current_path当前目录下
        md5进行文件是否一致校验
        '''
        command = args[0].split()
        if len(command)>1:
            filename = command[1]

            # print("os path******:",os.path)
            if os.path.isfile(filename):
                filesize = os.stat(filename).st_size
                base_filename = os.path.basename(filename)
                msg_dic = {
                "action":"put",
                "filename":base_filename,
                "filesize":filesize,
                "overridden":True
                }
                # 将信息转化成json格式 发送
                self.client.send(json.dumps(msg_dic).encode())
                # print("client send:",json.dumps(msg_dic).encode())
                # 接收server返回的磁盘空间状态
                status_code = self.client.recv(1024).decode()
                # server返回 202 磁盘空间够用 即可发送文件
                if status_code =="202":
                    self.client.send("000".encode())
                    send_size = int(self.client.recv(1024).decode())
                    if send_size == filesize:
                        print_strs = "Server has already been in file %s [filename] !"%filename
                    else:
                        print_strs = "upload over"
                    m = hashlib.md5()
                    f = open(filename,"rb")
                    f.seek(send_size)
                    for line in f:
                        m.update(line)
                        send_size = f.tell()
                        self.client.send(line)
                        # 显示进度条
                        self.__progress(send_size, filesize, "uploading.....")
                    print(print_strs)
                    f.close()
                    self.client.send(m.hexdigest().encode())
                    status_code = self.client.recv(1024).decode()
                    if status_code == "203":
                        print("\nThe FtpServer get the same file")
                    else:
                        print("\nThe FtpServer not get the same file!!")
                else:
                    print("\nThe FtpServer diskfull!")
            else:
                print("%s not exist !"%(filename))
        else:
            print("[401] %s error!!"%(command))

    def __progress(self, trans_size, file_size, mode):
        '''
        显示进度条
        trans_size: 已经传输的数据大小
        file_size: 文件的总大小
        mode: 模式
        '''
        bar_length = 100    #进度条长度
        percent = float(trans_size) / float(file_size)
        hashes = '=' * int(percent * bar_length)    #进度条显示的数量长度百分比
        spaces = ' ' * (bar_length - len(hashes))    #定义空格的数量=总长度-显示长度
        # 格式化输入上传状态：uploading.....:2.26M/2.26M 100% [====================================================================]
        # \r 默认表示将输出的内容返回到第一个指针，这样的话，后面的内容会覆盖前面的内容
        # print()默认换行输出，所以用sys.stdout.write
        sys.stdout.write(
            "\r%s:%.2fM/%.2fM %d%% [%s]"%(mode,trans_size/1048576,file_size/1048576,percent*100,hashes+spaces))
        sys.stdout.flush()

    def __universal_method_havedata(self, msg_dic):
        self.client.send(json.dumps(msg_dic).encode())
        recv_data = self.client.recv(1024).decode()
        if recv_data != "000":
            print(recv_data)

    def __universal_method_nodata(self, msg_dic):
        self.client.send(json.dumps(msg_dic).encode())
        recv_status = self.client.recv(1024).decode()
        if recv_status == "401":
            print("%s : not right!"%(msg_dic["cmd"]))

        if recv_status != "401" and msg_dic["action"] == "cd":
            # 在连续的两次recv之间插入一次send交互 防止粘包
            self.client.send("000".encode())
            recv_msg = self.client.recv(1024).decode()
            print(recv_msg)

if __name__ == "__main__":
    ip_port =("localhost",9999)         #服务端ip、端口
    client = Myclient(ip_port)     #创建客户端实例
    client.start()                      #开始连接