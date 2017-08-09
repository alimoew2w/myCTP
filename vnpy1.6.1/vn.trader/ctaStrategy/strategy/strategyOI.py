# encoding: UTF-8
"""
################################################################################
@william

期货公司持仓排名追随策略
################################################################################
"""
from __future__ import division
import os
import sys

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
class OIStrategy(CtaTemplate):
    """ oiRank 交易策略 """
    ############################################################################
    ## william
    ## 策略类的名称和作者
    ## -------------------------------------------------------------------------
    name         = 'OiRank'
    className    = 'OIStrategy'
    strategyID   = className
    author       = 'Lin HuanGeng'
    ############################################################################
####
####
    ##
    ##
    ############################################################################
    ## -------------------------------------------------------------------------
    ## 各种控制条件
    ## 策略的基本变量，由引擎管理
    inited         = False                    # 是否进行了初始化
    trading        = False                    # 是否启动交易，由引擎管理
    tradingOpen    = False                    # 开盘启动交易
    tradingClose   = False                    # 收盘开启交易
    pos            = 0                        # 持仓情况
    sendMailStatus = False                    # 是否已经发送邮件
    tradingClosePositionAll    = False        # 是否强制平仓所有合约
    tradingClosePositionSymbol = False        # 是否强制平仓单个合约
    ## -------------------------------------------------------------------------

    # 参数列表，保存了参数的名称
    # paramList = ['name',
    #              'className',
    #              'author',
    #              'vtSymbol']
    
    # # 变量列表，保存了变量的名称
    # varList = ['inited',
    #            'trading',
    #            'pos']

    ## -------------------------------------------------------------------------
    ## 从 TickData 提取的字段
    ## -------------------------------------------------------------------------
    tickFileds = ['symbol', 'vtSymbol', 'lastPrice', 'bidPrice1', 'askPrice1',
                  'bidVolume1', 'askVolume1', 'upperLimit', 'lowerLimit']
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
####
####
    ##
    ##
    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(OIStrategy, self).__init__(ctaEngine, setting)

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
                            FROM fl_open_t_2
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
        self.positionInfoClose = self.ctaEngine.mainEngine.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
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
        ##
        ## =====================================================================
        if self.ctaEngine.mainEngine.multiStrategy:
            self.fetchTradingOrders()
        else:
            self.generateTradingOrders()

        print '#'*80
        print '%s策略启动' %self.name

        print '#'*80
        print '当日开盘需要执行的订单为:'
        print self.tradingOrdersOpen
        print '#'*80
        print '当日收盘需要执行的订单为:'
        print self.tradingOrdersClose

        ## ---------------------------------------------------------------------
        ## 当前策略下面的所有合约集合
        self.vtSymbolList = list(set(self.openInfo.InstrumentID.values) |
                                 set(self.failedInfo.InstrumentID.values)
                                 # | set(self.positionInfo.InstrumentID.values)
                                 | set(self.positionInfoClose.InstrumentID.values)
                                )
        for i in self.vtSymbolList:
            self.tickTimer[i] = datetime.now()

        print '#'*80
        print "@william 策略初始化成功 !!!"
        # self.writeCtaLog(u'%s策略初始化' %self.name)
        print self.vtSymbolList
        print '#'*80
        ########################################################################
        ## william
        self.putEvent()


    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        # tempTick = tick.__dict__
        # tempTick = {k:tick.__dict__[k] for k in self.tickFileds}

        ## =====================================================================
        if not self.trading:
            return 
        elif tick.vtSymbol not in [self.tradingOrdersOpen[k]['vtSymbol'] for k in self.tradingOrdersOpen.keys()] + [self.tradingOrdersClose[k]['vtSymbol'] for k in self.tradingOrdersClose.keys()]:
            return 
        elif ((datetime.now() - self.tickTimer[tick.vtSymbol]).seconds <= 5):
            return
        ## =====================================================================
        
        ## ---------------------------------------------------------------------
        self.lastTickData[tick.vtSymbol] = {k:tick.__dict__[k] for k in self.tickFileds}
        self.updateCancelOrders(tick.vtSymbol)
        ## ---------------------------------------------------------------------

        ## =====================================================================
        if self.tradingOpen:
            ####################################################################
            self.prepareTradingOrder(vtSymbol       = tick.vtSymbol, 
                                     tradingOrders  = self.tradingOrdersOpen, 
                                     orderIDList    = self.vtOrderIDListOpen)
        elif self.tradingClose:
            ####################################################################
            self.prepareTradingOrder(vtSymbol        = tick.vtSymbol, 
                                     tradingOrders   = self.tradingOrdersClose, 
                                     orderIDList     = self.vtOrderIDListClose)
        ## =====================================================================

        ########################################################################
        # 发出状态更新事件
        self.putEvent()

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
    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def stratTradeEvent(self, trade):
        """处理策略交易与持仓信息
        """
        ## =====================================================================
        if trade.vtOrderID not in list(set(self.vtOrderIDListOpen) | set(self.vtOrderIDListClose)):
            return
        ## =====================================================================

        ## =====================================================================
        ## 连接 MySQL 设置
        conn = self.ctaEngine.mainEngine.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
        cursor = conn.cursor()
        ## =====================================================================

        ## =====================================================================
        ## 0. 数据预处理
        ## =====================================================================
        self.stratTrade = trade.__dict__
        self.stratTrade['InstrumentID'] = self.stratTrade['vtSymbol']
        self.stratTrade['strategyID'] = self.strategyID
        self.stratTrade['tradeTime']  = datetime.now().strftime('%Y-%m-%d') + " " + self.stratTrade['tradeTime']
        self.stratTrade['TradingDay']  = self.ctaEngine.tradingDate

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

        ## ---------------------------------------------------------------------
        tempFields = ['strategyID','InstrumentID','TradingDay','direction','volume']
        tempRes = pd.DataFrame([[self.stratTrade[k] for k in tempFields]], columns = tempFields)
        ## =====================================================================


        ########################################################################
        ## william
        ## 更新数量
        ## 更新交易日期
        if self.stratTrade['vtOrderID'] in self.vtOrderIDListOpen:
            # ------------------------------------------------------------------
            self.tradingOrdersOpen[tempKey]['volume'] -= self.stratTrade['volume']
            if self.tradingOrdersOpen[tempKey]['volume'] == 0:
                self.tradingOrdersOpen.pop(tempKey, None)
                self.tradedOrdersOpen[tempKey] = tempKey
            # ------------------------------------------------------------------
        elif self.stratTrade['vtOrderID'] in self.vtOrderIDListClose:
            # ------------------------------------------------------------------
            self.tradingOrdersClose[tempKey]['volume'] -= self.stratTrade['volume']
            if self.tradingOrdersClose[tempKey]['volume'] == 0:
                self.tradingOrdersClose.pop(tempKey, None)
                self.tradedOrdersClose[tempKey] = tempKey
            # ------------------------------------------------------------------
        

        ## =================================================================
        ## 2. 更新 positionInfo
        ## =================================================================
        if self.stratTrade['offset'] == u'开仓':
            ################################################################
            ## 1. 更新 mysql.positionInfo
            ################################################################
            ## mysqlPositionInfo: 存储在 mysql 数据库的持仓信息，需要更新
            mysqlPositionInfo = self.ctaEngine.mainEngine.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
                                    """
                                    SELECT *
                                    FROM positionInfo
                                    WHERE strategyID = '%s'
                                    """ %(self.strategyID))
            # mysqlPositionInfoOthers = self.ctaEngine.mainEngine.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
            #                         """
            #                         SELECT *
            #                         FROM positionInfo
            #                         WHERE NOT(strategyID = '%s')
            #                         """ %(self.strategyID))
            ## 看看是不是已经在数据库里面了
            tempPosInfo = mysqlPositionInfo.loc[mysqlPositionInfo.InstrumentID == tempRes.loc[0,'InstrumentID']][mysqlPositionInfo.TradingDay == tempRes.loc[0,'TradingDay']][mysqlPositionInfo.direction == tempRes.loc[0,'direction']]
            if len(tempPosInfo) == 0:
                ## 如果不在
                ## 则直接添加过去即可
                try:
                    # conn = self.ctaEngine.mainEngine.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
                    # cursor = conn.cursor()
                    tempRes.to_sql(con=conn, name='positionInfo', if_exists='append', flavor='mysql', index = False)
                    # conn.close()
                except:
                    print "\n"+'#'*80
                    print '写入 MySQL 数据库出错'
                    # self.onStop()
                    # print '停止策略 %s' %self.name
                    print '#'*80+"\n"
            else:
                ## 如果在
                ## 则需要更新数据
                mysqlPositionInfo.at[tempPosInfo.index[0], 'volume'] += tempRes.loc[0,'volume']
                mysqlPositionInfo = mysqlPositionInfo.loc[mysqlPositionInfo.volume != 0]
                # mysqlPositionInfo = mysqlPositionInfo.append(mysqlPositionInfoOthers, ignore_index=True)
                try:
                    # conn = self.ctaEngine.mainEngine.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
                    # cursor = conn.cursor()
                    cursor.execute("""
                                    DELETE FROM positionInfo
                                    WHERE strategyID = '%s'
                                   """ %(self.strategyID))
                    conn.commit()
                    mysqlPositionInfo.to_sql(con=conn, name='positionInfo', if_exists='append', flavor='mysql', index = False)
                    # conn.close()
                except:
                    print "\n"+'#'*80
                    print '写入 MySQL 数据库出错'
                    # self.onStop()
                    # print '停止策略 %s' %self.name
                    print '#'*80+"\n"
            ## -------------------------------------------------------------
        elif self.stratTrade['offset'] in [u'平仓', u'平昨', u'平今']:
            ## -------------------------------------------------------------
            ## 1. 更新 mysql.positionInfo
            ################################################################
            if self.stratTrade['direction'] == 'long':
                tempDirection = 'short'
            elif self.stratTrade['direction'] == 'short':
                tempDirection = 'long'
            ## -------------------------------------------------------------
            
            ## =====================================================================================
            if self.stratTrade['vtOrderID'] in self.vtOrderIDListOpen:
                ## 只有在 tradingOrders 的平仓信息，需要更新到数据库
                ## 因为 failedInfo 已经把未成交的订单记录下来了
                ## =================================================================================
                ## mysqlPositionInfo: 存储在 mysql 数据库的持仓信息，需要更新
                mysqlFailedInfo = self.ctaEngine.mainEngine.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
                        """
                        SELECT *
                        FROM failedInfo
                        WHERE strategyID = '%s'
                        """ %(self.strategyID))
                # mysqlFailedInfoOthers = self.ctaEngine.mainEngine.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
                #         """
                #         SELECT *
                #         FROM failedInfo
                #         WHERE NOT (strategyID = '%s')
                #         """ %(self.strategyID))
                 #-------------------------------------------------------------------
                if len(mysqlFailedInfo) != 0:
                    #-------------------------------------------------------------------
                    tempPosInfo = mysqlFailedInfo.loc[mysqlFailedInfo.InstrumentID == self.stratTrade['InstrumentID']][mysqlFailedInfo.direction == self.stratTrade['direction']][mysqlFailedInfo.offset == tempOffset]

                    mysqlFailedInfo.at[tempPosInfo.index[0], 'volume'] -= self.stratTrade['volume']
                    mysqlFailedInfo = mysqlFailedInfo.loc[mysqlFailedInfo.volume != 0]
                    # mysqlFailedInfo = mysqlFailedInfo.append(mysqlFailedInfoOthers, ignore_index=True)
                    try:
                        # conn = self.ctaEngine.mainEngine.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
                        # cursor = conn.cursor()
                        cursor.execute("""
                                        DELETE FROM failedInfo
                                        WHERE strategyID = '%s'
                                       """ %(self.strategyID))
                        conn.commit()
                        mysqlFailedInfo.to_sql(con=conn, name='failedInfo', if_exists='append', flavor='mysql', index = False)
                        # conn.close()
                    except:
                        print "\n"+'#'*80
                        print '写入 MySQL 数据库出错'
                        # self.onStop()
                        # print '停止策略 %s' %self.name
                        print '#'*80+"\n"
                    #-------------------------------------------------------------------
            elif self.stratTrade['vtOrderID'] in self.vtOrderIDListClose:
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
                # mysqlPositionInfoOthers = self.ctaEngine.mainEngine.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
                #                         """
                #                         SELECT *
                #                         FROM positionInfo
                #                         WHERE NOT(strategyID = '%s')
                #                         """ %(self.strategyID))

                tempPosInfo = self.positionInfoClose.loc[self.positionInfoClose.InstrumentID == tempRes.at[0,'InstrumentID']][self.positionInfoClose.direction == tempDirection]
                tempPosInfo2 = mysqlPositionInfo.loc[mysqlPositionInfo.InstrumentID == tempPosInfo.at[tempPosInfo.index[0],'InstrumentID']][mysqlPositionInfo.TradingDay == tempPosInfo.at[tempPosInfo.index[0],'TradingDay']][mysqlPositionInfo.direction == tempPosInfo.at[tempPosInfo.index[0],'direction']]
                mysqlPositionInfo.at[tempPosInfo2.index[0], 'volume'] -= tempRes.at[0,'volume']
                mysqlPositionInfo = mysqlPositionInfo.loc[mysqlPositionInfo.volume != 0]
                # mysqlPositionInfo = mysqlPositionInfo.append(mysqlPositionInfoOthers, ignore_index=True)
                try:
                    # conn = self.ctaEngine.mainEngine.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
                    # cursor = conn.cursor()
                    cursor.execute("""
                                    DELETE FROM positionInfo
                                    WHERE strategyID = '%s'
                                   """ %(self.strategyID))
                    conn.commit()                    
                    mysqlPositionInfo.to_sql(con=conn, name='positionInfo', if_exists='append', flavor='mysql', index = False)
                    # conn.close()
                except:
                    print "\n"+'#'*80
                    print '写入 MySQL 数据库出错'
                    # self.onStop()
                    # print '停止策略 %s' %self.name
                    print '#'*80+"\n"
                ## =================================================================================
             ## =====================================================================================

        # tempFields = ['strategyID','vtSymbol','TradingDay','tradeTime','direction','offset','volume','price']
        tempTradingInfo = pd.DataFrame([[self.stratTrade[k] for k in self.tradingInfoFields]], 
            columns = self.tradingInfoFields)
        ## -----------------------------------------------------------------
        self.updateTradingInfo(tempTradingInfo)
        self.tradingInfo = self.tradingInfo.append(tempTradingInfo, ignore_index=True)
        ## -----------------------------------------------------------------
        # ######################################################################
        conn.close()

        ############################################################################################
        ## 处理 MySQL 数据库的 tradingOrders
        ## 如果成交了，需要从这里面再删除交易订单
        ############################################################################################
        if trade.vtOrderID in list(set(self.vtOrderIDListOpen) | set(self.vtOrderIDListClose)) and self.ctaEngine.mainEngine.multiStrategy:
            self.updateTradingOrdersTable(self.stratTrade)
        # 发出状态更新事件
        self.putEvent()

    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def registerEvent(self):
        """注册事件监听"""
        # self.ctaEngine.mainEngine.eventEngine.register(EVENT_TICK, self.onClosePosition)
        # self.ctaEngine.mainEngine.eventEngine.register(EVENT_TRADE, self.stratTradeEvent)
        # self.ctaEngine.mainEngine.eventEngine.register(EVENT_TRADE, self.closePositionTradeEvent)
        ## ---------------------------------------------------------------------
        ## 更新交易记录,并写入 mysql
        self.ctaEngine.mainEngine.eventEngine.register(EVENT_TIMER, self.updateTradingStatus)
        ## ---------------------------------------------------------------------
        ## 收盘发送邮件
        # self.ctaEngine.mainEngine.eventEngine.register(EVENT_TIMER, self.sendMail)
        ## ---------------------------------------------------------------------

    #---------------------------------------------------------------------------


    ############################################################################
    ## william
    ## 从 MySQL 数据库读取策略持仓信息
    ############################################################################
    def generateTradingOrders(self):
        """
        初始化交易订单
        """
        ## =====================================================================
        ## 策略初始化
        ## 对订单进行预先处理
        ## =====================================================================
        if len(self.positionInfo) != 0:
            self.positionInfoToday = self.positionInfo[self.positionInfo.TradingDay == self.ctaEngine.tradingDate]

            if len(self.positionInfoToday) != 0:
                for i in self.positionInfoToday.index:
                    if self.positionInfoToday.at[i,'direction'] == 'long':
                        tempDirection = 1
                    elif self.positionInfoToday.at[i,'direction'] == 'short':
                        tempDirection = -1

                    tempOpenInfo = self.openInfo[self.openInfo.InstrumentID == self.positionInfoToday.at[i,'InstrumentID']][self.openInfo.direction == tempDirection]
                    if len(tempOpenInfo) != 0:
                        self.openInfo.at[tempOpenInfo.index[0],'volume'] -= self.positionInfoToday.at[i,'volume']
                ## -------------------------------------------------------------
                self.openInfo.drop(self.openInfo[self.openInfo.volume == 0].index, inplace = True)
                self.openInfo = self.openInfo.reset_index(drop=True)

        if len(self.failedInfo) == 0:
            if len(self.openInfo) != 0:
                for i in range(len(self.openInfo)):
                    ## direction
                    if self.openInfo.at[i, 'direction'] == 1:
                        tempDirection = 'buy'
                    elif self.openInfo.at[i, 'direction'] == -1:
                        tempDirection = 'short'
                    self.tradingOrdersOpen[self.openInfo.at[i,'InstrumentID'] + '-' + tempDirection] = {
                        'vtSymbol': self.openInfo.at[i, 'InstrumentID'],
                        'direction': tempDirection,
                        'volume': self.openInfo.at[i, 'volume'],
                        'TradingDay': self.openInfo.at[i, 'TradingDay']
                    }
            else:
                pass
        else:
            if len(self.openInfo) == 0: 
                for i in range(len(self.failedInfo)):
                    ## direction
                    if self.failedInfo.at[i, 'direction'] == 'long':
                        tempDirection = 'cover'
                    elif self.failedInfo.at[i, 'direction'] == 'short':
                        tempDirection = 'sell'
                    self.tradingOrdersOpen[self.failedInfo.at[i,'InstrumentID'] + '-' + tempDirection] = {
                        'vtSymbol': self.failedInfo.at[i, 'InstrumentID'],
                        'direction': tempDirection,
                        'volume': self.failedInfo.at[i, 'volume'],
                        'TradingDay': self.failedInfo.at[i, 'TradingDay']
                    }
            else:
                self.x = list(set(self.failedInfo.InstrumentID.values) & set(self.openInfo.InstrumentID.values))
                self.y = [i for i in self.failedInfo.InstrumentID.values if i not in self.openInfo.InstrumentID.values]
                self.z = [i for i in self.openInfo.InstrumentID.values if i not in self.failedInfo.InstrumentID.values]

                # print x
                # print y
                # print z

                if len(self.x) != 0:
                    for i in self.x:
                        tempFailedVolume = int(self.failedInfo.loc[self.failedInfo.InstrumentID == i, 'volume'].values)
                        tempOpenVolume = int(self.openInfo.loc[self.openInfo.InstrumentID == i, 'volume'])
                        tempDiffVolume = tempFailedVolume - tempOpenVolume
                        tempFailedTradingDay = self.failedInfo.loc[self.failedInfo.InstrumentID == i, 'TradingDay'].values[0]
                        tempOpenTraingDay = self.openInfo.loc[self.openInfo.InstrumentID == i, 'TradingDay'].values[0]

                        if self.failedInfo.loc[self.failedInfo.InstrumentID == i, 'direction'].values == 'long':
                            if self.openInfo.loc[self.openInfo.InstrumentID == i, 'direction'].values == 1:
                                tempDirection1 = 'cover'
                                tempVolume1 = tempFailedVolume
                                tempKey1 = i + '-' + tempDirection1
                                tempTradingDay1 = tempFailedTradingDay
                                self.tradingOrdersOpen[tempKey1] = {'vtSymbol':i,
                                                          'direction':tempDirection1,
                                                          'volume':tempVolume1,
                                                          'TradingDay':tempTradingDay1}

                                tempDirection2 = 'buy'
                                tempVolume2 = tempOpenVolume
                                tempKey2 = i + '-' + tempDirection2
                                tempTradingDay2 = tempOpenTraingDay
                                self.tradingOrdersOpen[tempKey2] = {'vtSymbol':i,
                                                          'direction':tempDirection2,
                                                          'volume':tempVolume2,
                                                          'TradingDay':tempTradingDay2}
                            elif self.openInfo.loc[self.openInfo.InstrumentID == i, 'direction'].values == -1:
                                if tempDiffVolume > 0:
                                    tempDirection = 'cover'
                                    tempTradingDay = tempFailedTradingDay
                                else:
                                    tempDirection = 'short'
                                    tempTradingDay = tempOpenTraingDay
                                tempKey = i + '-' + tempDirection
                                self.tradingOrdersOpen[tempKey] = {'vtSymbol':i,
                                                          'direction':tempDirection,
                                                          'volume':abs(tempDiffVolume),
                                                          'TradingDay':tempTradingDay}   
                        elif self.failedInfo.loc[self.failedInfo.InstrumentID == i, 'direction'].values == 'short':
                            if self.openInfo.loc[self.openInfo.InstrumentID == i, 'direction'].values == 1:
                                if tempDiffVolume > 0:
                                    tempDirection = 'sell'
                                    tempTradingDay = tempFailedTradingDay
                                else:
                                    tempDirection = 'buy'
                                    tempTradingDay = tempOpenTraingDay
                                tempKey = i + '-' + tempDirection
                                self.tradingOrdersOpen[tempKey] = {'vtSymbol':i,
                                                          'direction':tempDirection,
                                                          'volume':abs(tempDiffVolume),
                                                          'TradingDay':tempTradingDay}
                            elif self.openInfo.loc[self.openInfo.InstrumentID == i, 'direction'].values == -1:
                                tempDirection1 = 'sell'
                                tempVolume1 = tempFailedVolume
                                tempKey1 = i + '-' + tempDirection1
                                tempTradingDay1 = tempFailedTradingDay
                                self.tradingOrdersOpen[tempKey1] = {'vtSymbol':i,
                                                          'direction':tempDirection1,
                                                          'volume':tempVolume1,
                                                          'TradingDay':tempTradingDay1}

                                tempDirection2 = 'short'
                                tempVolume2 = tempOpenVolume
                                tempKey2 = i + '-' + tempDirection2
                                tempTradingDay2 = tempOpenTraingDay
                                self.tradingOrdersOpen[tempKey2] = {'vtSymbol':i,
                                                          'direction':tempDirection2,
                                                          'volume':tempVolume2,
                                                          'TradingDay':tempTradingDay2}

                ## 
                if len(self.y) != 0:
                    for i in self.y:
                        ## direction
                        if self.failedInfo.loc[self.failedInfo.InstrumentID == i, 'direction'].values == 'long':
                            tempDirection = 'cover'
                        elif self.failedInfo.loc[self.failedInfo.InstrumentID == i, 'direction'].values == 'short':
                            tempDirection = 'sell'
                        tempVolume = int(self.failedInfo.loc[self.failedInfo.InstrumentID == i, 'volume'].values)
                        tempKey = i + '-' + tempDirection
                        tempTradingDay = self.failedInfo.loc[self.failedInfo.InstrumentID == i, 'TradingDay'].values[0]
                        self.tradingOrdersOpen[tempKey] = {'vtSymbol':i,
                                                  'direction':tempDirection,
                                                  'volume':tempVolume,
                                                  'TradingDay':tempTradingDay}
                ##
                
                if len(self.z) != 0:
                    for i in self.z:
                        ## -----------------------------------------------------
                        ## direction
                        if self.openInfo.loc[self.openInfo.InstrumentID == i, 'direction'].values == 1:
                            tempDirection = 'buy'
                        elif self.openInfo.loc[self.openInfo.InstrumentID == i, 'direction'].values == -1:
                            tempDirection = 'short'
                        ## -----------------------------------------------------
                        ## volume
                        tempVolume = int(self.openInfo.loc[self.openInfo.InstrumentID == i, 'volume'].values)
                        tempKey = i + '-' + tempDirection
                        tempTradingDay = self.openInfo.loc[self.openInfo.InstrumentID == i, 'TradingDay'].values[0]
                        self.tradingOrdersOpen[tempKey] = {'vtSymbol':i,
                                                  'direction':tempDirection,
                                                  'volume':tempVolume,
                                                  'TradingDay':tempTradingDay}

        # print '#'*80

    ############################################################################
    ## william
    ## 从 MySQL 数据库读取策略持仓信息
    ############################################################################
    def fetchTradingOrders(self):
        """
        提取交易订单
        """
        # pass
        tempOpen = self.ctaEngine.mainEngine.dbMySQLQuery('FL_SimNow',
                            """
                            SELECT *
                            FROM tradingOrders
                            WHERE strategyID = '%s'
                            AND TradingDay = '%s'
                            AND stage = 'open'
                            """ %(self.strategyID,self.ctaEngine.tradingDate))

        if len(tempOpen) != 0:
            for i in range(len(tempOpen)):
                tempKey = tempOpen.at[i,'InstrumentID'] + '-' + tempOpen.at[i,'orderType']
                ## ---------------------------------------------------------------------
                # if tempOpen.at[i,'orderType'] == 'buy':
                #     tempDirection = 'long'
                # elif tempOpen.at[i,'orderType'] == 'short':
                #     tempDirection = 'short'
                ## ---------------------------------------------------------------------
                self.tradingOrdersOpen[tempKey] = {
                    'vtSymbol': tempOpen.at[i,'InstrumentID'],
                    'direction': tempOpen.at[i,'orderType'],
                    'volume':tempOpen.at[i,'volume'],
                    'TradingDay':tempOpen.at[i,'TradingDay']
                }
                self.tickTimer[tempOpen.at[i,'InstrumentID']] = datetime.now()



    ############################################################################
    ## william
    ## 更新状态，需要订阅
    ############################################################################
    def updateTradingStatus(self, event):
        ## =====================================================================
        ## 启动尾盘交易
        ## =====================================================================
        if (datetime.now().hour in [8,20] and  datetime.now().minute >= 58) or \
           (datetime.now().hour in [9,21] and  datetime.now().minute <= 5):
            self.tradingOpen = True
        else:
            self.tradingOpen = False
        ## ---------------------------------------------------------------------
        if datetime.now().hour == 13 and datetime.now().minute >= 39 and \
           (datetime.now().second >= ( 59 - max(20, len(self.tradingOrdersClose)*1.5)) ):
            self.tradingClose = True
        else:
            self.tradingClose = False

        ## =====================================================================
        ## 从 MySQL 数据库提取尾盘需要平仓的持仓信息
        ## postionInfoClose
        ## =====================================================================
        if datetime.now().hour == 13 and datetime.now().minute >= 1 and datetime.now().second == 59:
            ## 持仓合约信息
            self.positionInfoClose = self.ctaEngine.mainEngine.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
                                """
                                SELECT *
                                FROM positionInfo
                                WHERE strategyID = '%s'
                                """ %(self.strategyID))
            if len(self.positionInfoClose) != 0:
                for i in range(len(self.positionInfoClose)):
                    self.tickTimer[self.positionInfoClose.loc[i,'InstrumentID']] = datetime.now()
                    ## ---------------------------------------------------------
                    ## direction
                    if self.positionInfoClose.loc[i,'direction'] == 'long':
                        tempDirection = 'sell'
                    elif self.positionInfoClose.loc[i,'direction'] == 'short':
                        tempDirection = 'cover'
                    else:
                        pass
                    ## ---------------------------------------------------------
                    ## volume
                    tempVolume = int(self.positionInfoClose.loc[i,'volume'])
                    tempKey = self.positionInfoClose.loc[i,'InstrumentID'] + '-' + tempDirection
                    tempTradingDay = self.positionInfoClose.loc[i,'TradingDay']
                    self.tradingOrdersClose[tempKey] = {'vtSymbol':self.positionInfoClose.loc[i,'InstrumentID'],
                                                   'direction':tempDirection,
                                                   'volume':tempVolume,
                                                   'TradingDay':tempTradingDay}
        ## =====================================================================

        ## =====================================================================
        ## 更新订单字典
        ## =====================================================================
        self.updateTradingOrdersDict(tradingOrders = self.tradingOrdersClose, 
                                     tradedOrders  = self.tradedOrdersClose)
