# encoding: UTF-8
################################################################################
## william
## 用于记录 CTP Tick Data
################################################################################
ROOT_PATH = "/home/william/Documents/myCTP/vnpy1.6.1/vn.trader"
# DATA_PATH = "/media/william/Storage2/vnpyData"
################################################################################
##　william
## 加载包
import sys
import os
import ctypes
import platform

import re
from datetime import datetime
import time
import csv
import json

SETTING_FILE = os.path.normpath(os.path.join(ROOT_PATH,'main/setting','VT_setting.json'))
MAIN_SETTING = json.load(file(SETTING_FILE))
################################################################################

################################################################################
## 添加路径
################################################################################
MAIN_PATH = os.path.normpath(os.path.join(ROOT_PATH, 'main'))
sys.path.append(MAIN_PATH)
os.chdir(MAIN_PATH)
################################################################################

################################################################################
# path = os.path.dirname(__file__)
# path = ROOT_PATH
ChinaFuturesCalendar = os.path.normpath(os.path.join(ROOT_PATH,'main','ChinaFuturesCalendar.csv'))
TradingDay = []
with open(ChinaFuturesCalendar) as f:
    ChinaFuturesCalendar = csv.reader(f)
    for row in ChinaFuturesCalendar:
        if row[1] >= '20170101':
            TradingDay.append(row[1])
TradingDay.pop(0)
# print TradingDay

if datetime.now().strftime("%Y%m%d") not in TradingDay:
    print '#'*80
    sys.exit("启禀圣上，今日赌场不开张!!!")
    # sys.exit("Not TradingDaY!!!")
################################################################################


################################################################################
##　增加路径说明
##　william
import vtPath
import eventEngine, vtEngineRecorder, vtGateway
from vtEngineRecorder import MainEngine
import vtFunction

################################################################################
## ========================== 开始启动主程序 ================================== ##
################################################################################
"""主程序入口"""
# 初始化主引擎和主窗口对象
############################################################################
## william
## 继承 vtEngine::MainEngine
mainEngine = MainEngine()
mainEngine.DATA_PATH = MAIN_SETTING['DATA_PATH']
############################################################################
print "\n#######################################################################"
print "main 主函数启动成功！！！"
time.sleep(1.0)
print "#######################################################################\n"
############################################################################


## /////////////////////////////////////////////////////////////////////////////
## 保存 Tick Data 为 /data/csv
dataFile = os.path.join(mainEngine.DATA_PATH,'TickData', (datetime.now().strftime('%Y%m%d')+ '.csv'))

if not os.path.exists(dataFile):
    myHeader = ['timeStamp','date','time','symbol','exchange',\
                'lastPrice','preSettlementPrice','preClosePrice',\
                'openPrice','highestPrice','lowestPrice','closePrice',\
                'upperLimit','lowerLimit','settlementPrice','volume','turnover',\
                'preOpenInterest','openInterest','preDelta','currDelta',\
                'bidPrice1','bidPrice2','bidPrice3','bidPrice4','bidPrice5',\
                'askPrice1','askPrice2','askPrice3','askPrice4','askPrice5',\
                'bidVolume1','bidVolume2','bidVolume3','bidVolume4','bidVolume5',\
                'askVolume1','askVolume2','askVolume3','askVolume4','askVolume5',\
                'averagePrice']
    with open(dataFile, 'w') as f:
        wr = csv.writer(f)
        wr.writerow(myHeader)
    f.close()
## /////////////////////////////////////////////////////////////////////////////

############################################################################
## william
## 默认启动连接 CTP
gatewayName = 'CTP'
print "GatewayName:", gatewayName

try:
    mainEngine.connectCTPAccount(accountInfo = 'HiCloud')
except:
    sys.exit("Failed to connect to CTP!!!")
################################################################################
mainEngine.saveContractInfo()

################################################################################
## william
## 保存合约信息
import pandas as pd
contractInfo = mainEngine.dataEngine.getAllContracts()

dfHeader = ['symbol','name','exchange','gatewayName','productClass',
            'size','priceTick','longMarginRatio','shortMarginRatio']
dfData = []

for contract in contractInfo:
    try:
        dfData.append([contract.__dict__[k] for k in dfHeader])
    except:
        contract.longMarginRatio = ''
        contract.shortMarginRatio = ''
        dfData.append([contract.__dict__[k] for k in dfHeader])

df = pd.DataFrame(dfData, columns = dfHeader)

reload(sys) # reload 才能调用 setdefaultencoding 方法
sys.setdefaultencoding('utf-8')

df.to_csv(os.path.join(mainEngine.DATA_PATH,'ContractInfo', 
    ('ContractInfo_' + datetime.now().strftime('%Y%m%d') + '.csv')), index = False)
################################################################################


## /////////////////////////////////////////////////////////////////////////////
print "\n#######################################################################"
print "正在下载 CTP Tick Data !!!"
print "#######################################################################\n"
## /////////////////////////////////////////////////////////////////////////////
