# encoding: UTF-8

'''
本文件中实现了行情数据记录引擎，用于汇总TICK数据，并生成K线插入数据库。

使用DR_setting.json来配置需要收集的合约，以及主力合约代码。
'''

################################################################################
## william
## 用于收集 CTP Tick Data
"""
import os
path = '/home/william/Documents/vnpy/vnpy-1.6.1/vn.trader/dataRecorder/'
os.chdir(path)
print os.getcwd()
"""
################################################################################
################################################################################
## william
## 不要打印 TickData

'''
global printTickData
printTickData = True
'''
'''
global saveTickData
saveTickData = True
'''

################################################################################


################################################################################

################################################################################
##　william
import MySQLdb

################################################################################


import json
import os
import copy
from collections import OrderedDict
from datetime import datetime, timedelta
from Queue import Queue
from threading import Thread

from eventEngine import *
from vtGateway import VtSubscribeReq, VtLogData
from drBase import *

## /////////////////////////////////////////////////////////////////////////////
## william
## SaveTickData
from vtFunctionSaveTickData import todayDate
## /////////////////////////////////////////////////////////////////////////////

from language import text

########################################################################
class DrEngine(object):
    """数据记录引擎"""

    ############################################################################
    ## william
    ##
    settingFileName = 'DR_settingSaveTickData.json'
    path = os.path.abspath(os.path.dirname(__file__))
    settingFileName = os.path.join(path, settingFileName)    

    #----------------------------------------------------------------------
    def __init__(self, mainEngine, eventEngine):
        """Constructor"""
        self.mainEngine = mainEngine
        self.eventEngine = eventEngine
        
        # 当前日期
        self.today = todayDate()
        
        # 主力合约代码映射字典，key为具体的合约代码（如IF1604），value为主力合约代码（如IF0000）
        self.activeSymbolDict = {}
        
        # Tick对象字典
        self.tickDict = {}
        
        # K线对象字典
        self.barDict = {}
        
        ########################################################################
        ## william
        ## 是否激活 self.active
        ########################################################################
        # 负责执行数据库插入的单独线程相关
        self.active = False                     # 工作状态
        self.queue = Queue()                    # 队列

        ## /////////////////////////////////////////////////////////////////////
        ## william
        ## SaveTickData
        self.thread = Thread(target=self.run)   # 线程
        ########################################################################

        ########################################################################
        
        # 载入设置，订阅行情
        '''
        print "#######################################################################"
        print u"class DrEngine.loadSetting()"
        print "#######################################################################"
        '''
        self.loadSetting()
        
    #----------------------------------------------------------------------
    def loadSetting(self):
        """载入设置"""
        with open(self.settingFileName) as f:
            drSetting = json.load(f)
            
            # 如果working设为False则不启动行情记录功能
            working = drSetting['working']
            if not working:
                return
            
            if 'tick' in drSetting:
                l = drSetting['tick']
                """
                print "#######################################################################"
                print u"l = drSetting['tick']:==>"
                print l[0:2]
                print "#######################################################################"
                """
                for setting in l:
                    
                    #print "#######################################################################"
                    #print 'setting:==>'
                    #print setting

                    symbol = setting[0]
                    vtSymbol = symbol

                    #print 'symbol = setting[0]:==>'
                    #print symbol
                    #print 'setting[1]:==>', setting[1]
                    #print setting[0]
                    #print setting[1]
                    

                    req = VtSubscribeReq()
                    req.symbol = setting[0]
                    
                    # 针对LTS和IB接口，订阅行情需要交易所代码
                    if len(setting)>=3:
                        req.exchange = setting[2]
                        vtSymbol = '.'.join([symbol, req.exchange])
                    
                    # 针对IB接口，订阅行情需要货币和产品类型
                    if len(setting)>=5:
                        req.currency = setting[3]
                        req.productClass = setting[4]
                    
                    
                    # 订阅合约
                    ############################################################
                    ## william
                    ## 订阅 CTP 行情数据
                    ## 行情记录
                    ## 针对所有的 DR_setting.json
                    ############################################################
                    contract = self.mainEngine.getContract(vtSymbol)
                    '''
                    print contract
                    print vars(contract)
                    print contract.__dict__
                    '''
                    if contract:
                        gateway = contract.gatewayName
                        ## req = VtSubscribeReq()
                        ## req.symbol = contract.symbol
                        ## req.exchange = contract.exchange

                        self.mainEngine.subscribe(req, contract.gatewayName)
                    else:
                        print vtSymbol,'合约没有找到'
                    
                    
                    ############################################################
                    ## william
                    ## 
                    ############################################################
                    # self.mainEngine.subscribe(req, setting[1])
                    '''
                    print "#######################################################################"
                    print 'req = VtSubscribeReq()', req
                    print 'setting[1]:==>', setting[1]
                    print "#######################################################################"
                    '''
                    drTick = DrTickData()           # 该tick实例可以用于缓存部分数据（目前未使用）
                    self.tickDict[vtSymbol] = drTick
                    
            if 'bar' in drSetting:
                l = drSetting['bar']
                
                for setting in l:
                    symbol = setting[0]
                    vtSymbol = symbol
                    
                    req = VtSubscribeReq()
                    req.symbol = symbol                    

                    if len(setting)>=3:
                        req.exchange = setting[2]
                        vtSymbol = '.'.join([symbol, req.exchange])

                    if len(setting)>=5:
                        req.currency = setting[3]
                        req.productClass = setting[4]                    
                    
                    self.mainEngine.subscribe(req, setting[1])  
                    
                    bar = DrBarData() 
                    self.barDict[vtSymbol] = bar
            
            ####################################################################
            ## william
            ## 所有的都变成 active
            ####################################################################
            
            if 'active' in drSetting:
                d = drSetting['active']
                
                # 注意这里的vtSymbol对于IB和LTS接口，应该后缀.交易所
                for activeSymbol, vtSymbol in d.items():
                    self.activeSymbolDict[vtSymbol] = activeSymbol

            # 启动数据插入线程
            self.start()
            
            # 注册事件监听
            self.registerEvent()    

    #---------------------------------------------------------------------------
    ############################################################################
    ## william
    ## 原来的单词拼写有错误,
    ## def procecssTickEvent(self, event):
    ############################################################################
    def processTickEvent(self, event):
        
        """处理行情推送"""
        tick = event.dict_['data']
        vtSymbol = tick.vtSymbol
        """
        print "#######################################################################"
        print u"tick = event.dict['data']:", tick
        print u"tick.keys()"
        temp = vars(tick).keys()
        print temp
        print u"tick.values()"
        print vars(tick).values()
        print "#######################################################################\n"
        """
        ########################################################################
        ## william
        ## Tick Data
        ########################################################################
        # 转化Tick格式
        drTick = DrTickData()
        d = drTick.__dict__
        for key in d.keys():
            if key != 'datetime':
                d[key] = tick.__getattribute__(key)
        drTick.datetime = datetime.strptime(' '.join([tick.date, tick.time]), '%Y%m%d %H:%M:%S.%f')
        tempFields = ['bidPrice1','bidPrice2','bidPrice3','bidPrice4','bidPrice5',\
                      'askPrice1','askPrice2','askPrice3','askPrice4','askPrice5',\
                      'settlementprice']   
        for i in tempFields:
            if d[i] > 1.79e+99:
                d[i] = 0  
        ########################################################################
        ## william 
        ## 在这里获取 Tick Data
        ## /////////////////////////////////////////////////////////////////////////////
        print "\n#######################################################################"
        # print u"在这里获取 Tick Data !!!==>  ",drTick.__dict__['symbol']
        # print drTick.__dict__
        print '在这里获取 Tick Data !!!==>', d['symbol']
        print d
        self.mainEngine.dbWriteCSV(d)
        print "#######################################################################\n"
        ## /////////////////////////////////////////////////////////////////////////////
        ########################################################################
            
        # 更新分钟线数据
        if vtSymbol in self.barDict:
            bar = self.barDict[vtSymbol]
            
            # 如果第一个TICK或者新的一分钟
            if not bar.datetime or bar.datetime.minute != drTick.datetime.minute:    
                if bar.vtSymbol:
                    newBar = copy.copy(bar)
                    self.insertData(MINUTE_DB_NAME, vtSymbol, newBar)
                    
                    if vtSymbol in self.activeSymbolDict:
                        activeSymbol = self.activeSymbolDict[vtSymbol]
                        self.insertData(MINUTE_DB_NAME, activeSymbol, newBar)                    
                    
                    self.writeDrLog(text.BAR_LOGGING_MESSAGE.format(symbol=bar.vtSymbol, 
                                                                    time=bar.time, 
                                                                    open=bar.open, 
                                                                    high=bar.high, 
                                                                    low=bar.low, 
                                                                    close=bar.close))
                         
                bar.vtSymbol = drTick.vtSymbol
                bar.symbol = drTick.symbol
                bar.exchange = drTick.exchange
                
                bar.open = drTick.lastPrice
                bar.high = drTick.lastPrice
                bar.low = drTick.lastPrice
                bar.close = drTick.lastPrice
                
                bar.date = drTick.date
                bar.time = drTick.time
                bar.datetime = drTick.datetime
                bar.volume = drTick.volume
                bar.openInterest = drTick.openInterest        
            # 否则继续累加新的K线
            else:                               
                bar.high = max(bar.high, drTick.lastPrice)
                bar.low = min(bar.low, drTick.lastPrice)
                bar.close = drTick.lastPrice            



    ############################################################################
    ## william
    ## 获取所有合约的行情数据
    ## def processAllTickEvent
    ############################################################################

    #----------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.eventEngine.register(EVENT_TICK, self.processTickEvent)

        ########################################################################
        ## william
        ## 注册保存 Tick Data 的事件,
        ## 如果满足条件,自动退出程序的运行
        ## Ref: /vn.trader/dataRecorder/drEngine.py/ def exitfun()
        ########################################################################
        """ 退出 DataRecorder 的程序"""
        self.eventEngine.register(EVENT_TIMER,self.exitfun)
 
    #----------------------------------------------------------------------
    def insertData(self, dbName, collectionName, data):
        """插入数据到数据库（这里的data可以是CtaTickData或者CtaBarData）"""
        self.queue.put((dbName, collectionName, data.__dict__))
        
    #----------------------------------------------------------------------
    def run(self):
        """运行插入线程"""
        ########################################################################
        ## william
        ## 获取 CTP 行情 mdApi 推送的 Tick Data
        ## 并保存到 vtEngine.dbWriterCSV()
        ## 当持仓中的合约被点击后,开始运行 mainEngine.dbInsert()
        ########################################################################
        '''
        while self.active:
            try:
                dbName, collectionName, d = self.queue.get(block=True, timeout=1)
                self.mainEngine.dbInsert(dbName, collectionName, d)
            except Empty:
                pass
        '''
        ########################################################################
        ## william
        ## 这里,当持仓的合约被鼠标激活后,
        ## 把合约的信息打印到终端
        ########################################################################
        # while self.active:
        #     ## 如果需要保存到 csv 文件
        #     '''
        #     if saveTickData:
        #         try:
        #             dbName, collectionName, d = self.queue.get(block=True, timeout=1)
        #             ## print d
        #             self.mainEngine.dbWriteCSV(d)
        #         except Empty:
        #             pass
        #     '''
        #     try:
        #         #dbName, collectionName, d = self.queue.get(block=True, timeout=1)
        #         ## print d
        #         ############################################################
        #         ## william
        #         ## 是不是要保存数据到 csv 文件
        #         ## /////////////////////////////////////////////////////////////
        #         ## william
        #         ## SaveTickData
        #         #self.mainEngine.dbWriteCSV(d)
        #         ## /////////////////////////////////////////////////////////////
        #         ############################################################
        #     except Empty:
        #         pass     

    #---------------------------------------------------------------------------
    def start(self):
        """启动"""
        self.active = True
        self.thread.start()
        
    #---------------------------------------------------------------------------
    def stop(self):
        """退出"""
        if self.active:
            self.active = False
            self.thread.join()
        
    #---------------------------------------------------------------------------
    def writeDrLog(self, content):
        """快速发出日志事件"""
        log = VtLogData()
        log.logContent = content
        event = Event(type_=EVENT_DATARECORDER_LOG)
        event.dict_['data'] = log
        self.eventEngine.put(event)   
    ################################################################################
    ## william
    ## 增加 dataRecorder.dbW
    def exitfun(self,event):
        if self.exittime():
            print 'exit0'
            os._exit(0)
    #----------------------------------------------------------------------
    def exittime(self):
        """退出标志"""
        re = False
        t  = datetime.now()
        h  = t.hour
        m  = t.minute
        if h == 2 and m > 35:
            re = True
            print h,m,re
        return re
    ################################################################################

