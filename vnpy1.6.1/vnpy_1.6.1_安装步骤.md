# vnpy_1.6.1 安装步骤

> 这是使用 `vnpy` [1.6.1](http://vnpy.oss-cn-shanghai.aliyuncs.com/vnpy-1.6.1.zip) 进行调试的，机器环境为 Linux Mint 18.1.

--------------------------------------------------------------------------------

## 安装相关的软件

1. Anaconda2 4.0.0:

        sudo chmod +x Anaconda2-4.0.0-Linux-x86_64.sh
        sh /Anaconda2-4.0.0-Linux-x86_64.sh
        export PATH="/home/william/anaconda2/bin:$python"

    > 这里需要注意的是,如果已经安装了 Anaconda2 4.2.3,即最新版本的,那么可以使用以下命令来安装 pyQt

        conda install pyqt=4

        ## Ref:https://github.com/ContinuumIO/anaconda-issues/issues/483
        conda install libgcc

2. pip 安装

        sudo apt-get install python-setuptools
        sudo apt-get install build-essential python-dev libmysqlclient-dev
        sudo apt-get install python-mysqldb

        ## 需要安装 Boost, 否则在编译 vn.api/vn.ctp 的时候会报错
        sudo apt install cmake libblkid-dev libboost-all-dev libaudit-dev e2fslibs-dev

        pip install --upgrade pip
        pip install pymongo qdarkstyle zmq msgpack-python websocket
        pip install pyqtgraph
        pip install MySQL-python

3. talib 安装：

        conda install -c https://conda.anaconda.org/quantopian ta-lib

4. vn.ctp: 记得需要先在 /myCTP/Toolkits/vnpy-1.6.1/vn.api/vn.ctp, 先编译文件,得到动态链接库, 然后再把 `vn.api/vn.ctp/` 文件和 `vn.trader/gateway` 文件夹复制过去.

        cd /vn.api/vn.ctp
        sudo chmod a+x build.sh
        ./build.sh

5. vn.ib
    
        cd /vn.api/vn.ib
        sudo chmod a+x build.sh
        ./build.sh

6. MongoDB
    
        sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 0C49F3730359A14518585931BC711F9BA15703C6
    
    > `ubuntu 16.04`:

        echo "deb [ arch=amd64,arm64 ] http://repo.mongodb.org/apt/ubuntu xenial/mongodb-org/3.4 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-3.4.list
        sudo apt-get update
        sudo apt-get install -y mongodb-org
        sudo service mongod start

    > 查看是不是已经启动了：

        vim /var/log/mongodb/mongod.log

    > 找到以下命令就说明成功启动：
     
        2017-05-04T12:06:50.810+0800 I NETWORK  [thread1] waiting for connections on port 27017“


## 配置文件

1. `/vn.trader/VT_Setting.json`：修改界面的字体、语言、颜色、mongodb 的连接、MySQL 数据库连接等:

        {
            "fontFamily"    : "微软雅黑",
            "fontSize"      : 10,       

            "mongoHost"     : "localhost",
            "mongoPort"     : 27017,
            "mongoLogging"  : true,     

            "mysqlHost"     : "192.168.1.106",
            "mysqlPort"     : 3306,
            "mysqlDB"       : "china_futures_bar",
            "mysqlUser"     : "******",
            "mysqlPassword" : "******",        

            "darkStyle"     : true,
            "language"      : "chinese"
        }

2. `/vn.trader/gateway/ctpGateway/CTP_connect.json`, 填写 *SimNow CTP* 模拟账户的信息:

        {
            "brokerID"      : "9999", 
            "tdAddress"     : "tcp://180.168.146.187:10000", 
            "password"      : "******", 
            "mdAddress"     : "tcp://180.168.146.187:10010", 
            "userID"        : "******"
        }

3. `/vn.trader/dataRecorder/DR_setting.json`: 需要订阅的合约,由 `/vn.trader/vtFunction/def refreshDatarecodeSymbol():` 来生成, 格式如下:

        {  
            "tick": 
                    [
                        ["sn1802", "SHFE"], 
                        ["sn1803", "SHFE"]
                    ],
            "working": true,
            "Active" :
        }

4. `/vn.trader/ctaStrategy/CTA_setting.json`, 设置策略名称、交易的合约等信息:
    
    > 注意,原来的模板仅提供了单合约的,这个可以在 `vtSymbol` 设置为踹个 `list`,然后在策略里面做循环.

        [
            {
                "name": "double ema",
                "className": "EmaDemoStrategy",
                "vtSymbol": ["IF1706","IC1706","IH1706"]
            },      

            {
                "name": "atr rsi",
                "className": "AtrRsiStrategy",
                "vtSymbol": "IC1706"
            },      

            {
                "name": "king keltner",
                "className": "KkStrategy",
                "vtSymbol": "IH1706"
            }
        ]


## 调试步骤

1. 运行 /vn.trader/vtMain.py，即可启动界面：

        python /vn.trader/vtMain.py

2. 或者单独建立一个 `myTest.py` 的文件,进行分步调试.


## 修改文件
