# encoding: UTF-8
################################################################################
## william
## 用于记录 CTP Tick Data
################################################################################

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
################################################################################


################################################################################
import csv
path = os.path.dirname(__file__)
ChinaFuturesCalendar = os.path.normpath(os.path.join(path,'main','ChinaFuturesCalendar.csv'))
TradingDay = []
with open(ChinaFuturesCalendar) as f:
    ChinaFuturesCalendar = csv.reader(f)
    for row in ChinaFuturesCalendar:
        if row[1] >= '20170101':
            TradingDay.append(row[1])
TradingDay.pop(0)
# print TradingDay

if datetime.now().strftime("%Y%m%d") not in TradingDay:
    sys.exit("Not TradingDaY!!!")

################################################################################
##　增加路径说明
################################################################################
ROOT_PATH = "/home/william/Documents/myCTP/vnpy1.6.1/vn.trader"
main_path = os.path.normpath(os.path.join(ROOT_PATH, 'main'))
data_recorder_path = "/home/william/Documents/myCTP/vnpy1.6.1/vn.data"

sys.path.append(main_path)
os.chdir(main_path)
################################################################################
##　william
import vtPath
import eventEngine, vtEngineRecorder, vtGateway
from vtEngineRecorder import MainEngine
import vtFunction

## /////////////////////////////////////////////////////////////////////////////
## 保存 Tick Data 为 /data/csv
import csv
dataFile = os.path.join(data_recorder_path,'TickData', (datetime.now().strftime('%Y%m%d')+ '.csv'))

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


################################################################################
## ========================== 开始启动主程序 ================================== ##
################################################################################
"""主程序入口"""
# 初始化主引擎和主窗口对象
############################################################################
## william
## 继承 vtEngine::MainEngine
mainEngine = MainEngine()

############################################################################
## william
## 增加 “启动成功” 的提示。
##'''
# mainWindow = MainWindow(mainEngine, mainEngine.eventEngine)
# ## mainWindow.showMaximized() 
# mainWindow.showMinimized()  
##'''
print "\n#######################################################################"
print u"main 主函数启动成功！！！"
time.sleep(1.0)
print "#######################################################################\n"
############################################################################


############################################################################
## william
## 默认启动连接 CTP 
gatewayName = 'CTP'
print U"GatewayName:", gatewayName

try:
    mainEngine.connect(gatewayName)
    print u"CTP 正在登录!!!",
    for i in range(50):
        print ".",
        time.sleep(.1)

    print "\n#---------------------------------------------------------------"
    print u"CTP 连接成功!!!"
    print "#---------------------------------------------------------------"
except:
    print "#---------------------------------------------------------------"
    print u"CTP 连接失败!!!"
    print "#---------------------------------------------------------------"
################################################################################
mainEngine.saveContractInfo()

################################################################################
## william
## 保存合约信息
import pandas as pd
contractInfo = mainEngine.dataEngine.getAllContracts()

dfHeader = ['symbol','name','exchange','gatewayName','productClass','size','priceTick']
dfData = []

for contract in contractInfo:
    dfData.append([contract.__dict__[k] for k in dfHeader])

df = pd.DataFrame(dfData, columns = dfHeader)
df.to_csv(os.path.join(data_recorder_path,'ContractInfo', ('ContractInfo_' + datetime.now().strftime('%Y%m%d') + '.csv')), index = False)
################################################################################


## /////////////////////////////////////////////////////////////////////////////
print "\n#######################################################################"
print u"正在下载 CTP Tick Data !!!"
print "#######################################################################\n"
## /////////////////////////////////////////////////////////////////////////////
