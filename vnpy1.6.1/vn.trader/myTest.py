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

import vtPath
################################################################################
##　william
################################################################################
print "\n#######################################################################"
print u"vtPath 测试成功！！！"
print "#######################################################################\n"

################################################################################
##　william
## Break Point
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
SETTING_FILENAME = os.path.join(path, SETTING_FILENAME) 
#
#
#
#
#
#
#
#
#
"""主程序入口"""
# 重载sys模块，设置默认字符串编码方式为utf8
reload(sys)
sys.setdefaultencoding('utf8')  

################################################################################
##　william
## 去掉 windows 的设置
################################################################################
# 设置Windows底部任务栏图标
#### if 'Windows' in platform.uname() :
####     ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('vn.trader')     

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
print u"mainEngine 可以使用的方法与属性包括以下这些:"
print dir(mainEngine)
print "#######################################################################\n"

############################################################################
##　william
## 保存 Tick Data 为 /data/csv
############################################################################
## >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
"""
import os.path      

dataFile = os.path.join('/home/william/Documents/vnpy/vnpy-1.6.1/data/',(mainEngine.todayDate + '.csv'))  
print dataFile  

if not os.path.exists(dataFile):
    myHeader = "TradingDay,time,symbol,exchange,lastPrice,volume,openInterest,upperLimit,lowerLimit,bidPrice1,bidPrice2,bidPrice3,bidPrice4,bidPrice5,askPrice1,askPrice2,askPrice3,askPrice4,askPrice5,bidVolume1,bidVolume2,bidVolume3,bidVolume4,bidVolume5,askVolume1,askVolume2,askVolume3,askVolume4,askVolume5,averageprice"    

    with open(dataFile, 'w') as f:
        f.write(myHeader + '\n')
"""
## <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

############################################################################
## william
## 获取 mainEngine 的所有合约信息
"""
AllContractInfo = mainEngine.getAllContracts()
print len(AllContractInfo)  

dfHeader = vars(AllContractInfo[0]).keys()
print dfHeader
dfData = [] 

for i in range(len(AllContractInfo)):
    dt = AllContractInfo[i]
    temp = vars(dt).values()
    dfData.append(temp)
df = pd.DataFrame(dfData, columns = dfHeader)
print df
df = df.ix[:,['gatewayName','name','exchange','symbol','priceTick','productClass','vtSymbol','size']]
print df

## 因为已经在 MainEngine 中自动启动 DataEngine.loadContracts(), 所有合约信息已经保存在 mainEngine.dataEngine.contractDict
## 也可以使用  
AllContractInfo = mainEngine.dataEngine.contractDict
print type(AllContractInfo) 

dfHeader = vars(AllContractInfo[AllContractInfo.keys()[0]]).keys()
print dfHeader
dfData   = []   

for key in AllContractInfo.keys():
    temp = AllContractInfo[key]
    tempRes = vars(temp).values()
    dfData.append(tempRes)
'''
print dfData
'''
df = pd.DataFrame(dfData, columns = dfHeader)
df = df.ix[:,['gatewayName','name','exchange','symbol','priceTick','productClass','vtSymbol','size']]
print df
"""
############################################################################


############################################################################
## william
## 增加 “启动成功” 的提示。
##'''
mainWindow = MainWindow(mainEngine, mainEngine.eventEngine)
## mainWindow.showMaximized() 
mainWindow.showMinimized()  
##'''
print "\n#######################################################################"
print u"main 主函数启动成功！！！"
time.sleep(5.0)
print "#######################################################################\n"
############################################################################



############################################################################
## william
## 默认启动连接 MySQL
## 已经在 vtEngine.MainEngine.connect() 连接 CTP 后自动连接 MySQL 数据库
"""
mainEngine.dbMySQLConnect()

try:
    mysqlQueryTest = mainEngine.dbMySQLQuery('china_futures_bar', \
                        "select * from daily where tradingday = 20170504 limit 2;")
    for k in mysqlQueryTest:
        print k
except:
    print u"MySQL 查询失败!!!"
"""
############################################################################


############################################################################
## william
## 默认启动连接 CTP 
print "#######################################################################"
print "以下是目前可以使用的 gateway name:"
time.sleep(1.0)
for i in range(len(GATEWAY_DICT)):  
    print u"#---------------------------------------------------------------"
    print i+1, ":===>", list(GATEWAY_DICT)[i]
    print u"#---------------------------------------------------------------"
print "#######################################################################"

gatewayName = 'CTP'
print U"GatewayName:", gatewayName

try:
    mainEngine.connect(gatewayName)
    print u"CTP 正在登录!!!",
    for i in range(50):
        print ".",
        time.sleep(.2)

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
## vtFunction
## 保存当天的 contractInfo 为 csv
"""
try:
    contractInfo = vtFunction.getContractInfo()a
    print "#---------------------------------------------------------------"
    print "合约信息 查询成功!!!"
    print "#---------------------------------------------------------------"
    print "#######################################################################"
    print u"以下是今天的所有合约信息:"
    print contractInfo
    print "#######################################################################"
except:
    print "#---------------------------------------------------------------"
    print u"合约信息 查询失败!!!"
    print "#---------------------------------------------------------------"
"""
############################################################################

############################################################################
## william
## 更新 /dataRecorder/DR_setting

# vtFunction.refreshDatarecodeSymbol()

'''
vtFunction.refreshDatarecodeSymbol()
print "#######################################################################"
print u"DR_setting 已经更新完成!!!"
print "#######################################################################"
'''
############################################################################


############################################################################
## william
## 查询命令

## 1. mainEngine.drEngine.getAccountInfo()
## 2. mainEngine.drEngine.getPositionInfo()
## 3. 委托单查询: mainEngine.getAllOrders()


# temp = mainEngine.drEngine.getAccountInfo()
# # print temp

# temp2 = mainEngine.drEngine.getPositionInfo()
# print pd.DataFrame(temp2)

# '''
# print temp2.keys()
# print temp2.values()
# '''

# ## [re.sub('-long|-short','', k) for k in temp2.keys()]

# mainEngine.getAllOrders()
# allOrders = mainEngine.getAllOrders()

# if allOrders:
#     print allOrders[allOrders['status'] == u'全部成交']
# else:
#     print u"没有查询到订单信息"


# mainEngine.drEngine.getTradeInfo()
# mainEngine.drEngine.getTradeInfo()
####################################################################
## william
##
## >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
## 下单命令
## Finished
## Ref: /vn.trader/gateway/ctpGateway/ctpGateway.py/class CtpTdApi(TdApi) / def sendOrder(self, orderReq)
## 1. mainEngine.sendOrder(orderReq, gatewayName)
'''
orderReq = VtOrderReq()
orderReq.symbol = 'i1709'
orderReq.volume  = 5
orderReq.price   = 468.0

## william
## 注意:这里的变量不用加引号!!!
## -----------------------------------------------------------------------------
# 价格类型映射
## priceTypeMap = {}
## priceTypeMap[PRICETYPE_LIMITPRICE] = defineDict["THOST_FTDC_OPT_LimitPrice"]
## priceTypeMap[PRICETYPE_MARKETPRICE] = defineDict["THOST_FTDC_OPT_AnyPrice"]
## priceTypeMapReverse = {v: k for k, v in priceTypeMap.items()} 
## -----------------------------------------------------------------------------
orderReq.priceType = PRICETYPE_LIMITPRICE

## -----------------------------------------------------------------------------
# 方向类型映射
## directionMap = {}
## directionMap[DIRECTION_LONG] = defineDict['THOST_FTDC_D_Buy']
## directionMap[DIRECTION_SHORT] = defineDict['THOST_FTDC_D_Sell']
## directionMapReverse = {v: k for k, v in directionMap.items()}
## -----------------------------------------------------------------------------
orderReq.direction = DIRECTION_LONG

## -----------------------------------------------------------------------------
# 开平类型映射
## offsetMap = {}
## offsetMap[OFFSET_OPEN] = defineDict['THOST_FTDC_OF_Open']
## offsetMap[OFFSET_CLOSE] = defineDict['THOST_FTDC_OF_Close']
## offsetMap[OFFSET_CLOSETODAY] = defineDict['THOST_FTDC_OF_CloseToday']
## offsetMap[OFFSET_CLOSEYESTERDAY] = defineDict['THOST_FTDC_OF_CloseYesterday']
## offsetMapReverse = {v:k for k,v in offsetMap.items()}
## -----------------------------------------------------------------------------
orderReq.offset = OFFSET_OPEN

print pd.DataFrame([orderReq.__dict__.values()], columns =  orderReq.__dict__.keys())

mainEngine.sendOrder(orderReq, gatewayName)
'''
## <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<


## >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
## 2. mainEngine.cancelOrder()

## <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

## 
## print mainEngine.getAllWorkingOrders()
## >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
## 一键全部撤单
## Finished
## Ref: /vn.trader/vtEngine.py/class MainEngine/def cancelOrderAll(self):
## 3. mainEngine.cancelOrderAll()
'''
mainEngine.cancelOrderAll()
'''
## <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

##########################################################################


################################################################################
## william
## CTA 策略
# print mainEngine.ctaEngine.ChinaFuturesCalendar

# 加载设置
mainEngine.ctaEngine.loadSetting()

print mainEngine.ctaEngine.__dict__
print mainEngine.ctaEngine.strategyDict
print mainEngine.ctaEngine.tickStrategyDict

# 初始化策略
mainEngine.ctaEngine.initStrategy('Bollinger Band')


################################################################################
'''
print mainEngine.ctaEngine.ChinaFuturesCalendar

# 加载设置
mainEngine.ctaEngine.loadSetting()

print mainEngine.ctaEngine.__dict__
print mainEngine.ctaEngine.strategyDict
print mainEngine.ctaEngine.tickStrategyDict

# 初始化策略
mainEngine.ctaEngine.initStrategy('Bollinger Band')

# 启动策略
mainEngine.ctaEngine.startStrategy('Bollinger Band')


## =============================================================================
print mainEngine.ctaEngine.strategyDict['Bollinger Band'].__dict__

y = mainEngine.ctaEngine.strategyDict

strat = y['Bollinger Band']
print dir(strat)
print strat.__dict__
print strat.__dict__.keys()
print strat.minuteData

print strat.ctaEngine.today.date()

md = strat.minuteData
print md[md['TradingDay'] == strat.ctaEngine.today.date()]

vtSymbol = 'i1709'
u = md[md['InstrumentID'] == vtSymbole][md['TradingDay'] == strat.ctaEngine.today.date()]['Minute']
print u
'''


################################################################################

# 启动策略
mainEngine.ctaEngine.startStrategy('Bollinger Band')
y = mainEngine.ctaEngine.strategyDict
strat = y['Bollinger Band']

# mainEngine.ctaEngine.stopStrategy('Bollinger Band')
