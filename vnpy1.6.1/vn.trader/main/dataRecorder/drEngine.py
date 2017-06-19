# encoding: UTF-8

'''
本文件中实现了行情数据记录引擎，用于汇总TICK数据，并生成K线插入数据库。

使用DR_setting.json来配置需要收集的合约，以及主力合约代码。
'''

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
from vtGateway import * 
from drBase import *
from vtFunction import todayDate
from language import text

import pandas as pd
################################################################################
import copy

################################################################################
class DrEngine(object):
    """数据记录引擎"""

    settingFileName = 'DR_setting.json'
    path = os.path.abspath(os.path.dirname(__file__))
    settingFileName = os.path.join(path, settingFileName)    

    #---------------------------------------------------------------------------
    def __init__(self, mainEngine, eventEngine):
        """Constructor"""
        self.mainEngine = mainEngine
        self.eventEngine = eventEngine

        ########################################################################
        ## william
        ## 
        self.accountInfo = VtAccountData()
        ## 多个合约的持仓信息
        ## 返回一个字典,避免重复
        ## key 是 vtGateway/VtPositionData/ 下面的 symbolPosition
        ## symbolPosition 格式:i1709-long(short), 代表合约多空
        self.positionInfo = {}

        self.tradeInfo = VtTradeData()
        ########################################################################

        
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
        self.thread = Thread(target=self.run)   # 线程
        ########################################################################
        ## william
        ## DrEngine 关闭,则不再保存数据到 CSV 文件
        ########################################################################
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

                for setting in l:

                    symbol = setting[0]
                    vtSymbol = symbol

                    req = VtSubscribeReq()
                    req.symbol = setting[0]
                    
                    # 针对LTS和IB接口，订阅行情需要交易所代码
                    if len(setting) >= 3:
                        req.exchange = setting[2]
                        vtSymbol = '.'.join([symbol, req.exchange])
                    
                    # 针对IB接口，订阅行情需要货币和产品类型
                    if len(setting) >= 5:
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

    ############################################################################
    ## william
    ## 处理合约信息
    ## -------------------------------------------------------------------------


    ############################################################################
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
        ########################################################################
        ## william
        ## Tick Data
        ## drTick,可以在这里直接保存为 csv
        ## 或者插入数据库
        ########################################################################
        # 转化Tick格式
        drTick = DrTickData()
        d = drTick.__dict__
        for key in d.keys():
            if key != 'datetime':
                d[key] = tick.__getattribute__(key)
        drTick.datetime = datetime.strptime(' '.join([tick.date, tick.time]), '%Y%m%d %H:%M:%S.%f')            
        # 更新Tick数据
        if vtSymbol in self.tickDict:
            self.insertData(TICK_DB_NAME, vtSymbol, drTick)
            ####################################################################
            ## william
            ## print u"更新Tick数据"
            ## 这里使用了 insertData 插入到线程,原来用的是 mongoDB
            if vtSymbol in self.activeSymbolDict:
                activeSymbol = self.activeSymbolDict[vtSymbol]
                self.insertData(TICK_DB_NAME, activeSymbol, drTick)
            ####################################################################
            ## william
            ## 在 UI 界面的 '行情记录里面' 打印
            ## 我在这里把这个功能关闭掉了
            ####################################################################
            # 发出日志
            '''
            self.writeDrLog(text.TICK_LOGGING_MESSAGE.format(symbol=drTick.vtSymbol,
                                                             time=drTick.time, 
                                                             last=drTick.lastPrice, 
                                                             bid=drTick.bidPrice1, 
                                                             ask=drTick.askPrice1))
            '''
            ####################################################################
            ## william
            ## 处理 Tick Data
            """
            print u"#######################################################################"
            print u"处理行情推送:"
            print text.TICK_LOGGING_MESSAGE.format(symbol=drTick.vtSymbol,
                                                             time=drTick.time, 
                                                             last=drTick.lastPrice, 
                                                             bid=drTick.bidPrice1, 
                                                             ask=drTick.askPrice1)
            print u"#######################################################################"
            """
            ####################################################################
            
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
    ## 获取账户信息
    ## def processAccountEvent(self, event):
    ############################################################################
    def processAccountInfoEvent(self, event):
        """处理账户推送"""
        account = event.dict_['data']

        ########################################################################
        # 转化 VtAccount 格式
        # self.VtAccountInfo = VtAccountData()
        d = self.accountInfo.__dict__

        for key in d.keys():
            if key != 'datetime':
                d[key] = account.__getattribute__(key)

        self.accountInfo.datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # print self.accountInfo.__dict__

        # print VtAccount.__dict__
        #return d
        ########################################################################
        ## william
        ## 是不是需要写入数据库:
        ## gatewayName = 'CTP'
        ## self.insertData(ACCOUNT_DB_NAME, gatewayName, VtAccountInfo)
    
        # ----------------------------------------------------------------------
    ############################################################################
    ## william
    ## 返回账户信息
    ############################################################################
    def getAccountInfo(self):
        """获取当前账号的权益、可用资金、当前仓位比例, 投资仓位比例上限"""
        # return self.balance, self.available, self.percent, self.percentLimit
        temp = self.accountInfo.__dict__
        print pd.DataFrame([temp.values()], columns = temp.keys())
        return self.accountInfo.__dict__

    
    def processPositionInfoEvent(self, event):
        """处理账户推送"""
        position = event.dict_['data']
        
        tempRes = VtPositionData()
        d = tempRes.__dict__
        for key in d.keys():
            if key != 'datetime':
                d[key] = position.__getattribute__(key) 

        if tempRes.direction == u"多":
            tempRes.symbolPosition = tempRes.symbol + '-' + u'long'
        elif tempRes.direction == u"空":
            tempRes.symbolPosition = tempRes.symbol + '-' + u'short'
        else:
            tempRes.symbolPosition = tempRes.symbol + '-' + u'unknown'

        tempRes.datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  

        self.positionInfo[tempRes.__dict__['symbolPosition']] = tempRes.__dict__    
        ########################################################################
        ## william
        ## 是不是需要写入数据库:
        ## gatewayName = 'CTP'
        ## self.insertData(ACCOUNT_DB_NAME, gatewayName, VtAccountInfo)
    
        # ----------------------------------------------------------------------
    ############################################################################
    ## william
    ## 返回账户信息
    ############################################################################
    def getPositionInfo(self):
        """获取当前账号的持仓信息"""
        ########################################################################
        ## william
        ## 1.先在屏幕打印出来
        ## 2.返回一个字典,避免重复
        print pd.DataFrame(self.positionInfo)
        return self.positionInfo

    ############################################################################
    ## william    
    ## 如果订单有成交,则立即发出通知
    def processTradeInfoEvent(self, event):
        """通知成交订单"""
        trade = event.dict_['data']

        ########################################################################
        # 转化 VtTradeData 格式
        # self.tradeInfo = VtAccountData()
        d = self.tradeInfo.__dict__

        for key in d.keys():
            if key != 'datetime':
                d[key] = trade.__getattribute__(key)
                
        self.tradeInfo.tradeStatus = u'全部成交'
        print "\n#######################################################################"
        print u"当前成交订单的详细信息:"
        temp = self.tradeInfo.__dict__
        print "-----------------------------------------------------------------------"
        tempRes = pd.DataFrame([temp.values()], columns = temp.keys())
        print tempRes[['symbol','exchange','price','direction','offset','volume','tradeStatus','tradeTime','orderID']]
        print "#######################################################################"

    def getTradeInfo(self):
        """获取成交订单信息"""
        temp = self.tradeInfo.__dict__
        print pd.DataFrame([temp.values()], columns = temp.keys())
        return self.tradeInfo.__dict__
 
    ## +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def getIndicatorInfo(self, dbName, initCapital):
        """读取指标并写入相应的数据库"""
        ## =====================================================================
        ## 持仓合约信息
        posInfo = copy.copy(self.getPositionInfo())
        tempPosInfo = {}

        for key in posInfo.keys():
            if posInfo[key]['position'] > 0:
                tempFields = ['symbol','direction','price','position','positionProfit','size']
                tempPosInfo[key] = {k:posInfo[key][k] for k in tempFields}
                tempPosInfo[key]['size'] = int(tempPosInfo[key]['size'])
                # --------------------------------------------------------------------------
                if tempPosInfo[key]['direction'] == u'多':
                    tempPosInfo[key]['positionPct'] = (tempPosInfo[key]['price'] * tempPosInfo[key]['size'] * self.mainEngine.getContract(tempPosInfo[key]['symbol']).longMarginRatio)
                elif tempPosInfo[key]['direction'] == u'空':
                    tempPosInfo[key]['positionPct'] = (tempPosInfo[key]['price'] * tempPosInfo[key]['size'] * self.mainEngine.getContract(tempPosInfo[key]['symbol']).shortMarginRatio)

                tempPosInfo[key]['positionPct'] = round(tempPosInfo[key]['positionPct'] * tempPosInfo[key]['position'] / self.accountInfo.balance * 100, 4)
            # --------------------------------------------------------------------------
        # print x
        # print pd.DataFrame(x).transpose()
        if len(tempPosInfo) != 0:
            tempRes1 = pd.DataFrame(tempPosInfo).transpose()

        ## =====================================================================
        ## 账户基金净值
        accInfo = copy.copy(self.accountInfo.__dict__)

        accInfo['marginPct'] = accInfo['margin'] / accInfo['balance'] * 100

        accInfo['balance'] = accInfo['balance'] / initCapital
        accInfo['preBalance'] = accInfo['preBalance'] / initCapital
        accInfo['deltaBalancePct'] = (accInfo['balance'] - accInfo['preBalance']) / accInfo['preBalance'] * 100

        tempFields = ['balance','preBalance','deltaBalancePct','marginPct', 'positionProfit','closeProfit']
        for k in tempFields:
            accInfo[k] = round(accInfo[k],4)

        tempFields = ['vtAccountID','datetime','preBalance','balance','deltaBalancePct','marginPct','positionProfit','closeProfit']
        tempRes2 = pd.DataFrame([[accInfo[k] for k in tempFields]], columns = tempFields)
        ## =====================================================================
        conn = self.mainEngine.dbMySQLConnect(dbName)
        cursor = conn.cursor()
        ## ---------------------------------------------------------------------
        if len(tempPosInfo) != 0:
            tempRes1.to_sql(con=conn, name='report_position', if_exists='replace', flavor='mysql', index = True)
        else:
            cursor.execute('truncate table report_position')
        ## ---------------------------------------------------------------------
        tempRes2.to_sql(con=conn, name='report_account', if_exists='replace', flavor='mysql', index = False)
        conn.close()   



    #----------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.eventEngine.register(EVENT_TICK, self.processTickEvent)

        ########################################################################
        ## william
        ## 获取账户信息
        self.eventEngine.register(EVENT_ACCOUNT, self.processAccountInfoEvent)

        ## 持仓信息
        self.eventEngine.register(EVENT_POSITION, self.processPositionInfoEvent)

        ## 成交订单
        self.eventEngine.register(EVENT_TRADE, self.processTradeInfoEvent)
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
        while self.active:
            ## 如果需要保存到 csv 文件
            '''
            if saveTickData:
                try:
                    dbName, collectionName, d = self.queue.get(block=True, timeout=1)
                    ## print d
                    self.mainEngine.dbWriteCSV(d)
                except Empty:
                    pass
            '''
            try:
                dbName, collectionName, d = self.queue.get(block=True, timeout=1)
                ## print d
                ############################################################
                ## william
                ## 是不是要保存数据到 csv 文件
                ## self.mainEngine.dbWriteCSV(d)
                ############################################################
            except Empty:
                pass     

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
    ############################################################################
    ## william
    ## 增加程序退出的设定
    ## exitfun()
    def exitfun(self,event):
        if self.exittime():
            print 'exit0'
            os._exit(0)
    #---------------------------------------------------------------------------
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
    ############################################################################
