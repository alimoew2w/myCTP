# vnpy 1.7.2 安装步骤

## Ubuntu:(Workstation)

```bash
cd /home/william/Documents/vnpyDev
wget http://vnpy.oss-cn-shanghai.aliyuncs.com/vnpy-1.7.2.zip 
unzip vnpy-1.7.2.zip

cd vnpy-1.7.2/

ll
# total 64
# drwxrwxr-x  6 william william 4096 Dec  8 15:10 ./
# drwxrwxr-x  4 william william 4096 Dec 10 14:37 ../
# drwxrwxr-x  3 william william 4096 Dec  8 15:10 docker/
# drwxrwxr-x  2 william william 4096 Dec  8 15:10 docs/
# drwxrwxr-x 13 william william 4096 Dec  8 15:10 examples/
# -rw-rw-r--  1 william william  447 Dec  8 15:10 .gitignore
# -rw-rw-r--  1 william william  283 Dec  8 15:10 install.bat
# -rwxr-xr-x  1 william william  471 Dec  8 15:10 install.sh*
# -rw-rw-r--  1 william william 1087 Dec  8 15:10 LICENSE
# -rw-rw-r--  1 william william 3151 Dec  8 15:10 README-en.md
# -rw-rw-r--  1 william william 9961 Dec  8 15:10 README.md
# -rw-rw-r--  1 william william   82 Dec  8 15:10 requirements.txt
# -rw-rw-r--  1 william william 2415 Dec  8 15:10 setup.py
# drwxrwxr-x  8 william william 4096 Dec  8 15:10 vnpy/
```

### 修改　`install.sh`

```bash
#!/bin/bash

#Build ctp/lts/ib api
pushd vnpy/api/ctp
bash build.sh
popd

## =============================================================================
# pushd vnpy/api/lts
# bash build.sh
# popd

# pushd vnpy/api/xtp
# bash build.sh
# popd

# pushd vnpy/api/ib
# bash build.sh
# popd
## =============================================================================

## =============================================================================
#　Install Python Modules
# 在当前用户下安装
pip install --user -r requirements.txt 
## =============================================================================

#Install Ta-Lib
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/
conda config --set show_channel_urls yes
conda install -c quantopian ta-lib=0.4.9

## =============================================================================
#Install vn.py
# python setup.py install
## =============================================================================

# 安装 PyQt 4
conda install pyqt=4

# 修改 /vnpy/trader/app/spreadTrading/uiStWidget.py
# self.horizontalHeader().setResizeMode(QtWidgets.QHeaderView.Stretch)
self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
```

### 修改　`requirements.txt`

```bash
pymongo 
websocket-client
msgpack-python
qdarkstyle
SortedContainers
snappy
futuquant
wmi
```

### 开始安装

``` bash
chmod +x install.sh

./install.sh

# ......
# Processing dependencies for vnpy==1.7.2
# Finished processing dependencies for vnpy==1.7.2
```

### 启动　run.py 报错

```bash
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
#   File "<string>", line 1, in <module>
#   File "/home/william/anaconda2/lib/python2.7/site-packages/vnpy-1.7.2-py2.7.egg/vnpy/trader/vtEngine.py", line 358, in <module>
#     class DataEngine(object):
#   File "/home/william/anaconda2/lib/python2.7/site-packages/vnpy-1.7.2-py2.7.egg/vnpy/trader/vtEngine.py", line 361, in DataEngine
#     contractFilePath = getTempPath(contractFileName)
#   File "/home/william/anaconda2/lib/python2.7/site-packages/vnpy-1.7.2-py2.7.egg/vnpy/trader/vtFunction.py", line 62, in getTempPath
#     os.makedirs(tempPath)
#   File "/home/william/anaconda2/lib/python2.7/os.py", line 157, in makedirs
#     mkdir(name, mode)
# OSError: [Errno 13] Permission denied: '/opt/sublime_text/temp'

sudo chown -R 'william' /home/william/anaconda2/lib/python2.7
sudo mkdir -p  /opt/sublime_text/temp

## sudo chown william -R /opt/sublime_text/temp
## sudo chgrp william -R /opt/sublime_text/temp

sudo chmod 777 -R /opt/sublime_text/temp
```

### `set`

```bash
# Attribute Error: 'QHeaderView' object has no attribute 'setResizeMode'# 

# Traceback (most recent call last):
#   File "/home/william/anaconda2/lib/python2.7/site-packages/vnpy-1.7.2-py2.7.egg/vnpy/trader/uiMainWindow.py", line 197, in openAppFunction
#     self.widgetDict[appName] = appDetail['appWidget'](appEngine, self.eventEngine)
#   File "/home/william/anaconda2/lib/python2.7/site-packages/vnpy-1.7.2-py2.7.egg/vnpy/trader/app/spreadTrading/uiStWidget.py", line 464, in __init__
#     self.initUi()
#   File "/home/william/anaconda2/lib/python2.7/site-packages/vnpy-1.7.2-py2.7.egg/vnpy/trader/app/spreadTrading/uiStWidget.py", line 475, in initUi
#     self.algoManager = StAlgoManager(self.stEngine)
#   File "/home/william/anaconda2/lib/python2.7/site-packages/vnpy-1.7.2-py2.7.egg/vnpy/trader/app/spreadTrading/uiStWidget.py", line 372, in __init__
#     self.initUi()
#   File "/home/william/anaconda2/lib/python2.7/site-packages/vnpy-1.7.2-py2.7.egg/vnpy/trader/app/spreadTrading/uiStWidget.py", line 389, in initUi
#     self.horizontalHeader().setResizeMode(QtWidgets.QHeaderView.Stretch)
# AttributeError: 'QHeaderView' object has no attribute 'setResizeMode'

# 修改 /home/william/anaconda2/lib/python2.7/site-packages/vnpy-1.7.2-py2.7.egg/vnpy/trader/app/spreadTrading/uiStWidget.py

# self.horizontalHeader().setResizeMode(QtWidgets.QHeaderView.Stretch)
self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
```
