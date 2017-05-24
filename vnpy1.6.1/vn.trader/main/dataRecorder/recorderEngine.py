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
import csv
import shelve
################################################################################


################################################################################
class DrEngine(object):
    """数据记录引擎"""
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
        self.today = self.mainEngine.todayDate
        self.tradingDay = self.mainEngine.tradingDay
        
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
        # """载入设置"""
        ################################################################################
        ## william
        ## 保存合约信息到 /vn.trader/main
        ################################################################################
        contractInfo = self.mainEngine.dataEngine.getAllContracts()

        for contract in contractInfo:
            req = VtSubscribeReq()
            req.symbol = contract.symbol
            req.exchange = contract.exchange

            if contract.symbol:
                self.mainEngine.subscribe(req, contract.gatewayName)
            else:
                print contract.symbol,'合约没有找到'
        ## ---------------------------------------------------------------------
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

        tempFields = ['openPrice','highestPrice','lowestPrice','closePrice',\
                      'upperLimit','lowerLimit','openInterest','preDelta','currDelta',\
                      'bidPrice1','bidPrice2','bidPrice3','bidPrice4','bidPrice5',\
                      'askPrice1','askPrice2','askPrice3','askPrice4','askPrice5',\
                      'settlementPrice','averagePrice']   
        for i in tempFields:
            if d[i] > 1.79e+99:
                d[i] = 0

        print "\n#######################################################################"
        # print u"在这里获取 Tick Data !!!==>  ",drTick.__dict__['symbol']
        # print drTick.__dict__
        print '在这里获取 Tick Data !!!==>', d['symbol']
        print d
        ########################################################################
        ## william
        ## 保存到 csv
        ## Ref: /vn.trader/vtEngine/def dbWriteCSV(self,d)
        self.dbWriteCSV(d)
        print "#######################################################################\n"

    ## 向 csv 文件写入数据
    ############################################################################   
    def dbWriteCSV(self, d):
        """向 csv 文件写入数据，d是具体数据"""
        ########################################################################
        ## william
        ## d 从 /vn.trader/gateway/ctpGateway/ctpGateway.py 获取
        ########################################################################
        myFields = ['timeStamp','date','time','symbol','exchange',\
                    'lastPrice','preSettlementPrice','preClosePrice',\
                    'openPrice','highestPrice','lowestPrice','closePrice',\
                    'upperLimit','lowerLimit','settlementPrice','volume','turnover',\
                    'preOpenInterest','openInterest','preDelta','currDelta',\
                    'bidPrice1','bidPrice2','bidPrice3','bidPrice4','bidPrice5',\
                    'askPrice1','askPrice2','askPrice3','askPrice4','askPrice5',\
                    'bidVolume1','bidVolume2','bidVolume3','bidVolume4','bidVolume5',\
                    'askVolume1','askVolume2','askVolume3','askVolume4','askVolume5',\
                    'averagePrice']
        values = [d[k] for k in myFields]

        #print d
        path = os.path.abspath(os.path.dirname(__file__))
        tick_recorder_path = os.path.normpath(os.path.join(path,"../../..",'vn.data','TickData'))
        ########################################################################
        dataFile = os.path.join(tick_recorder_path,(str(self.mainEngine.todayDate) + '.csv'))

        with open(dataFile, 'a') as f:
            wr = csv.writer(f)
            wr.writerow(values)
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
 
    # #----------------------------------------------------------------------
    # def insertData(self, dbName, collectionName, data):
    #     """插入数据到数据库（这里的data可以是CtaTickData或者CtaBarData）"""
    #     self.queue.put((dbName, collectionName, data.__dict__))
        
    #----------------------------------------------------------------------
    def run(self):
        """运行插入线程"""

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
