# encoding: UTF-8

import sys
import os
import ctypes

################################################################################
##　william
## 加载包
################################################################################
################################################################################
## william
## 不要打印 TickData
'''
global printTickData
printTickData = True

global saveTickData
saveTickData = True
'''
################################################################################



################################################################################
##　增加路径说明
################################################################################
os.chdir("/home/william/Documents/vnpy/vnpy-1.6.1/vn.trader")

import vtPath
################################################################################
##　william
################################################################################
print "\n#######################################################################"
print u"vtPath 启动成功！！！"
print "#######################################################################"

################################################################################
##　william
## Break Point
################################################################################

## /////////////////////////////////////////////////////////////////////////////
## william
## SaveTickData
from vtEngineSaveTickData import MainEngine
import vtFunctionSaveTickData
## /////////////////////////////////////////////////////////////////////////////


################################################################################
##　william
################################################################################
print "\n#######################################################################"
print u"vtEngine 启动成功！！！"
print "#######################################################################"

'''
from uiMainWindow import *
'''
import time

# 文件路径名
#### path = os.path.abspath(os.path.dirname(__file__))    
path = "/home/william/Documents/vnpy/vnpy-1.6.1/vn.trader"

ICON_FILENAME = 'vnpy.ico'
ICON_FILENAME = os.path.join(path, ICON_FILENAME)  

################################################################################
## william
SETTING_FILENAME = 'VT_settingSavetIickData.json'
SETTING_FILENAME = os.path.join(path, SETTING_FILENAME)  


#----------------------------------------------------------------------
def main():
    """主程序入口"""
    # 重载sys模块，设置默认字符串编码方式为utf8
    reload(sys)
    sys.setdefaultencoding('utf8')

    # 初始化主引擎和主窗口对象
    mainEngine = MainEngine()
    
    print "\n#######################################################################"
    print u"main 主函数启动成功！！！"
    time.sleep(3)
    print "#######################################################################\n"
    ############################################################################

    ############################################################################
    ##　william
    ## 保存 Tick Data 为 /data/csv
    ############################################################################
    ## >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    import os.path      

    dataFile = os.path.join('/home/william/Documents/vnpy/vnpy-1.6.1/data/',(mainEngine.todayDate + '.csv'))  
    print dataFile  

    if not os.path.exists(dataFile): 
        myHeader = "tradingDay,time,instrumentID,exchangeID,lastPrice,volume,openInterest,upperLimit,lowerLimit,bidPrice1,bidPrice2,bidPrice3,bidPrice4,bidPrice5,askPrice1,askPrice2,askPrice3,askPrice4,askPrice5,bidVolume1,bidVolume2,bidVolume3,bidVolume4,bidVolume5,askVolume1,askVolume2,askVolume3,askVolume4,askVolume5,preSettlementPrice,settlementPrice,averagePrice"   
        with open(dataFile, 'w') as f:
            f.write(myHeader + '\n')
    ## <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

    ############################################################################
    ## william
    ## 默认启动连接 CTP 
    gatewayName = 'CTP'
    print U"GatewayName:", gatewayName

    try:
        mainEngine.connect(gatewayName)
        print u"CTP 正在登录!!!",
        for i in range(30):
            print ".",
            time.sleep(.25)
        print "\n#---------------------------------------------------------------"
        print u"CTP 连接成功!!!"
        print "#---------------------------------------------------------------"
    except:
        print "#---------------------------------------------------------------"
        print u"CTP 连接失败!!!"
        print "#---------------------------------------------------------------"
    ############################################################################

    ############################################################################
    ## william
    ## 更新 /dataRecorder/DR_setting
    vtFunctionSaveTickData.refreshDatarecodeSymbol()
    print "\n#######################################################################"
    print u"DR_setting 已经更新完成!!!"
    print "#######################################################################"
    ############################################################################

    print "\n#######################################################################"
    print u"正在下载 CTP Tick Data !!!"
    print "#######################################################################"

if __name__ == '__main__':
    main()
