# encoding: UTF-8
################################################################################
##　william
## 参数设置
################################################################################
ROOT_PATH      = "/home/william/Documents/myCTP/vnpy-1.7.2"
accountID      = "FL_SimNow"
accountName    = u"方莲模拟账户"
accountCapital = 1000000
################################################################################

# 重载sys模块，设置默认字符串编码方式为utf8
import sys,os,subprocess
os.putenv('DISPLAY', ':0.0')
reload(sys)
sys.setdefaultencoding('utf8')

## =============================================================================
# MAIN_PATH = os.path.join(ROOT_PATH, 'main')
MAIN_PATH = os.path.join(ROOT_PATH)
os.chdir(MAIN_PATH)
sys.path.append(MAIN_PATH)
## =============================================================================

# 判断操作系统
import platform
system = platform.system()
import re,datetime,time,csv
from datetime import datetime
## =============================================================================

# vn.trader模块
from vnpy.event import EventEngine
from vnpy.trader.vtEngine import MainEngine
from vnpy.trader.uiQt import createQApp
from vnpy.trader.uiMainWindow import MainWindow

# 加载底层接口
from vnpy.trader.gateway import ctpGateway

# 加载上层应用
from vnpy.trader.app import (riskManager, ctaStrategy, spreadTrading)


# ----------------------------------------------------------------------
def main():
    """主程序入口"""
    # 创建Qt应用对象
    qApp = createQApp()

    # 创建事件引擎
    ee = EventEngine()

    # 创建主引擎
    me = MainEngine(ee)

    # 添加交易接口
    me.addGateway(ctpGateway)

    # 添加上层应用
    me.addApp(riskManager)
    me.addApp(ctaStrategy)
    me.addApp(spreadTrading)

    # 创建主窗口
    mw = MainWindow(me, ee)
    mw.showMaximized()

    # 在主线程中启动Qt事件循环
    sys.exit(qApp.exec_())


if __name__ == '__main__':
    main()
