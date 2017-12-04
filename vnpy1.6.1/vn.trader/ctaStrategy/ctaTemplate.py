# encoding: UTF-8

'''
本文件包含了CTA引擎中的策略开发用模板，开发策略时需要继承CtaTemplate类。
'''

from __future__ import division
import os
import sys
from copy import copy

from ctaBase import *
from vtConstant import *

## 发送邮件通知
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import codecs
from tabulate import tabulate

import numpy as np
import pandas as pd
from pandas.io import sql
from datetime import *
import time
from eventType import *

pd.set_option('display.max_rows', 1000)

########################################################################
class CtaTemplate(object):
    """CTA策略模板"""
    
    # 策略类的名称和作者
    name       = EMPTY_UNICODE              # 策略实例名称
    className  = 'CtaTemplate'
    strategyID = EMPTY_STRING               # william:暂时与 className 一样
    author     = EMPTY_UNICODE
    
    # MongoDB数据库的名称，K线数据库默认为1分钟
    tickDbName = TICK_DB_NAME
    barDbName  = MINUTE_DB_NAME
    ############################################################################
    ## william
    ## 多合约组合
    vtSymbol     = EMPTY_STRING     
    productClass = EMPTY_STRING              # 产品类型（只有IB接口需要）
    currency     = EMPTY_STRING              # 货币（只有IB接口需要）
    
    ## -------------------------------------------------------------------------
    ## 各种控制条件
    ## 策略的基本变量，由引擎管理
    inited         = False                    # 是否进行了初始化
    trading        = False                    # 是否启动交易，由引擎管理
    tradingStart   = False                    # 开盘启动交易
    tradingEnd     = False                    # 收盘开启交易
    pos            = 0                        # 持仓情况
    sendMailStatus = False                    # 是否已经发送邮件
    tradingClosePositionAll    = False        # 是否强制平仓所有合约
    tradingClosePositionSymbol = False        # 是否强制平仓单个合约
    ## -------------------------------------------------------------------------

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol']
    
    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos']

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

    ## -------------------------------------------------------------------------
    ## 保存交易记录: tradingInfo
    ## 保存订单记录: orderInfo
    ## -------------------------------------------------------------------------
    tradingInfoFields = ['strategyID','InstrumentID','TradingDay','tradeTime',
                         'direction','offset','volume','price']
    orderInfoFields   = ['strategyID', 'vtOrderID', 'symbol', 'orderTime',
                         'status', 'direction', 'cancelTime', 'tradedVolume',
                         'frontID', 'sessionID', 'offset', 'price', 'totalVolume']
    failedInfoFields  = ['strategyID','InstrumentID','TradingDay',
                         'direction','offset','volume']

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        self.ctaEngine = ctaEngine

        ## =====================================================================
        ## 把　MySQL 数据库的　TradingDay　调整为　datetime 格式
        conn = self.ctaEngine.mainEngine.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
        cursor = conn.cursor()
        cursor.execute("""
                        ALTER TABLE failedInfo
                        MODIFY TradingDay date not null;
                       """)
        cursor.execute("""
                        ALTER TABLE positionInfo
                        MODIFY TradingDay date not null;
                       """)
        try:
            cursor.execute("""ALTER TABLE positionInfo DROP primary key""")
        except:
            pass
        cursor.execute("""
                        ALTER TABLE positionInfo 
                        ADD PRIMARY key (strategyID,InstrumentID,TradingDay,direction);
                       """)
        conn.commit()
        conn.close()        
        ## =====================================================================

        ## 设置策略的参数
        if setting:
            d = self.__dict__
            for key in self.paramList:
                if key in setting:
                    d[key] = setting[key]

        ## =====================================================================
        ## 订阅行情
        ## ---------------------------------------------------------------------
        if self.vtSymbolList:
            for vtSymbol in self.vtSymbolList:
                contract = self.ctaEngine.mainEngine.getContract(vtSymbol)
                if contract:
                    req          = VtSubscribeReq()
                    req.symbol   = contract.symbol
                    req.exchange = contract.exchange
                    # req.symbol = contract['symbol']
                    # req.exchange = contract['exchange']
                    # 对于IB接口订阅行情时所需的货币和产品类型，从策略属性中获取
                    # req.currency = strategy.currency
                    # req.productClass = strategy.productClass
                    ############################################################
                    ## william
                    self.ctaEngine.mainEngine.subscribe(req, contract.gatewayName)
                    ############################################################
                else:
                    ############################################################
                    ## william
                    print "\n"+'#'*80
                    print '%s的交易合约%s无法找到' %(self.name, vtSymbol)
                    print '#'*80+"\n"
                    self.writeCtaLog(u'%s的交易合约%s无法找到' %(self.name, vtSymbol))
        ## =====================================================================

    
    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        raise NotImplementedError
    
    # #----------------------------------------------------------------------
    # def onStart(self):
    #     """启动策略（必须由用户继承实现）"""
    #     raise NotImplementedError
    
    # #----------------------------------------------------------------------
    # def onStop(self):
    #     """停止策略（必须由用户继承实现）"""
    #     raise NotImplementedError

    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        ## =====================================================================
        ## 策略启动
        ## =====================================================================
        print '\n'+'#'*80
        print '%s策略启动' %self.name
        # self.writeCtaLog(u'%s策略启动' %self.name)
        self.trading = True
        print '#'*80
        self.putEvent()
        

    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        ## =====================================================================
        ## 策略停止
        ## =====================================================================
        print '\n'+'#'*80
        print '%s策略停止' %self.name
        self.trading = False
        ## ---------------------------------------------------------------------
        ## 取消所有的订单
        self.vtOrderIDListAll = list(set(self.vtOrderIDList) | 
                                     set(self.vtOrderIDListOpen) |
                                     set(self.vtOrderIDListClose) |
                                     set(self.vtOrderIDListFailedInfo) |
                                     set(self.vtOrderIDListClosePositionAll) |
                                     set(self.vtOrderIDListClosePositionSymbol))
        ## ---------------------------------------------------------------------
        if len(self.vtOrderIDListAll) != 0:
            for vtOrderID in self.vtOrderIDListAll:
                self.cancelOrder(vtOrderID)
        ## ---------------------------------------------------------------------
        print '#'*80
        # self.writeCtaLog(u'%s策略停止' %self.name)
        self.putEvent()


    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        raise NotImplementedError

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        raise NotImplementedError
    
    #----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        raise NotImplementedError
    
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        raise NotImplementedError
    
    #----------------------------------------------------------------------
    def buy(self, vtSymbol, price, volume, stop=False):
        """买开"""
        return self.sendOrder(vtSymbol, CTAORDER_BUY, price, volume, stop)
    
    #----------------------------------------------------------------------
    def sell(self, vtSymbol, price, volume, stop=False):
        """卖平"""
        return self.sendOrder(vtSymbol, CTAORDER_SELL, price, volume, stop)       

    #----------------------------------------------------------------------
    def short(self, vtSymbol, price, volume, stop=False):
        """卖开"""
        return self.sendOrder(vtSymbol, CTAORDER_SHORT, price, volume, stop)          
 
    #----------------------------------------------------------------------
    def cover(self, vtSymbol, price, volume, stop=False):
        """买平"""
        return self.sendOrder(vtSymbol, CTAORDER_COVER, price, volume, stop)
        
    #----------------------------------------------------------------------
    def sendOrder(self, vtSymbol, orderType, price, volume, stop=False):
        """发送委托"""
        if self.trading:
            # 如果stop为True，则意味着发本地停止单
            if stop:
                vtOrderID = self.ctaEngine.sendStopOrder(vtSymbol, orderType, price, volume, self)
            else:
                vtOrderID = self.ctaEngine.sendOrder(vtSymbol, orderType, price, volume, self) 
            return vtOrderID
        else:
            # 交易停止时发单返回空字符串
            return ''        
        
    #----------------------------------------------------------------------
    def cancelOrder(self, vtOrderID):
        """撤单"""
        # 如果发单号为空字符串，则不进行后续操作
        if not vtOrderID:
            return
        
        if STOPORDERPREFIX in vtOrderID:
            self.ctaEngine.cancelStopOrder(vtOrderID)
        else:
            self.ctaEngine.cancelOrder(vtOrderID)

        ## ---------------------------------------------------------------------
        ## william
        ## ---------------------------------------------------------------------
        # time.sleep(0)
    
    #----------------------------------------------------------------------
    def insertTick(self, tick):
        """向数据库中插入tick数据"""
        self.ctaEngine.insertData(self.tickDbName, self.vtSymbol, tick)
    
    #----------------------------------------------------------------------
    def insertBar(self, bar):
        """向数据库中插入bar数据"""
        self.ctaEngine.insertData(self.barDbName, self.vtSymbol, bar)
        
    #----------------------------------------------------------------------
    def loadTick(self, days):
        """读取tick数据"""
        return self.ctaEngine.loadTick(self.tickDbName, self.vtSymbol, days)
    
    #----------------------------------------------------------------------
    def loadBar(self, days):
        """读取bar数据"""
        return self.ctaEngine.loadBar(self.barDbName, self.vtSymbol, days)
    
    #----------------------------------------------------------------------
    def writeCtaLog(self, content):
        """记录CTA日志"""
        content = self.name + ':' + content
        self.ctaEngine.writeCtaLog(content)
        
    #----------------------------------------------------------------------
    def putEvent(self):
        """发出策略状态变化事件"""
        self.ctaEngine.putStrategyEvent(self.name)
        
    #----------------------------------------------------------------------
    def getEngineType(self):
        """查询当前运行的环境"""
        return self.ctaEngine.engineType
    

    ############################################################################
    ## 处理订单，并生成相应的字典格式
    ## @param vtSymbol: 合约代码
    ## @param orderDict: 订单的字典格式
    ## @param orderIDList: 订单列表
    ############################################################################
    def prepareTradingOrder(self, vtSymbol, tradingOrders, orderIDList, 
                            priceType, price = None, addTick = 0, discount = 0):
        """处理订单"""
        ## 生成交易列表
        tempTradingList = [k for k in tradingOrders.keys() if tradingOrders[k]['vtSymbol'] == vtSymbol]
        ####################################################################
        if tempTradingList:
            for i in tempTradingList:
                ## -------------------------------------------------------------
                ## 如果交易量依然是大于 0 ，则需要继续发送订单命令
                ## -------------------------------------------------------------
                if ((self.ctaEngine.mainEngine.getAllOrders() is not None) and 
                    ('vtOrderID' in tradingOrders[i].keys())):
                    ## =============================================================================
                    if tradingOrders[i]['vtOrderID'] in self.ctaEngine.mainEngine.getAllOrders().loc[\
                    self.ctaEngine.mainEngine.getAllOrders().status.isin([u'未成交',u'部分成交'])][\
                    self.ctaEngine.mainEngine.getAllOrders().vtOrderID.isin(orderIDList)].vtOrderID.values:
                        if ((datetime.now() - self.tickTimer[vtSymbol]).seconds > 3) and self.tradingEnd:
                            self.cancelOrder(tradingOrders[i]['vtOrderID'])
                            self.tickTimer[vtSymbol] = datetime.now()
                    ## -----------------------------------------------------------------------------
                    elif (tradingOrders[i]['vtOrderID'] in self.ctaEngine.mainEngine.getAllOrders().loc[\
                    self.ctaEngine.mainEngine.getAllOrders().status.isin([u'已撤销',u'全部成交'])][\
                    self.ctaEngine.mainEngine.getAllOrders().vtOrderID.isin(orderIDList)].vtOrderID.values) and \
                    tradingOrders[i]['volume']:
                        self.sendTradingOrder(tradingOrders = tradingOrders,
                                               orderDict    = tradingOrders[i],
                                               orderIDList  = orderIDList,
                                               priceType    = priceType,
                                               price        = price,
                                               addTick      = addTick,
                                               discount     = discount) 
                    elif (tradingOrders[i]['vtOrderID'] in self.ctaEngine.mainEngine.getAllOrders().loc[\
                    self.ctaEngine.mainEngine.getAllOrders().status.isin([u'拒单'])][\
                    self.ctaEngine.mainEngine.getAllOrders().vtOrderID.isin(orderIDList)].vtOrderID.values) and \
                    tradingOrders[i]['volume'] and ((datetime.now() - self.tickTimer[vtSymbol]).seconds >= 10) :
                        self.sendTradingOrder(tradingOrders = tradingOrders,
                                               orderDict    = tradingOrders[i],
                                               orderIDList  = orderIDList,
                                               priceType    = priceType,
                                               price        = price,
                                               addTick      = addTick,
                                               discount     = discount)
                    ## ============================================================================= 
                else:
                    self.sendTradingOrder(tradingOrders = tradingOrders,
                                          orderDict     = tradingOrders[i],
                                          orderIDList   = orderIDList,
                                          priceType     = priceType,
                                          price         = price,
                                          addTick       = addTick,
                                          discount      = discount)
        ########################################################################
        ## .....................................................................
        self.putEvent()
        ## .....................................................................

    ############################################################################
    ## 根据订单的字典格式，发送订单给 CTP
    ## @param stratTrade: 交易事件数据
    ## @param orderDict: 订单的字典格式
    ## @param orderIDList: 订单列表
    ## @param addTick 控制增加的价格
    ############################################################################
    def sendTradingOrder(self, tradingOrders, orderDict, orderIDList, priceType, price = None, addTick = 0, discount = 0):
        """发送单个合约的订单"""
        tempInstrumentID = orderDict['vtSymbol']
        tempPriceTick    = self.ctaEngine.tickInfo[tempInstrumentID]['priceTick']
        tempAskPrice1    = self.lastTickData[tempInstrumentID]['askPrice1']
        tempBidPrice1    = self.lastTickData[tempInstrumentID]['bidPrice1']
        tempUpperLimit   = self.lastTickData[tempInstrumentID]['upperLimit']
        tempLowerLimit   = self.lastTickData[tempInstrumentID]['lowerLimit']
        tempLastPrice    = self.lastTickData[tempInstrumentID]['lastPrice']
        tempDirection    = orderDict['direction']
        tempVolume       = orderDict['volume']

        ## =====================================================================
        ## 定义最佳价格
        ## ---------------------------------------------------------------------
        if priceType == 'best':
            if tempDirection in ['buy','cover']:
                tempBestPrice = tempBidPrice1 
            elif tempDirection in ['sell','short']:
                tempBestPrice = tempAskPrice1
        elif priceType == 'chasing':
            if tempDirection in ['buy','cover']:
                tempBestPrice = tempAskPrice1
            elif tempDirection in ['sell','short']:
                tempBestPrice = tempBidPrice1 
        elif priceType == 'last':
            tempBestPrice = tempLastPrice
        elif priceType == 'open':
            tempBestPrice = self.lastTickData[tempInstrumentID]['openPrice']
        elif priceType == 'limit':
            if price:
                tempBestPrice = price
            else:
                print "错误的价格"
                return None
        elif priceType == 'upper':
            tempBestPrice = tempUpperLimit
        elif priceType == 'lower':
            tempBestPrice = tempLowerLimit
        ## =====================================================================

        ## =====================================================================
        ## 无效价格
        ## ---------------------------------------------------------------------
        if (tempBestPrice <= 0 or tempBestPrice > 10000000):
            return None
        ## =====================================================================
        tempPrice = self.priceBetweenUpperLower(min(tempBestPrice * (1-discount), tempLastPrice) + 
                                                    tempPriceTick * addTick, tempInstrumentID)
        ########################################################################
        if tempDirection == 'buy':
            ## 如果是买入, AskPrice 需要增加一个 priceTick 的滑点
            # tempPrice = min(min(tempBestPrice * (1-discount), tempLastPrice) + tempPriceTick * addTick, tempUpperLimit)
            vtOrderID = self.buy(vtSymbol = tempInstrumentID, price = tempPrice, volume = tempVolume)
        elif tempDirection == 'short':
            ## 如果是卖出, BidPrice 需要减少一个 priceTick 的滑点
            # tempPrice = max(max(tempBestPrice * (1+discount), tempLastPrice) - tempPriceTick * addTick, tempLowerLimit)
            vtOrderID = self.short(vtSymbol = tempInstrumentID, price = tempPrice, volume = tempVolume)
        elif tempDirection == 'cover':
            ## 如果是买入, AskPrice 需要增加一个 priceTick 的滑点
            # tempPrice = min(min(tempBestPrice * (1-discount), tempLastPrice) + tempPriceTick * addTick, tempUpperLimit)
            vtOrderID = self.cover(vtSymbol = tempInstrumentID, price = tempPrice, volume = tempVolume)
        elif tempDirection == 'sell':
            ## 如果是卖出, BidPrice 需要减少一个 priceTick 的滑点
            # tempPrice = max(max(tempBestPrice * (1+discount), tempLastPrice) - tempPriceTick * addTick, tempLowerLimit)
            vtOrderID = self.sell(vtSymbol = tempInstrumentID, price = tempPrice, volume = tempVolume)
        ## ---------------------------------------------------------------------
        orderIDList.append(vtOrderID)
        ########################################################################
        self.tickTimer[tempInstrumentID]    = datetime.now()
        ## ---------------------------------------------------------------------
        tempKey = tempInstrumentID + '-' + tempDirection
        ## ---------------------------------------------------------------------
        tradingOrders[tempKey]['vtOrderID'] = vtOrderID
        if 'orderNo' not in tradingOrders[tempKey].keys():
            tradingOrders[tempKey]['orderNo'] = 1
        else:
            tradingOrders[tempKey]['orderNo'] += 1
        ## .....................................................................
        self.putEvent()
        ## .....................................................................

    ############################################################################
    ## william
    ## 限制价格在 UpperLimit 和 LowerLimit 之间
    ############################################################################
    def priceBetweenUpperLower(self, price, vtSymbol):
        tempUpperLimit = self.lastTickData[vtSymbol]['upperLimit']
        tempLowerLimit = self.lastTickData[vtSymbol]['lowerLimit']
        # tempRes = min(max(tempLowerLimit, price), tempUpperLimit)    
        return min(max(tempLowerLimit, price), tempUpperLimit)

    ############################################################################
    ## william
    ## 处理前一日未成交的订单
    ############################################################################
    def processFailedInfo(self, failedInfo):
        """处理未成交订单"""
        ## =====================================================================
        if len(failedInfo) == 0:
            return
        ## =====================================================================

        self.tradingOrdersFailedInfo = {}
        ## =====================================================================
        for i in range(len(failedInfo)):
            ## -------------------------------------------------------------
            ## direction
            if failedInfo.loc[i,'direction'] == 'long':
                if failedInfo.loc[i,'offset'] == u'开仓':
                    tempDirection = 'buy'
                elif failedInfo.loc[i,'offset'] == u'平仓':
                    tempDirection = 'cover'
            elif failedInfo.loc[i,'direction'] == 'short':
                if failedInfo.loc[i,'offset'] == u'开仓':
                    tempDirection = 'short'
                elif failedInfo.loc[i,'offset'] == u'平仓':
                    tempDirection = 'sell'
            ## -------------------------------------------------------------
            ## volume
            tempVolume     = failedInfo.loc[i,'volume']
            tempKey        = failedInfo.loc[i,'InstrumentID'] + '-' + tempDirection
            tempTradingDay = failedInfo.loc[i,'TradingDay']
            
            self.tradingOrdersFailedInfo[tempKey] = {
                'vtSymbol'   :failedInfo.loc[i,'InstrumentID'],
                'direction'  :tempDirection,
                'volume'     :tempVolume,
                'TradingDay' :tempTradingDay}
        ## =====================================================================


    ############################################################################
    ## onClosePosition
    ############################################################################
    def onClosePosition(self, tick):
        """
        收到行情TICK推送（必须由用户继承实现）
        Ref: ctaEngine.py, 通过把 Tick 数据推送到策略函数里面
        self.callStrategyFunc(strategy, strategy.onClosePosition, ctaTick)
        """
        ## =====================================================================
        if not ((self.tradingClosePositionAll or self.tradingClosePositionSymbol) and self.trading):
            return 
        elif tick.vtSymbol not in [self.tradingOrdersClosePositionAll[k]['vtSymbol'] 
                                    for k in self.tradingOrdersClosePositionAll.keys()] + \
                                  [self.tradingOrdersClosePositionSymbol[k]['vtSymbol'] 
                                    for k in self.tradingOrdersClosePositionSymbol.keys()]:
            return 
        elif ((datetime.now() - self.tickTimer[tick.vtSymbol]).seconds <= 5):
            return 
        ## =====================================================================
        # tempTick = {k:tick.__dict__[k] for k in self.tickFileds}
        ## ---------------------------------------------------------------------
        self.lastTickData[tick.vtSymbol] = {k:tick.__dict__[k] for k in self.tickFileds}
        self.updateCancelOrders(tick.vtSymbol)
        ## ---------------------------------------------------------------------

        ############################################################################################
        if tick.symbol in [self.tradingOrdersClosePositionAll[k]['vtSymbol'] for k in self.tradingOrdersClosePositionAll.keys()] and self.tradingClosePositionAll:
            self.prepareTradingOrder(vtSymbol        = tick.vtSymbol, 
                                     tradingOrders   = self.tradingOrdersClosePositionAll, 
                                     orderIDList     = self.vtOrderIDListClosePositionAll,
                                     price           = 'chasing')
        ############################################################################################
        if tick.symbol in [self.tradingOrdersClosePositionSymbol[k]['vtSymbol'] for k in self.tradingOrdersClosePositionSymbol.keys()]:
            self.prepareTradingOrder(vtSymbol        = tick.vtSymbol, 
                                     tradingOrders   = self.tradingOrdersClosePositionSymbol, 
                                     orderIDList     = self.vtOrderIDListClosePositionSymbol,
                                     price           = 'chasing')
        ############################################################################################

        # =====================================================================
        # 发出状态更新事件
        self.putEvent()
        # =====================================================================


    def closePositionTradeEvent(self, trade):
        """
        处理一键全平仓的成交事件
        Ref: ctaEngine.py, 把成交信息推送到策略函数
        self.callStrategyFunc(strategy, strategy.closePositionTradeEvent, trade)
        """
        ## =====================================================================
        if not ((self.tradingClosePositionAll or self.tradingClosePositionSymbol) and self.trading):
            return None
        elif trade.vtOrderID not in \
            list(set(self.vtOrderIDListClosePositionAll) | 
                 set(self.vtOrderIDListClosePositionSymbol)):
            return None
        ## =====================================================================

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
        tempKey = self.stratTrade['vtSymbol'] + '-' + tempDirection
        ## ---------------------------------------------------------------------

        ## ---------------------------------------------------------------------
        tempFields = ['strategyID','InstrumentID','TradingDay','direction','volume']
        tempRes = pd.DataFrame([[self.stratTrade[k] for k in tempFields]], columns = tempFields)
        ## =====================================================================

        ## =====================================================================
        ## 1. 修改 orderDict 的数量
        ## =====================================================================
        if self.stratTrade['vtOrderID'] in self.vtOrderIDListClosePositionAll:
            # ------------------------------------------------------------------
            self.tradingOrdersClosePositionAll[tempKey]['volume'] -= self.stratTrade['volume']
            if self.tradingOrdersClosePositionAll[tempKey]['volume'] == 0:
                self.tradingOrdersClosePositionAll.pop(tempKey, None)   
        elif self.stratTrade['vtOrderID'] in self.vtOrderIDListClosePositionSymbol:
            # ------------------------------------------------------------------
            self.tradingOrdersClosePositionSymbol[tempKey]['volume'] -= self.stratTrade['volume']
            if self.tradingOrdersClosePositionSymbol[tempKey]['volume'] == 0:
                self.tradingOrdersClosePositionSymbol.pop(tempKey, None)

        ## =====================================================================
        ## 2. 更新 positionInfo
        ## =====================================================================
        if tempOffset == u'平仓':
            mysqlPositionInfo = self.ctaEngine.mainEngine.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
                                    """
                                    SELECT *
                                    FROM positionInfo
                                    WHERE strategyID = '%s'
                                    AND InstrumentID = '%s'
                                    """ %(self.strategyID, self.stratTrade['InstrumentID'])).sort_values(by='TradingDay').reset_index()      
            if len(mysqlPositionInfo) != 0:
                cursor.execute("""
                                DELETE FROM positionInfo
                                WHERE strategyID = %s
                                AND InstrumentID = %s
                               """, (self.strategyID, self.stratTrade['InstrumentID']))
                conn.commit()
                for i in range(len(mysqlPositionInfo)):
                    tempVolume = mysqlPositionInfo.loc[0:i,'volume'].sum() - self.stratTrade['volume']
                    if tempVolume >= 0:
                        mysqlPositionInfo.at[i,'volume'] = tempVolume
                        mysqlPositionInfo = mysqlPositionInfo[i:]
                        mysqlPositionInfo = mysqlPositionInfo.loc[mysqlPositionInfo.volume != 0]
                        break
                ## =============================================================================
                try:
                    mysqlPositionInfo.to_sql(con=conn, name='positionInfo', if_exists='append', flavor='mysql', index = False)
                except:
                    print '\n' + '#'*80 
                    print '写入 MySQL 数据库出错'
                    # self.onStop()
                    # print '停止策略 %s' %self.name
                    print '#'*80 + '\n'

        ## =====================================================================
        ## 3. 保存交易记录
        ## =====================================================================
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


    ############################################################################
    # 一键全平仓
    ############################################################################
    def closePositionAll(self):
        """ 一键全平仓 """
        ## =====================================================================
        ## 开启
        self.tradingClosePositionAll = True
        ## =====================================================================
        self.stratPositionAll = self.ctaEngine.mainEngine.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
                            """
                            SELECT *
                            FROM positionInfo
                            WHERE strategyID = '%s'
                            """ %(self.strategyID))
        # print stratPositionAll

        tempClosePositionAll = self.stratPositionAll.groupby(['InstrumentID','direction'])['volume'].sum().reset_index()

        if len(tempClosePositionAll) != 0:
            for i in range(len(tempClosePositionAll)):
                ## direction
                if tempClosePositionAll.at[i,'direction'] == 'long':
                    tempDirection = 'sell'
                elif tempClosePositionAll.at[i,'direction'] == 'short':
                    tempDirection = 'cover'
                ##
                self.tradingOrdersClosePositionAll[tempClosePositionAll.at[i,'InstrumentID'] + '-' + tempDirection] = {
                    'vtSymbol': tempClosePositionAll.at[i, 'InstrumentID'],
                    'direction': tempDirection,
                    'volume': tempClosePositionAll.at[i, 'volume'],
                }
                self.tickTimer[tempClosePositionAll.at[i, 'InstrumentID']] = datetime.now()-timedelta(seconds = 5)


    ############################################################################
    ## 对单一的合约进行强制平仓
    ############################################################################
    def closePositionSymbol(self, vtSymbol):
        """ 一键全平仓 """
        ## =====================================================================
        ## 开启
        self.tradingClosePositionSymbol = True
        ## =====================================================================
        ## =====================================================================
        self.stratPositionSymbol = self.ctaEngine.mainEngine.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
                            """
                            SELECT *
                            FROM positionInfo
                            WHERE strategyID = '%s'
                            AND InstrumentID = '%s'
                            """ %(self.strategyID,vtSymbol))
        tempClosePositionSymbol = self.stratPositionSymbol.groupby(['direction'])['volume'].sum().reset_index()

        if len(tempClosePositionSymbol) != 0:
            for i in range(len(tempClosePositionSymbol)):
                ## direction
                if tempClosePositionSymbol.at[i,'direction'] == 'long':
                    tempDirection = 'sell'
                elif tempClosePositionSymbol.at[i,'direction'] == 'short':
                    tempDirection = 'cover'
                ##
                self.tradingOrdersClosePositionSymbol[vtSymbol + '-' + tempDirection] = {
                    'vtSymbol': vtSymbol,
                    'direction': tempDirection,
                    'volume': tempClosePositionSymbol.at[i, 'volume'],
                }
                self.tickTimer[vtSymbol] = datetime.now()-timedelta(seconds = 5)

    ############################################################################
    ## 更新取消的订单
    ############################################################################
    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def updateCancelOrders(self, vtSymbol):
        """ 更新取消未成交订单 """
        # pass
        ## =====================================================================
        if vtSymbol in self.tickTimer.keys():
            if (datetime.now() - self.tickTimer[vtSymbol]).seconds >= 10:
                for vtOrderID in self.vtOrderIDList:
                    try:
                        tempWorkingOrder = self.ctaEngine.mainEngine.getAllOrders()[
                                                (self.ctaEngine.mainEngine.getAllOrders().vtSymbol == k) &
                                                (self.ctaEngine.mainEngine.getAllOrders().vtOrderID == vtOrderID ) &
                                                (self.ctaEngine.mainEngine.getAllOrders().status == u'未成交')].vtOrderID.values
                    except:
                        tempWorkingOrder = None
                    ## =========================================================
                    if (tempWorkingOrder is not None) and len(tempWorkingOrder) != 0:
                        for i in tempWorkingOrder:
                            ## =================================================
                            self.cancelOrder(i)
                            self.tickTimer[k] = datetime.now()
                            ## =================================================
                    ## =========================================================
        ## =====================================================================
    
    ############################################################################
    ## 更新交易记录的数据表
    ############################################################################
    def updateTradingInfo(self, df, tbName = 'tradingInfo'):
        """更新交易记录"""
        conn = self.ctaEngine.mainEngine.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
        cursor = conn.cursor()
        df.to_sql(con       = conn, 
                  name      = tbName, 
                  flavor    = 'mysql', 
                  index     = False,
                  if_exists = 'append')
        conn.close()
    

    ############################################################################
    ## 更新交易日期
    ############################################################################
    def updateTradingDay(self, strategyID, InstrumentID, 
                         oldTradingDay, newTradingDay, 
                         direction, volume):
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
        ## =====================================================================

    ############################################################################
    ## 更新订单字典
    ############################################################################
    def updateTradingOrdersDict(self, tradingOrders, tradedOrders):
        """
        更新订单字典
        """
        ## =====================================================================
        ## sendMail
        if (datetime.now().strftime('%H:%M:%S') == '15:03:00' and 
            1 <= (datetime.now().weekday()+1) <= 5 and 
            self.trading):
            self.sendMailStatus = True
            self.sendMail()
        else:
            self.sendMailStatus = False
        ## =====================================================================

        conn = self.ctaEngine.mainEngine.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
        cursor = conn.cursor()
        ## =====================================================================
        ## 1. 更新账户信息
        ## 2. 更新 orderInfo
        ## =====================================================================
        if (datetime.now().minute % 5 == 0 and 
            self.trading and datetime.now().second == 59):
            ## 把账户信息写入 MysQL 数据库
            ## =====================================================================================
            self.ctaEngine.mainEngine.drEngine.getIndicatorInfo(dbName = self.ctaEngine.mainEngine.dataBase,
                                                                initCapital = self.ctaEngine.mainEngine.initCapital,
                                                                flowCapitalPre = self.ctaEngine.mainEngine.flowCapitalPre,
                                                                flowCapitalToday = self.ctaEngine.mainEngine.flowCapitalToday)
            ## =====================================================================================
            ## 把所有下单记录写入 MySQL 数据库
            # conn = self.ctaEngine.mainEngine.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
            # cursor = conn.cursor()
            tempOrderInfo = self.ctaEngine.mainEngine.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
                            """
                            SELECT *
                            FROM orderInfo
                            WHERE strategyID = '%s'
                            AND TradingDay = %s
                           """ %(self.strategyID, self.ctaEngine.tradingDay))
            stratOrderIDListAll = self.vtOrderIDList + self.vtOrderIDListOpen + self.vtOrderIDListClose + self.vtOrderIDListFailedInfo
            tempOrderIDList = [k for k in stratOrderIDListAll if k not in tempOrderInfo['vtOrderID'].values]
            ## -------------------------------------------------------------------------------------
            if len(tempOrderIDList) != 0:
                ## -------------------------------------------------------------
                df = pd.DataFrame([], columns = self.orderInfoFields)
                for i in tempOrderIDList:
                    df = df.append(self.ctaEngine.mainEngine.getAllOrders().loc[self.ctaEngine.mainEngine.getAllOrders().vtOrderID == i][self.orderInfoFields], ignore_index=True)
                df = df[self.orderInfoFields]
                df['TradingDay'] = self.ctaEngine.tradingDate
                df['strategyID'] = self.strategyID
                df = df[['TradingDay'] + self.orderInfoFields]
                ## 改名字
                df.columns.values[3] = 'InstrumentID'
                # print df
                if len(tempOrderInfo) != 0:
                    df = df.append(tempOrderInfo, ignore_index=True)
                if len(df) != 0:
                    ## -----------------------------------------------------------------------------
                    ## 清空记录
                    cursor.execute("""
                                    DELETE FROM orderInfo
                                    WHERE strategyID = %s
                                    AND TradingDay = %s
                                   """, (self.strategyID, self.ctaEngine.tradingDay))
                    conn.commit()
                    df.to_sql(con=conn, name='orderInfo', if_exists='append', flavor='mysql', index = False)
                    ## -----------------------------------------------------------------------------
            # conn.close()
            ## =====================================================================================

        ## =====================================================================
        ## 1. 更新未成交订单，并保存到 MySQL 数据库
        ## ===================================================================== 
        if (datetime.now().hour == 15) and (1 <= datetime.now().minute <= 2) and \
           (datetime.now().second % 30 == 0) and self.trading:
            ## -----------------------------------------------------------------
            self.failedOrders = {k:tradingOrders[k] \
                for k in tradingOrders.keys() if k not in tradedOrders.keys()}
            ## -----------------------------------------------------------------
            if len(self.failedOrders) != 0:
                dfData = []
                ## -------------------------------------------------------------
                for k in self.failedOrders.keys():
                    ## ---------------------------------------------------------
                    if self.failedOrders[k]['direction'] == 'buy':
                        tempDirection = 'long'
                        tempOffset    = u'开仓'
                    elif self.failedOrders[k]['direction'] == 'sell':
                        tempDirection = 'short'
                        tempOffset    = u'平仓'
                    elif self.failedOrders[k]['direction'] == 'short':
                        tempDirection = 'short'
                        tempOffset    = u'开仓'
                    elif self.failedOrders[k]['direction'] == 'cover':
                        tempDirection = 'long'
                        tempOffset    = u'平仓'
                    ## ---------------------------------------------------------
                    tempRes = [self.strategyID, self.failedOrders[k]['vtSymbol'], 
                               self.failedOrders[k]['TradingDay'], 
                               tempDirection, tempOffset, self.failedOrders[k]['volume']]
                    dfData.append(tempRes)
                    ## ---------------------------------------------------------
                    df = pd.DataFrame(dfData, columns = self.failedInfoFields)
                ## -------------------------------------------------------------
                cursor.execute("""
                                DELETE FROM failedInfo
                                WHERE strategyID = %s
                                AND TradingDay = %s
                               """,(self.strategyID, self.ctaEngine.tradingDay))
                conn.commit()
                df.to_sql(con=conn, name='failedInfo', if_exists='append', flavor='mysql', index = False)
                # conn.close()         
                ## -------------------------------------------------------------
                ####################################################################################
                ## 记得要从 positionInfo 持仓里面删除
                ####################################################################################
                for k in self.failedOrders.keys():
                    ## -----------------------------------------------------------------------------
                    ## 只有需要平仓的，才需要从 positionInfo 数据表剔除
                    ## -----------------------------------------------------------------------------
                    if self.failedOrders[k]['direction'] in ['sell', 'cover']:
                        ## -----------------------------------------------------
                        if self.failedOrders[k]['direction'] == 'sell':
                            tempDirection = 'long'
                        elif self.failedOrders[k]['direction'] == 'cover':
                            tempDirection = 'short'
                        ## -----------------------------------------------------

                        ## -------------------------------------------------------------------------
                        try:
                            cursor.execute("""
                                            DELETE FROM positionInfo
                                            WHERE strategyID = %s
                                            AND InstrumentID = %s
                                            AND TradingDay = %s
                                            AND direction  = %s
                                           """, (self.strategyID, self.failedOrders[k]['vtSymbol'], self.failedOrders[k]['TradingDay'], tempDirection))
                            conn.commit()
                        except:
                            None
                        ## -------------------------------------------------------------------------
        ##
        ## =====================================================================
        conn.close()
        ## =====================================================================


    ############################################################################
    ## 更新订单表
    ############################################################################
    def updateTradingOrdersTable(self, stratTrade):
        """
        更新交易订单表
        """
        ## =====================================================================
        conn = self.ctaEngine.mainEngine.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
        cursor = conn.cursor()

        ## ---------------------------------------------------------------------
        if self.stratTrade['offset'] == u'开仓':
            if self.stratTrade['direction'] == 'long':
                tempDirection = 'buy'
            elif self.stratTrade['direction'] == 'short':
                tempDirection = 'short'
        elif self.stratTrade['offset'] in [u'平仓', u'平昨', u'平今']:
            if self.stratTrade['direction'] == 'long':
                tempDirection = 'cover'
            elif self.stratTrade['direction'] == 'short':
                tempDirection = 'sell'
        ## ---------------------------------------------------------------------
        
        ## =====================================================================
        mysqlInfoTradingOrders = self.ctaEngine.mainEngine.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
                                """
                                SELECT *
                                FROM tradingOrders
                                WHERE strategyID = '%s'
                                AND InstrumentID = '%s'
                                AND orderType = '%s'
                                """ %(self.strategyID,self.stratTrade['vtSymbol'],
                                    tempDirection))
        # print mysqlInfoTradingOrders
        if len(mysqlInfoTradingOrders) != 0:
            for i in range(len(mysqlInfoTradingOrders)):
                tempVolume = mysqlInfoTradingOrders.at[i,'volume'] - self.stratTrade['volume']
                if tempVolume == 0:
                    cursor.execute("""
                                    DELETE FROM tradingOrders
                                    WHERE strategyID = %s
                                    AND InstrumentID = %s
                                    AND volume = %s
                                    AND orderType = %s
                                   """, (self.strategyID, self.stratTrade['vtSymbol'],
                                    mysqlInfoTradingOrders.at[i,'volume'],
                                    tempDirection))
                    conn.commit()
                else:
                    cursor.execute("""
                                    UPDATE tradingOrders
                                    SET volume = %s
                                    WHERE strategyID = %s
                                    AND InstrumentID = %s
                                    AND volume = %s
                                    AND orderType = %s
                                   """, (tempVolume, self.strategyID, 
                                    self.stratTrade['vtSymbol'],
                                    mysqlInfoTradingOrders.at[i,'volume'],
                                    tempDirection))
                    conn.commit()
        ## ---------------------------------------------------------------------
        conn.close()


    ############################################################################
    ## 更新 vtOrderIDList
    ############################################################################
    def updateVtOrderIDList(self, vtOrderIDList, stage):
        """
        更新 vtOrderIDList
        """
        tempWorkingInfo = self.ctaEngine.mainEngine.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
                                    """
                                    SELECT vtOrderID
                                    FROM workingInfo
                                    WHERE strategyID = '%s'
                                    AND TradingDay = '%s'
                                    AND stage = '%s'
                                    AND not (vtOrderID is NULL)
                                    """ %(self.strategyID, self.ctaEngine.tradingDay, stage))
        if len(tempWorkingInfo.vtOrderID):
            for i in range(len(tempWorkingInfo)):
                if tempWorkingInfo.vtOrderID.values[i] not in vtOrderIDList:
                    vtOrderIDList.append(tempWorkingInfo.vtOrderID.values[i])

    ############################################################################
    ## 更新 tradingOrders 里面的字段： vrOrderID
    ############################################################################

    def updateTradingOrdersVtOrderID(self, tradingOrders, stage):
        """
        更新交易订单的 vtOrderID
        """
        tempWorkingInfo = self.ctaEngine.mainEngine.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
                                    """
                                    SELECT *
                                    FROM workingInfo
                                    WHERE strategyID = '%s'
                                    AND TradingDay = %s
                                    AND stage = '%s'
                                    """ %(self.strategyID, self.ctaEngine.tradingDay, stage))
        # print tempWorkingInfo
        if len(tradingOrders):
            for i in range(len(tradingOrders)):
                temp = tempWorkingInfo.loc[tempWorkingInfo.vtSymbol == tradingOrders[tradingOrders.keys()[i]]['vtSymbol']][tempWorkingInfo.orderType == tradingOrders[tradingOrders.keys()[i]]['direction']].reset_index(drop = True)
                if len(temp) == 0:
                    continue
                if temp.at[0,'vtOrderID'] not in [self.ctaEngine.mainEngine.getAllWorkingOrders()[j].vtOrderID for j in range(len(self.ctaEngine.mainEngine.getAllWorkingOrders()))]:
                    continue
                if ('vtOrderID' not in tradingOrders[tradingOrders.keys()[i]].keys() or
                    tradingOrders[tradingOrders.keys()[i]]['vtOrderID'] < temp.at[0,'vtOrderID']):
                    tradingOrders[tradingOrders.keys()[i]]['vtOrderID'] = temp.at[0,'vtOrderID']
                    self.ctaEngine.orderStrategyDict[temp.at[0,'vtOrderID']] =  self.ctaEngine.strategyDict[self.name]

    ############################################################################
    ## 更新 workingInfo
    ############################################################################
    def updateWorkingInfo(self, tradingOrders, stage):
        """
        更新 workingInfo 表格
        """
        conn = self.ctaEngine.mainEngine.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
        cursor = conn.cursor()

        tempWorkingInfo = self.ctaEngine.mainEngine.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
                                    """
                                    SELECT *
                                    FROM workingInfo
                                    WHERE strategyID = '%s'
                                    AND TradingDay = '%s'
                                    AND stage = '%s'
                                    """ %(self.strategyID, self.ctaEngine.tradingDay, stage))

        dfHeader = ['TradingDay','strategyID','vtSymbol','vtOrderID',
                    'orderType','volume','stage']
        dfData   = []

        if tradingOrders:
            for k in tradingOrders.keys():
                temp = copy(tradingOrders[k])
                temp['strategyID'] = self.strategyID
                temp['orderType'] = temp['direction']
                temp['stage'] = stage
                if 'vtOrderID' not in temp.keys():
                    # temp['vtOrderID'] = ''
                    continue
                elif temp['vtSymbol'] in tempWorkingInfo.vtSymbol.values:
                    if temp['vtOrderID'] < tempWorkingInfo.loc[tempWorkingInfo.vtSymbol == temp['vtSymbol']].vtOrderID.values[0]:
                        continue
                dfData.append([temp[kk] for kk in dfHeader])
        df = pd.DataFrame(dfData, columns = dfHeader)

        cursor.execute("""
                        DELETE FROM workingInfo
                        WHERE strategyID = '%s'
                        AND stage = '%s'
                       """ %(self.strategyID, stage))
        conn.commit()
        df.to_sql(con=conn, name='workingInfo', if_exists='append', flavor='mysql', index = False)
        conn.close()


    ############################################################################
    ## 保存到 MySQL
    ############################################################################
    # def saveToMySQL(self, df, con = conn, tbName):
    #     try:
    #         df.to_sql(
    #         con       = con, 
    #         name      = tbName, 
    #         if_exists = 'append', 
    #         flavor    = 'mysql', 
    #         index     = False
    #         )
    #     except:
    #         pass

    ############################################################################
    ## 收盘发送交易播报的邮件通知
    ############################################################################
    def sendMail(self):
        """发送邮件通知给：汉云交易员"""
        ## -----------  ----------------------------------------------------------
        if self.sendMailStatus and self.trading:
            self.sendMailStatus = False
            ## -----------------------------------------------------------------
            ## -----------------------------------------------------------------
            self.ctaEngine.mainEngine.drEngine.getIndicatorInfo(dbName = self.ctaEngine.mainEngine.dataBase,
                                                                initCapital = self.ctaEngine.mainEngine.initCapital,
                                                                flowCapitalPre = self.ctaEngine.mainEngine.flowCapitalPre,
                                                                flowCapitalToday = self.ctaEngine.mainEngine.flowCapitalToday)
            ## -----------------------------------------------------------------
            ## -----------------------------------------------------------------------------
            
            ## 如果是多策略，使用数据库
            ## 如果是单个策略，使用策略名称
            if self.ctaEngine.mainEngine.multiStrategy:
                tempID = self.ctaEngine.mainEngine.dataBase
            else:
                tempID = self.strategyID

            sender = tempID + '@hicloud.com'

            if self.ctaEngine.mainEngine.multiStrategy:
                self.tradingInfo = self.ctaEngine.mainEngine.dbMySQLQuery(
                    self.ctaEngine.mainEngine.dataBase,
                    """
                    SELECT *
                    FROM tradingInfo
                    WHERE TradingDay = '%s'
                    """ %(self.ctaEngine.tradingDay))

            ## 公司内部人员
            receiversMain = self.ctaEngine.mainEngine.mailReceiverMain
            ## 其他人员
            receiversOthers = self.ctaEngine.mainEngine.mailReceiverOthers

            ## -----------------------------------------------------------------------------
            tempFile = os.path.join('/tmp',('tradingRecord_' + tempID + '.txt'))
            with codecs.open(tempFile, "w", "utf-8") as f:
                # f.write('{0}'.format(40*'='))
                f.write('{0}'.format('\n' + 20 * '#'))
                f.write('{0}'.format(u'\n## 策略信息'))
                f.write('{0}'.format('\n' + 20 * '#'))
                f.write('{0}'.format('\n[TradingDay]: ' + self.ctaEngine.tradingDate.strftime('%Y-%m-%d')))
                f.write('{0}'.format('\n[UpdateTime]: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                f.write('{0}'.format('\n[strategyID]: ' + tempID))
                f.write('{0}'.format('\n[TraderName]: ' + self.author))
                f.write('{0}'.format('\n' + 100*'-' + '\n'))
                ## -------------------------------------------------------------------------
                f.write('{0}'.format('\n' + 20 * '#'))
                f.write('{0}'.format(u'\n## 基金净值'))
                f.write('{0}'.format('\n' + 20 * '#'))
                f.write('{0}'.format('\n' + 100*'-') + '\n')
                f.write(tabulate(self.ctaEngine.mainEngine.drEngine.accountBalance.ix[:, self.ctaEngine.mainEngine.drEngine.accountBalance.columns != 'commission'].transpose(),
                                    headers = ['Index','Value'], tablefmt = 'rst'))
                f.write('{0}'.format('\n' + 100*'-') + '\n')
                ## -------------------------------------------------------------------------
                f.write('{0}'.format('\n' + 20 * '#'))
                f.write('{0}'.format(u'\n## 基金持仓'))
                f.write('{0}'.format('\n' + 20 * '#'))
                f.write('{0}'.format('\n' + 100*'-') + '\n')
                f.write('{0}'.format(self.ctaEngine.mainEngine.drEngine.accountPosition))
                f.write('{0}'.format('\n' + 100*'-') + '\n')
                ## -------------------------------------------------------------------------
                f.write('{0}'.format('\n' + 20 * '#'))
                f.write('{0}'.format('\n## 当日已交易'))
                f.write('{0}'.format('\n' + 20 * '#'))
                f.write('{0}'.format('\n' + 100*'-') + '\n')
                if len(self.tradingInfo) != 0:
                    tempTradingInfo = self.tradingInfo
                    tempTradingInfo.index += 1
                    f.write('{0}'.format(tempTradingInfo))
                f.write('{0}'.format('\n' + 100*'-') + '\n')
                ## -------------------------------------------------------------------------
                f.write('{0}'.format('\n' + 20 * '#'))
                f.write('{0}'.format('\n## 当日未交易'))
                f.write('{0}'.format('\n' + 20 * '#'))
                f.write('{0}'.format('\n' + 100*'-') + '\n')
                if len(self.failedOrders) != 0:
                    f.write('{0}'.format(pd.DataFrame(self.failedOrders).transpose()))
                f.write('{0}'.format('\n' + 100*'-') + '\n')

            ## -----------------------------------------------------------------------------
            # message = MIMEText(stratYY.strategyID, 'plain', 'utf-8')
            fp = open(tempFile, "r")
            message = MIMEText(fp.read().decode('string-escape').decode("utf-8"), 'plain', 'utf-8')
            fp.close()

            ## 显示:发件人
            message['From'] = Header(sender, 'utf-8')
            ## 显示:收件人
            message['To']   =  Header('汉云交易员', 'utf-8')

            ## 主题
            subject = self.ctaEngine.tradingDay + '：' + self.ctaEngine.mainEngine.accountName + '『' +self.ctaEngine.mainEngine.dataBase + '』交易播报'
            message['Subject'] = Header(subject, 'utf-8')

            try:
                smtpObj = smtplib.SMTP('localhost')
                smtpObj.sendmail(sender, receiversMain, message.as_string())
                print '\n' + '#'*80
                print "邮件发送成功"
                print '#'*80
            except smtplib.SMTPException:
                print '\n' + '#'*80
                print "Error: 无法发送邮件"
                print '#'*80
            ## 间隔 1 秒
            time.sleep(1)

            ## -----------------------------------------------------------------------------
            # message = MIMEText(stratYY.strategyID, 'plain', 'utf-8')
            fp      = open(tempFile, "r")
            lines   = fp.readlines()
            l       = lines[0:([i for i in range(len(lines)) if '当日已交易' in lines[i]][0] - 1)]
            message = MIMEText(''.join(l).decode('string-escape').decode("utf-8"), 'plain', 'utf-8')
            fp.close()

            ## 显示:发件人
            message['From'] = Header(sender, 'utf-8')
            ## 显示:收件人
            message['To']   =  Header('汉云管理员', 'utf-8')

            ## 主题
            subject = self.ctaEngine.tradingDay + '：' + self.ctaEngine.mainEngine.accountName + '『' +self.ctaEngine.mainEngine.dataBase + '』交易播报'
            message['Subject'] = Header(subject, 'utf-8')

            try:
                smtpObj = smtplib.SMTP('localhost')
                smtpObj.sendmail(sender, receiversOthers, message.as_string())
                print '\n' + '#'*80
                print "邮件发送成功"
                print '#'*80
            except smtplib.SMTPException:
                print '#'*80
                print "Error: 无法发送邮件"
                print '\n' + '#'*80
            ## 间隔 1 秒
            time.sleep(1)

########################################################################
class TargetPosTemplate(CtaTemplate):
    """
    允许直接通过修改目标持仓来实现交易的策略模板
    
    开发策略时，无需再调用buy/sell/cover/short这些具体的委托指令，
    只需在策略逻辑运行完成后调用setTargetPos设置目标持仓，底层算法
    会自动完成相关交易，适合不擅长管理交易挂撤单细节的用户。    
    
    使用该模板开发策略时，请在以下回调方法中先调用母类的方法：
    onTick
    onBar
    onOrder
    
    假设策略名为TestStrategy，请在onTick回调中加上：
    super(TestStrategy, self).onTick(tick)
    
    其他方法类同。
    """
    
    className = 'TargetPosTemplate'
    author = u'量衍投资'
    
    # 目标持仓模板的基本变量
    tickAdd = 1             # 委托时相对基准价格的超价
    lastTick = None         # 最新tick数据
    lastBar = None          # 最新bar数据
    targetPos = EMPTY_INT   # 目标持仓
    orderList = []          # 委托号列表

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'targetPos']

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(TargetPosTemplate, self).__init__(ctaEngine, setting)
        
    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情推送"""
        self.lastTick = tick
        
        # 实盘模式下，启动交易后，需要根据tick的实时推送执行自动开平仓操作
        if self.trading:
            self.trade()
        
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到K线推送"""
        self.lastBar = bar
    
    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托推送"""
        if order.status == STATUS_ALLTRADED or order.status == STATUS_CANCELLED:
            self.orderList.remove(order.vtOrderID)
    
    #----------------------------------------------------------------------
    def setTargetPos(self, targetPos):
        """设置目标仓位"""
        self.targetPos = targetPos
        
        self.trade()
        
    #----------------------------------------------------------------------
    def trade(self):
        """执行交易"""
        # 先撤销之前的委托
        for vtOrderID in self.orderList:
            self.cancelOrder(vtOrderID)
        self.orderList = []
        
        # 如果目标仓位和实际仓位一致，则不进行任何操作
        posChange = self.targetPos - self.pos
        if not posChange:
            return
        
        # 确定委托基准价格，有tick数据时优先使用，否则使用bar
        longPrice = 0
        shortPrice = 0
        
        if self.lastTick:
            if posChange > 0:
                longPrice = self.lastTick.askPrice1 + self.tickAdd
            else:
                shortPrice = self.lastTick.bidPrice1 - self.tickAdd
        else:
            if posChange > 0:
                longPrice = self.lastBar.close + self.tickAdd
            else:
                shortPrice = self.lastBar.close - self.tickAdd
        
        ########################################################################
        ## william
        ## BackTesting
        ########################################################################
        # 回测模式下，采用合并平仓和反向开仓委托的方式
        if self.getEngineType() == ENGINETYPE_BACKTESTING:
            if posChange > 0:
                vtOrderID = self.buy(longPrice, abs(posChange))
            else:
                vtOrderID = self.short(shortPrice, abs(posChange))
            self.orderList.append(vtOrderID)
        
        ########################################################################
        ## william
        ## Trading
        ########################################################################
        # 实盘模式下，首先确保之前的委托都已经结束（全成、撤销）
        # 然后先发平仓委托，等待成交后，再发送新的开仓委托
        else:
            # 检查之前委托都已结束
            if self.orderList:
                return
            
            # 买入
            if posChange > 0:
                if self.pos < 0:
                    vtOrderID = self.cover(longPrice, abs(self.pos))
                else:
                    vtOrderID = self.buy(longPrice, abs(posChange))
            # 卖出
            else:
                if self.pos > 0:
                    vtOrderID = self.sell(shortPrice, abs(self.pos))
                else:
                    vtOrderID = self.short(shortPrice, abs(posChange))
            self.orderList.append(vtOrderID)
    
