# encoding: UTF-8
"""
################################################################################
@william

云扬一号
"""
################################################################################
## @william
from __future__ import division
import os
import sys

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
    name         = 'Yun Yang'
    className    = 'YYStrategy'
    strategyID   = className
    author       = 'Lin HuanGeng'
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

        ## =====================================================================
        ## 如果上一个交易日有未完成的订单,需要优先处理
        ## =====================================================================
        if len(self.failedInfo) != 0:
            for i in range(len(self.failedInfo)):
                ## -------------------------------------------------------------
                ## direction
                if self.failedInfo.loc[i,'direction'] == 'long':
                    if self.failedInfo.loc[i,'offset'] == u'开仓':
                        tempDirection = 'buy'
                    elif self.failedInfo.loc[i,'offset'] == u'平仓':
                        tempDirection = 'cover'
                elif self.failedInfo.loc[i,'direction'] == 'short':
                    if self.failedInfo.loc[i,'offset'] == u'开仓':
                        tempDirection = 'short'
                    elif self.failedInfo.loc[i,'offset'] == u'平仓':
                        tempDirection = 'sell'
                ## -------------------------------------------------------------
                ## volume
                tempVolume = self.failedInfo.loc[i,'volume']
                tempKey    = self.failedInfo.loc[i,'InstrumentID'] + '-' + tempDirection
                tempTradingDay = self.failedInfo.loc[i,'TradingDay']
                self.tradingOrdersFailedInfo[tempKey] = {'vtSymbol':self.failedInfo.loc[i,'InstrumentID'],
                                                         'direction':tempDirection,
                                                         'volume':tempVolume,
                                                         'TradingDay':tempTradingDay}

        ## =====================================================================
        ## 1.先计算持仓的信息
        ## =====================================================================
        if len(self.positionInfo) != 0:
            ## -----------------------------------------------------------------
            ## 排除当天已经成交的订单
            ## 如果检测到 TradingDay 是当前交易日,则进行剔除处理
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
            ## -----------------------------------------------------------------

            ## -----------------------------------------------------------------
            ## 计算持仓超过5天的
            for i in range(len(self.positionInfo)):
                tempTradingDay = self.positionInfo.loc[i,'TradingDay']
                tempHoldingDays = self.ctaEngine.ChinaFuturesCalendar[self.ctaEngine.ChinaFuturesCalendar.days.between(tempTradingDay, self.ctaEngine.tradingDate, inclusive = True)].shape[0] - 1
                self.positionInfo.loc[i,'holdingDays'] = tempHoldingDays
            ## -----------------------------------------------------------------
            tempFields = ['strategyID','InstrumentID','TradingDay','direction','volume']
            self.positionInfo = self.positionInfo[self.positionInfo.holdingDays >= 5].reset_index(drop=True)[tempFields]

  

        ## =====================================================================
        ## 2.计算开仓的信息
        ## =====================================================================
        if len(self.positionInfo) == 0:
            ## -----------------------------------------------------------------
            ## 没有 5 天以上的合约, 不进行处理
            ## 只处理 openInfo
            ## -----------------------------------------------------------------
            if len(self.openInfo) != 0:
                for i in range(len(self.openInfo)):
                    ## ---------------------------------------------------------
                    ## direction
                    if self.openInfo.at[i,'direction'] == 1:
                        tempDirection = 'buy'
                    elif self.openInfo.at[i,'direction'] == -1:
                        tempDirection = 'short'
                    else:
                        pass
                    ## ---------------------------------------------------------
                    ## volume
                    tempVolume = int(self.openInfo.at[i,'volume'])
                    tempKey = self.openInfo.at[i,'InstrumentID'] + '-' + tempDirection
                    tempTradingDay = self.openInfo.at[i,'TradingDay']
                    self.tradingOrders[tempKey] = {'vtSymbol':self.openInfo.at[i,'InstrumentID'],
                                                   'direction':tempDirection,
                                                   'volume':tempVolume,
                                                   'TradingDay':tempTradingDay}
            elif (len(self.openInfo) == 0) and (len(self.failedInfo) == 0):
                pass
                # print "\n#######################################################################"
                # print '今天没有需要交易的订单'
                # self.onStop()
                # print '停止策略 %s' %self.name
                # print "#######################################################################\n"
        else:
            ## -----------------------------------------------------------------
            ## 存在 5 天以上的持仓合约, 需要平仓
            ## -----------------------------------------------------------------
            if len(self.openInfo) == 0:
                ## -------------------------------------------------------------
                ## 当天没有开仓信息
                ## 只需要处理持仓超过5天的信息
                ## -------------------------------------------------------------
                for i in range(len(self.positionInfo)):
                    ## ---------------------------------------------------------
                    ## direction
                    if self.positionInfo.at[i,'direction'] == 'long':
                        tempDirection = 'sell'
                    elif self.positionInfo.at[i,'direction'] == 'short':
                        tempDirection = 'cover'
                    else:
                        pass
                    ## ---------------------------------------------------------
                    ## volume
                    tempVolume = int(self.positionInfo.at[i,'volume'])
                    tempKey = self.positionInfo.at[i,'InstrumentID'] + '-' + tempDirection
                    tempTradingDay = self.positionInfo.at[i,'TradingDay']
                    self.tradingOrders[tempKey] = {'vtSymbol':self.positionInfo.at[i,'InstrumentID'],
                                                   'direction':tempDirection,
                                                   'volume':tempVolume,
                                                   'TradingDay':tempTradingDay}
            else:
                ## 如果当天有持仓
                ## 又有开仓
                ## x: 交集
                ## y: positionInfo
                ## z: openInfo
                self.x = list(set(self.positionInfo.InstrumentID.values) & set(self.openInfo.InstrumentID.values))
                self.y = [i for i in self.positionInfo.InstrumentID.values if i not in self.openInfo.InstrumentID.values]
                self.z = [i for i in self.openInfo.InstrumentID.values if i not in self.positionInfo.InstrumentID.values]

                ## =================================================================================
                if len(self.x) != 0:
                    for i in self.x:
                        tempPosVolume = int(self.positionInfo.loc[self.positionInfo.InstrumentID == i, 'volume'].values)
                        tempOpenVolume = int(self.openInfo.loc[self.openInfo.InstrumentID == i, 'volume'].values)
                        tempDiffVolume = tempPosVolume - tempOpenVolume
                        ## direction
                        if self.positionInfo.loc[self.positionInfo.InstrumentID == i, 'direction'].values == 'long':
                            if self.openInfo.loc[self.openInfo.InstrumentID == i, 'direction'].values == 1:
                                ## =================================================================
                                ## 如果是同一个方向的
                                ## =================================================================
                                tempTradingDay = self.positionInfo.loc[self.positionInfo.InstrumentID == i, 'TradingDay'].values[0]
                                ## ---------------------------------------------
                                if tempDiffVolume > 0:
                                    tempDirection = 'sell'
                                    tempTradingDayOpen = tempTradingDay
                                elif tempDiffVolume < 0:
                                    tempDirection = 'buy'
                                    tempTradingDayOpen = self.ctaEngine.tradingDate
                                ## ---------------------------------------------
                                ## =================================================================
                                ## -----------------------------------------------------------------
                                ## 只更新持仓时间, 不进行交易
                                self.updateTradingDay(strategyID = self.strategyID,
                                                      InstrumentID = i,
                                                      oldTradingDay = tempTradingDay,
                                                      newTradingDay = self.ctaEngine.tradingDate,
                                                      direction = 'long',
                                                      volume = min(tempPosVolume, tempOpenVolume))
                                if tempDiffVolume > 0:
                                    tempPositionInfo = self.positionInfo.loc[self.positionInfo.InstrumentID == i]
                                    tempPositionInfo.at[tempPositionInfo.index[0], 'volume'] = tempDiffVolume
                                    conn = self.ctaEngine.mainEngine.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
                                    cursor = conn.cursor()
                                    tempPositionInfo.to_sql(con=conn, name='positionInfo', if_exists='append', flavor='mysql', index = False)
                                    conn.close()
                                ## -----------------------------------------------------------------
                                if tempDiffVolume != 0:
                                    tempVolume = abs(tempDiffVolume)
                                    tempKey = i + '-' + tempDirection
                                    self.tradingOrders[tempKey] = {'vtSymbol':i,
                                                                   'direction':tempDirection,
                                                                   'volume':tempVolume,
                                                                   'TradingDay':tempTradingDayOpen}
                                ## =================================================================
                            ## =====================================================================
                            elif self.openInfo.loc[self.openInfo.InstrumentID == i, 'direction'].values == -1:
                                ## =================================================================
                                ## 如果是不同方向的
                                ## =================================================================
                                ## -----------------------------------------------------------------
                                ## 先进行原来持仓的多头平仓
                                ## -----------------------------------------------------------------
                                tempDirection1  = 'sell'
                                tempVolume1     = int(self.positionInfo.loc[self.positionInfo.InstrumentID == i, 'volume'].values)
                                tempKey1        = i + '-' + tempDirection1
                                tempTradingDay1 = self.positionInfo.loc[self.positionInfo.InstrumentID == i, 'TradingDay'].values[0]

                                ## -----------------------------------------------------------------
                                ## 再进行新的空头开仓
                                ## -----------------------------------------------------------------
                                tempDirection2  = 'short'
                                tempVolume2     = int(self.openInfo.loc[self.openInfo.InstrumentID == i, 'volume'].values)
                                tempKey2        = i + '-' + tempDirection2
                                tempTradingDay2 = self.openInfo.loc[self.openInfo.InstrumentID == i, 'TradingDay'].values[0]

                                self.tradingOrders[tempKey1] = {'vtSymbol':i,
                                                                'direction':tempDirection1,
                                                                'volume':tempVolume1,
                                                                'TradingDay':tempTradingDay1}

                                self.tradingOrders[tempKey2] = {'vtSymbol':i,
                                                                'direction':tempDirection2,
                                                                'volume':tempVolume2,
                                                                'TradingDay':tempTradingDay2}
                            else:
                                pass
                        elif self.positionInfo.loc[self.positionInfo.InstrumentID == i, 'direction'].values == 'short':
                            if self.openInfo.loc[self.openInfo.InstrumentID == i, 'direction'].values == 1:
                                ## -----------------------------------------------------------------
                                ## 先进行原来持仓的空头平仓
                                ## -----------------------------------------------------------------
                                tempDirection1  = 'cover'
                                tempVolume1     = int(self.positionInfo.loc[self.positionInfo.InstrumentID == i, 'volume'].values)
                                tempKey1        = i + '-' + tempDirection1
                                tempTradingDay1 = self.positionInfo.loc[self.positionInfo.InstrumentID == i, 'TradingDay'].values[0]

                                ## -----------------------------------------------------------------
                                ## 再进行新的多头开仓
                                ## -----------------------------------------------------------------
                                tempDirection2  = 'buy'
                                tempVolume2     = int(self.openInfo.loc[self.openInfo.InstrumentID == i, 'volume'].values)
                                tempKey2        = i + '-' + tempDirection2
                                tempTradingDay2 = self.openInfo.loc[self.openInfo.InstrumentID == i, 'TradingDay'].values[0]

                                self.tradingOrders[tempKey1] = {'vtSymbol':i,
                                                                'direction':tempDirection1,
                                                                'volume':tempVolume1,
                                                                'TradingDay':tempTradingDay1}

                                self.tradingOrders[tempKey2] = {'vtSymbol':i,
                                                                'direction':tempDirection2,
                                                                'volume':tempVolume2,
                                                                'TradingDay':tempTradingDay2}

                            elif self.openInfo.loc[self.openInfo.InstrumentID == i, 'direction'].values == -1:
                               ## =================================================================
                                ## 如果是同一个方向的
                                ## =================================================================
                                tempTradingDay = self.positionInfo.loc[self.positionInfo.InstrumentID == i, 'TradingDay'].values[0]
                                ## ---------------------------------------------
                                if tempDiffVolume > 0:
                                    tempDirection = 'cover'
                                    tempTradingDayOpen = tempTradingDay
                                elif tempDiffVolume < 0:
                                    tempDirection = 'short'
                                    tempTradingDayOpen = self.ctaEngine.tradingDate
                                ## ---------------------------------------------
                                ## =================================================================
                                ## -----------------------------------------------------------------
                                ## 只更新持仓时间, 不进行交易
                                self.updateTradingDay(strategyID = self.strategyID,
                                                      InstrumentID = i,
                                                      oldTradingDay = tempTradingDay,
                                                      newTradingDay = self.ctaEngine.tradingDate,
                                                      direction = 'short',
                                                      volume = min(tempPosVolume, tempOpenVolume))
                                ## -----------------------------------------------------------------
                                if tempDiffVolume > 0:
                                    tempPositionInfo = self.positionInfo.loc[self.positionInfo.InstrumentID == i]
                                    tempPositionInfo.at[tempPositionInfo.index[0], 'volume'] = tempDiffVolume
                                    conn = self.ctaEngine.mainEngine.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
                                    cursor = conn.cursor()
                                    tempPositionInfo.to_sql(con=conn, name='positionInfo', if_exists='append', flavor='mysql', index = False)
                                    conn.close()

                                if tempDiffVolume != 0:
                                    tempVolume = abs(tempDiffVolume)
                                    tempKey = i + '-' + tempDirection
                                    self.tradingOrders[tempKey] = {'vtSymbol':i,
                                                                   'direction':tempDirection,
                                                                   'volume':tempVolume,
                                                                   'TradingDay':tempTradingDayOpen}
                                ## =================================================================
                            else:
                                pass
                        else:
                            pass

                ## =================================================================================
                if len(self.y) != 0:
                    for i in self.y:
                        ## -----------------------------------------------------
                        ## direction
                        if self.positionInfo.loc[self.positionInfo.InstrumentID == i, 'direction'].values == 'long':
                            tempDirection = 'sell'
                        elif self.positionInfo.loc[self.positionInfo.InstrumentID == i, 'direction'].values == 'short':
                            tempDirection = 'cover'
                        ## -----------------------------------------------------
                        ## volume
                        tempVolume = int(self.positionInfo.loc[self.positionInfo.InstrumentID == i, 'volume'].values)
                        tempKey = i + '-' + tempDirection
                        tempTradingDay = self.positionInfo.loc[self.positionInfo.InstrumentID == i, 'TradingDay'].values[0]
                        self.tradingOrders[tempKey] = {'vtSymbol':i,
                                                       'direction':tempDirection,
                                                       'volume':tempVolume,
                                                        'TradingDay':tempTradingDay}

                ## =================================================================================
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
                        self.tradingOrders[tempKey] = {'vtSymbol':i,
                                                       'direction':tempDirection,
                                                       'volume':tempVolume,
                                                        'TradingDay':tempTradingDay}

        print '#'*80
        print '%s策略启动' %self.name

        if len(self.failedInfo) != 0:
            print '前一日失败未成交的订单:'
            print self.tradingOrdersFailedInfo
            print '-'*80

        print '当日需要执行的订单为:'
        print self.tradingOrders

        ## ---------------------------------------------------------------------
        ## 当前策略下面的所有合约集合
        self.vtSymbolList = list(set(self.openInfo.InstrumentID.values) |
                                 set(self.failedInfo.InstrumentID.values) |
                                 set(self.positionInfo.InstrumentID.values)
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
        ## =====================================================================
        tempTick = {k:tick.__dict__[k] for k in self.tickFileds}
        # print tempTick
        ## =====================================================================
        
        ## =====================================================================
        if not self.trading:
            return 
        elif tick.vtSymbol not in [self.tradingOrders[k]['vtSymbol'] for k in self.tradingOrders.keys()] + [self.tradingOrdersFailedInfo[k]['vtSymbol'] for k in self.tradingOrdersFailedInfo.keys()] + [self.tradingOrdersClosePositionAll[k]['vtSymbol'] for k in self.tradingOrdersClosePositionAll.keys()] + [self.tradingOrdersClosePositionSymbol[k]['vtSymbol'] for k in self.tradingOrdersClosePositionSymbol.keys()]:
            return 
        elif ((datetime.now() - self.tickTimer[tick.vtSymbol]).seconds <= 4):
            return 
        ## =====================================================================

        ## ---------------------------------------------------------------------
        self.lastTickData[tick.vtSymbol] = tempTick
        self.updateCancelOrders(tick.vtSymbol)
        ## ---------------------------------------------------------------------

        ########################################################################
        ## william
        ## =====================================================================
        if len(self.failedInfo) != 0 and self.trading:
            ####################################################################
            self.prepareTradingOrder(vtSymbol    = tick.vtSymbol, 
                                     orderDict   = self.tradingOrdersFailedInfo, 
                                     orderIDList = self.vtOrderIDListFailedInfo)
        ## =====================================================================


        ## =====================================================================
        if (tick.vtSymbol in [self.tradingOrders[k]['vtSymbol'] for k in self.tradingOrders.keys()] and self.tradingClose):
            ####################################################################
            self.prepareTradingOrder(vtSymbol    = tick.vtSymbol, 
                                     orderDict   = self.tradingOrders, 
                                     orderIDList = self.vtOrderIDList)
        ## =====================================================================

        ############################################################################################
        if tick.symbol in [self.tradingOrdersClosePositionAll[k]['vtSymbol'] for k in self.tradingOrdersClosePositionAll.keys()] and self.tradingClosePositionAll:
            self.prepareTradingOrder(vtSymbol    = tick.vtSymbol, 
                                     orderDict   = self.tradingOrdersClosePositionAll, 
                                     orderIDList = self.vtOrderIDListClosePositionAll)
        ############################################################################################
        if tick.symbol in [self.tradingOrdersClosePositionSymbol[k]['vtSymbol'] for k in self.tradingOrdersClosePositionSymbol.keys()]:
            self.prepareTradingOrder(vtSymbol    = tick.vtSymbol, 
                                     orderDict   = self.tradingOrdersClosePositionSymbol, 
                                     orderIDList = self.vtOrderIDListClosePositionSymbol)
        ############################################################################################
        
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
    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def stratTradeEvent(self, event):
        """
        处理策略交易与持仓信息
        """
        ## =====================================================================
        if event.dict_['data'].vtOrderID not in list(set(self.vtOrderIDList) | 
                                                     set(self.vtOrderIDListFailedInfo) ):
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
        self.stratTrade = event.dict_['data'].__dict__
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


        ## =====================================================================
        ## 1. 修改 orderDict 的数量
        ## =====================================================================
        if self.stratTrade['vtOrderID'] in self.vtOrderIDList:
            # ------------------------------------------------------------------
            self.tradingOrders[tempKey]['volume'] -= self.stratTrade['volume']
            if self.tradingOrders[tempKey]['volume'] == 0:
                self.tradingOrders.pop(tempKey, None)
                self.tradedOrders[tempKey] = tempKey
        elif self.stratTrade['vtOrderID'] in self.vtOrderIDListFailedInfo:
            # ------------------------------------------------------------------
            self.tradingOrdersFailedInfo[tempKey]['volume'] -= self.stratTrade['volume']
            # ------------------------------------------------------------------
            ## 如果是平仓，需要再把当天的 tradingOrders 相关的合约持仓数量做调整
            if (self.stratTrade['offset'] in [u'平仓', u'平昨', u'平今']) and (tempKey in self.tradingOrders.keys()):
                if self.tradingOrders[tempKey]['TradingDay'] == self.tradingOrdersFailedInfo[tempKey]['TradingDay']:
                    self.tradingOrders[tempKey]['volume'] -= self.stratTrade['volume']
                    if self.tradingOrders[tempKey]['volume'] == 0:
                        self.tradingOrders.pop(tempKey, None)
                        self.tradedOrders[tempKey] = tempKey
            # ------------------------------------------------------------------
            # ------------------------------------------------------------------
            tempPosInfo = self.failedInfo.loc[self.failedInfo.InstrumentID == self.stratTrade['vtSymbol']][self.failedInfo.direction == self.stratTrade['direction']][self.failedInfo.offset == tempOffset].reset_index(drop = True)
            self.stratTrade['TradingDay']  = tempPosInfo.at[0, 'TradingDay']
            # ------------------------------------------------------------------

        ## =====================================================================
        ## 2. 更新 positionInfo
        ## =====================================================================
        if self.stratTrade['offset'] == u'开仓':
            ####################################################################
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
                    tempRes.to_sql(con=conn, name='positionInfo', if_exists='append', flavor='mysql', index = False)
                except:
                    print '\n' + '#'*80 
                    print '写入 MySQL 数据库出错'
                    # self.onStop()
                    # print '停止策略 %s' %self.name
                    print '#'*80 + '\n'
            else:
                ## 如果在
                ## 则需要更新数据
                mysqlPositionInfo.at[tempPosInfo.index[0], 'volume'] += tempRes.loc[0,'volume']
                mysqlPositionInfo = mysqlPositionInfo.loc[mysqlPositionInfo.volume != 0]
                try:
                    mysqlPositionInfo.to_sql(con=conn, name='positionInfo', if_exists='replace', flavor='mysql', index = False)
                except:
                    print '\n' + '#'*80 
                    print '写入 MySQL 数据库出错'
                    # self.onStop()
                    # print '停止策略 %s' %self.name
                    print '#'*80 + '\n'
            ## -------------------------------------------------------------
        elif self.stratTrade['offset'] in [u'平仓', u'平昨', u'平今']:
            ################################################################
            if self.stratTrade['direction'] == 'long':
                tempDirection = 'short'
            elif self.stratTrade['direction'] == 'short':
                tempDirection = 'long'
            ## -------------------------------------------------------------
            if self.stratTrade['vtOrderID'] in self.vtOrderIDList:
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
                tempPosInfo2 = mysqlPositionInfo.loc[mysqlPositionInfo.InstrumentID == tempPosInfo.at[tempPosInfo.index[0],'InstrumentID']][mysqlPositionInfo.TradingDay == tempPosInfo.at[tempPosInfo.index[0],'TradingDay']][mysqlPositionInfo.direction == tempPosInfo.at[tempPosInfo.index[0],'direction']]
                mysqlPositionInfo.at[tempPosInfo2.index[0], 'volume'] -= tempRes.at[0,'volume']
                mysqlPositionInfo = mysqlPositionInfo.loc[mysqlPositionInfo.volume != 0]
                try:
                    mysqlPositionInfo.to_sql(con=conn, name='positionInfo', if_exists='replace', flavor='mysql', index = False)
                except:
                    print '\n' + '#'*80 
                    print '写入 MySQL 数据库出错'
                    # self.onStop()
                    # print '停止策略 %s' %self.name
                    print '#'*80 + '\n'
                ## =================================================================================


        #===================================================================
        if self.stratTrade['vtOrderID'] in self.vtOrderIDListFailedInfo:
            ## 更新 tradingOrdersFailedInfo 的数量
            if self.tradingOrdersFailedInfo[tempKey]['volume'] == 0:
                self.tradingOrdersFailedInfo.pop(tempKey, None)
            #-------------------------------------------------------------------
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
                    mysqlFailedInfo.to_sql(con=conn, name='failedInfo', if_exists='replace', flavor='mysql', index = False)
                except:
                    print '\n' + '#'*80 
                    print '写入 MySQL 数据库出错'
                    # self.onStop()
                    # print '停止策略 %s' %self.name
                    print '#'*80 + '\n'
                #-------------------------------------------------------------------
            self.failedInfo = self.ctaEngine.mainEngine.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
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
        tempFields = ['strategyID','vtSymbol','TradingDay','tradeTime','direction','offset','volume','price']
        tempTradingInfo = pd.DataFrame([[self.stratTrade[k] for k in tempFields]], 
            columns = ['strategyID','InstrumentID','TradingDay','tradeTime','direction','offset','volume','price'])
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
        self.ctaEngine.mainEngine.eventEngine.register(EVENT_TRADE, self.stratTradeEvent)
        self.ctaEngine.mainEngine.eventEngine.register(EVENT_TRADE, self.closePositionEvent)
        ## ---------------------------------------------------------------------
        ## 更新交易记录,并写入 mysql
        self.ctaEngine.mainEngine.eventEngine.register(EVENT_TIMER, self.updateTradingStatus)
        ## 收盘发送邮件
        self.ctaEngine.mainEngine.eventEngine.register(EVENT_TIMER, self.sendMail)
        ## ---------------------------------------------------------------------

    #---------------------------------------------------------------------------
    ############################################################################
    ## william
    ## 从 MySQL 数据库读取策略持仓信息

    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def updateTradingStatus(self, event):
        # pass
        ## =====================================================================
        ## 启动尾盘交易
        if datetime.now().hour == 14 and datetime.now().minute >= 59 and \
           (datetime.now().second >= ( 59 - max(10, len(self.tradingOrders)*1.0)) ):
        # if datetime.now().hour == 1 and datetime.now().minute >= 1:
            self.tradingClose = True
        else:
            self.tradingClose = False
        ## =====================================================================

        ## =====================================================================
        ## 更新订单字典
        ## =====================================================================
        self.updateTradingOrders(tradingOrders = self.tradingOrders, 
                                 tradedOrders  = self.tradedOrders)

        # self.failedOrders = {k:self.tradingOrders[k] for k in self.tradingOrders.keys() if k not in self.tradedOrders.keys()}

        # ## =====================================================================
        # if self.trading == True and datetime.now().minute % 14 == 0 and datetime.now().second == 59:
        #     self.ctaEngine.mainEngine.drEngine.getIndicatorInfo(dbName = self.ctaEngine.mainEngine.dataBase,
        #                                                         initCapital = self.ctaEngine.mainEngine.initCapital,
        #                                                         flowCapitalPre = self.ctaEngine.mainEngine.flowCapitalPre,
        #                                                         flowCapitalToday = self.ctaEngine.mainEngine.flowCapitalToday)
        # ## =====================================================================

        # if (datetime.now().hour == 15) and (datetime.now().minute >= 2) and (datetime.now().second == 59):
        #     if len(self.failedOrders) != 0:
        #         dfHeader = ['strategyID','InstrumentID','TradingDay','direction','offset','volume']
        #         dfData   = []
        #         ## -------------------------------------------------------------
        #         for k in self.failedOrders.keys():
        #             temp_strategyID = self.strategyID
        #             temp_InstrumentID = self.failedOrders[k]['vtSymbol']
        #             temp_TradingDay = self.failedOrders[k]['TradingDay']

        #             if self.failedOrders[k]['direction'] == 'buy':
        #                 temp_direction = 'long'
        #                 temp_offset    = u'开仓'
        #             elif self.failedOrders[k]['direction'] == 'sell':
        #                 temp_direction = 'short'
        #                 temp_offset    = u'平仓'
        #             elif self.failedOrders[k]['direction'] == 'short':
        #                 temp_direction = 'short'
        #                 temp_offset    = u'开仓'
        #             elif self.failedOrders[k]['direction'] == 'cover':
        #                 temp_direction = 'long'
        #                 temp_offset    = u'平仓'

        #             temp_volume = self.failedOrders[k]['volume']
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
        #         for k in self.failedOrders.keys():
        #             if self.failedOrders[k]['direction'] in ['sell', 'cover']:
        #                 if self.failedOrders[k]['direction'] == 'sell':
        #                     tempDirection = 'long'
        #                 elif self.failedOrders[k]['direction'] == 'cover':
        #                     tempDirection = 'short'

        #                 temp_strategyID = self.strategyID
        #                 temp_InstrumentID = self.failedOrders[k]['vtSymbol']
        #                 temp_TradingDay = self.failedOrders[k]['TradingDay']

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
