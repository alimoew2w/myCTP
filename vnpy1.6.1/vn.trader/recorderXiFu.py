# encoding: UTF-8
################################################################################
## william
## 用于记录 CTP Tick Data
################################################################################
ROOT_PATH = "/home/william/Documents/myCTP/vnpy1.6.1/vn.trader"
accountID = "XiFu"
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

import globalSetting
globalSetting.accountID = accountID

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

## -----------------------------------------------------------------------------
accountInfo = 'CTP' + '_connect_account_' + accountID + '.json'
accountInfo = os.path.normpath(os.path.join(ROOT_PATH,'main/setting',accountInfo))
accountInfo = json.load(file(accountInfo))
## -----------------------------------------------------------------------------

############################################################################
print "\n"+'#'*80
print "main 主函数启动成功！！！"
time.sleep(1.0)
print "#"*80+"\n"
############################################################################


## /////////////////////////////////////////////////////////////////////////////
## 保存 Tick Data 为 /data/csv
dataFile = os.path.join(mainEngine.DATA_PATH, accountInfo['accountID'], 'TickData', (datetime.now().strftime('%Y%m%d')+ '.csv'))

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
    mainEngine.connectCTPAccount(accountID = accountInfo['accountID'])
except:
    sys.exit("Failed to connect to CTP!!!")
################################################################################
mainEngine.saveContractInfo()

################################################################################
time.sleep(20)

# print dir(mainEngine)

from shutil import copyfile
try:
    copyfile(os.path.normpath(os.path.join(ROOT_PATH,'main','contract.csv')),
            os.path.join(mainEngine.DATA_PATH, accountInfo['accountID'], 'ContractInfo', 
             (datetime.now().strftime('%Y%m%d') + '.csv')))
except:
    None
## /////////////////////////////////////////////////////////////////////////////
print "\n"+'#'*80
print "正在下载 CTP Tick Data !!!"
print "#"*80+"\n"
## /////////////////////////////////////////////////////////////////////////////
