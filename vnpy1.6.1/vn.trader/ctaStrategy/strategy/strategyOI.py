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

        print '#'*80
        print '%s策略启动' %self.name

        print '当日需要执行的订单为:'
        print self.tradingOrdersOpen

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
        self.writeCtaLog(u'%s策略初始化' %self.name)
        print self.vtSymbolList
        print '#'*80
        ########################################################################
        ## william
        self.putEvent()


    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        # tempTick = tick.__dict__
        tempTick = {k:tick.__dict__[k] for k in self.tickFileds}

        ## =====================================================================
        if not self.trading:
            return 
        elif tick.vtSymbol not in [self.tradingOrdersOpen[k]['vtSymbol'] for k in self.tradingOrdersOpen.keys()] + [self.tradingOrdersClose[k]['vtSymbol'] for k in self.tradingOrdersClose.keys()]:
            return 
        elif ((datetime.now() - self.tickTimer[tick.vtSymbol]).seconds <= 5):
            return
        ## =====================================================================
        
        ## ---------------------------------------------------------------------
        self.lastTickData[tick.vtSymbol] = tempTick
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
                try:
                    # conn = self.ctaEngine.mainEngine.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
                    # cursor = conn.cursor()
                    mysqlPositionInfo.to_sql(con=conn, name='positionInfo', if_exists='replace', flavor='mysql', index = False)
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
                 #-------------------------------------------------------------------
                if len(mysqlFailedInfo) != 0:
                    #-------------------------------------------------------------------
                    tempPosInfo = mysqlFailedInfo.loc[mysqlFailedInfo.InstrumentID == self.stratTrade['InstrumentID']][mysqlFailedInfo.direction == self.stratTrade['direction']][mysqlFailedInfo.offset == tempOffset]

                    mysqlFailedInfo.at[tempPosInfo.index[0], 'volume'] -= self.stratTrade['volume']
                    mysqlFailedInfo = mysqlFailedInfo.loc[mysqlFailedInfo.volume != 0]

                    try:
                        # conn = self.ctaEngine.mainEngine.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
                        # cursor = conn.cursor()
                        mysqlFailedInfo.to_sql(con=conn, name='failedInfo', if_exists='replace', flavor='mysql', index = False)
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
                tempPosInfo = self.positionInfoClose.loc[self.positionInfoClose.InstrumentID == tempRes.at[0,'InstrumentID']][self.positionInfoClose.direction == tempDirection]
                tempPosInfo2 = mysqlPositionInfo.loc[mysqlPositionInfo.InstrumentID == tempPosInfo.at[tempPosInfo.index[0],'InstrumentID']][mysqlPositionInfo.TradingDay == tempPosInfo.at[tempPosInfo.index[0],'TradingDay']][mysqlPositionInfo.direction == tempPosInfo.at[tempPosInfo.index[0],'direction']]
                mysqlPositionInfo.at[tempPosInfo2.index[0], 'volume'] -= tempRes.at[0,'volume']
                mysqlPositionInfo = mysqlPositionInfo.loc[mysqlPositionInfo.volume != 0]
                try:
                    # conn = self.ctaEngine.mainEngine.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
                    # cursor = conn.cursor()
                    mysqlPositionInfo.to_sql(con=conn, name='positionInfo', if_exists='replace', flavor='mysql', index = False)
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

    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def updateTradingStatus(self, event):
        ## =====================================================================
        ## 启动尾盘交易
        ## =====================================================================
        if datetime.now().hour in [9,22] and  datetime.now().minute <= 55:
            self.tradingOpen = True
        else:
            self.tradingOpen = False
        ## ---------------------------------------------------------------------
        if datetime.now().hour == 22 and datetime.now().minute == 59 and \
           (datetime.now().second >= ( 59 - max(30, len(self.tradingOrdersClose)*1.5)) ):
            self.tradingClose = True
        else:
            self.tradingClose = False

        ## =====================================================================
        ## 从 MySQL 数据库提取尾盘需要平仓的持仓信息
        ## postionInfoClose
        ## =====================================================================
        if datetime.now().hour == 22 and datetime.now().minute >= 55 and datetime.now().second == 59:
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
        self.updateTradingOrders(tradingOrders = self.tradingOrdersClose, 
                                 tradedOrders  = self.tradedOrdersClose)



        # self.failedOrdersClose = {k:self.tradingOrdersClose[k] for k in self.tradingOrdersClose.keys() if k not in self.tradedOrdersClose.keys()}

        # ## =====================================================================
        # if (self.trading == True and datetime.now().minute % 8 == 0 and datetime.now().second == 59) or (datetime.now().hour in [9,15,21] and datetime.now().minute in [3,5,7,10,15] and datetime.now().second == 59):
        #     ## =====================================================================================
        #     self.ctaEngine.mainEngine.drEngine.getIndicatorInfo(dbName = self.ctaEngine.mainEngine.dataBase,
        #                                                         initCapital = self.ctaEngine.mainEngine.initCapital,
        #                                                         flowCapitalPre = self.ctaEngine.mainEngine.flowCapitalPre,
        #                                                         flowCapitalToday = self.ctaEngine.mainEngine.flowCapitalToday)
        #     ## =====================================================================================
        #     conn = self.ctaEngine.mainEngine.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
        #     cursor = conn.cursor()
        #     tempOrderInfo = self.ctaEngine.mainEngine.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
        #                     """
        #                     SELECT *
        #                     FROM orderInfo
        #                     WHERE strategyID = '%s'
        #                     AND TradingDay = %s
        #                    """ %(self.strategyID, self.ctaEngine.tradingDay))
        #     stratOrderIDList = self.vtOrderIDList + self.vtOrderIDListOpen + self.vtOrderIDListClose + self.vtOrderIDListFailedInfo
        #     tempOrderIDList = [k for k in stratOrderIDList if k not in tempOrderInfo['vtOrderID'].values]

        #     if len(tempOrderIDList) != 0:
        #         ## -------------------------------------------------------------
        #         cursor.execute("""
        #                         DELETE FROM orderInfo
        #                         WHERE strategyID = %s
        #                         AND TradingDay = %s
        #                        """, (self.strategyID, self.ctaEngine.tradingDay))
        #         conn.commit()
        #         ## -------------------------------------------------------------
        #         dfHeader = ['strategyID', 'vtOrderID', 'symbol', 'orderTime', 'status', 'direction', 'cancelTime', 'tradedVolume', 'frontID', 'sessionID', 'offset', 'price', 'totalVolume']
        #         dfData = []
        #         df = pd.DataFrame([], columns = dfHeader)
        #         for i in tempOrderIDList:
        #             df = df.append(self.ctaEngine.mainEngine.getAllOrders().loc[self.ctaEngine.mainEngine.getAllOrders().vtOrderID == i][dfHeader], ignore_index=True)
        #         df = df[dfHeader]
        #         df['TradingDay'] = self.ctaEngine.tradingDate
        #         df['strategyID'] = self.strategyID
        #         df = df[['TradingDay']+dfHeader]
        #         ## 改名字
        #         df.columns.values[3] = 'InstrumentID'
        #         # print df
        #         if len(tempOrderInfo) != 0:
        #             df = df.append(tempOrderInfo, ignore_index=True)
        #         if len(df) != 0:
        #             df.to_sql(con=conn, name='orderInfo', if_exists='append', flavor='mysql', index = False)
        #     conn.close()
        #     ## =====================================================================================
        # ## =====================================================================

        # if (datetime.now().hour == 15) and (datetime.now().minute >= 2) and (datetime.now().second == 59):
        #     ## =====================================================================================
        #     if len(self.failedOrdersClose) != 0:
        #         dfHeader = ['strategyID','InstrumentID','TradingDay','direction','offset','volume']
        #         dfData   = []
        #         ## -------------------------------------------------------------
        #         for k in self.failedOrdersClose.keys():
        #             temp_strategyID = self.strategyID
        #             temp_InstrumentID = self.failedOrdersClose[k]['vtSymbol']
        #             temp_TradingDay = self.failedOrdersClose[k]['TradingDay']

        #             if self.failedOrdersClose[k]['direction'] == 'buy':
        #                 temp_direction = 'long'
        #                 temp_offset    = u'开仓'
        #             elif self.failedOrdersClose[k]['direction'] == 'sell':
        #                 temp_direction = 'short'
        #                 temp_offset    = u'平仓'
        #             elif self.failedOrdersClose[k]['direction'] == 'short':
        #                 temp_direction = 'short'
        #                 temp_offset    = u'开仓'
        #             elif self.failedOrdersClose[k]['direction'] == 'cover':
        #                 temp_direction = 'long'
        #                 temp_offset    = u'平仓'

        #             temp_volume = self.failedOrdersClose[k]['volume']
        #             tempRes = [temp_strategyID, temp_InstrumentID, temp_TradingDay, temp_direction, temp_offset, temp_volume]
        #             dfData.append(tempRes)
        #             df = pd.DataFrame(dfData, columns = dfHeader)
        #         ## -------------------------------------------------------------
        #         conn = self.ctaEngine.mainEngine.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
        #         cursor = conn.cursor()
        #         df.to_sql(con=conn, name='failedInfo', if_exists='replace', flavor='mysql', index = False)
        #         conn.close()
        #         ####################################################################################
        #         ## 记得要从 positionInfo 持仓里面删除
        #         ####################################################################################
        #         for k in self.failedOrdersClose.keys():
        #             if self.failedOrdersClose[k]['direction'] in ['sell', 'cover']:
        #                 if self.failedOrdersClose[k]['direction'] == 'sell':
        #                     tempDirection = 'long'
        #                 elif self.failedOrdersClose[k]['direction'] == 'cover':
        #                     tempDirection = 'short'

        #                 temp_strategyID = self.strategyID
        #                 temp_InstrumentID = self.failedOrdersClose[k]['vtSymbol']
        #                 temp_TradingDay = self.failedOrdersClose[k]['TradingDay']

        #                 ## -------------------------------------------------------------
        #                 try:
        #                     conn = self.ctaEngine.mainEngine.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
        #                     cursor = conn.cursor()
        #                     cursor.execute("""
        #                                     DELETE FROM positionInfo
        #                                     WHERE strategyID = %s
        #                                     AND InstrumentID = %s
        #                                     AND TradingDay = %s
        #                                     AND direction  = %s
        #                                    """, (self.strategyID, temp_InstrumentID, temp_TradingDay, tempDirection))
        #                     conn.commit()
        #                     conn.close()
        #                 except:
        #                     None
        #                 ## -------------------------------------------------------------
        #     ## =====================================================================================

