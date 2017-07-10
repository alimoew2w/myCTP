# encoding: UTF-8
"""
################################################################################
@william

云扬一号

################################################################################
"""
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
    ## william
    ############################################################################
    trading        = False                  # 是否启动交易
    sendMailStatus = False                  # 是否已经发送邮件

    ############################################################################
    ## william
    ## vtOrderIDList 是一个 vtOrderID 的集合,只保存当前策略的交易信息
    vtOrderIDList = []                      # 保存委托代码的列表
    vtOrderIDListFailedInfo = []            # 失败的合约订单存储
    ############################################################################

    ############################################################################
    ## william
    ## 用于保存每个合约最后(最新)一条 tick 的数据
    lastTickData = {}                       # 保留最新的价格数据

    ############################################################################
    ## william
    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author']

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading']
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
        self.vtSymbolList = []
        ## ---------------------------------------------------------------------
        ## 计时器, 用于记录单个合约发单的间隔时间
        ## ---------------------------------------------------------------------
        self.tickTimer    = {}

        ## ---------------------------------------------------------------------
        ## tick 处理的字段, 目前只用以下几个
        ## ---------------------------------------------------------------------
        self.tickFileds   = ['symbol', 'vtSymbol', 'lastPrice', 'bidPrice1', 'askPrice1',
                             'bidVolume1', 'askVolume1']
        ## ---------------------------------------------------------------------
        ## 交易订单存放位置
        self.tradingOrders = {}             ## 当日订单, 正常需要处理的
        ## 字典格式如下
        ## 1. vtSymbol
        ## 2. direction: buy, sell, short, cover
        ## 3. volume
        ## 4. TradingDay

        self.tradingOrdersFailedInfo = {}   ## 上一个交易日没有完成的订单,需要优先处理
                                            ##
        self.tradedOrders  = {}             ## 当日订单完成的情况
        self.tradedOrdersFailedInfo  = {}   ## 当日订单完成的情况
                                            ##
        self.failedOrders  = {}             ## 当日未成交订单的统计情况,收盘后写入数据库,failedInfo

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
                    if self.openInfo.loc[i,'direction'] == 1:
                        tempDirection = 'buy'
                    elif self.openInfo.loc[i,'direction'] == -1:
                        tempDirection = 'short'
                    else:
                        pass
                    ## ---------------------------------------------------------
                    ## volume
                    tempVolume = int(self.openInfo.loc[i,'volume'])
                    tempKey = self.openInfo.loc[i,'InstrumentID'] + '-' + tempDirection
                    tempTradingDay = self.openInfo.loc[i,'TradingDay']
                    self.tradingOrders[tempKey] = {'vtSymbol':self.openInfo.loc[i,'InstrumentID'],
                                                   'direction':tempDirection,
                                                   'volume':tempVolume,
                                                   'TradingDay':tempTradingDay}
            elif (len(self.openInfo) == 0) and (len(self.failedInfo) == 0):
                pass
                # print "\n#######################################################################"
                # print u'今天没有需要交易的订单'
                # self.onStop()
                # print u'停止策略 %s' %self.name
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
                    if self.positionInfo.loc[i,'direction'] == 'long':
                        tempDirection = 'sell'
                    elif self.positionInfo.loc[i,'direction'] == 'short':
                        tempDirection = 'cover'
                    else:
                        pass
                    ## ---------------------------------------------------------
                    ## volume
                    tempVolume = int(self.positionInfo.loc[i,'volume'])
                    tempKey = self.positionInfo.loc[i,'InstrumentID'] + '-' + tempDirection
                    tempTradingDay = self.positionInfo.loc[i,'TradingDay']
                    self.tradingOrders[tempKey] = {'vtSymbol':self.positionInfo.loc[i,'InstrumentID'],
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

        print '#################################################################'
        print u'%s策略启动' %self.name

        if len(self.failedInfo) != 0:
            print u'前一日失败未成交的订单:'
            print self.tradingOrdersFailedInfo
            print '-'*65

        print u'当日需要执行的订单为:'
        print self.tradingOrders

        ## ---------------------------------------------------------------------
        ## 当前策略下面的所有合约集合
        self.vtSymbolList = list(set(self.openInfo.InstrumentID.values) |
                                 set(self.failedInfo.InstrumentID.values) |
                                 set(self.positionInfo.InstrumentID.values)
                                )
        for i in self.vtSymbolList:
            self.tickTimer[i] = datetime.now()

        print '#################################################################'
        print u"@william 策略初始化成功 !!!"
        self.writeCtaLog(u'%s策略初始化' %self.name)
        print self.vtSymbolList
        print '#################################################################'

        ########################################################################
        ## william
        self.putEvent()

    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def onStart(self):
        """启动策略（必须由用户继承实现）"""

        ## =====================================================================
        ## 策略启动
        ## =====================================================================
        print '#################################################################'
        print u'%s策略启动' %self.name
        self.writeCtaLog(u'%s策略启动' %self.name)
        self.trading = True
        # if len(self.tradingOrders) == 0 and len(self.tradingOrdersFailedInfo) == 0:
        #     print "\n#################################################################"
        #     print u'今天没有需要交易的订单'
        #     self.onStop()
        #     print u'停止策略 %s' %self.name
        #     print "#################################################################\n"
        self.putEvent()
        print '#################################################################'

    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        print '#################################################################'
        print u'%s策略停止' %self.name
        self.trading = False
        ## ---------------------------------------------------------------------
        ## 取消所有的订单
        for vtOrderID in list(set(self.vtOrderIDList) | set(self.vtOrderIDListFailedInfo)):
            self.cancelOrder(vtOrderID)
        ## ---------------------------------------------------------------------
        print '#################################################################'
        self.writeCtaLog(u'%s策略停止' %self.name)
        self.putEvent()

    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        # tempTick = tick.__dict__
        tempTick = {k:tick.__dict__[k] for k in self.tickFileds}
        tempFailedOrdersSymbol = [self.failedOrders[k]['vtSymbol'] for k in self.failedOrders.keys()]
        ########################################################################
        ## william
        if len(self.failedInfo) != 0 and self.trading:
            if tick.vtSymbol in self.failedInfo.InstrumentID.values and tick.vtSymbol in self.tickTimer.keys():
                self.lastTickData[tick.vtSymbol] = tempTick
                if (datetime.now().second % 2 == 0) and ((datetime.now() - self.tickTimer[tick.vtSymbol]).seconds >= 3):
                    self.processFailedInfo(tick.vtSymbol)

        ## =====================================================================
        ## ---------------------------------------------------------------------
        if datetime.now().hour == 14 and datetime.now().minute >= 10:
        # if datetime.now().hour >= 9:
            # if tick.vtSymbol in self.vtSymbolList:
            if len(self.failedOrders) != 0:
                if tick.vtSymbol in tempFailedOrdersSymbol:
                    self.lastTickData[tick.vtSymbol] = tempTick

        ## =====================================================================

        ## =====================================================================
        ## ---------------------------------------------------------------------
        if datetime.now().hour == 14 and datetime.now().minute >= 59 and (datetime.now().second >= ( 59 - max(10, len(self.tradingOrders)*1.1)) ) and datetime.now().second % 2 == 0 and self.trading:
        # if datetime.now().hour >= 9 and datetime.now().second % 2 == 0 and self.trading:
            ################################################################
            ## william
            ## 存储有 self.lastTickData
            ## 保证有 tick data
            if len(self.failedOrders) != 0:
                if tick.vtSymbol in tempFailedOrdersSymbol:
                    if (datetime.now() - self.tickTimer[tick.vtSymbol]).seconds >= 3:
                        self.prepareTradingOrder(tick.vtSymbol)
                # pass
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

    def processFailedInfo(self, vtSymbol):
        ## =====================================================================
        ## 1. 取消当前的活跃订单
        ## =====================================================================
        self.failedInfoWorkingOrders = []
        # self.failedInfoAllTradedOrders  = []
        # self.failedInfoPartTradedOrders  = []

        for vtOrderID in self.vtOrderIDListFailedInfo:
            ## -----------------------------------------------------------------
            try:
                tempWorkingOrder = self.ctaEngine.mainEngine.getAllOrders()[
                                        (self.ctaEngine.mainEngine.getAllOrders().vtSymbol == vtSymbol) &
                                        (self.ctaEngine.mainEngine.getAllOrders().vtOrderID == vtOrderID ) &
                                        (self.ctaEngine.mainEngine.getAllOrders().status == u'未成交')].vtOrderID.values
            except:
                tempWorkingOrder = None

            if (tempWorkingOrder is not None) and len(tempWorkingOrder) != 0:
                for i in range(len(tempWorkingOrder)):
                    if tempWorkingOrder[i] not in self.failedInfoWorkingOrders:
                        self.failedInfoWorkingOrders.append(tempWorkingOrder[i])

            # ## -----------------------------------------------------------------

        ## =====================================================================
        ## 2. 根据已经成交的订单情况, 重新处理生成新的订单
        ## =====================================================================
        if len(self.failedInfoWorkingOrders) != 0:
            for vtOrderID in self.failedInfoWorkingOrders:
            ####################################################################
                self.cancelOrder(vtOrderID)
                self.tickTimer[vtSymbol]    = datetime.now()
            ####################################################################
        else:
            tempSymbolList = [self.tradingOrdersFailedInfo[k]['vtSymbol'] for k in self.tradingOrdersFailedInfo.keys()]
            tempSymbolList = [i for i in tempSymbolList if i == vtSymbol]

            tempTradingList = [k for k in self.tradingOrdersFailedInfo.keys() if self.tradingOrdersFailedInfo[k]['vtSymbol'] == vtSymbol]

            ####################################################################
            for i in tempTradingList:
                ## -------------------------------------------------------------
                ## 如果交易量依然是大于 0 ，则需要继续发送订单命令
                ## -------------------------------------------------------------
                if self.tradingOrdersFailedInfo[i]['volume'] != 0:
                    self.sendTradingOrder(tradingOrderDict = self.tradingOrdersFailedInfo[i],
                                          my_vtOrderIDList = self.vtOrderIDListFailedInfo)
            ####################################################################

    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def prepareTradingOrder(self, vtSymbol):
        """处理订单"""
        ## =====================================================================
        ## 对订单进行预处理
        ## =====================================================================

        ## =====================================================================
        ## 1. 取消当前的活跃订单
        ## =====================================================================
        ## .....................................................................
        self.vtSymbolWorkingOrders     = []     ## 未成交
        # self.vtSymbolAllTradedOrders   = []     ## 全部成交
        # self.vtSymbolPartTradedOrders  = []     ## 部分成交

        for vtOrderID in self.vtOrderIDList:
            ## -----------------------------------------------------------------
            ## 未成交
            ## -----------------------------------------------------------------
            try:
                tempWorkingOrder = self.ctaEngine.mainEngine.getAllOrders()[
                                        (self.ctaEngine.mainEngine.getAllOrders().vtSymbol == vtSymbol) &
                                        (self.ctaEngine.mainEngine.getAllOrders().vtOrderID == vtOrderID ) &
                                        (self.ctaEngine.mainEngine.getAllOrders().status == u'未成交')].vtOrderID.values
            except:
                tempWorkingOrder = None

            if (tempWorkingOrder is not None) and len(tempWorkingOrder) != 0:
                for i in range(len(tempWorkingOrder)):
                    if tempWorkingOrder[i] not in self.vtSymbolWorkingOrders:
                        self.vtSymbolWorkingOrders.append(tempWorkingOrder[i])
            ## -----------------------------------------------------------------

        ## =====================================================================
        ## 2. 根据已经成交的订单情况, 重新处理生成新的订单
        ## =====================================================================
        if len(self.vtSymbolWorkingOrders) != 0:
            ####################################################################
            ## 如果有未成交的订单，则先取消原来的订单
            ## 因为有可能是价格有变化，原来的报价不适合成交
            ## -----------------------------------------------------------------
            for vtOrderID in self.vtSymbolWorkingOrders:
                self.cancelOrder(vtOrderID)
                self.tickTimer[vtSymbol]    = datetime.now()
            ####################################################################
        elif len(self.vtSymbolWorkingOrders) == 0:
            ####################################################################
            ## 如果没有未成交订单，则进行下面的订单管理操作
            ## -----------------------------------------------------------------
            tempSymbolList = [self.tradingOrders[k]['vtSymbol'] for k in self.tradingOrders.keys()]
            tempSymbolList = [i for i in tempSymbolList if i == vtSymbol]
            ## -----------------------------------------------------------------
            ## 生成交易列表
            tempTradingList = [k for k in self.tradingOrders.keys() if self.tradingOrders[k]['vtSymbol'] == vtSymbol]

            ####################################################################
            for i in tempTradingList:
                ## -------------------------------------------------------------
                ## 如果交易量依然是大于 0 ，则需要继续发送订单命令
                ## -------------------------------------------------------------
                if self.tradingOrders[i]['volume'] != 0:
                    self.sendTradingOrder(tradingOrderDict = self.tradingOrders[i],
                                          my_vtOrderIDList = self.vtOrderIDList)
            ####################################################################

        ## .....................................................................
        self.putEvent()
        ## .....................................................................

    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def sendTradingOrder(self, tradingOrderDict, my_vtOrderIDList):
        """发送单个合约的订单"""
        tempInstrumentID = tradingOrderDict['vtSymbol']
        tempPriceTick    = self.ctaEngine.mainEngine.getContract(tempInstrumentID).priceTick
        tempAskPrice1    = self.lastTickData[tempInstrumentID]['askPrice1']
        tempBidPrice1    = self.lastTickData[tempInstrumentID]['bidPrice1']
        tempDirection    = tradingOrderDict['direction']
        tempVolume       = tradingOrderDict['volume']

        ########################################################################
        if tempDirection == 'buy':
            ## 如果是买入, AskPrice 需要增加一个 priceTick 的滑点
            tempPrice = tempAskPrice1 + tempPriceTick
            vtOrderID = self.buy(vtSymbol = tempInstrumentID, price = tempPrice, volume = tempVolume)
            my_vtOrderIDList.append(vtOrderID)
        elif tempDirection == 'short':
            ## 如果是卖出, BidPrice 需要减少一个 priceTick 的滑点
            tempPrice = tempBidPrice1 - tempPriceTick
            vtOrderID = self.short(vtSymbol = tempInstrumentID, price = tempPrice, volume = tempVolume)
            my_vtOrderIDList.append(vtOrderID)
        elif tempDirection == 'cover':
            ## 如果是买入, AskPrice 需要增加一个 priceTick 的滑点
            tempPrice = tempAskPrice1 + tempPriceTick
            vtOrderID = self.cover(vtSymbol = tempInstrumentID, price = tempPrice, volume = tempVolume)
            my_vtOrderIDList.append(vtOrderID)
        elif tempDirection == 'sell':
            ## 如果是卖出, BidPrice 需要减少一个 priceTick 的滑点
            tempPrice = tempBidPrice1 - tempPriceTick
            vtOrderID = self.sell(vtSymbol = tempInstrumentID, price = tempPrice, volume = tempVolume)
            my_vtOrderIDList.append(vtOrderID)
        else:
            return None
        ########################################################################
        self.tickTimer[tempInstrumentID]    = datetime.now()
        ## .....................................................................
        self.putEvent()
        ## .....................................................................

    ############################################################################
    ## william
    ## 以下用来处理持仓仓位的问题
    ############################################################################
    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def stratTradeEvent(self, event):
        """处理策略交易与持仓信息
        """
        self.stratTrade = event.dict_['data'].__dict__
        self.stratTrade['InstrumentID'] = self.stratTrade['vtSymbol']

        ## =====================================================================
        if self.stratTrade['vtOrderID'] not in list(set(self.vtOrderIDList) | set(self.vtOrderIDListFailedInfo)):
            return
        ## =====================================================================

        ## =================================================================
        ## 1. stratTrade['vtOrderID'] 是唯一标识
        ## =================================================================
        self.stratTrade['strategyID'] = self.strategyID
        # print u"stratTrade.__dict__:====>"
        # # print stratTrade.__dict__
        # print u"stratTrade:==>", stratTrade
        #
        ## -----------------------------------------------------------------
        if self.stratTrade['direction'] == u'多':
            self.stratTrade['direction'] = 'long'
            ## -----------------------------------------------------------------
            if self.stratTrade['offset'] == u'开仓':
                tempKey = self.stratTrade['vtSymbol'] + '-' + 'buy'
            elif self.stratTrade['offset'] == u'平仓':
                tempKey = self.stratTrade['vtSymbol'] + '-' + 'cover'
            ## -----------------------------------------------------------------
        elif self.stratTrade['direction'] == u'空':
            self.stratTrade['direction'] = 'short'
            ## -----------------------------------------------------------------
            if self.stratTrade['offset'] == u'开仓':
                tempKey = self.stratTrade['vtSymbol'] + '-' + 'short'
            elif self.stratTrade['offset'] == u'平仓':
                tempKey = self.stratTrade['vtSymbol'] + '-' + 'sell'
            ## -----------------------------------------------------------------
        ## -----------------------------------------------------------------

        ## -----------------------------------------------------------------
        self.stratTrade['tradeTime']  = datetime.now().strftime('%Y-%m-%d') + " " +  self.stratTrade['tradeTime']
        ## -----------------------------------------------------------------


        ## ---------------------------------------------------------------------
        tempFields = ['strategyID','InstrumentID','TradingDay','direction','volume']
        ## ---------------------------------------------------------------------

        ########################################################################
        ## william
        ## 更新数量
        if self.stratTrade['vtOrderID'] in self.vtOrderIDList:
            self.tradingOrders[tempKey]['volume'] -= self.stratTrade['volume']
            # ------------------------------------------------------------------
            self.stratTrade['TradingDay']  = self.ctaEngine.tradingDate

        elif self.stratTrade['vtOrderID'] in self.vtOrderIDListFailedInfo:
            self.tradingOrdersFailedInfo[tempKey]['volume'] -= self.stratTrade['volume']
            # ------------------------------------------------------------------
            tempPosInfo = self.failedInfo.loc[self.failedInfo.InstrumentID == self.stratTrade['vtSymbol']][self.failedInfo.direction == self.stratTrade['direction']][self.failedInfo.offset == self.stratTrade['offset']].reset_index(drop = True)
            self.stratTrade['TradingDay']  = tempPosInfo.at[0, 'TradingDay']
            # ------------------------------------------------------------------

            ## =================================================================
            ## 2. 更新 positionInfo
            ## =================================================================

        if self.stratTrade['offset'] == u'开仓':
            ################################################################
            ## 1. 更新 self.tradingOrders
            ################################################################
            # if self.stratTrade['vtOrderID'] in self.vtOrderIDList:
            #     ## 更新 self.tradingOrders 的 volume
            #     self.tradingOrders[tempKey]['volume'] -= self.stratTrade['volume']
            # elif self.stratTrade['vtOrderID'] in self.vtOrderIDListFailedInfo:
            #     self.tradingOrdersFailedInfo[tempKey]['volume'] -= self.stratTrade['volume']
            ################################################################
            ## 2. 更新 mysql.positionInfo
            ################################################################                ## 如果是开仓的话,直接添加
            # tempRes = pd.DataFrame([[self.stratTrade[k] for k in tempFields]], columns = ['strategyID','InstrumentID','TradingDay','tradeTime','direction','volume'])
            tempRes = pd.DataFrame([[self.stratTrade[k] for k in tempFields]], columns = tempFields)
            ## -------------------------------------------------------------
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
                    conn = self.ctaEngine.mainEngine.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
                    cursor = conn.cursor()
                    tempRes.to_sql(con=conn, name='positionInfo', if_exists='append', flavor='mysql', index = False)
                    conn.close()
                except:
                    print "\n#######################################################################"
                    print u'写入 MySQL 数据库出错'
                    # self.onStop()
                    # print u'停止策略 %s' %self.name
                    print "#######################################################################\n"
            else:
                ## 如果在
                ## 则需要更新数据
                mysqlPositionInfo.at[tempPosInfo.index[0], 'volume'] += tempRes.loc[0,'volume']
                mysqlPositionInfo = mysqlPositionInfo.loc[mysqlPositionInfo.volume != 0]
                try:
                    conn = self.ctaEngine.mainEngine.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
                    cursor = conn.cursor()
                    mysqlPositionInfo.to_sql(con=conn, name='positionInfo', if_exists='replace', flavor='mysql', index = False)
                    conn.close()
                except:
                    print "\n#######################################################################"
                    print u'写入 MySQL 数据库出错'
                    # self.onStop()
                    # print u'停止策略 %s' %self.name
                    print "#######################################################################\n"
            ## -------------------------------------------------------------
        elif self.stratTrade['offset'] in [u'平仓', u'平昨', u'平今']:
            ## -------------------------------------------------------------
            ## 1. 获取平仓的信息
            ## -------------------------------------------------------------
            # if self.stratTrade['vtOrderID'] in self.vtOrderIDList:
            #     tempPositionInfo = self.positionInfo[self.positionInfo.InstrumentID == self.stratTrade['InstrumentID']]
            # elif self.stratTrade['vtOrderID'] in self.vtOrderIDListFailedInfo:
            #     tempPositionInfo = self.failedInfo[self.failedInfo.InstrumentID == self.stratTrade['InstrumentID']]

            ################################################################
            ## 1. 更新 self.tradingOrders
            ################################################################

            # if self.stratTrade['vtOrderID'] in self.vtOrderIDList:
            #     ## 更新 self.tradingOrders 的 volume
            #     self.tradingOrders[tempKey]['volume'] -= self.stratTrade['volume']
            # elif self.stratTrade['vtOrderID'] in self.vtOrderIDListFailedInfo:
            #     self.tradingOrdersFailedInfo[tempKey]['volume'] -= self.stratTrade['volume']

            ################################################################
            ## 2. 更新 mysql.positionInfo
            ################################################################
            tempRes = pd.DataFrame([[self.stratTrade[k] for k in tempFields]], columns = tempFields)
            if self.stratTrade['direction'] == 'long':
                tempDirection = 'short'
            elif self.stratTrade['direction'] == 'short':
                tempDirection = 'long'
            ## -------------------------------------------------------------
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
                conn = self.ctaEngine.mainEngine.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
                cursor = conn.cursor()
                mysqlPositionInfo.to_sql(con=conn, name='positionInfo', if_exists='replace', flavor='mysql', index = False)
                conn.close()
            except:
                print "\n#######################################################################"
                print u'写入 MySQL 数据库出错'
                # self.onStop()
                # print u'停止策略 %s' %self.name
                print "#######################################################################\n"

        else:
            pass

        #===================================================================
        if self.stratTrade['vtOrderID'] in self.vtOrderIDListFailedInfo:
            ## 更新 tradingOrdersFailedInfo 的数量
            if self.tradingOrdersFailedInfo[tempKey]['volume'] == 0:
                self.tradingOrdersFailedInfo.pop(tempKey, None)
            #-------------------------------------------------------------------
            mysqlFailInfo = self.ctaEngine.mainEngine.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
                    """
                    SELECT *
                    FROM failedInfo
                    WHERE strategyID = '%s'
                    """ %(self.strategyID))
            #-------------------------------------------------------------------

            tempPosInfo = mysqlFailInfo.loc[mysqlFailInfo.InstrumentID == self.stratTrade['InstrumentID']][mysqlFailInfo.direction == self.stratTrade['direction']][mysqlFailInfo.offset == self.stratTrade['offset']]

            mysqlFailInfo.at[tempPosInfo.index[0], 'volume'] -= self.stratTrade['volume']
            mysqlFailInfo = mysqlFailInfo.loc[mysqlFailInfo.volume != 0]

            try:
                conn = self.ctaEngine.mainEngine.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
                cursor = conn.cursor()
                mysqlFailInfo.to_sql(con=conn, name='failedInfo', if_exists='replace', flavor='mysql', index = False)
                conn.close()
            except:
                print "\n#######################################################################"
                print u'写入 MySQL 数据库出错'
                # self.onStop()
                # print u'停止策略 %s' %self.name
                print "#######################################################################\n"
            #-------------------------------------------------------------------
            self.failedInfo = self.ctaEngine.mainEngine.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
                    """
                    SELECT *
                    FROM failedInfo
                    WHERE strategyID = '%s'
                    """ %(self.strategyID))
        #-------------------------------------------------------------------
        #===================================================================

        tempFields = ['strategyID','vtSymbol','TradingDay','tradeTime','direction','offset','volume','price']
        tempTradingInfo = pd.DataFrame([[self.stratTrade[k] for k in tempFields]], columns = ['strategyID','InstrumentID','TradingDay','tradeTime','direction','offset','volume','price'])
        ## -----------------------------------------------------------------
        self.updateTradingInfo(tempTradingInfo)
        self.tradingInfo = self.tradingInfo.append(tempTradingInfo, ignore_index=True)
        ## -----------------------------------------------------------------

        ## =================================================================
        ## 3. 更新 self.tradingOrders
        ## =================================================================
        if len(self.tradingOrders) != 0:
            for k in self.tradingOrders.keys():
                if self.tradingOrders[k]['volume'] == 0:
                    self.tradedOrders[k] = k
                    self.tradingOrders.pop(k, None)

        # ######################################################################
        # 发出状态更新事件
        self.putEvent()

    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def registerEvent(self):
        """注册事件监听"""
        self.ctaEngine.mainEngine.eventEngine.register(EVENT_TRADE, self.stratTradeEvent)
        ## ---------------------------------------------------------------------
        ## 更新交易记录,并写入 mysql
        self.ctaEngine.mainEngine.eventEngine.register(EVENT_TIMER, self.updateTradingOrders)
        ## ---------------------------------------------------------------------
        ## 收盘发送邮件
        self.ctaEngine.mainEngine.eventEngine.register(EVENT_TIMER, self.sendMail)
        ## ---------------------------------------------------------------------

    #---------------------------------------------------------------------------
    ############################################################################
    ## william
    ## 从 MySQL 数据库读取策略持仓信息

    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def updateTradingInfo(self, df):
        """更新交易记录"""
        conn = self.ctaEngine.mainEngine.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
        cursor = conn.cursor()
        df.to_sql(con=conn, name='tradingInfo', if_exists='append', flavor='mysql', index = False)
        conn.close()

    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def updateTradingDay(self, strategyID, InstrumentID, oldTradingDay, newTradingDay, direction, volume):
        """更新交易日历"""
        conn = self.ctaEngine.mainEngine.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
        cursor = conn.cursor()
        cursor.execute("""
                        UPDATE positionInfo
                        SET TradingDay = %s, volume = %s
                        WHERE strategyID = %s
                        AND InstrumentID = %s
                        AND TradingDay = %s
                        AND direction = %s
                       """, (newTradingDay, volume, strategyID,
                             InstrumentID, oldTradingDay, direction))
        conn.commit()
        conn.close()

    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def updateTradingOrders(self, event):
        # pass
        # if 15 < datetime.now().hour < 17:
        #     self.failedOrders = {k:self.tradingOrders[k] for k in self.tradingOrders.keys() if k not in self.tradedOrders.keys()}
        self.failedOrders = {k:self.tradingOrders[k] for k in self.tradingOrders.keys() if k not in self.tradedOrders.keys()}

        ## =====================================================================
        if self.trading == True and datetime.now().minute % 14 == 0 and datetime.now().second == 59:
            self.ctaEngine.mainEngine.drEngine.getIndicatorInfo(dbName = self.ctaEngine.mainEngine.dataBase,
                                                                initCapital = self.ctaEngine.mainEngine.initCapital)
        ## =====================================================================

        if (datetime.now().hour == 15) and (datetime.now().minute >= 2) and (datetime.now().second == 59):
            if len(self.failedOrders) != 0:
                dfHeader = ['strategyID','InstrumentID','TradingDay','direction','offset','volume']
                dfData   = []
                ## -------------------------------------------------------------
                for k in self.failedOrders.keys():
                    temp_strategyID = self.strategyID
                    temp_InstrumentID = self.failedOrders[k]['vtSymbol']
                    temp_TradingDay = self.failedOrders[k]['TradingDay']

                    if self.failedOrders[k]['direction'] == 'buy':
                        temp_direction = 'long'
                        temp_offset    = u'开仓'
                    elif self.failedOrders[k]['direction'] == 'sell':
                        temp_direction = 'short'
                        temp_offset    = u'平仓'
                    elif self.failedOrders[k]['direction'] == 'short':
                        temp_direction = 'short'
                        temp_offset    = u'开仓'
                    elif self.failedOrders[k]['direction'] == 'cover':
                        temp_direction = 'long'
                        temp_offset    = u'平仓'

                    temp_volume = self.failedOrders[k]['volume']
                    tempRes = [temp_strategyID, temp_InstrumentID, temp_TradingDay, temp_direction, temp_offset, temp_volume]
                    dfData.append(tempRes)
                    df = pd.DataFrame(dfData, columns = dfHeader)
                ## -------------------------------------------------------------
                conn = self.ctaEngine.mainEngine.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
                cursor = conn.cursor()
                df.to_sql(con=conn, name='failedInfo', if_exists='replace', flavor='mysql', index = False)
                conn.close()
                ####################################################################################
                ## 记得要从 positionInfo 持仓里面删除
                ####################################################################################
                for k in self.failedOrders.keys():
                    if self.failedOrders[k]['direction'] in ['sell', 'cover']:
                        if self.failedOrders[k]['direction'] == 'sell':
                            tempDirection = 'long'
                        elif self.failedOrders[k]['direction'] == 'cover':
                            tempDirection = 'short'

                        temp_strategyID = self.strategyID
                        temp_InstrumentID = self.failedOrders[k]['vtSymbol']
                        temp_TradingDay = self.failedOrders[k]['TradingDay']

                        ## -------------------------------------------------------------
                        try:
                            conn = self.ctaEngine.mainEngine.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
                            cursor = conn.cursor()
                            cursor.execute("""
                                            DELETE FROM positionInfo
                                            WHERE strategyID = %s
                                            AND InstrumentID = %s
                                            AND TradingDay = %s
                                            AND direction  = %s
                                           """, (self.strategyID, temp_InstrumentID, temp_TradingDay, tempDirection))
                            conn.commit()
                            conn.close()
                        except:
                            None
                        ## -------------------------------------------------------------


    def sendMail(self, event):
        """发送邮件通知给：汉云交易员"""
        if (datetime.now().hour == 15) and (datetime.now().minute == 3) and (datetime.now().second == 59) and self.trading:
            self.sendMailStatus = True
        ## -----------  ----------------------------------------------------------
        if self.sendMailStatus and self.trading:
            self.sendMailStatus = False
            ## -----------------------------------------------------------------
            ## -----------------------------------------------------------------
            self.ctaEngine.mainEngine.drEngine.getIndicatorInfo(dbName = self.ctaEngine.mainEngine.dataBase,
                                                                initCapital = self.ctaEngine.mainEngine.initCapital)
            ## -----------------------------------------------------------------
            ## -----------------------------------------------------------------------------
            sender = self.strategyID + '@hicloud.com'
            receivers = self.ctaEngine.mainEngine.mailReceiver
            ccReceivers = self.ctaEngine.mainEngine.mailCC
            ## -----------------------------------------------------------------------------

            ## -----------------------------------------------------------------------------
            # 三个参数：第一个为文本内容，第二个 plain 设置文本格式，第三个 utf-8 设置编码
            ## 内容，例如
            # message = MIMEText('Python 邮件发送测试...', 'plain', 'utf-8')
            ## -----------------------------------------------------------------------------
            with codecs.open("/tmp/tradingRecord.txt", "w", "utf-8") as f:
                # f.write('{0}'.format(40*'='))
                f.write('{0}'.format('\n' + 20 * '#'))
                f.write('{0}'.format(u'\n## 策略信息'))
                f.write('{0}'.format('\n' + 20 * '#'))
                f.write('{0}'.format('\n[TradingDay]: ' + self.ctaEngine.tradingDate.strftime('%Y-%m-%d')))
                f.write('{0}'.format('\n[UpdateTime]: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                f.write('{0}'.format('\n[StrategyID]: ' + self.strategyID))
                f.write('{0}'.format('\n[TraderName]: ' + self.author))
                f.write('{0}'.format('\n' + 120*'-' + '\n'))
                ## -------------------------------------------------------------------------
                f.write('{0}'.format('\n' + 20 * '#'))
                f.write('{0}'.format(u'\n## 基金净值'))
                f.write('{0}'.format('\n' + 20 * '#'))
                f.write('{0}'.format('\n' + 120*'-') + '\n')
                f.write('{0}'.format(self.ctaEngine.mainEngine.drEngine.accountBalance))
                f.write('{0}'.format('\n' + 120*'-') + '\n')
                ## -------------------------------------------------------------------------
                f.write('{0}'.format('\n' + 20 * '#'))
                f.write('{0}'.format(u'\n## 基金持仓'))
                f.write('{0}'.format('\n' + 20 * '#'))
                f.write('{0}'.format('\n' + 120*'-') + '\n')
                f.write('{0}'.format(self.ctaEngine.mainEngine.drEngine.accountPosition))
                f.write('{0}'.format('\n' + 120*'-') + '\n')
                ## -------------------------------------------------------------------------
                f.write('{0}'.format('\n' + 20 * '#'))
                f.write('{0}'.format('\n## 当日已交易'))
                f.write('{0}'.format('\n' + 20 * '#'))
                f.write('{0}'.format('\n' + 120*'-') + '\n')
                if len(self.tradingInfo) != 0:
                    tempTradingInfo = self.tradingInfo
                    tempTradingInfo.index += 1
                    f.write('{0}'.format(tempTradingInfo))
                f.write('{0}'.format('\n' + 120*'-') + '\n')
                ## -------------------------------------------------------------------------
                f.write('{0}'.format('\n' + 20 * '#'))
                f.write('{0}'.format('\n## 当日未交易'))
                f.write('{0}'.format('\n' + 20 * '#'))
                f.write('{0}'.format('\n' + 120*'-') + '\n')
                if len(self.failedOrders) != 0:
                    f.write('{0}'.format(pd.DataFrame(self.failedOrders).transpose()))
                f.write('{0}'.format('\n' + 120*'-') + '\n')


            ## -----------------------------------------------------------------------------
            # message = MIMEText(stratYY.strategyID, 'plain', 'utf-8')
            fp = open("/tmp/tradingRecord.txt", "r")
            message = MIMEText(fp.read().decode('string-escape').decode("utf-8"), 'plain', 'utf-8')
            fp.close()

            ## 显示:发件人
            message['From'] = Header(sender, 'utf-8')
            ## 显示:收件人
            message['To'] =  Header('汉云交易员', 'utf-8')

            ## 主题
            subject = self.ctaEngine.tradingDay + u'：云扬1号交易播报'
            message['Subject'] = Header(subject, 'utf-8')

            try:
                smtpObj = smtplib.SMTP('localhost')
                smtpObj.sendmail(sender, receivers+ccReceivers, message.as_string())
                print "邮件发送成功"
            except smtplib.SMTPException:
                print "Error: 无法发送邮件"
            ## 间隔 1 秒
            time.sleep(1)
