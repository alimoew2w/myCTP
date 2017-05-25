# `setting` 配置文件

本文件夹主要用于储存涉及账户安全的 `.json` 配置文件, 我把这些文件做了隐藏设置. 将来克隆项目的时候, 需要自己重新配置.

- `VT_setting.json`: 顶层的配置文件, 具体格式如下

        {
            "fontFamily"    : "微软雅黑",
            "fontSize"      : 10,       

            "mongoHost"     : "localhost",
            "mongoPort"     : 27017,
            "mongoLogging"  : true,     

            "mysqlHost"     : "MySQL 服务器 ip 地址",
            "mysqlPort"     : 端口号,
            "mysqlDB"       : "任选一个数据库",
            "mysqlUser"     : "用户名",
            "mysqlPassword" : "用户密码",        

            "darkStyle"     : true,
            "language"      : "chinese"
        }

- `CTP_setting.json`: CTP 账户连接配置文件.

        {
            "brokerID": "9999", 
            "tdAddress": "tcp://180.168.146.187:10000", 
            "password": "CTP账户密码", 
            "mdAddress": "tcp://180.168.146.187:10010", 
            "userID": "CTP账户ID"
        }

