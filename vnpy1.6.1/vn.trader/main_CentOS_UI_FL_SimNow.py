# encoding: UTF-8
################################################################################
##　william
## 参数设置
################################################################################
ROOT_PATH   = "/home/trader/myVnpy/vnpy1.6.1/vn.trader"
accountID   = "FL_SimNow"
accountName = u"方莲模拟账户"
################################################################################


################################################################################
##　william
## 加载包
################################################################################
import sys
import os
import ctypes
import platform

import re
from datetime import datetime
import time
import csv
os.putenv('DISPLAY', ':0.0')
import subprocess
################################################################################


################################################################################
## william
##　增加路径说明
################################################################################
MAIN_PATH = os.path.join(ROOT_PATH, 'main')
os.chdir(MAIN_PATH)
sys.path.append(MAIN_PATH)
import vtPath
################################################################################


################################################################################
## william
##　判断当天是否有交易
################################################################################
TradingDay = []
with open('ChinaFuturesCalendar.csv') as f:
    ChinaFuturesCalendar = csv.reader(f)
    for row in ChinaFuturesCalendar:
        if row[1] >= '20170101':
            TradingDay.append(row[1])
TradingDay.pop(0)

if datetime.now().strftime("%Y%m%d") not in TradingDay:
    print '#'*80
    sys.exit("启禀圣上，今日赌场不开张!!!")
    print '#'*80
################################################################################


################################################################################
## william
##　启动主函数入口
################################################################################
from vtEngine import MainEngine
import vtFunction
################################################################################
##　william
################################################################################
from uiMainWindow import *

ICON_FILENAME    = 'vnpy.ico'
ICON_FILENAME    = os.path.join(MAIN_PATH, ICON_FILENAME)

SETTING_FILENAME = 'VT_setting.json'
SETTING_FILENAME = os.path.join(MAIN_PATH, 'setting', SETTING_FILENAME)

################################################################################
"""主程序入口"""
################################################################################
#----------------------------------------------------------------------
def main():
    ############################################################################
    # 重载sys模块，设置默认字符串编码方式为utf8
    reload(sys)
    sys.setdefaultencoding('utf8')

    ############################################################################
    ##　william
    ## 去掉 windows 的设置
    ############################################################################
    # 设置Windows底部任务栏图标
    if 'Windows' in platform.uname() :
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('vn.trader')

    # 初始化Qt应用对象
    app = QtGui.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(ICON_FILENAME))
    app.setFont(BASIC_FONT)

    # 设置Qt的皮肤
    try:
        f = file(SETTING_FILENAME)
        setting = json.load(f)
        if setting['darkStyle']:
            import qdarkstyle
            app.setStyleSheet(qdarkstyle.load_stylesheet(pyside=False))
        f.close()
    except:
        pass

    # 初始化主引擎和主窗口对象
    ############################################################################
    ## william
    ## 继承 vtEngine::MainEngine
    mainEngine = MainEngine()
    mainEngine.accountID = accountID
    mainEngine.accountName = accountName

    print "\n"+'#'*80
    print "main 主函数启动成功！！！"
    time.sleep(1)
    print '#'*80+"\n"
    ############################################################################

    ############################################################################
    ## william
    ## 增加 “启动成功” 的提示。
    ##'''
    mainWindow = MainWindow(mainEngine, mainEngine.eventEngine)
    mainWindow.showMaximized()
    # mainWindow.showMinimized()

    ############################################################################
    ##　william
    ## 接入 CTP 
    ############################################################################
    gatewayName = 'CTP'

    try:
        mainEngine.connectCTPAccount(accountID = accountID)
        print "CTP 正在登录!!!",
        for i in range(33):
            print ".",
            time.sleep(.05)
        print "\n"+'#'*80
        print "CTP 连接成功!!!"
        print '#'*80
    except:
        print "\n"+'#'*80
        sys.exit("CTP 连接失败!!!")
        print '#'*80
    ############################################################################



    ############################################################################
    ## william
    ## CTA 策略

    ## =========================================================================
    ## 数据库名称
    mainEngine.ROOT_PATH          = ROOT_PATH
    mainEngine.dataBase           = accountID
    mainEngine.multiStrategy      = True
    mainEngine.initCapital        = 1000000
    mainEngine.flowCapitalPre     = 0
    mainEngine.flowCapitalToday   = 0
    ## 公司内部人员
    mainEngine.mailReceiverMain   = ['fl@hicloud-investment.com']
    ## 其他人员
    mainEngine.mailReceiverOthers = ['fl@hicloud-investment.com']
    
    mainEngine.openDiscountYY     = 0.002
    mainEngine.closeDiscountYY    = 0.0025
    mainEngine.openAddTickYY      = 0
    mainEngine.closeAddTickYY     = 0
    
    mainEngine.openDiscountOI     = 0.0028
    mainEngine.closeDiscountOI    = 0.0019
    mainEngine.openAddTickOI      = -4
    mainEngine.closeAddTickOI     = -1
    ## =========================================================================


    ############################################################################
    ##　william
    ## 是否启动多策略交易系统
    ############################################################################
    if mainEngine.multiStrategy:
        subprocess.call(['Rscript',
                        os.path.join(ROOT_PATH,'ctaStrategy','start_signal.R'),
                        mainEngine.ROOT_PATH,mainEngine.dataBase], shell = False)
        time.sleep(1)
    ############################################################################



    ############################################################################
    ##　william
    ## 接入 CTP 
    ############################################################################
    ## =========================================================================
    # 加载设置
    mainEngine.ctaEngine.loadSetting()

    print mainEngine.ctaEngine.strategyDict
    ## 所有的策略字典
    stratAll = mainEngine.ctaEngine.strategyDict
    ## =========================================================================

    ###########################################################################
    # 初始化策略
    ## YYStrategy
    mainEngine.ctaEngine.initStrategy('YunYang')
    stratYY = stratAll['YunYang']
    # mainEngine.ctaEngine.startStrategy('YunYang')
    # ## 停止策略运行
    # mainEngine.ctaEngine.stopStrategy('YunYang')


    ############################################################################
    # 初始化策略
    ## YYStrategy
    mainEngine.ctaEngine.initStrategy('OiRank')
    stratOI = stratAll['OiRank']
    # mainEngine.ctaEngine.startStrategy('OiRank')
    ## 停止策略运行
    # mainEngine.ctaEngine.stopStrategy('OiRank')

    ############################################################################
    tempStratOrders = list(set(stratYY.vtOrderIDListOpen) |
                           set(stratYY.vtOrderIDListClose) |
                           set(stratOI.vtOrderIDListOpen) |
                           set(stratOI.vtOrderIDListClose) |
                           set(stratOI.vtOrderIDListUpperLower))

    while(0):
        tempAllWorkingOrders = [mainEngine.getAllWorkingOrders()[j].vtOrderID 
                for j in range(len(mainEngine.getAllWorkingOrders())) 
                    if mainEngine.getAllWorkingOrders()[j].vtOrderID not in tempStratOrders]

        print tempAllWorkingOrders

        if tempAllWorkingOrders:
            for vtOrderID in tempAllWorkingOrders:
                mainEngine.ctaEngine.cancelOrder(vtOrderID)
            time.sleep(0.1)
        else:
            break
    ############################################################################

    mainEngine.ctaEngine.startStrategy('YunYang')
    mainEngine.ctaEngine.startStrategy('OiRank')

    ############################################################################
    mainEngine.drEngine.getIndicatorInfo(dbName           = mainEngine.dataBase,
                                         initCapital      = mainEngine.initCapital,
                                         flowCapitalPre   = mainEngine.flowCapitalPre,
                                         flowCapitalToday = mainEngine.flowCapitalToday)
    # 在主线程中启动Qt事件循环
    sys.exit(app.exec_())
    
if __name__ == '__main__':
    main()
