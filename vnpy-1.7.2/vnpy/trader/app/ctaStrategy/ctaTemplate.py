# encoding: UTF-8

'''
本文件包含了CTA引擎中的策略开发用模板，开发策略时需要继承CtaTemplate类。
'''

from __future__ import division
import os,sys,subprocess

from vnpy.trader.vtConstant import *
from vnpy.trader.vtObject import VtBarData
from vnpy.trader.vtEvent import *

from .ctaBase import *
from vnpy.trader import vtFunction

## -----------------------------------------------------------------------------
from logging import INFO, ERROR
import talib
import pandas as pd
from tabulate import tabulate
from pandas.io import sql
from datetime import *
import time
import math

import re,ast,json
from copy import copy

pd.set_option('display.max_rows', 1000)
## -----------------------------------------------------------------------------
reload(sys) # Python2.5 初始化后会删除 sys.setdefaultencoding 这个方法，我们需要重新载入   
sys.setdefaultencoding('utf-8')   

########################################################################
class CtaTemplate(object):
    """CTA策略模板"""
    
    # 策略类的名称和作者
    name       = EMPTY_UNICODE              # 策略实例名称
    className  = u'CtaTemplate'
    strategyID = EMPTY_STRING               # william:暂时与 className 一样
    author     = EMPTY_UNICODE
    
    # MongoDB数据库的名称，K线数据库默认为1分钟
    tickDbName = TICK_DB_NAME
    barDbName = MINUTE_DB_NAME
    
    # 策略的基本参数
    vtSymbol = EMPTY_STRING        # 交易的合约vt系统代码    
    productClass = EMPTY_STRING    # 产品类型（只有IB接口需要）
    currency = EMPTY_STRING        # 货币（只有IB接口需要）
    
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
    
    ## =========================================================================
    # 同步列表，保存了需要保存到数据库的变量名称
    syncList = ['pos']
    ## =========================================================================

    ## -------------------------------------------------------------------------
    ## 从 TickData 提取的字段
    ## -------------------------------------------------------------------------
    # lastTickFileds = ['vtSymbol', 'datetime', 'lastPrice',
    #                   'volume', 'turnover',
    #                   'openPrice', 'highestPrice', 'lowestPrice',
    #                   'bidPrice1', 'askPrice1',
    #                   'bidVolume1', 'askVolume1',
    #                   'upperLimit','lowerLimit'
    #                   ]
    # lastTickDict = {}                  # 保留最新的价格数据
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

    ## -------------------------------------------------------------------------
    tradedOrders           = {}        # 当日订单完成的情况
    tradedOrdersOpen       = {}        # 当日开盘完成的已订单
    tradedOrdersClose      = {}        # 当日收盘完成的已订单
    tradedOrdersFailedInfo = {}        # 昨天未成交订单的已交易订单
    ## -------------------------------------------------------------------------

    ## -------------------------------------------------------------------------
    tradingOrdersClosePositionAll    = {}     ## 一键全平仓的交易订单
    tradingOrdersClosePositionSymbol = {}     ## 一键平仓合约的交易订单

    ## -------------------------------------------------------------------------
    ## 各种交易订单的合成
    ## -------------------------------------------------------------------------
    vtOrderIDList           = []        # 保存委托代码的列表
    vtOrderIDListOpen       = []        # 开盘的订单
    vtOrderIDListClose      = []        # 收盘的订单
    vtOrderIDListFailedInfo = []        # 失败的合约订单存储
    vtOrderIDListUpperLower = []        # 涨跌停价格成交的订单
    ## -------------------------------------------------------------------------
    
    ## -------------------------------------------------------------------------
    vtOrderIDListClosePositionAll    = []     # 一键全平仓
    vtOrderIDListClosePositionSymbol = []     # 一键全平仓
    ## -------------------------------------------------------------------------
    vtOrderIDListAll   = []                   # 所有订单集合

    ## 子订单的拆单比例实现
    subOrdersLevel = {'level0':{'weight': 0.30, 'deltaTick': 0},
                      'level1':{'weight': 0.70, 'deltaTick': 1},
                      'level2':{'weight': 0, 'deltaTick': 2}
                     }
    totalOrderLevel = 1 + (len(subOrdersLevel) - 1) * 2

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

    ## --------------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        ## 通过 ctaEngine 调用 mainEngine
        self.ctaEngine = ctaEngine

        ## =====================================================================
        ## 交易时点
        self.tradingCloseHour    = 14
        self.tradingCloseMinute1 = 50
        self.tradingCloseMinute2 = 59
        ## =====================================================================

        ## =====================================================================
        ## 把　MySQL 数据库的　TradingDay　调整为　datetime 格式
        conn = vtFunction.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
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

        ## =====================================================================
        # 设置策略的参数
        if setting:
            d = self.__dict__
            for key in self.paramList:
                if key in setting:
                    d[key] = setting[key]
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
        self.ctaEngine.mainEngine.writeLog('-'*48, gatewayName = '')
        self.writeCtaLog(u'%s策略启动' %self.name)
        self.ctaEngine.mainEngine.writeLog('-'*48, gatewayName = '')
        self.trading = True
        self.putEvent()
        

    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        ## =====================================================================
        ## 策略停止
        ## =====================================================================
        self.writeCtaLog(u'%s策略停止' %self.name)
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
    def onStopOrder(self, so):
        """收到停止单推送（必须由用户继承实现）"""
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
    
    ## =========================================================================
    ## william
    ## =========================================================================
    #----------------------------------------------------------------------
    def sendOrder(self, vtSymbol, orderType, price, volume, stop=False):
        """发送委托"""
        if self.trading:
            # 如果stop为True，则意味着发本地停止单
            if stop:
                vtOrderIDList = self.ctaEngine.sendStopOrder(vtSymbol, orderType, price, volume, self)
            else:
                vtOrderIDList = self.ctaEngine.sendOrder(vtSymbol, orderType, price, volume, self) 
            return vtOrderIDList
        else:
            # 交易停止时发单返回空字符串
            return [] 


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
            
    #----------------------------------------------------------------------
    def cancelAll(self):
        """全部撤单"""
        self.ctaEngine.cancelAll(self.name)
    
    #----------------------------------------------------------------------
    def insertMongoTick(self, tick):
        """向数据库中插入tick数据"""
        self.ctaEngine.insertMongoData(self.tickDbName, self.vtSymbol, tick)
    
    #----------------------------------------------------------------------
    def insertMongoBar(self, bar):
        """向数据库中插入bar数据"""
        self.ctaEngine.insertMongoData(self.barDbName, self.vtSymbol, bar)
        
    #----------------------------------------------------------------------
    def loadTick(self, days):
        """读取tick数据"""
        ## =====================================================================
        ## william
        ## 
        # return self.ctaEngine.loadTick(self.tickDbName, self.vtSymbol, days)
        pass
        ## =====================================================================

    #----------------------------------------------------------------------
    def loadBar(self, days):
        """读取bar数据"""
        ## =====================================================================
        ## william
        ## 
        # return self.ctaEngine.loadBar(self.barDbName, self.vtSymbol, days)
        pass
        ## =====================================================================
    
    #----------------------------------------------------------------------
    def writeCtaLog(self, content, logLevel = INFO):
        """记录CTA日志"""
        content = self.name + ':' + content
        self.ctaEngine.writeCtaLog(content, logLevel = logLevel)
        
    #----------------------------------------------------------------------
    def putEvent(self):
        """发出策略状态变化事件"""
        self.ctaEngine.putStrategyEvent(self.name)
        
    #----------------------------------------------------------------------
    def getEngineType(self):
        """查询当前运行的环境"""
        return self.ctaEngine.engineType
    
    #----------------------------------------------------------------------
    def saveSyncData(self):
        """保存同步数据到数据库"""
        self.ctaEngine.saveSyncData(self)

    ## =========================================================================
    ## william
    ## 从 MySQL 数据库获取交易订单
    ## =========================================================================
    def fetchTradingOrders(self, stage):
        """ 从 MySQL 数据库获取交易订单 """
        ## ---------------------------------------------------------------------
        ##@param stage: 1.'open', 2.'close'
        ##@param tradingOrdersX: 1,'tradingOrdersOpen', 2.'tradingOrdersClose'
        ## ---------------------------------------------------------------------
        tempOrders = vtFunction.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
            """
            SELECT *
            FROM tradingOrders
            WHERE strategyID = '%s'
            AND TradingDay = '%s'
            AND stage = '%s'
            """ %(self.strategyID, self.ctaEngine.tradingDate, stage))
        tradingOrdersX = {}
        ## ---------------------------------------------------------------------
        if len(tempOrders) == 0:
            return tradingOrdersX
        ## ---------------------------------------------------------------------
        for i in range(len(tempOrders)):
            tempKey = tempOrders.at[i,'InstrumentID'] + '-' + tempOrders.at[i,'orderType']
            ##
            tradingOrdersX[tempKey] = {
                'vtSymbol'      : tempOrders.at[i,'InstrumentID'],
                'direction'     : tempOrders.at[i,'orderType'],
                'volume'        : tempOrders.at[i,'volume'],
                'TradingDay'    : tempOrders.at[i,'TradingDay'],
                'vtOrderIDList' : [],
                'subOrders'     : {},
                'lastTimer'     : datetime.now()
                }
            ## -----------------------------------------------------------------
            ## 开盘的拆单
            if stage == 'open':
                totalVolume = tempOrders.at[i,'volume']
                ## -------------------------------------------------------------
                if totalVolume < 3:
                    volume_2 = 0
                    volume_1 = 0
                    volume_0 = totalVolume
                elif 3 <= totalVolume < 5:
                    volume_2 = 0
                    volume_1 = 1
                    volume_0 = totalVolume - volume_1 * 2
                elif totalVolume >= 5:
                    volume_2 = totalVolume * self.subOrdersLevel['level2']['weight'] // 2
                    volume_1 = (totalVolume - volume_2*2) * self.subOrdersLevel['level1']['weight'] // 2
                    volume_0 = totalVolume - (volume_1 + volume_2) * 2
                ## --------------------------------------------------   -----------
                tradingOrdersX[tempKey]['subOrders'] = {'level0':{
                                                                 'volume': int(volume_0),
                                                                 'deltaTick': 0,
                                                                 'status': None},
                                                        'level1':{
                                                                 'volume': int(volume_1),
                                                                 'deltaTick': 1,
                                                                 'status_u': None,
                                                                 'status_d': None},
                                                        'level2':{
                                                                 'volume': int(volume_2),
                                                                 'deltaTick': 2,
                                                                 'status_u': None,
                                                                 'status_d': None}}
            ## -----------------------------------------------------------------
            self.tickTimer[tempOrders.at[i,'InstrumentID']] = datetime.now()
        ## ---------------------------------------------------------------------
        return tradingOrdersX


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
                'vtSymbol'      : failedInfo.loc[i,'InstrumentID'],
                'direction'     : tempDirection,
                'volume'        : tempVolume,
                'TradingDay'    : tempTradingDay,
                'vtOrderIDList' : []
                }
        ## =====================================================================


    def updateTradingOrdersVtOrderID(self, tradingOrders, stage):
        """
        更新交易订单的 vtOrderID
        """
        ## =====================================================================
        ## MySQL 数据库保存的活跃订单
        mysqlWorkingInfo = vtFunction.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
                            """
                            SELECT *
                            FROM workingInfo
                            WHERE strategyID = '%s'
                            AND TradingDay = %s
                            AND stage = '%s'
                            """ %(self.strategyID, self.ctaEngine.tradingDay, stage))
        if len(tradingOrders) == 0:
            return
        ## 交易所保存的活跃订单
        exchWorkingInfo = [self.ctaEngine.mainEngine.getAllWorkingOrders()[j].vtOrderID 
                           for j in range(len(self.ctaEngine.mainEngine.getAllWorkingOrders()))]            
        ## =====================================================================
        for key in tradingOrders.keys():
            temp = mysqlWorkingInfo.loc[(mysqlWorkingInfo.vtSymbol == tradingOrders[key]['vtSymbol']) & 
                                        (mysqlWorkingInfo.orderType == tradingOrders[key]['direction'])].reset_index(drop = True)
            if len(temp) == 0:
                continue
            tempVtOrderIDList = ast.literal_eval(temp.at[0,'vtOrderIDList'])

            if all(vtOrderID not in exchWorkingInfo for vtOrderID in tempVtOrderIDList):
                continue

            if (not tradingOrders[key]['vtOrderIDList']):
                tradingOrders[key]['vtOrderIDList'] = tempVtOrderIDList
            else:
                tradingOrders[key]['vtOrderIDList'] = list(
                    set(tradingOrders[key]['vtOrderIDList']) | 
                    set(tempVtOrderIDList))
            ## -----------------------------------------------------------------
            for vtOrderID in tempVtOrderIDList:
                self.ctaEngine.orderStrategyDict[vtOrderID] = self.ctaEngine.strategyDict[self.name]
        ## =====================================================================


    def updateVtOrderIDList(self, stage):
        """
        更新 vtOrderIDList
        """
        ## =====================================================================
        ## MySQL 数据库保存的活跃订单
        mysqlWorkingInfo = vtFunction.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
                            """
                            SELECT *
                            FROM workingInfo
                            WHERE strategyID = '%s'
                            AND TradingDay = %s
                            AND stage = '%s'
                            """ %(self.strategyID, self.ctaEngine.tradingDay, stage))
        if len(mysqlWorkingInfo) == 0:
            return

        tempVtOrderIDList = []
        for i in range(len(mysqlWorkingInfo)):
            tempVtOrderIDList.extend(ast.literal_eval(mysqlWorkingInfo.at[i,'vtOrderIDList']))
        ## =====================================================================
        if stage == 'open':
            self.vtOrderIDListOpen = list(set(self.vtOrderIDListOpen) |
                                          set(tempVtOrderIDList))
        else:
            self.vtOrderIDListClose = list(set(self.vtOrderIDListClose) |
                                          set(tempVtOrderIDList))

    ############################################################################
    ## william
    ## 限制价格在 UpperLimit 和 LowerLimit 之间
    ############################################################################
    def priceBetweenUpperLower(self, price, vtSymbol):
        tempUpperLimit = self.ctaEngine.lastTickDict[vtSymbol]['upperLimit']
        tempLowerLimit = self.ctaEngine.lastTickDict[vtSymbol]['lowerLimit']
        return min(max(tempLowerLimit, price), tempUpperLimit)

    ############################################################################
    ## william
    ## 处理订单，并生成相应的字典格式
    ## @param vtSymbol: 合约代码
    ## @param orderDict: 订单的字典格式
    ## @param orderIDList: 订单列表
    ############################################################################
    def prepareTradingOrder(self, vtSymbol, tradingOrders, orderIDList, 
                            priceType, price = None, addTick = 0, discount = 0):
        """处理订单"""
        ## 生成交易列表
        tempTradingList = [k for k in tradingOrders.keys() 
                             if tradingOrders[k]['vtSymbol'] == vtSymbol and
                                tradingOrders[k]['volume'] != 0]
        ## ---------------------------------------------------------------------
        if not tempTradingList:
            return
        ## ---------------------------------------------------------------------
        allOrders = self.ctaEngine.mainEngine.getAllOrdersDataFrame()
        if len(allOrders):
            tempFinishedOrders = allOrders.loc[allOrders.status.isin([u'已撤销',u'全部成交'])][\
                                               allOrders.vtSymbol == vtSymbol][\
                                               allOrders.vtOrderID.isin(orderIDList)].vtOrderID.values
        else:
            tempFinishedOrders = []

        for i in tempTradingList:
            ## -------------------------------------------------------------
            ## 如果交易量依然是大于 0 ，则需要继续发送订单命令
            ## -------------------------------------------------------------
            if ((len(allOrders) == 0) or 
                (not tradingOrders[i]['vtOrderIDList']) or 
                (all(vtOrderID in tempFinishedOrders for 
                                  vtOrderID in tradingOrders[i]['vtOrderIDList']))):
                if self.tradingEnd and ((datetime.now() - self.tickTimer[vtSymbol]).seconds > 3) and len(tradingOrders[i]['vtOrderIDList']):
                    self.tickTimer[vtSymbol] = datetime.now()
                    tempWorkingOrders = allOrders.loc[allOrders.status.isin([u'未成交',u'部分成交'])][\
                                                      allOrders.vtSymbol == vtSymbol][\
                                                      allOrders.vtOrderID.isin(orderIDList)].vtOrderID.values
                    if not tempWorkingOrders:
                        return
                    for vtOrderID in tradingOrders[i]['vtOrderIDList']:
                        if vtOrderID in tempWorkingOrders:
                            self.cancelOrder(vtOrderID)
                else:
                    self.sendTradingOrder(tradingOrders = tradingOrders,
                                          orderDict     = tradingOrders[i],
                                          orderIDList   = orderIDList,
                                          priceType     = priceType,
                                          price         = price,
                                          addTick       = addTick,
                                          discount      = discount)

    ############################################################################
    ## william
    ## 实现拆分订单
    ############################################################################
    def prepareTradingOrderSplit(self, vtSymbol, tradingOrders, orderIDList, 
                                 priceType, price = None, addTick = 0, discount = 0):
        """处理订单"""
        ## 生成交易列表

        tempTradingList = [k for k in tradingOrders.keys() 
                             if tradingOrders[k]['vtSymbol'] == vtSymbol and
                                tradingOrders[k]['volume'] != 0]
        ## ---------------------------------------------------------------------
        if not tempTradingList:
            return
        ## ---------------------------------------------------------------------
        allOrders = self.ctaEngine.mainEngine.getAllOrdersDataFrame()
        if len(allOrders):
            tempWorkingOrders  = allOrders.loc[allOrders.status.isin([u'未成交',u'部分成交'])][\
                                               allOrders.vtSymbol == vtSymbol][\
                                               allOrders.vtOrderID.isin(orderIDList)]
            tempWorkingVolume = sum(tempWorkingOrders.totalVolume)
        else:
            # tempWorkingOrders = []
            tempWorkingVolume = 0

        for i in tempTradingList:
            ## -------------------------------------------------------------
            ## 如果交易量依然是大于 0 ，则需要继续发送订单命令
            ## -------------------------------------------------------------
            if self.tradingStart:
                totalVolume = tradingOrders[i]['subOrders']['level0']['volume'] + \
                              sum([tradingOrders[i]['subOrders'][l]['volume'] for l in ['level1','level2']]) * 2
                ## ---------------------------------------------------------------------------------
                if len(allOrders):
                    tempFinishedOrders  = allOrders.loc[allOrders.status.isin([u'已撤销',u'全部成交'])][\
                                                       allOrders.vtSymbol == vtSymbol][\
                                                       allOrders.vtOrderID.isin(orderIDList)]
                    tempFinishedVolume = sum(tempFinishedOrders.totalVolume)
                else:
                    tempFinishedVolume = 0
                ## 指定价格
                remainingVolume = totalVolume - tempWorkingVolume - tempFinishedVolume
                if remainingVolume <= 0:
                    return
                ## ---------------------------------------------------------------------------------
                
                ## ---------------------------------------------------------------------------------
                if tradingOrders[i]['direction'] == u'buy':
                    price_0 = self.ctaEngine.lastTickDict[vtSymbol]['openPrice'] * (1 - discount)
                elif tradingOrders[i]['direction'] == u'short':
                    price_0 = self.ctaEngine.lastTickDict[vtSymbol]['openPrice'] * (1 + discount)
                ## ---------------------------------------------------------------------------------
                
                ## ---------------------------------------------------------------------------------
                for l in ['level2', 'level1']:
                    ## ---------------------------------------------------------
                    if tradingOrders[i]['subOrders'][l]['volume'] == 0:
                        continue
                    ## ---------------------------------------------------------
                    deltaTick = tradingOrders[i]['subOrders'][l]['deltaTick']
                    deltaTick_quick = deltaTick
                    deltaTick_slow  = -deltaTick

                    if tradingOrders[i]['direction'] == u'buy':
                        status_quick    = 'status_u'
                        status_slow     = 'status_d'
                    elif tradingOrders[i]['direction'] == u'short':
                        status_quick    = 'status_d'
                        status_slow     = 'status_u'

                    ## ---------------------------------------------------------
                    if not tradingOrders[i]['subOrders'][l][status_quick]:
                        self.sendTradingOrder(tradingOrders = tradingOrders,
                                              orderDict     = tradingOrders[i],
                                              orderIDList   = orderIDList,
                                              priceType     = 'limit',
                                              volume        = tradingOrders[i]['subOrders'][l]['volume'],
                                              price         = price_0,
                                              addTick       = deltaTick_quick)
                        tradingOrders[i]['subOrders'][l][status_quick] = 'sended'
                        return
                        ## -----------------------------------------------------
                    else:
                        ## -------------------------------------------------------------------------
                        if not tradingOrders[i]['subOrders']['level0']['status']:
                            self.sendTradingOrder(tradingOrders = tradingOrders,
                                                  orderDict     = tradingOrders[i],
                                                  orderIDList   = orderIDList,
                                                  priceType     = 'limit',
                                                  volume        = tradingOrders[i]['subOrders']['level0']['volume'],
                                                  price         = price_0)
                            tradingOrders[i]['subOrders']['level0']['status'] = 'sended'
                            return
                        ## -------------------------------------------------------------------------
                        elif not tradingOrders[i]['subOrders'][l][status_slow]:
                            self.sendTradingOrder(tradingOrders = tradingOrders,
                                                  orderDict     = tradingOrders[i],
                                                  orderIDList   = orderIDList,
                                                  priceType     = 'limit',
                                                  volume        = tradingOrders[i]['subOrders'][l]['volume'],
                                                  price         = price_0,
                                                  addTick       = deltaTick_slow)
                            tradingOrders[i]['subOrders'][l][status_slow] = 'sended'
                            return
                            ## -----------------------------------------------------
                ## ---------------------------------------------------------------------------------

                # ---------------------------------------------------------------------------------
                # leve0 是肯定都要发的
                if ((not tradingOrders[i]['subOrders']['level0']['status']) and 
                    tradingOrders[i]['subOrders']['level0']['volume'] == tradingOrders[i]['volume']):
                    self.sendTradingOrder(tradingOrders = tradingOrders,
                                          orderDict     = tradingOrders[i],
                                          orderIDList   = orderIDList,
                                          priceType     = 'limit',
                                          volume        = tradingOrders[i]['subOrders']['level0']['volume'],
                                          price         = price_0)
                    tradingOrders[i]['subOrders']['level0']['status'] = 'sended'
                    return
                # ---------------------------------------------------------------------------------

            elif (self.tradingBetween and 
                 (datetime.now() - tradingOrders[i]['lastTimer']).seconds >= 55):
                ## -------------------------------------------------------------
                remainingMinute = self.tradingCloseMinute2-1 - datetime.now().minute
                if remainingMinute == 0:
                    return
                remainingVolume = int(math.ceil(
                    (tradingOrders[i]['volume'] - tempWorkingVolume) / float(remainingMinute)))
                if remainingVolume == 0:
                    return
                ## -------------------------------------------------------------
                self.sendTradingOrder(tradingOrders = tradingOrders,
                                      orderDict     = tradingOrders[i],
                                      orderIDList   = orderIDList,
                                      priceType     = priceType,
                                      volume        = remainingVolume,
                                      price         = price,
                                      addTick       = addTick,
                                      discount      = discount)
                tradingOrders[i]['lastTimer'] = datetime.now()

    ############################################################################
    ## 根据订单的字典格式，发送订单给 CTP
    ## @param stratTrade: 交易事件数据
    ## @param orderDict: 订单的字典格式
    ## @param orderIDList: 订单列表
    ## @param addTick 控制增加的价格
    ############################################################################
    def sendTradingOrder(self, tradingOrders, orderDict, orderIDList, 
                         priceType, price = None, 
                         volume = None, addTick = 0, discount = 0):
        """发送单个合约的订单"""

        ## =====================================================================
        ## 基本信息
        ## ---------------------------------------------------------------------
        tempInstrumentID = orderDict['vtSymbol']
        tempPriceTick    = self.ctaEngine.tickInfo[tempInstrumentID]['priceTick']
        tempAskPrice1    = self.ctaEngine.lastTickDict[tempInstrumentID]['askPrice1']
        tempBidPrice1    = self.ctaEngine.lastTickDict[tempInstrumentID]['bidPrice1']
        tempLastPrice    = self.ctaEngine.lastTickDict[tempInstrumentID]['lastPrice']
        tempDirection    = orderDict['direction']
        if volume:
            tempVolume   = volume
        else:
            tempVolume   = orderDict['volume']

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
            tempBestPrice = self.ctaEngine.lastTickDict[tempInstrumentID]['openPrice']
        elif priceType == 'upper':
            tempBestPrice = self.ctaEngine.lastTickDict[tempInstrumentID]['upperLimit']
        elif priceType == 'lower':
            tempBestPrice = self.ctaEngine.lastTickDict[tempInstrumentID]['lowerLimit']
        elif priceType == 'limit':
            if price:
                tempBestPrice = price
            else:
                print "错误的价格"
                return None
        ## =====================================================================


        ## =====================================================================
        ## 限定价格在 UpperLimit 和 LowerLimit 之间
        ## ---------------------------------------------------------------------
        if tempDirection in ['buy','cover']:
            tempPrice = self.priceBetweenUpperLower(
                tempBestPrice * (1-discount) + tempPriceTick * addTick, 
                tempInstrumentID)
        elif tempDirection in ['short','sell']:
            tempPrice = self.priceBetweenUpperLower(
                tempBestPrice * (1+discount) - tempPriceTick * addTick, 
                tempInstrumentID)
        ## =====================================================================

        ## =====================================================================
        ## 开始下单
        ## ---------------------------------------------------------------------
        if tempDirection == 'buy':
            vtOrderIDList = self.buy(vtSymbol = tempInstrumentID, price = tempPrice, volume = tempVolume)
        elif tempDirection == 'short':
            vtOrderIDList = self.short(vtSymbol = tempInstrumentID, price = tempPrice, volume = tempVolume)
        elif tempDirection == 'cover':
            vtOrderIDList = self.cover(vtSymbol = tempInstrumentID, price = tempPrice, volume = tempVolume)
        elif tempDirection == 'sell':
            vtOrderIDList = self.sell(vtSymbol = tempInstrumentID, price = tempPrice, volume = tempVolume)
        ## =====================================================================
        
        ## =====================================================================
        ## 更新信息
        ## ---------------------------------------------------------------------
        orderIDList.extend(vtOrderIDList)
        self.tickTimer[tempInstrumentID]= datetime.now()
        ## ---------------------------------------------------------------------
        
        ## ---------------------------------------------------------------------
        ## orderNo: 已经下单的次数计数
        ## 未来可以用于控制订单
        tempKey = tempInstrumentID + '-' + tempDirection
        tradingOrders[tempKey]['vtOrderIDList'].extend(vtOrderIDList)
        if 'orderNo' not in tradingOrders[tempKey].keys():
            tradingOrders[tempKey]['orderNo'] = 1
        else:
            tradingOrders[tempKey]['orderNo'] += 1
        ## ---------------------------------------------------------------------

        ## .....................................................................
        # self.putEvent()
        ## .....................................................................


    ############################################################################
    ## 更新 交易状态
    ## self.trading
    ## self.tradingStart
    ## self.tradingEnd
    ## self.tradingBetween
    ############################################################################
    def updateTradingStatus(self):
        h = datetime.now().hour
        m = datetime.now().minute
        s = datetime.now().second
        ## =====================================================================
        ## 启动尾盘交易
        ## =====================================================================
        if ((h in [8,20] and m >= 59 and s >= 45) or 
           ( ((21 <= h <= 24) or (0 <= h <= 2) or (9 <= h <= (self.tradingCloseHour-1))) and m <= 59 ) or 
           (h == self.tradingCloseHour and m < self.tradingCloseMinute1)):
            self.tradingStart = True
        else:
            self.tradingStart = False

        ## ---------------------------------------------------------------------
        if (h == self.tradingCloseHour and 
           (self.tradingCloseMinute1+1) <= m < (self.tradingCloseMinute2-1)):
            self.tradingBetween = True
        else:
            self.tradingBetween = False

        ## ---------------------------------------------------------------------
        if (h == self.tradingCloseHour and m == self.tradingCloseMinute2 and 
           (s >= (59 - max(15, len(self.tradingOrdersClose)*1.0)))):
            self.tradingEnd = True
        else:
            self.tradingEnd = False
        ## ---------------------------------------------------------------------

        ## =====================================================================
        ## 如果是开盘交易
        ## 则取消开盘交易的所有订单
        if (h == self.tradingCloseHour and 
            (self.tradingCloseMinute1 <= m <= self.tradingCloseMinute1 or
             self.tradingCloseMinute2-1) <= m <= (self.tradingCloseMinute2-1) and 
            s <= 20 and (s % 10 == 0)):
            ## -----------------------------------------------------------------
            if (len(self.vtOrderIDListOpen) != 0 or 
                len(self.vtOrderIDListClose) != 0 or 
                len(self.vtOrderIDListUpperLower) != 0):
                allOrders = self.ctaEngine.mainEngine.getAllOrdersDataFrame()
                for vtOrderID in self.vtOrderIDListOpen + self.vtOrderIDListClose + self.vtOrderIDListUpperLower:
                    if vtOrderID in allOrders.loc[allOrders.status.isin([u'未成交',u'部分成交'])].vtOrderID.values:
                            self.cancelOrder(vtOrderID)
            ## -----------------------------------------------------------------
        ## =====================================================================

        ## =====================================================================
        ## 如果是收盘交易
        ## 则取消开盘交易的所有订单
        # if (h == self.tradingCloseHour and 
        #     (self.tradingCloseMinute2-1) <= m <= (self.tradingCloseMinute2-1) and 
        #     s <= 20 and (s % 10 == 0)):
        #     ## -----------------------------------------------------------------
        #     if (len(self.vtOrderIDListOpen) != 0 or 
        #         len(self.vtOrderIDListClose) != 0):
        #         allOrders = self.ctaEngine.mainEngine.getAllOrdersDataFrame()
        #         for vtOrderID in self.vtOrderIDListOpen + self.vtOrderIDListClose:
        #             if vtOrderID in allOrders.loc[allOrders.status.isin([u'未成交',u'部分成交'])].vtOrderID.values:
        #                     self.cancelOrder(vtOrderID)
            ## -----------------------------------------------------------------
        ## =====================================================================

        ## =====================================================================
        ## 生成收盘交易的订单
        if (h == self.tradingCloseHour and 
            m in [self.tradingCloseMinute1, (self.tradingCloseMinute2-1)] and 
            20 <= s < 30  and 
            self.ctaEngine.mainEngine.multiStrategy and 
            (s == 29 or s % 10 == 0)):
            self.writeCtaLog(u'Rscript end_signal.R')
            subprocess.call(['Rscript',
                             os.path.join(self.ctaEngine.mainEngine.ROOT_PATH,
                             'vnpy/trader/app/ctaStrategy/Rscripts',
                             'end_signal.R'),
                             self.ctaEngine.mainEngine.ROOT_PATH, 
                             self.ctaEngine.mainEngine.dataBase], 
                             shell = False)

        ## =====================================================================
        ## 从 MySQL 数据库提取尾盘需要平仓的持仓信息
        ## postionInfoClose
        ## =====================================================================
        if (h == self.tradingCloseHour and 
            m in [self.tradingCloseMinute1, (self.tradingCloseMinute2-1)] and 
            30 <= s <= 59 and (s % 10 == 0 or len(self.tradingOrdersClose) == 0)):
            ## -----------------------------------------------------------------
            conn = vtFunction.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
            cursor = conn.cursor()
            cursor.execute("""
                            TRUNCATE TABLE workingInfo
                           """)
            conn.commit()
            conn.close()
            ## -----------------------------------------------------------------  



    ############################################################################
    ## 更新 workingInfo
    ############################################################################
    def updateWorkingInfo(self, tradingOrders, stage):
        """
        更新 workingInfo 表格
        """
        if not tradingOrders:
            return
        
        tempWorkingInfo = vtFunction.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
                                    """
                                    SELECT *
                                    FROM workingInfo
                                    WHERE strategyID = '%s'
                                    AND TradingDay = '%s'
                                    AND stage = '%s'
                                    """ %(self.strategyID, self.ctaEngine.tradingDay, stage))

        dfHeader = ['TradingDay','strategyID','vtSymbol','vtOrderIDList',
                    'orderType','volume','stage']
        dfData   = []

        for k in tradingOrders.keys():
            temp = copy(tradingOrders[k])
            if not temp['vtOrderIDList']:
                continue
            temp['strategyID'] = self.strategyID
            temp['orderType'] = temp['direction']
            temp['vtOrderIDList'] = json.dumps(temp['vtOrderIDList'])
            temp['stage'] = stage
            dfData.append([temp[kk] for kk in dfHeader])
        df = pd.DataFrame(dfData, columns = dfHeader)

        ## ---------------------------------------------------------------------
        conn = vtFunction.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
        cursor = conn.cursor()
        cursor.execute("""
                        DELETE FROM workingInfo
                        WHERE strategyID = '%s'
                        AND stage = '%s'
                       """ %(self.strategyID, stage))
        conn.commit()
        conn.close()
        self.saveMySQL(df = df, tbl = 'workingInfo', over = 'append')
        ## ---------------------------------------------------------------------


    ############################################################################
    ## 更新交易记录的数据表
    ############################################################################
    def updateTradingInfo(self, df):
        """更新交易记录"""
        self.saveMySQL(df = df, 
                       tbl = 'tradingInfo',
                       over = 'append')


    ############################################################################
    ## 更新订单表
    ############################################################################
    def updateTradingOrdersTable(self, stratTrade):
        """
        更新交易订单表
        """
        ## =====================================================================
        conn = vtFunction.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
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
        mysqlInfoTradingOrders = vtFunction.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
                                """
                                SELECT *
                                FROM tradingOrders
                                WHERE strategyID = '%s'
                                AND InstrumentID = '%s'
                                AND orderType = '%s'
                                """ %(self.strategyID,self.stratTrade['vtSymbol'],
                                      tempDirection))
        if not len(mysqlInfoTradingOrders):
            return
        ## ---------------------------------------------------------------------
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
    ## 更新订单字典
    ## orderInfo
    ############################################################################
    def updateOrderInfo(self):
        """
        更新订单记录表 orderInfo
        """
        ## =====================================================================
        ## 1. 更新账户信息
        ## 2. 更新 orderInfo
        ## =====================================================================

        ## 把账户信息写入 MysQL 数据库
        ## =====================================================================
        self.ctaEngine.mainEngine.dataEngine.getIndicatorInfo(
            dbName = self.ctaEngine.mainEngine.dataBase,
            initialCapital = self.ctaEngine.mainEngine.initialCapital,
            flowCapitalPre = self.ctaEngine.mainEngine.flowCapitalPre,
            flowCapitalToday = self.ctaEngine.mainEngine.flowCapitalToday)
        ## =====================================================================
        ## 把所有下单记录写入 MySQL 数据库
        mysqlOrderInfo = vtFunction.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
                        """
                        SELECT *
                        FROM orderInfo
                        WHERE strategyID = '%s'
                        AND TradingDay = %s
                       """ %(self.strategyID, self.ctaEngine.tradingDay))
        stratOrderIDListAll = self.vtOrderIDListOpen + self.vtOrderIDListClose + self.vtOrderIDListFailedInfo + self.vtOrderIDListUpperLower
        tempOrderIDList = [k for k in stratOrderIDListAll if k not in mysqlOrderInfo['vtOrderID'].values]
        ## ---------------------------------------------------------------------
        if len(tempOrderIDList) == 0:
            return 
        ## ---------------------------------------------------------------------
        df = pd.DataFrame([], columns = self.orderInfoFields)
        for i in tempOrderIDList:
            tempOrderInfo = self.ctaEngine.mainEngine.getAllOrdersDataFrame().loc[self.ctaEngine.mainEngine.getAllOrdersDataFrame().vtOrderID == i]
            tempOrderInfo['strategyID'] = self.strategyID
            df = df.append(tempOrderInfo[self.orderInfoFields], ignore_index=True)
        df = df[self.orderInfoFields]
        df['TradingDay'] = self.ctaEngine.tradingDate
        df['strategyID'] = self.strategyID
        df = df[['TradingDay'] + self.orderInfoFields]
        ## 改名字
        df.columns.values[3] = 'InstrumentID'
        if len(mysqlOrderInfo) != 0:
            df = df.append(mysqlOrderInfo, ignore_index=True)
        if len(df) != 0:
            ## -----------------------------------------------------------------
            conn = vtFunction.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
            cursor = conn.cursor()
            ## 清空记录
            cursor.execute("""
                            DELETE FROM orderInfo
                            WHERE strategyID = %s
                            AND TradingDay = %s
                           """, (self.strategyID, self.ctaEngine.tradingDay))
            conn.commit()
            conn.close()
            ## 写入记录
            ## 去掉重复的行
            df = df.drop_duplicates().reset_index(drop = True)
            self.saveMySQL(df = df, tbl = 'orderInfo', over = 'append')
        ## =====================================================================


    ############################################################################
    ## 更新失败未成交订单
    ############################################################################
    def updateFailedInfo(self, tradingOrders, tradedOrders):
        """更新收盘后未成交的订单"""

        ## 提取失败订单
        self.failedOrders = {k:tradingOrders[k] 
                             for k in tradingOrders.keys() if k not in tradedOrders.keys()}
        ## -----------------------------------------------------------------
        if not self.failedOrders:
            return
        ## -----------------------------------------------------------------

        ## =============================================================================
        dfData = []
        ## -------------------------------------------------------------
        for k in self.failedOrders.keys():
            ## ---------------------------------------------------------
            if self.failedOrders[k]['direction'] == 'buy':
                tempDirection = 'long'
                tempOffset    = u'开仓'
            elif self.failedOrders[k]['direction'] == 'sell':
                tempDirection    = 'short'
                tempDirectionPos = 'long'
                tempOffset       = u'平仓'
            elif self.failedOrders[k]['direction'] == 'short':
                tempDirection = 'short'
                tempOffset    = u'开仓'
            elif self.failedOrders[k]['direction'] == 'cover':
                tempDirection    = 'long'
                tempDirectionPos = 'short'
                tempOffset       = u'平仓'
            ## ---------------------------------------------------------
            tempRes = [self.strategyID, self.failedOrders[k]['vtSymbol'], 
                       self.failedOrders[k]['TradingDay'], 
                       tempDirection, tempOffset, self.failedOrders[k]['volume']]
            dfData.append(tempRes)
            ## ---------------------------------------------------------

            ## -----------------------------------------------------------------------------
            ## 只有需要平仓的，才需要从 positionInfo 数据表剔除
            ## -----------------------------------------------------------------------------
            if self.failedOrders[k]['direction'] in ['sell', 'cover']:
                try:
                    cursor.execute("""
                                    DELETE FROM positionInfo
                                    WHERE strategyID = %s
                                    AND InstrumentID = %s
                                    AND TradingDay = %s
                                    AND direction  = %s
                                   """, (self.strategyID, self.failedOrders[k]['vtSymbol'], self.failedOrders[k]['TradingDay'], tempDirectionPos))
                    conn.commit()
                except:
                    None
            ## -------------------------------------------------------------------------

        df = pd.DataFrame(dfData, columns = self.failedInfoFields)
        ## -------------------------------------------------------------
        conn = vtFunction.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
        cursor = conn.cursor()
        cursor.execute("""
                        DELETE FROM failedInfo
                        WHERE strategyID = %s
                        AND TradingDay = %s
                       """,(self.strategyID, self.ctaEngine.tradingDay))
        conn.commit()
        conn.close()
        ## =============================================================================
        self.saveMySQL(df = df, tbl = 'failedInfo', over = 'append')
        ## =====================================================================
        
        ## =====================================================================



    ############################################################################
    ## 订单成交后
    ## 处理 开仓的订单
    ############################################################################
    def processOffsetOpen(self, stratTrade):
        """处理开仓订单"""
       
        ## =====================================================================
        ## 1. 更新 mysql.positionInfo
        ## =====================================================================
        ## mysqlPositionInfo: 存储在 mysql 数据库的持仓信息，需要更新
        mysqlPositionInfo = vtFunction.dbMySQLQuery(
            self.ctaEngine.mainEngine.dataBase,
            """
            SELECT *
            FROM positionInfo
            WHERE strategyID = '%s'
            """ %(self.strategyID))

        ## 看看是不是已经在数据库里面了
        tempPosInfo = mysqlPositionInfo.loc[mysqlPositionInfo.InstrumentID == stratTrade['InstrumentID']][\
                                            mysqlPositionInfo.TradingDay == stratTrade['TradingDay']][\
                                            mysqlPositionInfo.direction == stratTrade['direction']]
        ## ---------------------------------------------------------------------
        conn   = vtFunction.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
        cursor = conn.cursor()
        ## ---------------------------------------------------------------------
        if len(tempPosInfo) == 0:
            ## 如果不在
            ## 则直接添加过去即可
            try:
                tempFields = ['strategyID','InstrumentID','TradingDay','direction','volume']
                tempRes = pd.DataFrame([[stratTrade[k] for k in tempFields]], columns = tempFields)
                self.saveMySQL(df = tempRes, tbl = 'positionInfo', over = 'append')
            except:
                self.writeCtaLog(u'processOffsetOpen 开仓订单 写入 MySQL 数据库出错',
                                 logLevel = ERROR)
        else:
            ## 如果在
            ## 则需要更新数据
            mysqlPositionInfo.at[tempPosInfo.index[0], 'volume'] += stratTrade['volume']
            mysqlPositionInfo = mysqlPositionInfo.loc[mysqlPositionInfo.volume != 0]
            try:
                cursor.execute("""
                                DELETE FROM positionInfo
                                WHERE strategyID = '%s'
                               """ %(self.strategyID))
                conn.commit()
                self.saveMySQL(df = mysqlPositionInfo, tbl = 'positionInfo', over = 'append')
            except:
                self.writeCtaLog(u'processOffsetOpen 开仓订单 写入 MySQL 数据库出错',
                                 logLevel = ERROR)
            finally:
                conn.close()
        ## -----------------------------------------------------------------


    ############################################################################
    ## 订单成交后
    ## 处理 平仓的订单
    ############################################################################
    def processOffsetClose(self, stratTrade):
        """处理开仓订单"""

        ## ---------------------------------------------------------------------
        if stratTrade['direction'] == 'long':
            tempDirectionPos = 'short'
        elif stratTrade['direction'] == 'short':
            tempDirectionPos = 'long'
        ## ---------------------------------------------------------------------

        ## =====================================================================
        ## mysqlPositionInfo: 存储在 mysql 数据库的持仓信息，需要更新
        mysqlPositionInfo = vtFunction.dbMySQLQuery(
            self.ctaEngine.mainEngine.dataBase,
            """
            SELECT *
            FROM positionInfo
            WHERE strategyID = '%s'
            """ %(self.strategyID))
        tempPosInfo = mysqlPositionInfo.loc[mysqlPositionInfo.InstrumentID == stratTrade['InstrumentID']][\
                                            mysqlPositionInfo.direction == tempDirectionPos].sort_values(by='TradingDay', ascending = True)
        ## ---------------------------------------------------------------------------------
        for i in range(len(tempPosInfo)):
            tempResVolume = tempPosInfo.loc[tempPosInfo.index[i],'volume'] - stratTrade['volume']
            mysqlPositionInfo.at[tempPosInfo.index[i], 'volume'] = tempResVolume
            if tempResVolume >= 0:
                break
        ## ---------------------------------------------------------------------------------
        mysqlPositionInfo = mysqlPositionInfo.loc[mysqlPositionInfo.volume > 0]   
        ## ---------------------------------------------------------------------
        conn   = vtFunction.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
        cursor = conn.cursor()
        ## ---------------------------------------------------------------------
        try:
            cursor.execute("""
                            DELETE FROM positionInfo
                            WHERE strategyID = '%s'
                           """ %(self.strategyID))
            conn.commit()
            self.saveMySQL(df = mysqlPositionInfo, tbl = 'positionInfo', over = 'append')
        except:
            self.writeCtaLog(u'processOffsetClose 平仓订单 写入 MySQL 数据库出错', 
                               logLevel = ERROR)
        finally:
            conn.close()
        ## =========================================================================


    ############################################################################
    ## 订单成交后
    ## 处理 failedInfo
    ############################################################################
    def processTradingOrdersFailedInfo(self, stratTrade):
        """处理昨日未成交失败的订单，需要更新 failedInfo"""
        mysqlFailedInfo = vtFunction.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
                """
                SELECT *
                FROM failedInfo
                WHERE strategyID = '%s'
                """ %(self.strategyID))
        ## ---------------------------------------------------------------------
        if len(mysqlFailedInfo) == 0:
            return
        ## ---------------------------------------------------------------------

        ## ---------------------------------------------------------------------
        tempPosInfo = mysqlFailedInfo.loc[mysqlFailedInfo.InstrumentID == stratTrade['InstrumentID']][\
                                          mysqlFailedInfo.direction == stratTrade['direction']][\
                                          mysqlFailedInfo.offset == stratTrade['offset']]

        mysqlFailedInfo.at[tempPosInfo.index[0], 'volume'] -= stratTrade['volume']
        mysqlFailedInfo = mysqlFailedInfo.loc[mysqlFailedInfo.volume != 0]
        ## ---------------------------------------------------------------------
        conn   = vtFunction.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
        cursor = conn.cursor()
        ## ---------------------------------------------------------------------
        try:
            cursor.execute("""
                            DELETE FROM failedInfo
                            WHERE strategyID = '%s'
                           """ %(self.strategyID))
            conn.commit()
            self.saveMySQL(df = mysqlFailedInfo, tbl = 'failedInfo', over = 'append')
        except:
            self.writeCtaLog(u'processTradingOrdersFailedInfo 昨日未成交订单 写入 MySQL 数据库出错',
                             logLevel = ERROR)
        finally:
            conn.close()
        ## ---------------------------------------------------------------------

    ############################################################################
    ## 从 MySQL 数据库读取数据
    ############################################################################
    def fetchMySQL(self, query):
        vtFunction.fetchMySQL(db    = self.ctaEngine.mainEngine.dataBase, 
                              query = query)

    ############################################################################
    ## 保存数据 DataFrame 格式到 MySQL
    ############################################################################
    def saveMySQL(self, df, tbl, over):
        vtFunction.saveMySQL(df   = df, 
                             db   = self.ctaEngine.mainEngine.dataBase, 
                             tbl  = tbl, 
                             over = over)

    
########################################################################
class BarManager(object):
    """
    K线合成器，支持：
    1. 基于Tick合成1分钟K线
    2. 基于1分钟K线合成X分钟K线（X可以是2、3、5、10、15、30、60）
    """

    #----------------------------------------------------------------------
    def __init__(self, onBar, xmin=0, onXminBar=None):
        """Constructor"""
        self.bar = None             # 1分钟K线对象
        self.onBar = onBar          # 1分钟K线回调函数
        
        self.xminBar = None         # X分钟K线对象
        self.xmin = xmin            # X的值
        self.onXminBar = onXminBar  # X分钟K线的回调函数
        
        self.lastTick = None        # 上一TICK缓存对象
        
    #----------------------------------------------------------------------
    def updateTick(self, tick):
        """TICK更新"""
        newMinute = False   # 默认不是新的一分钟
        
        # 尚未创建对象
        if not self.bar:
            self.bar = VtBarData()
            newMinute = True
        # 新的一分钟
        elif self.bar.datetime.minute != tick.datetime.minute:
            # 生成上一分钟K线的时间戳
            self.bar.datetime = self.bar.datetime.replace(second=0, microsecond=0)  # 将秒和微秒设为0
            self.bar.date = self.bar.datetime.strftime('%Y%m%d')
            self.bar.time = self.bar.datetime.strftime('%H:%M:%S.%f')
            
            # 推送已经结束的上一分钟K线
            self.onBar(self.bar)
            
            # 创建新的K线对象
            self.bar = VtBarData()
            newMinute = True
            
        # 初始化新一分钟的K线数据
        if newMinute:
            self.bar.vtSymbol = tick.vtSymbol
            self.bar.symbol = tick.symbol
            self.bar.exchange = tick.exchange

            self.bar.open = tick.lastPrice
            self.bar.high = tick.lastPrice
            self.bar.low = tick.lastPrice
        # 累加更新老一分钟的K线数据
        else:                                   
            self.bar.high = max(self.bar.high, tick.lastPrice)
            self.bar.low = min(self.bar.low, tick.lastPrice)

        # 通用更新部分
        self.bar.close = tick.lastPrice        
        self.bar.datetime = tick.datetime  
        self.bar.openInterest = tick.openInterest
   
        if self.lastTick:
            self.bar.volume += (tick.volume - self.lastTick.volume) # 当前K线内的成交量
            
        # 缓存Tick
        self.lastTick = tick

    #----------------------------------------------------------------------
    def updateBar(self, bar):
        """1分钟K线更新"""
        # 尚未创建对象
        if not self.xminBar:
            self.xminBar = VtBarData()
            
            self.xminBar.vtSymbol = bar.vtSymbol
            self.xminBar.symbol = bar.symbol
            self.xminBar.exchange = bar.exchange
        
            self.xminBar.open = bar.open
            self.xminBar.high = bar.high
            self.xminBar.low = bar.low            
            
            self.xminBar.datetime = bar.datetime    # 以第一根分钟K线的开始时间戳作为X分钟线的时间戳
        # 累加老K线
        else:
            self.xminBar.high = max(self.xminBar.high, bar.high)
            self.xminBar.low = min(self.xminBar.low, bar.low)
    
        # 通用部分
        self.xminBar.close = bar.close        
        self.xminBar.openInterest = bar.openInterest
        self.xminBar.volume += int(bar.volume)                
            
        # X分钟已经走完
        if not (bar.datetime.minute + 1) % self.xmin:   # 可以用X整除
            # 生成上一X分钟K线的时间戳
            self.xminBar.datetime = self.xminBar.datetime.replace(second=0, microsecond=0)  # 将秒和微秒设为0
            self.xminBar.date = self.xminBar.datetime.strftime('%Y%m%d')
            self.xminBar.time = self.xminBar.datetime.strftime('%H:%M:%S.%f')
            
            # 推送
            self.onXminBar(self.xminBar)
            
            # 清空老K线缓存对象
            self.xminBar = None


########################################################################
class ArrayManager(object):
    """
    K线序列管理工具，负责：
    1. K线时间序列的维护
    2. 常用技术指标的计算
    """

    #----------------------------------------------------------------------
    def __init__(self, size=100):
        """Constructor"""
        self.count = 0                      # 缓存计数
        self.size = size                    # 缓存大小
        self.inited = False                 # True if count>=size
        
        self.openArray = np.zeros(size)     # OHLC
        self.highArray = np.zeros(size)
        self.lowArray = np.zeros(size)
        self.closeArray = np.zeros(size)
        self.volumeArray = np.zeros(size)
        
    #----------------------------------------------------------------------
    def updateBar(self, bar):
        """更新K线"""
        self.count += 1
        if not self.inited and self.count >= self.size:
            self.inited = True
        
        self.openArray[0:self.size-1] = self.openArray[1:self.size]
        self.highArray[0:self.size-1] = self.highArray[1:self.size]
        self.lowArray[0:self.size-1] = self.lowArray[1:self.size]
        self.closeArray[0:self.size-1] = self.closeArray[1:self.size]
        self.volumeArray[0:self.size-1] = self.volumeArray[1:self.size]
    
        self.openArray[-1] = bar.open
        self.highArray[-1] = bar.high
        self.lowArray[-1] = bar.low        
        self.closeArray[-1] = bar.close
        self.volumeArray[-1] = bar.volume
        
    #----------------------------------------------------------------------
    @property
    def open(self):
        """获取开盘价序列"""
        return self.openArray
        
    #----------------------------------------------------------------------
    @property
    def high(self):
        """获取最高价序列"""
        return self.highArray
    
    #----------------------------------------------------------------------
    @property
    def low(self):
        """获取最低价序列"""
        return self.lowArray
    
    #----------------------------------------------------------------------
    @property
    def close(self):
        """获取收盘价序列"""
        return self.closeArray
    
    #----------------------------------------------------------------------
    @property    
    def volume(self):
        """获取成交量序列"""
        return self.volumeArray
    
    #----------------------------------------------------------------------
    def sma(self, n, array=False):
        """简单均线"""
        result = talib.SMA(self.close, n)
        if array:
            return result
        return result[-1]
        
    #----------------------------------------------------------------------
    def std(self, n, array=False):
        """标准差"""
        result = talib.STDDEV(self.close, n)
        if array:
            return result
        return result[-1]
    
    #----------------------------------------------------------------------
    def cci(self, n, array=False):
        """CCI指标"""
        result = talib.CCI(self.high, self.low, self.close, n)
        if array:
            return result
        return result[-1]
        
    #----------------------------------------------------------------------
    def atr(self, n, array=False):
        """ATR指标"""
        result = talib.ATR(self.high, self.low, self.close, n)
        if array:
            return result
        return result[-1]
        
    #----------------------------------------------------------------------
    def rsi(self, n, array=False):
        """RSI指标"""
        result = talib.RSI(self.close, n)
        if array:
            return result
        return result[-1]
    
    #----------------------------------------------------------------------
    def macd(self, fastPeriod, slowPeriod, signalPeriod, array=False):
        """MACD指标"""
        macd, signal, hist = talib.MACD(self.close, fastPeriod,
                                        slowPeriod, signalPeriod)
        if array:
            return macd, signal, hist
        return macd[-1], signal[-1], hist[-1]
    
    #----------------------------------------------------------------------
    def adx(self, n, array=False):
        """ADX指标"""
        result = talib.ADX(self.high, self.low, self.close, n)
        if array:
            return result
        return result[-1]
    
    #----------------------------------------------------------------------
    def boll(self, n, dev, array=False):
        """布林通道"""
        mid = self.sma(n, array)
        std = self.std(n, array)
        
        up = mid + std * dev
        down = mid - std * dev
        
        return up, down    
    
    #----------------------------------------------------------------------
    def keltner(self, n, dev, array=False):
        """肯特纳通道"""
        mid = self.sma(n, array)
        atr = self.atr(n, array)
        
        up = mid + atr * dev
        down = mid - atr * dev
        
        return up, down
    
    #----------------------------------------------------------------------
    def donchian(self, n, array=False):
        """唐奇安通道"""
        up = talib.MAX(self.high, n)
        down = talib.MIN(self.low, n)
        
        if array:
            return up, down
        return up[-1], down[-1]
