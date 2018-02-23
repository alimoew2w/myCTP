# encoding: UTF-8

"""
YYStrategy 策略的交易实现
＠william
"""
from __future__ import division
import os,sys,subprocess

from vnpy.trader.vtObject import VtBarData
from vnpy.trader.vtConstant import EMPTY_STRING
from vnpy.trader.app.ctaStrategy.ctaTemplate import (CtaTemplate, 
                                                     BarManager, 
                                                     ArrayManager)
from vnpy.trader.vtEvent import *
from vnpy.trader import vtFunction
## -----------------------------------------------------------------------------
from logging import INFO, ERROR
import pandas as pd
from pandas.io import sql

from datetime import *
import time
import pprint
from copy import copy
import re,ast,json
## -----------------------------------------------------------------------------


########################################################################
class YYStrategy(CtaTemplate):
    """ oiRank 交易策略 """
    ############################################################################
    ## william
    ## 策略类的名称和作者
    ## -------------------------------------------------------------------------
    name         = u'YunYang'
    className    = u'YYStrategy'
    strategyID   = className
    author       = u'Lin HuanGeng'
    ############################################################################
    
    ## =========================================================================
    ## william
    ## 以下是我的修改
    ############################################################################
    ## -------------------------------------------------------------------------
    ## 各种控制条件
    ## 策略的基本变量，由引擎管理
    trading      = False                    # 是否启动交易，由引擎管理
    tradingStart = False                    # 开盘启动交易
    tradingEnd   = False                    # 收盘开启交易
    tickTimer    = {}                  # 计时器, 用于记录单个合约发单的间隔时间
    ## -------------------------------------------------------------------------

    ## -------------------------------------------------------------------------
    ## 各种交易订单的合成
    ## 交易订单存放位置
    ## 字典格式如下
    ## 1. vtSymbol
    ## 2. direction: buy, sell, short, cover
    ## 3. volume
    ## 4. TradingDay
    ## 5. vtOrderIDList
    ## -------------------------------------------------------------------------
    tradingOrders           = {}       # 单日的订单
    tradingOrdersOpen       = {}       # 当日开盘的订单
    tradingOrdersClose      = {}       # 当日收盘的订单
    tradingOrdersUpperLower = {}       # 以涨跌停价格的订单
    tradingOrdersFailedInfo = {}       # 上一个交易日没有完成的订单,需要优先处理
    ## -------------------------------------------------------------------------
    tradedOrders            = {}       # 当日订单完成的情况
    tradedOrdersOpen        = {}       # 当日开盘完成的已订单
    tradedOrdersClose       = {}       # 当日收盘完成的已订单
    tradedOrdersFailedInfo  = {}       # 昨天未成交订单的已交易订单
    tradedOrdersUpperLower  = {}       # 已经成交的涨跌停订单
    ## -------------------------------------------------------------------------

    ## -------------------------------------------------------------------------
    ## 各种交易订单的合成
    ## -------------------------------------------------------------------------
    vtOrderIDList           = []       # 保存委托代码的列表
    vtOrderIDListOpen       = []       # 开盘的订单
    vtOrderIDListClose      = []       # 收盘的订单
    vtOrderIDListFailedInfo = []       # 失败的合约订单存储
    vtOrderIDListUpperLower = []       # 涨跌停价格成交的订单
    vtOrderIDListAll        = []       # 所有订单集合
    ## -------------------------------------------------------------------------

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        ## 从　ctaEngine 继承所有属性和方法
        super(YYStrategy, self).__init__(ctaEngine, setting)

        ## =====================================================================
        ## 交易时点
        self.tradingCloseHour    = 14
        self.tradingCloseMinute1 = 50
        self.tradingCloseMinute2 = 59
        ## =====================================================================

        ## ===================================================================== 
        ## william
        # 注意策略类中的可变对象属性（通常是list和dict等），在策略初始化时需要重新创建，
        # 否则会出现多个策略实例之间数据共享的情况，有可能导致潜在的策略逻辑错误风险，
        # 策略类中的这些可变对象属性可以选择不写，全都放在__init__下面，写主要是为了阅读
        # 策略时方便（更多是个编程习惯的选择） 
        # 
        ## ===================================================================== 

        ## =====================================================================
        ## 上一个交易日未成交订单
        self.failedInfo = vtFunction.dbMySQLQuery(
            self.ctaEngine.mainEngine.dataBase,
            """
            SELECT *
            FROM failedInfo
            WHERE strategyID = '%s'
            """ %(self.strategyID))
        self.processFailedInfo(self.failedInfo)

        ## ---------------------------------------------------------------------
        ## 查看当日已经交易的订单
        ## ---------------------------------------------------------------------
        self.tradingInfo = vtFunction.dbMySQLQuery(
            self.ctaEngine.mainEngine.dataBase,
            """
            SELECT *
            FROM tradingInfo
            WHERE strategyID = '%s'
            AND TradingDay = '%s'
            """ %(self.strategyID, self.ctaEngine.tradingDay))
        
        ########################################################################
        ## william
        # 注册事件监听
        self.registerEvent()
        ########################################################################

    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略初始化' %self.name)
        ## =====================================================================
        if self.ctaEngine.mainEngine.multiStrategy:
            ## -----------------------------------------------------------------
            self.tradingOrdersOpen = self.fetchTradingOrders(stage = 'open')
            self.updateTradingOrdersVtOrderID(tradingOrders = self.tradingOrdersOpen,
                                              stage = 'open')
            self.updateVtOrderIDList('open')
            ## -----------------------------------------------------------------
            self.tradingOrdersClose = self.fetchTradingOrders(stage = 'close')
            self.updateTradingOrdersVtOrderID(tradingOrders = self.tradingOrdersClose,
                                              stage = 'close')
            self.updateVtOrderIDList('close')
        else:
            pass
        ## =====================================================================

        ## ---------------------------------------------------------------------
        if self.tradingOrdersFailedInfo:
            self.writeCtaLog("昨日失败需要执行的订单\n%s\n%s\n%s" 
                %('-'*80,
                  pprint.pformat(self.tradingOrdersFailedInfo),
                  '-'*80))
        if self.tradingOrdersOpen:
            self.writeCtaLog("当日需要执行的开仓订单\n%s\n%s\n%s" 
                %('-'*80,
                  pprint.pformat(self.tradingOrdersOpen),
                  '-'*80))
        if self.tradingOrdersClose:
            self.writeCtaLog("当日需要执行的平仓订单\n%s\n%s\n%s" 
                %('-'*80,
                  pprint.pformat(self.tradingOrdersClose),
                  '-'*80))

        ## ---------------------------------------------------------------------
        try:
            self.positionContracts = self.ctaEngine.mainEngine.dataEngine.positionInfo.keys()
        except:
            self.positionContracts = []
        tempSymbolList = list(set(self.tradingOrdersOpen[k]['vtSymbol'] 
                                       for k in self.tradingOrdersOpen.keys()) | 
                              set(self.ctaEngine.allContracts) |
                              set(self.positionContracts))
        for symbol in tempSymbolList:
            if symbol not in self.tickTimer.keys():
                self.tickTimer[symbol] = datetime.now()
        ## =====================================================================
        self.updateTradingStatus()
        self.putEvent()
        ## =====================================================================

    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""

        ## =====================================================================
        # print tick.__dict__
        if not self.trading:
            return 
        elif tick.datetime <= (datetime.now() - timedelta(seconds=30)):
            return
        elif tick.vtSymbol not in [self.tradingOrdersOpen[k]['vtSymbol'] for k in self.tradingOrdersOpen.keys()] + \
        [self.tradingOrdersClose[k]['vtSymbol'] for k in self.tradingOrdersClose.keys()] + \
        [self.tradingOrdersFailedInfo[k]['vtSymbol'] for k in self.tradingOrdersFailedInfo.keys()]:
            return 
        elif ((datetime.now() - self.tickTimer[tick.vtSymbol]).seconds <= 1):
            return
        # =====================================================================

        ########################################################################
        ## william
        ## =====================================================================
        if self.tradingOrdersFailedInfo and self.tradingStart:
            self.prepareTradingOrder(vtSymbol      = tick.vtSymbol, 
                                     tradingOrders = self.tradingOrdersFailedInfo, 
                                     orderIDList   = self.vtOrderIDListFailedInfo,
                                     priceType     = 'chasing')
        ## =====================================================================

        ## =====================================================================
        if (tick.vtSymbol in [self.tradingOrdersOpen[k]['vtSymbol'] 
                             for k in self.tradingOrdersOpen.keys()]):
            if (self.tradingStart and not self.tradingEnd):
                tempPriceType = 'open'
                tempDiscount  = self.ctaEngine.mainEngine.openDiscountYY
                tempAddTick   = self.ctaEngine.mainEngine.openAddTickYY
            elif self.tradingBetween:
                tempPriceType = 'last'
                tempDiscount  = 0
                tempAddTick   = 0
            elif self.tradingEnd:
                tempPriceType = 'chasing'
                tempDiscount  = 0
                tempAddTick   = 1
            else:
                return
            ####################################################################
            self.prepareTradingOrder(vtSymbol      = tick.vtSymbol, 
                                     tradingOrders = self.tradingOrdersOpen, 
                                     orderIDList   = self.vtOrderIDListOpen,
                                     priceType     = tempPriceType,
                                     discount      = tempDiscount,
                                     addTick       = tempAddTick)
        ## =====================================================================


        ## =====================================================================
        if (tick.vtSymbol in [self.tradingOrdersClose[k]['vtSymbol'] 
                             for k in self.tradingOrdersClose.keys()]):
            if (self.tradingStart and not self.tradingEnd):
                tempPriceType = 'open'
                tempDiscount  = self.ctaEngine.mainEngine.closeDiscountYY
                tempAddTick   = self.ctaEngine.mainEngine.closeAddTickYY
            elif self.tradingBetween:
                tempPriceType = 'last'
                tempDiscount  = 0
                tempAddTick   = 0
            elif self.tradingEnd:
                tempPriceType = 'chasing'
                tempDiscount  = 0
                tempAddTick   = 1
            else:
                return
            ####################################################################
            self.prepareTradingOrder(vtSymbol      = tick.vtSymbol, 
                                     tradingOrders = self.tradingOrdersClose, 
                                     orderIDList   = self.vtOrderIDListClose,
                                     priceType     = tempPriceType,
                                     discount      = tempDiscount,
                                     addTick       = tempAddTick)
        ## =====================================================================



    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        """处理成交订单"""
        self.tickTimer[trade.vtSymbol] = datetime.now()
        ## ---------------------------------------------------------------------

        ## =====================================================================
        ## 0. 数据预处理
        ## =====================================================================
        self.stratTrade = copy(trade.__dict__)
        self.stratTrade['InstrumentID'] = self.stratTrade['vtSymbol']
        self.stratTrade['strategyID']   = self.strategyID
        self.stratTrade['tradeTime']    = datetime.now().strftime('%Y-%m-%d') + " " + self.stratTrade['tradeTime']
        self.stratTrade['TradingDay']   = self.ctaEngine.tradingDate

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

        ## ---------------------------------------------------------------------
        tempKey = self.stratTrade['vtSymbol'] + '-' + tempDirection
        ## ---------------------------------------------------------------------

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
        elif self.stratTrade['vtOrderID'] in self.vtOrderIDListFailedInfo:
            # ------------------------------------------------------------------
            self.tradingOrdersFailedInfo[tempKey]['volume'] -= self.stratTrade['volume']
            if self.tradingOrdersFailedInfo[tempKey]['volume'] == 0:
                self.tradingOrdersFailedInfo.pop(tempKey, None)
            # ------------------------------------------------------------------
            ## 需要更新一下 failedInfo
            self.stratTrade['TradingDay'] = self.ctaEngine.lastTradingDate
            self.processTradingOrdersFailedInfo(self.stratTrade)

        ## =====================================================================
        ## 2. 更新 positionInfo
        ## =====================================================================
        if self.stratTrade['offset'] == u'开仓':
            ## ------------------------------------
            ## 处理开仓的交易订单            
            self.processOffsetOpen(self.stratTrade)
            ## ------------------------------------
        elif self.stratTrade['offset'] in [u'平仓', u'平昨', u'平今']:
            ## -----------------------------------------------------------------
            ## 平仓只有在以下两个情况才处理
            ## 因为 failedInfo 已经预先处理过了
            if self.stratTrade['vtOrderID'] in self.vtOrderIDListClose:
                self.processOffsetClose(self.stratTrade)
            ## -----------------------------------------------------------------

        ## ---------------------------------------------------------------------
        tempTradingInfo = pd.DataFrame([[self.stratTrade[k] for k in self.tradingInfoFields]], 
            columns = self.tradingInfoFields)
        # self.updateTradingInfo(df = tempTradingInfo, tbName = 'tradingInfo')
        self.updateTradingInfo(df = tempTradingInfo)
        self.tradingInfo = self.tradingInfo.append(tempTradingInfo, ignore_index=True)
        ## ---------------------------------------------------------------------

        ########################################################################
        ## 处理 MySQL 数据库的 tradingOrders
        ## 如果成交了，需要从这里面再删除交易订单
        ########################################################################
        if (trade.vtOrderID in list(set(self.vtOrderIDListOpen) | 
                                    set(self.vtOrderIDListClose)) and 
            self.ctaEngine.mainEngine.multiStrategy):
            self.updateTradingOrdersTable(self.stratTrade)
        ########################################################################

        ## =====================================================================
        # 发出状态更新事件
        self.putEvent()
        ## =====================================================================


    ############################################################################
    ## william
    ## 更新状态，需要订阅
    ############################################################################
    def processTradingStatus(self, event):
        """处理交易状态变更"""
        ## -----------------------
        self.updateTradingStatus()
        ## -----------------------

        ## -----------------------
        h = datetime.now().hour
        m = datetime.now().minute
        s = datetime.now().second
        ## -----------------------

        if (h == self.tradingCloseHour and 
            m in [self.tradingCloseMinute1, (self.tradingCloseMinute2-1)] and 
            30 <= s <= 59 and (s % 10 == 0 or len(self.tradingOrdersClose) == 0)):
            ## =================================================================
            if self.ctaEngine.mainEngine.multiStrategy:
                ## -------------------------------------------------------------
                self.tradingOrdersOpen = self.fetchTradingOrders(stage = 'open')
                self.updateTradingOrdersVtOrderID(tradingOrders = self.tradingOrdersOpen,
                                                  stage = 'open')
                self.updateVtOrderIDList('open')
                ## -------------------------------------------------------------
                self.tradingOrdersClose = self.fetchTradingOrders(stage = 'close')
                self.updateTradingOrdersVtOrderID(tradingOrders = self.tradingOrdersClose,
                                                  stage = 'close')
                self.updateVtOrderIDList('close')
            ## =================================================================


        ## =====================================================================
        ## 更新 workingInfo
        ## =====================================================================
        if ((m % 5 == 0) and (s == 35)):
            self.updateOrderInfo()
            if self.tradingStart:
                self.updateWorkingInfo(self.tradingOrdersOpen, 'open')
                self.updateWorkingInfo(self.tradingOrdersClose, 'close')
            if (h == 15 and self.trading):
                self.updateFailedInfo(
                    tradingOrders = self.tradingOrdersClose, 
                    tradedOrders  = self.tradedOrdersClose)

    ## =========================================================================
    ## william
    ## 时间引擎
    ## =========================================================================
    def registerEvent(self):
        """注册事件监听"""
        ## ---------------------------------------------------------------------
        self.ctaEngine.eventEngine.register(EVENT_TIMER, self.processTradingStatus)
        ## ---------------------------------------------------------------------
