# encoding: UTF-8
"""
@william
云扬一号
"""
################################################################################
from __future__ import division
import os
import sys
import subprocess

## 发送邮件通知
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import codecs

cta_strategy_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(cta_strategy_path)
################################################################################
from ctaBase import *
from ctaTemplate import CtaTemplate

from vtGateway import VtSubscribeReq, VtOrderReq, VtCancelOrderReq, VtLogData

import numpy as np
import pandas as pd
from pandas.io import sql
from tabulate import tabulate

from datetime import *
import time
from eventType import *

################################################################################
class YYStrategy(CtaTemplate):
    """ 云扬一号 交易策略 """
    ############################################################################
    ## william
    # 策略类的名称和作者
    name         = 'YunYang'
    className    = 'YYStrategy'
    strategyID   = className
    author       = 'Lin HuanGeng'
    ############################################################################

    ############################################################################
    ## -------------------------------------------------------------------------
    ## 各种控制条件
    ## 策略的基本变量，由引擎管理
    inited         = False                    # 是否进行了初始化
    trading        = False                    # 是否启动交易，由引擎管理
    tradingStart   = False                    # 开盘启动交易
    # tradingStart2  = False                    # 开盘启动交易
    tradingEnd     = False                    # 收盘开启交易
    # tradingEnd2    = False                    # 收盘开启交易
    sendMailStatus = False                    # 是否已经发送邮件
    runRscript     = False                    # 运行 Rscript
    tradingClosePositionAll    = False        # 是否强制平仓所有合约
    tradingClosePositionSymbol = False        # 是否强制平仓单个合约
    ## -------------------------------------------------------------------------


    ## -------------------------------------------------------------------------
    ## 从 TickData 提取的字段
    ## -------------------------------------------------------------------------
    tickFileds = ['symbol', 'vtSymbol', 'datetime',
                  'lastPrice', 'bidPrice1', 'askPrice1',
                  'bidVolume1', 'askVolume1', 'upperLimit', 'lowerLimit', 'openPrice']
    lastTickData = {}                  # 保留最新的价格数据
    tickTimer    = {}                  # 计时器, 用于记录单个合约发单的间隔时间
    vtSymbolList = []                  # 策略的所有合约存放在这里
    ## -------------------------------------------------------------------------

    ## -------------------------------------------------------------------------
    ## 各种交易订单的合成
    ## 交易订单存放位置
    ## 字典格式如下
    ## 1. vtSymbol
    ## 2. direction: buy, sell, short, cover
    ## 3. volume
    ## 4. TradingDay
    ## 5. vtOrderID
    ## -------------------------------------------------------------------------
    tradingOrders      = {}            # 单日的订单
    tradingOrdersOpen  = {}            # 当日开盘的订单
    tradingOrdersClose = {}            # 当日收盘的订单
    ## -------------------------------------------------------------------------
    tradingOrdersFailedInfo = {}       # 上一个交易日没有完成的订单,需要优先处理
    ## -------------------------------------------------------------------------
    tradedOrders           = {}        # 当日订单完成的情况
    tradedOrdersOpen       = {}        # 当日开盘完成的已订单
    tradedOrdersClose      = {}        # 当日收盘完成的已订单
    tradedOrdersFailedInfo = {}        # 昨天未成交订单的已交易订单
    ## -------------------------------------------------------------------------
    failedOrders      = {}             # 当日未成交订单的统计情况,收盘后写入数据库,failedInfo
    failedOrdersOpen  = {}             # 开盘时候的未完成订单
    failedOrdersClose = {}             # 收盘时候的未完成订单
    ## -------------------------------------------------------------------------
    tradingOrdersClosePositionAll    = {}     ## 一键全平仓的交易订单
    tradingOrdersClosePositionSymbol = {}     ## 一键平仓合约的交易订单

    ## -------------------------------------------------------------------------
    ## 各种交易订单的合成
    ## -------------------------------------------------------------------------
    vtOrderIDList      = []                   # 保存委托代码的列表
    vtOrderIDListOpen  = []                   # 开盘的订单
    vtOrderIDListClose = []                   # 收盘的订单
    ## -------------------------------------------------------------------------
    vtOrderIDListFailedInfo          = []     # 失败的合约订单存储
    vtOrderIDListClosePositionAll    = []     # 一键全平仓
    vtOrderIDListClosePositionSymbol = []     # 一键全平仓
    ## -------------------------------------------------------------------------
    vtOrderIDListAll   = []                   # 所有订单集合
    ############################################################################
 
    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(YYStrategy, self).__init__(ctaEngine, setting)

        ########################################################################
        ## william
        ## 当天需要处理的订单字典
        ## 1. openInfo: 开仓的信息
        ## 2. failedInfo: 未成交的信息
        ## 3. positionInfo: 持仓的信息
        ## 4. tradingOrder:
        ## 其中
        ##    key   是合约名称
        ##    value 是具体的订单, 参考
        ## ---------------------------------------------------------------------
        ## 开仓信息, 需要检测是不是当前交易日的开仓, 使用了条件筛选
        self.openInfo = self.ctaEngine.mainEngine.dbMySQLQuery('lhg_trade',
                            """
                            SELECT *
                            FROM fl_open_t
                            WHERE TradingDay = '%s'
                            """ %self.ctaEngine.lastTradingDate)
        ## ---------------------------------------------------------------------
        ## 把交易日统一为当前交易日, 格式是 tradingDay, 即 20170101
        if len(self.openInfo) != 0:
            self.openInfo.TradingDay = self.ctaEngine.tradingDay

        ## ---------------------------------------------------------------------
        ## 上一个交易日未成交订单
        self.failedInfo = self.ctaEngine.mainEngine.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
                            """
                            SELECT *
                            FROM failedInfo
                            WHERE strategyID = '%s'
                            """ %(self.strategyID))

        ## ---------------------------------------------------------------------
        ## 持仓合约信息
        self.positionInfo = self.ctaEngine.mainEngine.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
                            """
                            SELECT *
                            FROM positionInfo
                            WHERE strategyID = '%s'
                            """ %(self.strategyID))
        ## ---------------------------------------------------------------------
        ## 查看当日已经交易的订单
        ## ---------------------------------------------------------------------
        self.tradingInfo = self.ctaEngine.mainEngine.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
                            """
                            SELECT *
                            FROM tradingInfo
                            WHERE strategyID = '%s'
                            AND TradingDay = '%s'
                            """ %(self.strategyID, self.ctaEngine.tradingDay))
        ########################################################################
        ## william
        # 注意策略类中的可变对象属性（通常是list和dict等），在策略初始化时需要重新创建，
        # 否则会出现多个策略实例之间数据共享的情况，有可能导致潜在的策略逻辑错误风险，
        # 策略类中的这些可变对象属性可以选择不写，全都放在__init__下面，写主要是为了阅读
        # 策略时方便（更多是个编程习惯的选择）
        ########################################################################
        ## william
        # 注册事件监听
        self.registerEvent()
        ########################################################################

    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        ## =====================================================================
        ## 策略初始化
        ## 对订单进行预先处理
        ## =====================================================================
        ##
        ## =====================================================================
        if self.ctaEngine.mainEngine.multiStrategy:
            self.fetchTradingOrders(stage = 'open')
            self.fetchTradingOrders(stage = 'close')
        else:
            self.generateTradingOrders()
        ## =====================================================================
        ##
        ## =====================================================================
        ## 如果上一个交易日有未完成的订单,需要优先处理
        ## =====================================================================
        ## ---------------------------------------------------------------------
        self.processFailedInfo(self.failedInfo)
        ## ---------------------------------------------------------------------

        print '#'*80
        print '%s策略启动' %self.name

        if len(self.failedInfo) != 0:
            print '前一日失败未成交的订单:'
            print self.tradingOrdersFailedInfo
            print '-'*80

        print '#'*80
        print '当日开盘需要执行的订单为:'
        print self.tradingOrdersOpen
        print '#'*80
        print '当日收盘需要执行的订单为:'
        print self.tradingOrdersClose

        ## ---------------------------------------------------------------------
        ## 当前策略下面的所有合约集合
        self.vtSymbolList = list(set(self.openInfo.InstrumentID.values) |
                                 set(self.failedInfo.InstrumentID.values) |
                                 set(self.positionInfo.InstrumentID.values)
                                )
        for i in self.vtSymbolList:
            self.tickTimer[i] = datetime.now()-timedelta(seconds = 5)

        print '#'*80
        print "@william 策略初始化成功 !!!"
        self.writeCtaLog(u'%s策略初始化' %self.name)
        print self.vtSymbolList
        print '#'*80
        ########################################################################
        ## william
        self.putEvent()


    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        ## =====================================================================
        if not self.trading:
            return 
        elif tick.datetime <= (datetime.now() - timedelta(seconds=30)):
            return
        elif tick.vtSymbol not in [self.tradingOrdersOpen[k]['vtSymbol'] for k in self.tradingOrdersOpen.keys()] + \
        [self.tradingOrdersClose[k]['vtSymbol'] for k in self.tradingOrdersClose.keys()] + \
        [self.tradingOrdersFailedInfo[k]['vtSymbol'] for k in self.tradingOrdersFailedInfo.keys()]:
            return
        elif ((datetime.now() - self.tickTimer[tick.vtSymbol]).seconds <= 2):
            return  
        ## =====================================================================

        ## ---------------------------------------------------------------------
        self.lastTickData[tick.vtSymbol] = {k:tick.__dict__[k] for k in self.tickFileds}
        ## ---------------------------------------------------------------------

        ########################################################################
        ## william
        ## =====================================================================
        if len(self.failedInfo) != 0 and self.tradingStart:
            self.prepareTradingOrder(vtSymbol      = tick.vtSymbol, 
                                     tradingOrders = self.tradingOrdersFailedInfo, 
                                     orderIDList   = self.vtOrderIDListFailedInfo,
                                     priceType     = 'chasing',
                                     addTick       = 1)
        ## =====================================================================

        ## =====================================================================
        if (tick.vtSymbol in [self.tradingOrdersOpen[k]['vtSymbol'] \
                             for k in self.tradingOrdersOpen.keys()] and 
            self.tradingStart and not self.tradingEnd):
            self.prepareTradingOrder(vtSymbol      = tick.vtSymbol, 
                                     tradingOrders = self.tradingOrdersOpen, 
                                     orderIDList   = self.vtOrderIDListOpen,
                                     priceType     = 'open',
                                     discount      = 0.0025)
        ## =====================================================================

        ## =====================================================================
        if (tick.vtSymbol in [self.tradingOrdersOpen[k]['vtSymbol'] \
                             for k in self.tradingOrdersOpen.keys()] and self.tradingEnd):
            self.prepareTradingOrder(vtSymbol      = tick.vtSymbol, 
                                     tradingOrders = self.tradingOrdersOpen, 
                                     orderIDList   = self.vtOrderIDListOpen,
                                     priceType     = 'chasing',
                                     addTick       = 1)
        ## =====================================================================


        ## =====================================================================
        if (tick.vtSymbol in [self.tradingOrdersOpen[k]['vtSymbol'] \
                             for k in self.tradingOrdersOpen.keys()] and self.tradingBetween):
            self.prepareTradingOrder(vtSymbol      = tick.vtSymbol, 
                                     tradingOrders = self.tradingOrdersOpen, 
                                     orderIDList   = self.vtOrderIDListOpen,
                                     priceType     = 'last',
                                     addTick       = 0)
        ## =====================================================================
        ## =====================================================================
        if (tick.vtSymbol in [self.tradingOrdersClose[k]['vtSymbol'] \
                             for k in self.tradingOrdersClose.keys()] and self.tradingBetween):
            self.prepareTradingOrder(vtSymbol      = tick.vtSymbol, 
                                     tradingOrders = self.tradingOrdersClose, 
                                     orderIDList   = self.vtOrderIDListClose,
                                     priceType     = 'last',
                                     addTick       = 0)
        ## =====================================================================


        ## =====================================================================
        if (tick.vtSymbol in [self.tradingOrdersClose[k]['vtSymbol'] \
                            for k in self.tradingOrdersClose.keys()] and 
            self.tradingStart and not self.tradingEnd):
            self.prepareTradingOrder(vtSymbol      = tick.vtSymbol, 
                                     tradingOrders = self.tradingOrdersClose, 
                                     orderIDList   = self.vtOrderIDListClose,
                                     priceType     = 'open',
                                     discount      = 0.003)

        ## =====================================================================
        if (tick.vtSymbol in [self.tradingOrdersClose[k]['vtSymbol'] \
                            for k in self.tradingOrdersClose.keys()] and self.tradingEnd):
            self.prepareTradingOrder(vtSymbol      = tick.vtSymbol, 
                                     tradingOrders = self.tradingOrdersClose, 
                                     orderIDList   = self.vtOrderIDListClose,
                                     priceType     = 'chasing',
                                     addTick       = 1)
        ## =====================================================================
        
        ## =====================================================================
        # 发出状态更新事件
        self.putEvent()
        ## =====================================================================

    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        # 发出状态更新事件
        self.putEvent()

    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def onTrade(self, trade):
        # 发出状态更新事件
        self.putEvent()

    ############################################################################
    ## william
    ## 以下用来处理持仓仓位的问题
    ############################################################################
    def stratTradeEvent(self, trade):
        """
        处理策略交易与持仓信息
        """

        ## =====================================================================
        if trade.vtOrderID not in list(set(self.vtOrderIDListOpen) | 
                                       set(self.vtOrderIDListClose) | 
                                       set(self.vtOrderIDListFailedInfo)):
            return None
        ## =====================================================================
        self.tickTimer[trade.vtSymbol] = datetime.now()
        ## =====================================================================
        ## 连接 MySQL 设置
        conn = self.ctaEngine.mainEngine.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
        cursor = conn.cursor()
        ## =====================================================================

        ## =====================================================================
        ## 0. 数据预处理
        ## =====================================================================
        self.stratTrade                 = trade.__dict__
        self.stratTrade['InstrumentID'] = self.stratTrade['vtSymbol']
        self.stratTrade['strategyID']   = self.strategyID
        self.stratTrade['tradeTime']    = datetime.now().strftime('%Y-%m-%d') + " " + self.stratTrade['tradeTime']
        ## ---------------------------------------------------------------------
        self.stratTrade['TradingDay']   = self.ctaEngine.tradingDate
        ## ---------------------------------------------------------------------

        ## ---------------------------------------------------------------------
        if self.stratTrade['offset'] == u'开仓':
            tempOffset = u'开仓'
            if self.stratTrade['direction'] == u'多':
                self.stratTrade['direction'] = 'long'
                tempDirection = 'buy'
            elif self.stratTrade['direction'] == u'空':
                self.stratTrade['direction'] = 'short'
                tempDirection = 'short'
        elif self.stratTrade['offset'] in [u'平仓', u'平昨', u'平今']:
            tempOffset = u'平仓'
            if self.stratTrade['direction'] == u'多':
                self.stratTrade['direction'] = 'long'
                tempDirection = 'cover'
            elif self.stratTrade['direction'] == u'空':
                self.stratTrade['direction'] = 'short'
                tempDirection = 'sell'
        ## ---------------------------------------------------------------------

        tempKey = self.stratTrade['vtSymbol'] + '-' + tempDirection
        ## ---------------------------------------------------------------------

        ## =====================================================================
        ## 1. 修改 orderDict 的数量
        ## =====================================================================
        if self.stratTrade['vtOrderID'] in self.vtOrderIDListOpen:
            # ------------------------------------------------------------------
            self.tradingOrdersOpen[tempKey]['volume'] -= self.stratTrade['volume']
            if self.tradingOrdersOpen[tempKey]['volume'] == 0:
                self.tradingOrdersOpen.pop(tempKey, None)
                self.tradedOrdersOpen[tempKey] = tempKey
        elif self.stratTrade['vtOrderID'] in self.vtOrderIDListClose:
            # ------------------------------------------------------------------
            self.tradingOrdersClose[tempKey]['volume'] -= self.stratTrade['volume']
            if self.tradingOrdersClose[tempKey]['volume'] == 0:
                self.tradingOrdersClose.pop(tempKey, None)
                self.tradedOrdersClose[tempKey] = tempKey
        elif self.stratTrade['vtOrderID'] in self.vtOrderIDListFailedInfo:
            # ------------------------------------------------------------------
            self.tradingOrdersFailedInfo[tempKey]['volume'] -= self.stratTrade['volume']
            # ------------------------------------------------------------------
            ## 如果是平仓，需要再把当天的 tradingOrders 相关的合约持仓数量做调整
            if (self.stratTrade['offset'] in [u'平仓', u'平昨', u'平今']) and (tempKey in self.tradingOrdersOpen.keys()):
                if self.tradingOrdersOpen[tempKey]['TradingDay'] == self.tradingOrdersFailedInfo[tempKey]['TradingDay']:
                    self.tradingOrdersOpen[tempKey]['volume'] -= self.stratTrade['volume']
                    if self.tradingOrdersOpen[tempKey]['volume'] == 0:
                        self.tradingOrdersOpen.pop(tempKey, None)
                        self.tradedOrdersOpen[tempKey] = tempKey
            # ------------------------------------------------------------------
            tempPosInfo = self.failedInfo.loc[self.failedInfo.InstrumentID == self.stratTrade['vtSymbol']][self.failedInfo.direction == self.stratTrade['direction']][self.failedInfo.offset == tempOffset].reset_index(drop = True)
            self.stratTrade['TradingDay']  = tempPosInfo.at[0, 'TradingDay']
            # ------------------------------------------------------------------

        ## ---------------------------------------------------------------------
        tempFields = ['strategyID','InstrumentID','TradingDay','direction','volume']
        tempRes = pd.DataFrame([[self.stratTrade[k] for k in tempFields]], columns = tempFields)
        ## =====================================================================

        ## =====================================================================
        ## 2. 更新 positionInfo
        ## =====================================================================
        if self.stratTrade['offset'] == u'开仓':
            ####################################################################
            ## mysqlPositionInfo: 存储在 mysql 数据库的持仓信息，需要更新
            mysqlPositionInfo = self.ctaEngine.mainEngine.dbMySQLQuery(
                self.ctaEngine.mainEngine.dataBase,
                """
                SELECT *
                FROM positionInfo
                WHERE strategyID = '%s'
                """ %(self.strategyID))
            ## 看看是不是已经在数据库里面了
            tempPosInfo = mysqlPositionInfo.loc[mysqlPositionInfo.InstrumentID == tempRes.loc[0,'InstrumentID']][mysqlPositionInfo.TradingDay == tempRes.loc[0,'TradingDay']][mysqlPositionInfo.direction == tempRes.loc[0,'direction']]
            if len(tempPosInfo) == 0:
                ## 如果不在
                ## 则直接添加过去即可
                try:
                    tempRes.to_sql(con=conn, 
                        name='positionInfo', 
                        if_exists='append', 
                        flavor='mysql', 
                        index = False)
                except:
                    print '\n' + '#'*80 
                    print '写入 MySQL 数据库出错'
                    print '#'*80 + '\n'
            else:
                ## 如果在
                ## 则需要更新数据
                mysqlPositionInfo.at[tempPosInfo.index[0], 'volume'] += tempRes.loc[0,'volume']
                mysqlPositionInfo = mysqlPositionInfo.loc[mysqlPositionInfo.volume != 0]
                try:
                    cursor.execute("""
                                    DELETE FROM positionInfo
                                    WHERE strategyID = '%s'
                                   """ %(self.strategyID))
                    conn.commit()
                    mysqlPositionInfo.to_sql(con=conn, 
                        name='positionInfo', 
                        if_exists='append', 
                        flavor='mysql', 
                        index = False)
                except:
                    print '\n' + '#'*80 
                    print '写入 MySQL 数据库出错'
                    print '#'*80 + '\n'
            ## -------------------------------------------------------------
        elif self.stratTrade['offset'] in [u'平仓', u'平昨', u'平今']:
            ################################################################
            if self.stratTrade['direction'] == 'long':
                tempDirection = 'short'
            elif self.stratTrade['direction'] == 'short':
                tempDirection = 'long'
            ## -------------------------------------------------------------
            if self.stratTrade['vtOrderID'] in self.vtOrderIDListClose:
                ## 只有在 tradingOrders 的平仓信息，需要更新到数据库
                ## 因为 failedInfo 已经把未成交的订单记录下来了
                ## =================================================================================
                ## mysqlPositionInfo: 存储在 mysql 数据库的持仓信息，需要更新
                mysqlPositionInfo = self.ctaEngine.mainEngine.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
                                        """
                                        SELECT *
                                        FROM positionInfo
                                        WHERE strategyID = '%s'
                                        """ %(self.strategyID))
                tempPosInfo = self.positionInfo.loc[self.positionInfo.InstrumentID == tempRes.at[0,'InstrumentID']][self.positionInfo.direction == tempDirection]
                tempPosInfo2 = mysqlPositionInfo.loc[mysqlPositionInfo.InstrumentID == tempPosInfo.at[tempPosInfo.index[0],'InstrumentID']][mysqlPositionInfo.direction == tempPosInfo.at[tempPosInfo.index[0],'direction']].sort_values(by='TradingDay', ascending = True)
                ## ---------------------------------------------------------------------------------
                for i in range(len(tempPosInfo2)):
                    tempResVolume = tempPosInfo2.loc[tempPosInfo2.index[i],'volume'] - tempRes.at[0,'volume']
                    mysqlPositionInfo.at[tempPosInfo2.index[i], 'volume'] = tempResVolume
                    if tempResVolume >= 0:
                        break
                ## ---------------------------------------------------------------------------------
                mysqlPositionInfo = mysqlPositionInfo.loc[mysqlPositionInfo.volume > 0]   
                try:
                    cursor.execute("""
                                    DELETE FROM positionInfo
                                    WHERE strategyID = '%s'
                                   """ %(self.strategyID))
                    conn.commit()
                    mysqlPositionInfo.to_sql(con=conn, name='positionInfo', if_exists='append', flavor='mysql', index = False)
                except:
                    print '\n' + '#'*80 
                    print '写入 MySQL 数据库出错'
                    print '#'*80 + '\n'
                ## =================================================================================

        #===================================================================
        if self.stratTrade['vtOrderID'] in self.vtOrderIDListFailedInfo:
            ## 更新 tradingOrdersFailedInfo 的数量
            if self.tradingOrdersFailedInfo[tempKey]['volume'] == 0:
                self.tradingOrdersFailedInfo.pop(tempKey, None)
            #-------------------------------------------------------------------
            mysqlFailedInfo = self.ctaEngine.mainEngine.dbMySQLQuery(
                self.ctaEngine.mainEngine.dataBase,
                """
                SELECT *
                FROM failedInfo
                WHERE strategyID = '%s'
                """ %(self.strategyID))

            #-------------------------------------------------------------------
            if len(mysqlFailedInfo) != 0:
                #-------------------------------------------------------------------
                tempPosInfo = mysqlFailedInfo.loc[mysqlFailedInfo.InstrumentID == self.stratTrade['InstrumentID']][mysqlFailedInfo.direction == self.stratTrade['direction']][mysqlFailedInfo.offset == tempOffset]

                mysqlFailedInfo.at[tempPosInfo.index[0], 'volume'] -= self.stratTrade['volume']
                mysqlFailedInfo = mysqlFailedInfo.loc[mysqlFailedInfo.volume != 0]
                # mysqlFailedInfo = mysqlFailedInfo.append(mysqlFailedInfoOthers, ignore_index = True)
                try:
                    cursor.execute("""
                                    DELETE FROM failedInfo
                                    WHERE strategyID = '%s'
                                   """ %(self.strategyID))
                    conn.commit()
                    mysqlFailedInfo.to_sql(con=conn, 
                        name='failedInfo', 
                        if_exists='append', 
                        flavor='mysql', 
                        index = False)
                except:
                    print '\n' + '#'*80 
                    print '写入 MySQL 数据库出错'
                    print '#'*80 + '\n'
                #-------------------------------------------------------------------
            self.failedInfo = self.ctaEngine.mainEngine.dbMySQLQuery(
                self.ctaEngine.mainEngine.dataBase,
                """
                SELECT *
                FROM failedInfo
                WHERE strategyID = '%s'
                """ %(self.strategyID))
        #-------------------------------------------------------------------
        #===================================================================

        ## =====================================================================
        ## 3. 保存交易记录
        ## =====================================================================
        tempTradingInfo = pd.DataFrame([[self.stratTrade[k] for k in self.tradingInfoFields]], 
            columns = self.tradingInfoFields)
        ## -----------------------------------------------------------------
        self.updateTradingInfo(df = tempTradingInfo, tbName = 'tradingInfo')
        self.tradingInfo = self.tradingInfo.append(tempTradingInfo, ignore_index=True)
        ## -----------------------------------------------------------------
        ############################################################################################
        conn.close()

        ############################################################################################
        ## 处理 MySQL 数据库的 tradingOrders
        ## 如果成交了，需要从这里面再删除交易订单
        ############################################################################################
        if trade.vtOrderID in list(set(self.vtOrderIDListOpen) | set(self.vtOrderIDListClose)) and self.ctaEngine.mainEngine.multiStrategy:
            self.updateTradingOrdersTable(self.stratTrade)
        # 发出状态更新事件
        self.putEvent()
        ############################################################################################



    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def registerEvent(self):
        """注册事件监听"""
        ## ---------------------------------------------------------------------
        ## 更新交易记录,并写入 mysql
        self.ctaEngine.mainEngine.eventEngine.register(EVENT_TIMER, self.updateTradingStatus)
        ## ---------------------------------------------------------------------

    ############################################################################
    ## william
    ## 从 MySQL 数据库读取策略持仓信息
    ############################################################################
    def generateTradingOrders(self):
        pass

    ############################################################################
    ## william
    ## 从 MySQL 数据库读取策略持仓信息
    ############################################################################
    def fetchTradingOrders(self, stage):
        """
        提取交易订单
        """
        tempOrders = self.ctaEngine.mainEngine.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
                            """
                            SELECT *
                            FROM tradingOrders
                            WHERE strategyID = '%s'
                            AND TradingDay = '%s'
                            AND stage = '%s'
                            """ %(self.strategyID, self.ctaEngine.tradingDate, stage))
        if len(tempOrders) != 0:
            ## ---------------------------------------------------------------------
            if stage == 'open':
                self.tradingOrdersOpen = {}
                self.vtOrderIDListOpen = []
            elif stage == 'close':
                self.tradingOrdersClose = {}
                self.vtOrderIDListClose = []
            ## -------------------------------------------------------------------------------------
            for i in range(len(tempOrders)):
                tempKey = tempOrders.at[i,'InstrumentID'] + '-' + tempOrders.at[i,'orderType']
                ## ---------------------------------------------------------------------
                ## ---------------------------------------------------------------------
                if stage == 'open':
                    self.tradingOrdersOpen[tempKey] = {
                        'vtSymbol': tempOrders.at[i,'InstrumentID'],
                        'direction': tempOrders.at[i,'orderType'],
                        'volume':tempOrders.at[i,'volume'],
                        'TradingDay':tempOrders.at[i,'TradingDay']
                    }
                    ## -----------------------------------------------------------------------------
                    self.updateTradingOrdersVtOrderID(tradingOrders = self.tradingOrdersOpen, 
                                                      stage = 'open')
                    self.updateVtOrderIDList(vtOrderIDList = self.vtOrderIDListOpen, 
                                             stage = 'open')
                    ## -----------------------------------------------------------------------------
                    self.tickTimer[tempOrders.at[i,'InstrumentID']] = datetime.now()
                elif stage == 'close':
                    self.tradingOrdersClose[tempKey] = {
                        'vtSymbol': tempOrders.at[i,'InstrumentID'],
                        'direction': tempOrders.at[i,'orderType'],
                        'volume':tempOrders.at[i,'volume'],
                        'TradingDay':tempOrders.at[i,'TradingDay']
                    }
                    ## -----------------------------------------------------------------------------
                    self.updateTradingOrdersVtOrderID(tradingOrders = self.tradingOrdersClose, 
                                                      stage = 'close')
                    self.updateVtOrderIDList(vtOrderIDList = self.vtOrderIDListClose, 
                                             stage = 'close')
                    ## -----------------------------------------------------------------------------
                    self.tickTimer[tempOrders.at[i,'InstrumentID']] = datetime.now()
            ## -------------------------------------------------------------------------------------
 
    ############################################################################
    ## william
    ## 更新状态，需要订阅
    ############################################################################
    def updateTradingStatus(self, event):
        ## =====================================================================
        tradingCloseHour    = 14
        tradingCloseMinute1 = 50
        tradingCloseMinute2 = 59
        ## =====================================================================

        ## =====================================================================
        ## 启动尾盘交易
        ## =====================================================================
        if (datetime.now().hour in [8,20] and datetime.now().minute >= 59 and datetime.now().second >= 45) or \
           ( ( (21 <= datetime.now().hour <= 24) or (0 <= datetime.now().hour <= 2) or (9 <= datetime.now().hour <= (tradingCloseHour-1)) ) and datetime.now().minute <= 59) or \
           (datetime.now().hour == tradingCloseHour and datetime.now().minute < tradingCloseMinute1):
            self.tradingStart = True
        else:
            self.tradingStart = False

        ## ---------------------------------------------------------------------
        if datetime.now().hour == tradingCloseHour and (tradingCloseMinute1+1) <= datetime.now().minute < (tradingCloseMinute2-1):
            self.tradingBetween = True
        else:
            self.tradingBetween = False

        ## ---------------------------------------------------------------------
        if datetime.now().hour == tradingCloseHour and datetime.now().minute == tradingCloseMinute2 and \
           (datetime.now().second >= ( 59 - max(10, len(self.tradingOrdersClose)*1.0)) ):
            self.tradingStart = True
            self.tradingEnd   = True
        else:
            self.tradingEnd = False

        ## =====================================================================
        ## 如果是收盘交易
        ## 则取消开盘交易的所有订单
        if (datetime.now().hour == tradingCloseHour and 
            tradingCloseMinute1 <= datetime.now().minute <= tradingCloseMinute1 and 
            datetime.now().second <= 20 and 
            (datetime.now().second % 10 == 0)):
            ## -----------------------------------------------------------------
            if (len(self.vtOrderIDListOpen) != 0) | (len(self.vtOrderIDListClose) != 0) :
                for vtOrderID in self.vtOrderIDListOpen + self.vtOrderIDListClose:
                    if vtOrderID in self.ctaEngine.mainEngine.getAllOrders().loc[self.ctaEngine.mainEngine.getAllOrders().status.isin([u'未成交',u'部分成交'])].vtOrderID.values:
                        self.cancelOrder(vtOrderID)
                    else:
                        None
            ## -----------------------------------------------------------------
        ## =====================================================================

        ## =====================================================================
        ## 如果是收盘交易
        ## 则取消开盘交易的所有订单
        if (datetime.now().hour == tradingCloseHour and 
            (tradingCloseMinute2-1) <= datetime.now().minute <= (tradingCloseMinute2-1) and 
            datetime.now().second <= 20 and 
            (datetime.now().second % 5 == 0)):
            ## -----------------------------------------------------------------
            if (len(self.vtOrderIDListOpen) != 0) | (len(self.vtOrderIDListClose) != 0) :
                for vtOrderID in self.vtOrderIDListOpen + self.vtOrderIDListClose:
                    if vtOrderID in self.ctaEngine.mainEngine.getAllOrders().loc[self.ctaEngine.mainEngine.getAllOrders().status.isin([u'未成交',u'部分成交'])].vtOrderID.values:
                        self.cancelOrder(vtOrderID)
                    else:
                        None
            ## -----------------------------------------------------------------
        ## =====================================================================

        ## =====================================================================
        ## 生成收盘交易的订单
        if (datetime.now().hour == tradingCloseHour and 
            tradingCloseMinute1 <= datetime.now().minute <= tradingCloseMinute1 and 
            20 <= datetime.now().second < 30  and 
            self.ctaEngine.mainEngine.multiStrategy and 
            not self.runRscript):
            ## 更新 tradingOrders
            subprocess.call(['Rscript',
                             os.path.join(self.ctaEngine.mainEngine.ROOT_PATH,'ctaStrategy','end_signal.R'),
                             self.ctaEngine.mainEngine.ROOT_PATH, self.ctaEngine.mainEngine.dataBase], shell = False)
            ## 更新 positionInfo
            self.positionInfo = self.ctaEngine.mainEngine.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
                    """
                    SELECT *
                    FROM positionInfo
                    WHERE strategyID = '%s'
                    """ %(self.strategyID))
            ##
            self.runRscript = True
            ##

        ## =====================================================================
        ## 尾盘读取交易订单
        ## ---------------------------------------------------------------------
        if (datetime.now().hour == tradingCloseHour and 
            tradingCloseMinute1 <= datetime.now().minute <= tradingCloseMinute1 and 
            30 <= datetime.now().second <= 59 and 
            (datetime.now().second % 10 == 0 or
            len(self.tradingOrdersClose) == 0) and 
            self.ctaEngine.mainEngine.multiStrategy):
            ## -----------------------------------------------------------------
            conn = self.ctaEngine.mainEngine.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
            cursor = conn.cursor()
            cursor.execute("""
                            TRUNCATE TABLE workingInfo
                           """)
            conn.commit()
            conn.close()
            ## -----------------------------------------------------------------
            self.fetchTradingOrders(stage = 'open')
            self.fetchTradingOrders(stage = 'close')
        ## =====================================================================

        ## =====================================================================
        ## 更新订单字典
        ## =====================================================================
        self.updateTradingOrdersDict(tradingOrders = dict(self.tradingOrdersOpen.items() + 
                                                          self.tradingOrdersClose.items()), 
                                     tradedOrders  = dict(self.tradedOrdersOpen.items() + 
                                                          self.tradedOrdersClose.items()))

        ## =====================================================================
        ## 更新 workingInfo
        ## =====================================================================
        if ( (datetime.now().minute % 3 == 0) and
             (datetime.now().second == 59) and
             self.tradingStart):
            self.updateWorkingInfo(self.tradingOrdersOpen, 'open')
            self.updateWorkingInfo(self.tradingOrdersClose, 'close')
