# encoding: UTF-8
"""
################################################################################
@william

云扬一号
"""
################################################################################
## @william
import os
import sys
# cta_strategy_path = '/home/william/Documents/vnpy/vnpy-1.6.1/vn.trader/ctaStrategy'
cta_strategy_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(cta_strategy_path)
################################################################################

import talib
import numpy as np

from ctaBase import *
from ctaTemplate import CtaTemplate

import pandas as pd
from pandas.io import sql
from datetime import *
from eventType import *

################################################################################
class YYStrategy(CtaTemplate):
    """ 云扬一号 交易策略"""
    ############################################################################
    ## william
    # 策略类的名称和作者
    name         = 'Yun Yang'
    className    = 'YYStrategy'
    strategyID   = className
    author       = 'Lin Huangen'

    ############################################################################
    ## william
    trading   = False                   # 是否启动交易

    ############################################################################
    ## william
    ## vtOrderIDList 是一个 vtOrderID 的集合,只保存当前策略的交易信息
    vtOrderIDList = []                      # 保存委托代码的列表
    ############################################################################

    ############################################################################
    lastTickData = {}
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
    #---------------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(YYStrategy, self).__init__(ctaEngine, setting)

        ########################################################################
        ## william
        ## 交易日历
        self.todayDate = self.ctaEngine.today.date()
        ########################################################################
        self.vtSymbolList = self.ctaEngine.mainEngine.dbMySQLQuery('lhg_trade', 'select * from lhg_open_t').InstrumentID.values
        ########################################################################
        ## william
        # 注册事件监听
        self.registerEvent()
        ########################################################################

        ########################################################################
        ## william
        ## 载入持仓数据
        self.dbMySQLStratPosInfo()

        ########################################################################
        ## william
        ## 当天需要处理的订单字典
        ## 其中
        ##    key   是合约名称
        ##    value 是具体的订单, 参考
        self.tradingInfo = self.ctaEngine.mainEngine.dbMySQLQuery('lhg_trade', 'select * from lhg_open_t')
        self.tradingOrderSeq = {}
        ########################################################################
        ## william
        # 注意策略类中的可变对象属性（通常是list和dict等），在策略初始化时需要重新创建，
        # 否则会出现多个策略实例之间数据共享的情况，有可能导致潜在的策略逻辑错误风险，
        # 策略类中的这些可变对象属性可以选择不写，全都放在__init__下面，写主要是为了阅读
        # 策略时方便（更多是个编程习惯的选择）        

    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略初始化' %self.name)
        ########################################################################
        # print self.dailyData
        ########################################################################
        ## william
        print '#################################################################'
        print u"@william 策略初始化成功 !!!"
        print self.vtSymbolList
        # print self.minuteData
        print '#################################################################'

        ########################################################################
        ## william
        self.putEvent()

    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""

        # 初始化
        tempCalendar = self.ctaEngine.ChinaFuturesCalendar
        tempToday    = self.ctaEngine.today.date()
        ## =====================================================================
        ## william
        ## 策略启动的时候需要从 MySQL 的数据库 fl.positionInfo 载入各个策略的持仓情况
        self.dbMySQLStratPosInfo()

        ########################################################################
        ## william
        ## 先计算今天需要处理的订单命令
        ## self.tradingOrderSeq
        if len(self.stratPosInfo) != 0:
            ####################################################################
            x = list(set(self.tradingInfo.InstrumentID.values) & set(self.stratPosInfo.InstrumentID.values))
            # print x
            if len(x) != 0:
                for i in x:
                    tempVolume = int(self.tradingInfo.loc[self.tradingInfo.InstrumentID == i, 'volume'].values)

                    if self.stratPosInfo.loc[self.stratPosInfo.InstrumentID == i, 'direction'].values == 'long':
                        if self.tradingInfo.loc[self.tradingInfo.InstrumentID == i, 'direction'].values == 1:
                            pass
                        else:
                            tempDirection = 'sell'
                            self.tradingOrderSeq[i] = {'direction':tempDirection,
                                                  'volume':tempVolume}
                    else:
                        if self.tradingInfo.loc[self.tradingInfo.InstrumentID == i, 'direction'].values == 1:
                            tempDirection = 'cover'
                            self.tradingOrderSeq[i] = {'direction':tempDirection,
                                                  'volume':tempVolume}
                        else:
                            pass

            # print tradingOrderSeq

            y = [i for i in self.stratPosInfo.InstrumentID.values if i not in self.tradingInfo.InstrumentID.values]
            # print y
            if len(y) != 0:
                for i in y:
                    tempTradingDay = pd.to_datetime(self.stratPosInfo.loc[self.stratPosInfo.InstrumentID == i, 'TradingDay'].values[0]).strftime('%Y%m%d')
                    tempHoldingDays = self.ctaEngine.ChinaFuturesCalendar[self.ctaEngine.ChinaFuturesCalendar.days.between(tempTradingDay,self.ctaEngine.mainEngine.tradingDay, inclusive = True)].shape[0] - 1
                    if tempHoldingDays >= 5:
                        tempVolume = int(self.stratPosInfo.loc[self.stratPosInfo.InstrumentID == i, 'volume'].values)

                        if self.stratPosInfo.loc[self.stratPosInfo.InstrumentID == i, 'direction'].values == 'long':
                            tempDirection = 'sell'
                        else:
                            tempDirection = 'cover'
                        
                        self.tradingOrderSeq[i] = {'direction':tempDirection, 'volume':tempVolume}
            # print tradingOrderSeq

            z = [i for i in self.tradingInfo.InstrumentID.values if i not in self.stratPosInfo.InstrumentID.values]
            # print z
            if len(z) != 0:
                for i in z:
                    if self.tradingInfo.loc[self.tradingInfo.InstrumentID == i, 'direction'].values == 1:
                        tempDirection = 'buy'
                    elif self.tradingInfo.loc[self.tradingInfo.InstrumentID == i, 'direction'].values == -1:
                        tempDirection = 'short'
                    else:
                        pass
                    tempVolume = int(self.tradingInfo.loc[self.tradingInfo.InstrumentID == i, 'volume'].values)
                    self.tradingOrderSeq[i] = {'direction':tempDirection, 'volume':tempVolume}
            # print tradingOrderSeq
            ####################################################################
        else:
        # [如果原来的持仓是空的]
        # 如果原来的持仓是空的,
        # 则只需要处理单日发出的信号
            ####################################################################
            for i in self.tradingInfo.InstrumentID.values:
                if self.tradingInfo.loc[self.tradingInfo.InstrumentID == i, 'direction'].values == 1:
                    tempDirection = 'buy'
                elif self.tradingInfo.loc[self.tradingInfo.InstrumentID == i, 'direction'].values == -1:
                    tempDirection = 'short'
                else:
                    pass
                tempVolume = int(self.tradingInfo.loc[self.tradingInfo.InstrumentID == i, 'volume'].values)
                self.tradingOrderSeq[i] = {'direction':tempDirection,
                                           'volume':tempVolume}
        ########################################################################

        print '#################################################################'
        print u'%s策略启动' %self.name
        print '#################################################################'
        self.writeCtaLog(u'%s策略启动' %self.name)
        self.putEvent()

    #---------------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        print '#################################################################'
        print u'%s策略停止' %self.name
        print '#################################################################'
        self.writeCtaLog(u'%s策略停止' %self.name)
        self.putEvent()

    #---------------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        if datetime.now().hour == 14 and datetime.now().minute >= 30:
            ####################################################################
            ## william
            ## 这个 tick 已经是 CtaTickData, 已经处理接收的数据
            ## Ref: /ctaStragegy/ class CtaEngine/ def processTickEvent(self, event):
            if tick.vtSymbol in self.vtSymbolList:
                self.lastTickData[tick.vtSymbol] = tick.__dict__
            ####################################################################
        ########################################################################
        ## william
        ## 
        if datetime.now().hour == 14 and datetime.now().minute >= 59 and datetime.now().second >= 53 and datetime.now().second % 2 == 0:
            ####################################################################
            ## william
            ## 保证有 lastTickData
            # if len(self.vtSymbolList) <= len(self.lastTickData.keys()):
            if tick.vtSymbol in self.tradingOrderSeq.keys():
                self.sendTradingOrder(tick.vtSymbol)
        # 发出状态更新事件
        self.putEvent()

    #---------------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        # 发出状态更新事件
        self.putEvent()

    #---------------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    #---------------------------------------------------------------------------
    def onTrade(self, trade):
        # 发出状态更新事件
        self.putEvent()


    def sendTradingOrder(self, vtSymbol):
        """发送单个合约的订单"""
        ## .....................................................................
        stratWorkingOrders  = []
        stratTradedSymbols  = []

        for orderID in self.vtOrderIDList:
            tempWorkingOrder = self.ctaEngine.mainEngine.getAllOrders()[self.ctaEngine.mainEngine.getAllOrders().vtSymbol == vtSymbol][self.ctaEngine.mainEngine.getAllOrders().orderID == orderID][self.ctaEngine.mainEngine.getAllOrders().status == u'未成交'].orderID.values
            if len(tempWorkingOrder) != 0 and tempWorkingOrder not in stratWorkingOrders:
                stratWorkingOrders.append(tempWorkingOrder[0])

            tempTradedSymbol = self.ctaEngine.mainEngine.getAllOrders()[self.ctaEngine.mainEngine.getAllOrders().vtSymbol == vtSymbol][self.ctaEngine.mainEngine.getAllOrders().vtOrderID == orderID][self.ctaEngine.mainEngine.getAllOrders().status == u'全部成交'].vtSymbol.values
            if len(tempTradedSymbol) != 0 and tempTradedSymbol not in stratTradedSymbols:
                stratTradedSymbols.append(tempTradedSymbol[0])
        ## .....................................................................

        ## .....................................................................
        if len(stratWorkingOrders) != 0:
            for orderID in stratWorkingOrders:
                self.cancelOrder(orderID)
        elif len(stratWorkingOrders) == 0 and vtSymbol not in stratTradedSymbols:
            tempInstrumentID = vtSymbol
            tempPriceTick    = self.ctaEngine.mainEngine.getContract(tempInstrumentID).priceTick
            tempAskPrice1    = self.lastTickData[tempInstrumentID]['askPrice1']
            tempBidPrice1    = self.lastTickData[tempInstrumentID]['bidPrice1']
            tempDirection    = self.tradingOrderSeq[tempInstrumentID]['direction']
            tempVolume       = self.tradingOrderSeq[tempInstrumentID]['volume']

            ############################################################
            if tempDirection == 'buy':
                ## 如果是买入, AskPrice 需要增加一个 priceTick 的滑点
                tempPrice = tempAskPrice1 + tempPriceTick
                vtOrderID = self.buy(vtSymbol = tempInstrumentID, price = tempPrice, volume = tempVolume)
                self.vtOrderIDList.append(vtOrderID)
            elif tempDirection == 'short':
                ## 如果是卖出, BidPrice 需要减少一个 priceTick 的滑点
                tempPrice = tempBidPrice1 - tempPriceTick
                vtOrderID = self.short(vtSymbol = tempInstrumentID, price = tempPrice, volume = tempVolume)
                self.vtOrderIDList.append(vtOrderID)
            elif tempDirection == 'cover':
                ## 如果是买入, AskPrice 需要增加一个 priceTick 的滑点
                tempPrice = tempAskPrice1 + tempPriceTick
                vtOrderID = self.cover(vtSymbol = tempInstrumentID, price = tempPrice, volume = tempVolume)
                self.vtOrderIDList.append(vtOrderID)
            elif tempDirection == 'sell':
                ## 如果是卖出, BidPrice 需要减少一个 priceTick 的滑点
                tempPrice = tempBidPrice1 - tempPriceTick
                vtOrderID = self.sell(vtSymbol = tempInstrumentID, price = tempPrice, volume = tempVolume)
                self.vtOrderIDList.append(vtOrderID)
            else:
                return None
                ########################################################
        ## .....................................................................

        ## .....................................................................
        self.putEvent()
        ## .....................................................................

    ############################################################################
    ## william
    ## 以下用来处理持仓仓位的问题
    ############################################################################
    def stratTradeEvent(self, event):
        """处理策略交易与持仓信息
        """
        stratTrade = event.dict_['data'].__dict__
        # print u"stratTrade.__dict__:====>"
        # # print stratTrade.__dict__
        # print u"stratTrade:==>", stratTrade

        # print self.vtOrderIDList

        ########################################################################
        ## william
        ## 更新持仓
        if stratTrade['vtOrderID'] in self.vtOrderIDList:
            ## 0 初始化持仓信息

            ## 1. strategyID
            stratTrade['strategyID'] = self.strategyID
            stratTrade['TradingDay']  = self.ctaEngine.mainEngine.tradingDay
            stratTrade['tradeTime']  = datetime.now().strftime('%Y-%m-%d') + " " +  stratTrade['tradeTime']      

            ## -----------------------------------------
            if stratTrade['direction'] == u'多':
                tempDirection = 'long'
            else:
                tempDirection = 'short'
            ## -----------------------------------------        

            ## 2. stratPosInfo
            InstrumentID = stratTrade['vtSymbol']
            if self.stratPosInfo[self.stratPosInfo.InstrumentID == InstrumentID].shape[0] == 0:
                ''' 如果没有持仓,则直接添加到持仓 '''
                tempRes = pd.DataFrame([[stratTrade['strategyID'], stratTrade['vtSymbol'], stratTrade['TradingDay'], stratTrade['tradeTime'], tempDirection,stratTrade['volume']]], columns = ['strategyID','InstrumentID','TradingDay','tradeTime','direction','volume'])
                self.stratPosInfo = self.stratPosInfo.append(tempRes)
            else:
                ''' 如果有持仓, 则需要更新数据 '''
                if self.stratPosInfo[self.stratPosInfo.InstrumentID == InstrumentID].reset_index(drop = True).loc[0,'direction'] != tempDirection:
                    self.stratPosInfo.loc[self.stratPosInfo.InstrumentID == InstrumentID,'volume'] -= stratTrade['volume']
                else:
                    self.stratPosInfo.loc[self.stratPosInfo.InstrumentID == InstrumentID,'volume'] += stratTrade['volume']

            ## 3. 更新策略的持仓数据      
            self.stratPosInfo = self.stratPosInfo[self.stratPosInfo.volume != 0]
            print self.stratPosInfo

            tempTradingInfo = pd.DataFrame([[stratTrade['strategyID'], stratTrade['vtSymbol'], stratTrade['TradingDay'], stratTrade['tradeTime'], tempDirection, stratTrade['offset'], stratTrade['volume'], stratTrade['price']]], columns = ['strategyID','InstrumentID','TradingDay','tradeTime','direction','offset','volume','price'])

            ## 4. 更新持仓信息,并写入 mysql
            self.updateStratPosInfo(self.stratPosInfo)
            self.updateTradingInfo(tempTradingInfo)

        ########################################################################

        # ######################################################################
        # 发出状态更新事件
        self.putEvent()

    #---------------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.ctaEngine.mainEngine.eventEngine.register(EVENT_TRADE, self.stratTradeEvent)

    def dbMySQLStratPosInfo(self):
        ########################################################################
        ## william
        self.stratPosInfo = self.ctaEngine.mainEngine.dbMySQLQuery('fl',"""select * from positionInfo where strategyID = '%s' """ %self.strategyID)
        if self.stratPosInfo.shape[0]:
            self.stratPosInfo.volume = self.stratPosInfo.volume.astype(int)
        ########################################################################

    #---------------------------------------------------------------------------
    ############################################################################
    ## william
    ## 从 MySQL 数据库读取策略持仓信息
    def updateStratPosInfo(self, df):
        """更新策略持仓信息"""
        conn = self.ctaEngine.mainEngine.dbMySQLConnect('fl')
        cursor = conn.cursor()
        cursor.execute(""" delete from fl.positionInfo where strategyID = '%s' """ %self.strategyID)
        # df = self.stratPosInfo
        df.to_sql(con=conn, name='positionInfo', if_exists='append', flavor='mysql', index = False)
        conn.close()

    ############################################################################
    def updateTradingInfo(self, df):
        """更新交易记录"""
        conn = self.ctaEngine.mainEngine.dbMySQLConnect('fl')
        cursor = conn.cursor()
        df.to_sql(con=conn, name='tradingInfo', if_exists='append', flavor='mysql', index = False)
        conn.close()   

    ############################################################################
    def updateTradingDay(self, strategyID, InstrumentID, TradingDay):
        """更新交易日历"""  
        conn = self.ctaEngine.mainEngine.dbMySQLConnect('fl')
        cursor = conn.cursor()
        cursor.execute("""
                        UPDATE positionInfo
                        SET TradingDay = %s
                        WHERE strategyID = %s
                        AND InstrumentID = %s
                       """, (TradingDay, strategyID, InstrumentID))
        conn.commit()
        conn.close()

