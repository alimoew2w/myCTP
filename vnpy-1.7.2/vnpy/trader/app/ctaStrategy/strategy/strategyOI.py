# encoding: UTF-8

"""
OIStrategy 策略的交易实现
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
import numpy as np
import pandas as pd
from pandas.io import sql
from tabulate import tabulate

from datetime import *
import time
import pprint
from copy import copy
import re,ast,json
## -----------------------------------------------------------------------------


########################################################################
class OIStrategy(CtaTemplate):
    """ oiRank 交易策略 """
    ############################################################################
    ## william
    ## 策略类的名称和作者
    ## -------------------------------------------------------------------------
    name         = u'OiRank'
    className    = u'OIStrategy'
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
    inited       = False                    # 是否进行了初始化
    trading      = False                    # 是否启动交易，由引擎管理
    tradingStart = False                    # 开盘启动交易
    tradingEnd   = False                    # 收盘开启交易
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
    tradingOrdersUpperLower = {}       # 以涨跌停价格的订单
    ## -------------------------------------------------------------------------
    tradingOrdersFailedInfo = {}       # 上一个交易日没有完成的订单,需要优先处理
    ## -------------------------------------------------------------------------
    tradedOrders           = {}        # 当日订单完成的情况
    tradedOrdersOpen       = {}        # 当日开盘完成的已订单
    tradedOrdersClose      = {}        # 当日收盘完成的已订单
    tradedOrdersFailedInfo = {}        # 昨天未成交订单的已交易订单
    tradedOrdersUpperLower = {}        # 已经成交的涨跌停订单
    ## -------------------------------------------------------------------------

    ## -------------------------------------------------------------------------
    ## 各种交易订单的合成
    ## -------------------------------------------------------------------------
    vtOrderIDList           = []        # 保存委托代码的列表
    vtOrderIDListOpen       = []        # 开盘的订单
    vtOrderIDListClose      = []        # 收盘的订单
    vtOrderIDListFailedInfo = []        # 失败的合约订单存储
    vtOrderIDListUpperLower = []        # 涨跌停价格成交的订单
    vtOrderIDListAll        = []        # 所有订单集合
    ## -------------------------------------------------------------------------

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        ## 从　ctaEngine 继承所有属性和方法
        super(OIStrategy, self).__init__(ctaEngine, setting)

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

        ## =====================================================================
        ## 涨跌停的订单
        temp = vtFunction.dbMySQLQuery(
            self.ctaEngine.mainEngine.dataBase,
            """
            SELECT *
            FROM UpperLowerInfo
            WHERE strategyID = '%s'
            AND TradingDay = '%s'
            """ %(self.strategyID, self.ctaEngine.tradingDate))
        if len(temp):
            for i in range(len(temp)):
                self.vtOrderIDListUpperLower.extend(ast.literal_eval(temp.ix[i,'vtOrderIDList']))
        ## =====================================================================
        
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
            self.tradingOrdersOpen = self.fetchTradingOrders(stage = 'open')
            self.updateTradingOrdersVtOrderID(tradingOrders = self.tradingOrdersOpen,
                                              stage = 'open')
            self.updateVtOrderIDList('open')
        else:
            # self.generateTradingOrders()
            pass
        ## =====================================================================
        ## 如果上一个交易日有未完成的订单,需要优先处理
        ## =====================================================================
        ## ---------------------------------------------------------------------
        self.processFailedInfo(self.failedInfo)
        ## ---------------------------------------------------------------------
        if self.tradingOrdersFailedInfo:
            self.writeCtaLog("昨日失败需要执行的订单\n%s\n%s\n%s" 
                %('-'*80,
                  pprint.pformat(self.tradingOrdersFailedInfo),
                  '-'*80))
        if self.tradingOrdersOpen:
            self.writeCtaLog("当日开盘需要执行的订单\n%s\n%s\n%s" 
                %('-'*80,
                  pprint.pformat(self.tradingOrdersOpen),
                  '-'*80))

        ## ---------------------------------------------------------------------
        try:
            self.positionContracts = self.ctaEngine.mainEngine.dataEngine.positionInfo.keys()
        except:
            self.positionContracts = []
        tempSymbolList = list(set(self.tradingOrdersOpen[k]['vtSymbol'] for k in self.tradingOrdersOpen.keys()) | 
                              set(self.ctaEngine.allContracts) |
                              set(self.positionContracts))
        for symbol in tempSymbolList:
            if symbol not in self.tickTimer.keys():
                self.tickTimer[symbol] = datetime.now()
        ## =====================================================================
        self.putEvent()
        ## =====================================================================

    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        # pass

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
        elif ((datetime.now() - self.tickTimer[tick.vtSymbol]).seconds <= 2):
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
        if (tick.vtSymbol in [self.tradingOrdersOpen[k]['vtSymbol'] \
                             for k in self.tradingOrdersOpen.keys()] and 
            self.tradingStart and not self.tradingEnd):
            ####################################################################
            self.prepareTradingOrder(vtSymbol      = tick.vtSymbol, 
                                     tradingOrders = self.tradingOrdersOpen, 
                                     orderIDList   = self.vtOrderIDListOpen,
                                     priceType     = 'last',
                                     addTick       = -1)
        ## =====================================================================


    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        """处理成交订单"""
        # print trade.__dict__
        self.tickTimer[trade.vtSymbol] = datetime.now()
        ## ---------------------------------------------------------------------
        
        ## =====================================================================
        ## 连接 MySQL 设置
        conn   = vtFunction.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
        cursor = conn.cursor()
        ## =====================================================================

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

        tempKey = self.stratTrade['vtSymbol'] + '-' + tempDirection
        ## ---------------------------------------------------------------------
        # print self.stratTrade

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

        ## ---------------------------------------------------------------------
        tempFields = ['strategyID','InstrumentID','TradingDay','direction','volume']
        tempRes = pd.DataFrame([[self.stratTrade[k] for k in tempFields]], columns = tempFields)
        ## =====================================================================

        ## =====================================================================
        ## 连接 MySQL 设置
        conn   = vtFunction.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
        cursor = conn.cursor()
        ## =====================================================================

        ## =====================================================================
        ## 2. 更新 positionInfo
        ## =====================================================================
        if self.stratTrade['offset'] == u'开仓':
            # ################################################################
            # ## 1. 更新 mysql.positionInfo
            # ################################################################
            # ## mysqlPositionInfo: 存储在 mysql 数据库的持仓信息，需要更新
            # mysqlPositionInfo = vtFunction.dbMySQLQuery(
            #     self.ctaEngine.mainEngine.dataBase,
            #     """
            #     SELECT *
            #     FROM positionInfo
            #     WHERE strategyID = '%s'
            #     """ %(self.strategyID))

            # ## 看看是不是已经在数据库里面了
            # tempPosInfo = mysqlPositionInfo.loc[mysqlPositionInfo.InstrumentID == self.stratTrade['InstrumentID']][\
            #                                     mysqlPositionInfo.TradingDay == self.stratTrade['TradingDay']][\
            #                                     mysqlPositionInfo.direction == self.stratTrade['direction']]
            # if len(tempPosInfo) == 0:
            #     ## 如果不在
            #     ## 则直接添加过去即可
            #     try:
            #         tempRes.to_sql(con=conn, 
            #             name      ='positionInfo', 
            #             if_exists ='append', 
            #             flavor    ='mysql', 
            #             index     = False)
            #     except:
            #         print "\n"+'#'*80
            #         print '写入 MySQL 数据库出错'
            #         print '#'*80+"\n"
            # else:
            #     ## 如果在
            #     ## 则需要更新数据
            #     mysqlPositionInfo.at[tempPosInfo.index[0], 'volume'] += tempRes.loc[0,'volume']
            #     mysqlPositionInfo = mysqlPositionInfo.loc[mysqlPositionInfo.volume != 0]
            #     try:
            #         cursor.execute("""
            #                         DELETE FROM positionInfo
            #                         WHERE strategyID = '%s'
            #                        """ %(self.strategyID))
            #         conn.commit()
            #         mysqlPositionInfo.to_sql(
            #             con       = conn, 
            #             name      = 'positionInfo', 
            #             if_exists = 'append', 
            #             flavor    = 'mysql', 
            #             index     =  False)
            #         # conn.close()
            #     except:
            #         print "\n"+'#'*80
            #         print '写入 MySQL 数据库出错'
            #         print '#'*80+"\n"
            # ## -----------------------------------------------------------------
            
            self.processOffsetOpen(self.strateTrade)
            ## =================================================================
            ## william
            ## 如果有开仓的情况，则相应的发出平仓的订单，
            ## 成交价格为　UpperLimit / LowerLimit 的 (?)
            if self.tradingStart:
                ## -------------------------------------------------------------
                ## 1. 「开多」 --> sell@upper
                ## 2. 「开空」 --> cover@lower
                if self.stratTrade['direction'] == 'long':
                    tempDirection = 'sell'
                    tempPriceType = 'upper'
                    # tempPriceType = 'last'
                elif self.stratTrade['direction'] == 'short':
                    tempDirection = 'cover'
                    tempPriceType = 'lower'
                    # tempPriceType = 'last'
                ## -------------------------------------------------------------
                tempKey = self.stratTrade['vtSymbol'] + '-' + tempDirection
                ## -------------------------------------------------------------
                ## 生成 tradingOrdersUpperLower
                self.tradingOrdersUpperLower[tempKey] = {
                        'vtSymbol'      : self.stratTrade['vtSymbol'],
                        'direction'     : tempDirection,
                        'volume'        : self.stratTrade['volume'],
                        'TradingDay'    : self.stratTrade['TradingDay'],
                        'vtOrderIDList' : []
                }
                ## -------------------------------------------------------------
                time.sleep(1)
                ## -------------------------------------------------------------
                # if re.sub('[0-9]', '', self.stratTrade['vtSymbol']) in ['i','jm','j']:
                #     tempAddTick = -2
                # elif re.sub('[0-9]', '', self.stratTrade['vtSymbol']) in ['rb']:
                #     tempAddTick = -10
                # else:
                #     tempAddTick = -8
                ## -------------------------------------------------------------
                tempAddTick = 1
                ## -------------------------------------------------------------

                ## -------------------------------------------------------------
                self.prepareTradingOrder(vtSymbol      = self.stratTrade['vtSymbol'], 
                                         tradingOrders = self.tradingOrdersUpperLower, 
                                         orderIDList   = self.vtOrderIDListUpperLower,
                                         priceType     = tempPriceType,
                                         addTick       = tempAddTick)
                # --------------------------------------------------------------
                # 获得 vtOrderID
                tempFields = ['TradingDay','vtSymbol','vtOrderIDList','direction','volume']
                self.tradingOrdersUpperLower[tempKey]['vtOrderIDList'] = json.dumps(self.tradingOrdersUpperLower[tempKey]['vtOrderIDList'])
                tempRes = pd.DataFrame([[self.tradingOrdersUpperLower[tempKey][k] for k in tempFields]], 
                                       columns = tempFields)
                tempRes.insert(1,'strategyID', self.strategyID)
                tempRes.rename(columns={'vtSymbol':'InstrumentID'}, inplace = True)
                try:
                    tempRes.to_sql(con=conn, name='UpperLowerInfo', 
                                   if_exists='append', flavor='mysql', index = False)
                except:
                    print "\n"+'#'*80
                    print '写入 MySQL 数据库出错'
                    print '#'*80+"\n"
            ## =================================================================

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
                mysqlFailedInfo = vtFunction.dbMySQLQuery(
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
                    try:
                        cursor.execute("""
                                        DELETE FROM failedInfo
                                        WHERE strategyID = '%s'
                                       """ %(self.strategyID))
                        conn.commit()
                        mysqlFailedInfo.to_sql(con=conn, 
                            name      ='failedInfo', 
                            if_exists ='append', 
                            flavor    ='mysql', 
                            index     = False)
                    except:
                        self.writeCtaLog(u'%s onTrade 执行平仓成交订单 写入 MySQL 数据库出错' %self.strategyID,
                                         logLevel = ERROR)
                    #-------------------------------------------------------------------
            elif self.stratTrade['vtOrderID'] in list(set(self.vtOrderIDListClose) |
                                                      set(self.vtOrderIDListUpperLower)):
                ## 只有在 tradingOrders 的平仓信息，需要更新到数据库
                ## 因为 failedInfo 已经把未成交的订单记录下来了
                ## =================================================================================
                ## mysqlPositionInfo: 存储在 mysql 数据库的持仓信息，需要更新
                mysqlPositionInfo = vtFunction.dbMySQLQuery(
                    self.ctaEngine.mainEngine.dataBase,
                    """
                    SELECT *
                    FROM positionInfo
                    WHERE strategyID = '%s'
                    """ %(self.strategyID))
                tempPosInfo = mysqlPositionInfo.loc[mysqlPositionInfo.InstrumentID == self.stratTrade['InstrumentID']][mysqlPositionInfo.direction == tempDirection].sort_values(by='TradingDay', ascending = True)
                ## ---------------------------------------------------------------------------------
                for i in range(len(tempPosInfo)):
                    tempResVolume = tempPosInfo.loc[tempPosInfo.index[i],'volume'] - tempRes.at[0,'volume']
                    mysqlPositionInfo.at[tempPosInfo.index[i], 'volume'] = tempResVolume
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
                    mysqlPositionInfo.to_sql(
                        con       = conn, 
                        name      = 'positionInfo', 
                        if_exists = 'append', 
                        flavor    = 'mysql', 
                        index     = False)
                except:
                    self.writeCtaLog(u'%s onTrade 执行平仓成交订单 写入 MySQL 数据库出错' %self.strategyID,
                                         logLevel = ERROR)
                ## =================================================================================
        
        #=======================================================================
        if self.stratTrade['vtOrderID'] in self.vtOrderIDListFailedInfo:
            # mysqlFailedInfo = vtFunction.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
            #         """
            #         SELECT *
            #         FROM failedInfo
            #         WHERE strategyID = '%s'
            #         """ %(self.strategyID))

            # #-------------------------------------------------------------------
            # if len(mysqlFailedInfo) != 0:
            #     #---------------------------------------------------------------
            #     tempPosInfo = mysqlFailedInfo.loc[mysqlFailedInfo.InstrumentID == self.stratTrade['InstrumentID']][mysqlFailedInfo.direction == self.stratTrade['direction']][mysqlFailedInfo.offset == tempOffset]

            #     mysqlFailedInfo.at[tempPosInfo.index[0], 'volume'] -= self.stratTrade['volume']
            #     mysqlFailedInfo = mysqlFailedInfo.loc[mysqlFailedInfo.volume != 0]
            #     try:
            #         cursor.execute("""
            #                         DELETE FROM failedInfo
            #                         WHERE strategyID = '%s'
            #                        """ %(self.strategyID))
            #         conn.commit()
            #         mysqlFailedInfo.to_sql(
            #             con       = conn, 
            #             name      = 'failedInfo', 
            #             if_exists = 'append', 
            #             flavor    = 'mysql', 
            #             index     = False)
            #     except:
            #         print '\n' + '#'*80 
            #         print '写入 MySQL 数据库出错'
            #         print '#'*80 + '\n'
            #     #---------------------------------------------------------------
            self.processTradingOrdersFailedInfo(self.stratTrade)
            ## 更新 failedInfo
            # self.failedInfo = vtFunction.dbMySQLQuery(self.ctaEngine.mainEngine.dataBase,
            #         """
            #         SELECT *
            #         FROM failedInfo
            #         WHERE strategyID = '%s'
            #         """ %(self.strategyID))
        #-----------------------------------------------------------------------
        #=======================================================================        


        ## ---------------------------------------------------------------------
        tempTradingInfo = pd.DataFrame([[self.stratTrade[k] for k in self.tradingInfoFields]], 
            columns = self.tradingInfoFields)
        self.updateTradingInfo(df = tempTradingInfo, tbName = 'tradingInfo')
        self.tradingInfo = self.tradingInfo.append(tempTradingInfo, ignore_index=True)
        ## ---------------------------------------------------------------------

        conn.close()

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
    def updateTradingStatus(self, event):
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
            self.tradingCloseMinute1 <= m <= self.tradingCloseMinute1 and 
            s <= 20 and (s % 5 == 0)):
            ## -----------------------------------------------------------------
            if (len(self.vtOrderIDListOpen) != 0 or 
                len(self.vtOrderIDListUpperLower) != 0):
                allOrders = self.ctaEngine.mainEngine.getAllOrdersDataFrame()
                for vtOrderID in self.vtOrderIDListOpen + self.vtOrderIDListUpperLower:
                    if vtOrderID in allOrders.loc[allOrders.status.isin([u'未成交',u'部分成交'])].vtOrderID.values:
                            self.cancelOrder(vtOrderID)
            ## -----------------------------------------------------------------
        ## =====================================================================

        ## =====================================================================
        ## 如果是收盘交易
        ## 则取消开盘交易的所有订单
        if (h == self.tradingCloseHour and 
            (self.tradingCloseMinute2-1) <= m <= (self.tradingCloseMinute2-1) and 
            s <= 20 and (s % 5 == 0)):
            ## -----------------------------------------------------------------
            if len(self.vtOrderIDListClose) != 0:
                allOrders = self.ctaEngine.mainEngine.getAllOrdersDataFrame()
                for vtOrderID in self.vtOrderIDListClose:
                    if vtOrderID in allOrders.loc[allOrders.status.isin([u'未成交',u'部分成交'])].vtOrderID.values:
                            self.cancelOrder(vtOrderID)
            ## -----------------------------------------------------------------
        ## =====================================================================

        ## =====================================================================
        ## 生成收盘交易的订单
        if (h == self.tradingCloseHour and 
            m in [self.tradingCloseMinute1, (self.tradingCloseMinute2-1)] and 
            20 <= s < 30  and 
            self.ctaEngine.mainEngine.multiStrategy and 
            (s == 29 or s % 10 == 0)):
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
            ## 持仓合约信息
            
            ## -----------------------------------------------------------------
            conn = vtFunction.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
            cursor = conn.cursor()
            cursor.execute("""
                            TRUNCATE TABLE workingInfo
                           """)
            conn.commit()
            ## -----------------------------------------------------------------            

            ## =================================================================
            self.positionInfo = vtFunction.dbMySQLQuery(
                self.ctaEngine.mainEngine.dataBase,
                """
                SELECT *
                FROM positionInfo
                WHERE strategyID = '%s'
                """ %(self.strategyID))
            ## =================================================================

            ## =================================================================
            if self.ctaEngine.mainEngine.multiStrategy:
                self.tradingOrdersClose = self.fetchTradingOrders(stage = 'close')
                self.updateTradingOrdersVtOrderID(tradingOrders = self.tradingOrdersClose,
                                                  stage = 'close')
                self.updateVtOrderIDList('close')
            ## =================================================================

            conn.close()
        ## =====================================================================



        ## =====================================================================
        ## 更新 workingInfo
        ## =====================================================================
        if ((m % 5 == 0) and (s == 15) and self.tradingStart):
            self.updateWorkingInfo(self.tradingOrdersOpen, 'open')
            self.updateWorkingInfo(self.tradingOrdersClose, 'close')
            self.updateOrderInfo()
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
        self.ctaEngine.eventEngine.register(EVENT_TIMER, self.updateTradingStatus)
        ## ---------------------------------------------------------------------
