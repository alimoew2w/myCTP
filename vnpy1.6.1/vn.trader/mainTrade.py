# encoding: UTF-8

import sys
import os
import ctypes
import platform

import re
################################################################################
##　william
## 加载包
################################################################################

################################################################################
##　增加路径说明
################################################################################
os.chdir("/home/william/Documents/myCTP/vnpy1.6.1/vn.trader/main")
sys.path.append("/home/william/Documents/myCTP/vnpy1.6.1/vn.trader/main")
import vtPath

################################################################################
from vtEngine import MainEngine
import vtFunction
################################################################################
##　william
################################################################################
print "\n#######################################################################"
print u"vtEngine 测试成功！！！"
print "#######################################################################"

from uiMainWindow import *

# 文件路径名
#### path = os.path.abspath(os.path.dirname(__file__))    
# path = "/home/william/Documents/vnpy/vnpy-1.6.1/vn.trader"
path = os.getcwd()

ICON_FILENAME = 'vnpy.ico'
ICON_FILENAME = os.path.join(path, ICON_FILENAME)  

SETTING_FILENAME = 'VT_setting.json'
SETTING_FILENAME = os.path.join(path, 'setting', SETTING_FILENAME) 

################################################################################
"""主程序入口"""
################################################################################

# 重载sys模块，设置默认字符串编码方式为utf8
reload(sys)
sys.setdefaultencoding('utf8')  

################################################################################
##　william
## 去掉 windows 的设置
################################################################################
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

print "\n#######################################################################"
print u"main 主函数启动成功！！！"
time.sleep(2.0)
print "#######################################################################\n"
############################################################################


gatewayName = 'CTP'
print U"GatewayName:", gatewayName

try:
    # mainEngine.connect(gatewayName)
    mainEngine.connectCTPAccount(accountInfo = 'accountTrade')
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
############################################################################

############################################################################
## william
## 增加 “启动成功” 的提示。
##'''
mainWindow = MainWindow(mainEngine, mainEngine.eventEngine)
## mainWindow.showMaximized() 
mainWindow.showMinimized()  


################################################################################
## william
## CTA 策略

# 加载设置
mainEngine.ctaEngine.loadSetting()

# print mainEngine.ctaEngine.__dict__
print mainEngine.ctaEngine.strategyDict
# print mainEngine.ctaEngine.tickStrategyDict


################################################################################
# 初始化策略
## BBStragegy
# mainEngine.ctaEngine.initStrategy('Bollinger Band')
# mainEngine.ctaEngine.startStrategy('Bollinger Band')
# strat = mainEngine.ctaEngine.strategyDict
# stratBB = strat['Bollinger Band']
# mainEngine.ctaEngine.stopStrategy('Bollinger Band')


################################################################################
# 初始化策略
## YYStrategy

mainEngine.ctaEngine.initStrategy('Yun Yang')

strat = mainEngine.ctaEngine.strategyDict
stratYY = strat['Yun Yang']
# time.sleep(30)
mainEngine.ctaEngine.startStrategy('Yun Yang')
## 停止策略运行
# mainEngine.ctaEngine.stopStrategy('Yun Yang')

################################################################################
mainEngine.drEngine.getIndicatorInfo('fl_trade')

