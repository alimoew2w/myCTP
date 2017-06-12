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
from ctaBase import *
from ctaTemplate import CtaTemplate

import numpy as np
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
    ## william
    ## 用于保存每个合约最后(最新)一条 tick 的数据
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

    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(YYStrategy, self).__init__(ctaEngine, setting)

        ########################################################################
        ## william
        ## 交易日历
        self.todayDate = self.ctaEngine.today.date()
        ########################################################################

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
        self.openInfo = self.ctaEngine.mainEngine.dbMySQLQuery('lhg_trade',
                            """
                            SELECT * 
                            FROM lhg_open_t
                            """)
        lastTradingDay = self.ctaEngine.ChinaFuturesCalendar.loc[self.ctaEngine.ChinaFuturesCalendar.days < self.ctaEngine.mainEngine.tradingDay, 'days'].max()

        self.openInfo = self.openInfo[self.openInfo.TradingDay == datetime.strptime(lastTradingDay,'%Y%m%d').date().strftime('%Y-%m-%d')]
        
        self.failedInfo = self.ctaEngine.mainEngine.dbMySQLQuery('fl_trade',
                            """
                            SELECT * 
                            FROM failedInfo
                            """)

        self.positionInfo = self.ctaEngine.mainEngine.dbMySQLQuery('fl_trade',
                            """
                            SELECT * 
                            FROM positionInfo
                            """)

        self.tradingOrders = {}
        self.tradedOrders  = {}
        self.failedOrders  = {}

        self.vtSymbolList = list(set(self.openInfo.InstrumentID.values) |
                                 set(self.failedInfo.InstrumentID.values) |
                                 set(self.positionInfo.InstrumentID.values)
                                )
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
        # 策略初始化
        ## =====================================================================
        self.writeCtaLog(u'%s策略初始化' %self.name)
        ########################################################################

        ########################################################################
        ## william
        print '#################################################################'
        print u"@william 策略初始化成功 !!!"
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

        ## =====================================================================
        ## 1.先计算持仓的信息
        ## =====================================================================
        if len(self.positionInfo) != 0:
            ## -----------------------------------------------------------------
            ## 排除当天已经成交的订单
            self.positionInfoToday = self.positionInfo[self.positionInfo.TradingDay == datetime.strptime(self.ctaEngine.mainEngine.tradingDay,'%Y%m%d').date()]

            if len(self.positionInfoToday) != 0:
                tempInstrumentID = self.positionInfoToday.InstrumentID.values
                for i in range(len(tempInstrumentID)):
                    temp = tempInstrumentID[i]
                    self.openInfo.drop(self.openInfo[self.openInfo.InstrumentID == temp].index, inplace = True)
                self.openInfo = self.openInfo.reset_index(drop=True)
            ## -----------------------------------------------------------------

            ## -----------------------------------------------------------------
            ## 计算持仓超过5天的
            for i in range(len(self.positionInfo)):
                tempTradingDay = self.positionInfo.loc[i,'TradingDay']
                tempHoldingDays = self.ctaEngine.ChinaFuturesCalendar[self.ctaEngine.ChinaFuturesCalendar.days.between(tempTradingDay.strftime('%Y%m%d'), self.ctaEngine.mainEngine.tradingDay, inclusive = True)].shape[0] - 1
                self.positionInfo.loc[i,'holdingDays'] = tempHoldingDays
            ## -----------------------------------------------------------------

            self.positionInfo = self.positionInfo[self.positionInfo.holdingDays >= 5]

        ## =====================================================================
        ## 2.计算开仓的信息
        ## =====================================================================
        if len(self.positionInfo) == 0:
            ## 没有 5 天以上的合约, 不进行处理
            ## 只处理 openInfo
            if len(self.openInfo) != 0:
                for i in range(len(self.openInfo)):
                    ## direction
                    if self.openInfo.loc[i,'direction'] == 1:
                        tempDirection = 'buy'
                    elif self.openInfo.loc[i,'direction'] == -1:
                        tempDirection = 'short'
                    else:
                        pass
                    ## volume
                    tempVolume = int(self.openInfo.loc[i,'volume'])
                    tempKey = self.openInfo.loc[i,'InstrumentID'] + '-' + tempDirection
                    self.tradingOrders[tempKey] = {'vtSymbol':self.openInfo.loc[i,'InstrumentID'],
                                                   'direction':tempDirection,
                                                   'volume':tempVolume}
            else:
                print "\n#######################################################################"
                print u'今天没有需要交易的订单'
                self.onStop()
                print u'停止策略 %s' %self.name
                print "#######################################################################\n"
        else:
            if len(self.openInfo) == 0:
                ## 当天没有开仓信息
                ## 只需要处理持仓超过5天的信息
                for i in range(len(self.positionInfo)):
                    ## direction
                    if self.positionInfo.loc[i,'direction'] == 'long':
                        tempDirection = 'sell'
                    elif self.positionInfo.loc[i,'direction'] == 'short':
                        tempDirection = 'cover'
                    else:
                        pass
                    ## volume
                    tempVolume = int(self.positionInfo.loc[i,'volume'])
                    tempKey = self.positionInfo.loc[i,'InstrumentID'] + '-' + tempDirection
                    self.tradingOrders[tempKey] = {'vtSymbol':self.positionInfo.loc[i,'InstrumentID'],
                                                   'direction':tempDirection,
                                                   'volume':tempVolume}
            else:
                ## 如果当天有持仓
                ## 又有开仓
                ## x: 交集
                ## y: positionInfo
                ## z: openInfo
                x = list(set(self.positionInfo.InstrumentID.values) & set(self.openInfo.InstrumentID.values))
                y = [i for i in self.positionInfo.InstrumentID.values if i not in self.openInfo.InstrumentID.values]
                z = [i for i in self.openInfo.InstrumentID.values if i not in self.positionInfo.InstrumentID.values]

                ## =============================================================
                if len(x) != 0:
                    for i in x:
                        ## direction
                        if self.positionInfo.loc[self.positionInfo.InstrumentID == i, 'direction'].values == 'long':
                            if self.openInfo.loc[self.openInfo.InstrumentID == i, 'direction'].values == 1:
                                tempTradingDay = self.positionInfo.loc[self.positionInfo.InstrumentID == i, 'TradingDay'].values[0].strftime('%Y%m%d')
                                self.updateTradingDay(strategyID = self.strategyID, InstrumentID = i, oldTradingDay = tempTradingDay, newTradingDay = self.ctaEngine.mainEngine.tradingDay, direction = 'long')
                            elif self.openInfo.loc[self.openInfo.InstrumentID == i, 'direction'].values == -1:
                                tempDirection1 = 'sell'
                                tempVolume1    = int(self.positionInfo.loc[self.positionInfo.InstrumentID == i, 'volume'].values)
                                tempKey1       = i + '-' + tempDirection1

                                tempDirection2 = 'short'
                                tempVolume2    = int(self.openInfo.loc[self.openInfo.InstrumentID == i, 'volume'].values)
                                tempKey2       = i + '-' + tempDirection2

                                self.tradingOrders[tempKey1] = {'vtSymbol':i,
                                                                'direction':tempDirection1,
                                                                'volume':tempVolume1}

                                self.tradingOrders[tempKey2] = {'vtSymbol':i,
                                                                'direction':tempDirection2,
                                                                'volume':tempVolume2}
                            else:
                                pass
                        elif self.positionInfo.loc[self.positionInfo.InstrumentID == i, 'direction'].values == 'short':
                            if self.openInfo.loc[self.openInfo.InstrumentID == i, 'direction'].values == 1:
                                tempDirection1 = 'cover'
                                tempVolume1    = int(self.positionInfo.loc[self.positionInfo.InstrumentID == i, 'volume'].values)
                                tempKey1       = i + '-' + tempDirection1

                                tempDirection2 = 'buy'
                                tempVolume2    = int(self.openInfo.loc[self.openInfo.InstrumentID == i, 'volume'].values)
                                tempKey2       = i + '-' + tempDirection2

                                self.tradingOrders[tempKey1] = {'vtSymbol':i,
                                                                'direction':tempDirection1,
                                                                'volume':tempVolume1}

                                self.tradingOrders[tempKey2] = {'vtSymbol':i,
                                                                'direction':tempDirection2,
                                                                'volume':tempVolume2}   
                            elif self.openInfo.loc[self.openInfo.InstrumentID == i, 'direction'].values == -1:
                                tempTradingDay = self.positionInfo.loc[self.positionInfo.InstrumentID == i, 'TradingDay'].values[0].strftime('%Y%m%d')
                                self.updateTradingDay(strategyID = self.strategyID, InstrumentID = i, oldTradingDay = tempTradingDay, newTradingDay = self.ctaEngine.mainEngine.tradingDay, direction = 'short')
                            else:
                                pass
                        else:
                            pass                    

                ## =============================================================
                if len(y) != 0:
                    for i in y:
                        ## direction
                        if self.positionInfo.loc[self.positionInfo.InstrumentID == i, 'direction'].values == 'long':
                            tempDirection = 'sell'
                        elif self.positionInfo.loc[self.positionInfo.InstrumentID == i, 'direction'].values == 'short':
                            tempDirection = 'cover'
                        ## volume
                        tempVolume = int(self.positionInfo.loc[self.positionInfo.InstrumentID == i, 'volume'].values)
                        tempKey = i + '-' + tempDirection
                        self.tradingOrders[tempKey] = {'vtSymbol':i,
                                                       'direction':tempDirection,
                                                       'volume':tempVolume}

                ## =============================================================
                if len(z) != 0:
                    for i in z:
                        ## direction
                        if self.openInfo.loc[self.openInfo.InstrumentID == i, 'direction'].values == 1:
                            tempDirection = 'buy'
                        elif self.openInfo.loc[self.openInfo.InstrumentID == i, 'direction'].values == -1:
                            tempDirection = 'short'
                        ## volume
                        tempVolume = int(self.openInfo.loc[self.openInfo.InstrumentID == i, 'volume'].values)
                        tempKey = i + '-' + tempDirection
                        self.tradingOrders[tempKey] = {'vtSymbol':i,
                                                       'direction':tempDirection,
                                                       'volume':tempVolume}

        print '#################################################################'
        print u'%s策略启动' %self.name
        print u'当前需要执行的订单为:'
        print self.tradingOrders
        print '#################################################################'
        self.writeCtaLog(u'%s策略启动' %self.name)
        self.putEvent()

    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        print '#################################################################'
        print u'%s策略停止' %self.name
        print '#################################################################'
        self.writeCtaLog(u'%s策略停止' %self.name)
        self.putEvent()

    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        ########################################################################
        ## william

        ## =====================================================================
        ## ---------------------------------------------------------------------
        if datetime.now().hour == 14 and datetime.now().minute >= 30:
        # if datetime.now().hour >= 9:
            if tick.vtSymbol in self.vtSymbolList:
                self.lastTickData[tick.vtSymbol] = tick.__dict__
        ## =====================================================================

        ## =====================================================================
        ## ---------------------------------------------------------------------
        if datetime.now().hour == 14 and datetime.now().minute >= 59 and datetime.now().second >= 55 and datetime.now().second % 2 == 0:
        # if datetime.now().hour >= 9:
            ################################################################
            ## william
            ## 存储有 self.lastTickData
            ## 保证有 tick data
            if tick.vtSymbol in [self.tradingOrders[k]['vtSymbol'] for k in self.tradingOrders.keys()]:
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
        self.vtSymbolWorkingOrders  = []
        self.vtSymbolTradedOrders   = []

        for vtOrderID in self.vtOrderIDList:
            tempWorkingOrder = self.ctaEngine.mainEngine.getAllOrders()[self.ctaEngine.mainEngine.getAllOrders().vtSymbol == vtSymbol][self.ctaEngine.mainEngine.getAllOrders().vtOrderID == vtOrderID][self.ctaEngine.mainEngine.getAllOrders().status == u'未成交'].vtOrderID.values
            if len(tempWorkingOrder) != 0:
                for i in range(len(tempWorkingOrder)):
                    if tempWorkingOrder[i] not in self.vtSymbolWorkingOrders:
                        self.vtSymbolWorkingOrders.append(tempWorkingOrder[i])

            tempTradedOrder = self.ctaEngine.mainEngine.getAllOrders()[self.ctaEngine.mainEngine.getAllOrders().vtSymbol == vtSymbol][self.ctaEngine.mainEngine.getAllOrders().vtOrderID == vtOrderID][self.ctaEngine.mainEngine.getAllOrders().status == u'全部成交'].vtOrderID.values
            if len(tempTradedOrder) != 0:
                for i in range(len(tempTradedOrder)):
                    if tempTradedOrder[i] not in self.vtSymbolTradedOrders:
                        self.vtSymbolTradedOrders.append(tempTradedOrder[i])

        ## =====================================================================
        ## 2. 根据已经成交的订单情况, 重新处理生成新的订单
        ## =====================================================================
        if len(self.vtSymbolWorkingOrders) != 0:
            for vtOrderID in self.vtSymbolWorkingOrders:
                self.cancelOrder(vtOrderID)
        else:
            tempSymbolList = [self.tradingOrders[k]['vtSymbol'] for k in self.tradingOrders.keys()]
            tempSymbolList = [i for i in tempSymbolList if i == vtSymbol]

            tempTradingList = [k for k in self.tradingOrders.keys() if self.tradingOrders[k]['vtSymbol'] == vtSymbol]

            if len(self.vtSymbolTradedOrders) == 0:
                ## 还没有成交
                ## 不要全部都下单
                for i in tempTradingList:
                    self.sendTradingOrder(tradingOrderDict = self.tradingOrders[i])
            elif len(self.vtSymbolTradedOrders) == 1:
                ## 有一个订单成交了
                if len(tempTradingList) == 2:
                    ## 但是如果有两个订单
                    tempTradedOrder = self.ctaEngine.mainEngine.getAllOrders()[self.ctaEngine.mainEngine.getAllOrders().vtOrderID == self.vtSymbolTradedOrders[0]]

                    if tempTradedOrder.direction.values == u'多':
                        if tempTradedOrder.offset.values == u'开仓':
                            tempDirection = 'buy'
                        elif tempTradedOrder.offset.values == u'平仓':
                            tempDirection = 'cover'
                    elif tempTradedOrder.direction.values == u'空':
                        if tempTradedOrder.offset.values == u'开仓':
                            tempDirection = 'short'
                        elif tempTradedOrder.offset.values == u'平仓':
                            tempDirection = 'sell'

                    tempRes = tempTradedOrder.vtSymbol.values[0] + '-' + tempDirection
                    tempTradingList.remove(tempRes)
                    ###################################################################
                    for i in tempTradingList:
                        self.sendTradingOrder(tradingOrderDict = self.tradingOrders[i])
                    ###################################################################
                elif len(tempTradingList) <= 1:
                    pass
            elif len(self.vtSymbolTradedOrders) == 2:
                ## 全部都成交了
                pass

        ## .....................................................................
        self.putEvent()
        ## .....................................................................

    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def sendTradingOrder(self, tradingOrderDict):
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
        ########################################################################

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
        # print u"stratTrade.__dict__:====>"
        # # print stratTrade.__dict__
        # print u"stratTrade:==>", stratTrade

        # print self.vtOrderIDList

        ########################################################################
        ## william
        ## 更新持仓
        if self.stratTrade['vtOrderID'] in self.vtOrderIDList:
            ## 0 初始化持仓信息

            ## =================================================================
            ## 1. stratTrade['vtOrderID'] 是唯一标识
            ## =================================================================
            
            self.stratTrade['strategyID'] = self.strategyID
            self.stratTrade['TradingDay']  = self.ctaEngine.mainEngine.tradingDay
            self.stratTrade['tradeTime']  = datetime.now().strftime('%Y-%m-%d') + " " +  self.stratTrade['tradeTime']      
            ## -----------------------------------------
            if self.stratTrade['direction'] == u'多':
                self.stratTrade['direction'] = 'long'
            else:
                self.stratTrade['direction'] = 'short'
            ## -----------------------------------------        

            ## =================================================================
            ## 2. 更新 positionInfo
            ## =================================================================
            tempFields = ['strategyID','vtSymbol','TradingDay','tradeTime','direction','volume']
            if self.stratTrade['offset'] == u'开仓':
                ## 如果是开仓的话,直接添加
                tempRes = pd.DataFrame([[self.stratTrade[k] for k in tempFields]], columns = ['strategyID','InstrumentID','TradingDay','tradeTime','direction','volume'])
                ## -------------------------------------------------------------
                conn = self.ctaEngine.mainEngine.dbMySQLConnect('fl_trade')
                cursor = conn.cursor()
                tempRes.to_sql(con=conn, name='positionInfo', if_exists='append', flavor='mysql', index = False)
                conn.close()  
                ## -------------------------------------------------------------
            elif self.stratTrade['offset'] == u'平仓':
                tempPositionInfo = self.positionInfo[self.positionInfo.InstrumentID == self.stratTrade['vtSymbol']]
                ## -------------------------------------------------------------
                conn = self.ctaEngine.mainEngine.dbMySQLConnect('fl_trade')
                cursor = conn.cursor()
                cursor.execute("""
                                DELETE FROM positionInfo
                                WHERE strategyID = %s
                                AND InstrumentID = %s
                                AND TradingDay = %s
                                AND direction  = %s
                               """, (self.strategyID, tempPositionInfo.InstrumentID.values[0], tempPositionInfo.TradingDay.values[0], tempPositionInfo.direction.values[0]))
                conn.commit()
                conn.close()  
                ## -------------------------------------------------------------
            else:
                pass

            tempFields = ['strategyID','vtSymbol','TradingDay','tradeTime','direction','offset','volume','price']
            tempTradingInfo = pd.DataFrame([[self.stratTrade[k] for k in tempFields]], columns = ['strategyID','InstrumentID','TradingDay','tradeTime','direction','offset','volume','price'])

            ## =================================================================
            ## 3. 更新 self.tradedOrders
            ## =================================================================
            if self.stratTrade['direction'] == 'long':
                if self.stratTrade['offset'] == u'开仓':
                    tempDirection = 'buy'
                elif self.stratTrade['offset'] == u'平仓':
                    tempDirection = 'sell'
            elif self.stratTrade['direction'] == 'short':
                if self.stratTrade['offset'] == u'开仓':
                    tempDirection = 'short'
                elif self.stratTrade['offset'] == u'平仓':
                    tempDirection = 'cover'

            tempKey = self.stratTrade['vtSymbol'] + '-' + tempDirection
            self.tradedOrders[tempKey] = {'vtSymbol':self.stratTrade['vtSymbol'],
                                          'direction':tempDirection,
                                          'volume':self.stratTrade['volume']}

            ## 更新交易记录,并写入 mysql
            self.updateTradingInfo(tempTradingInfo)

        ########################################################################

        # ######################################################################
        # 发出状态更新事件
        self.putEvent()

    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def registerEvent(self):
        """注册事件监听"""
        self.ctaEngine.mainEngine.eventEngine.register(EVENT_TRADE, self.stratTradeEvent)
        self.ctaEngine.mainEngine.eventEngine.register(EVENT_TIMER, self.updateTradingOrders)

    #---------------------------------------------------------------------------
    ############################################################################
    ## william
    ## 从 MySQL 数据库读取策略持仓信息

    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def updateTradingInfo(self, df):
        """更新交易记录"""
        conn = self.ctaEngine.mainEngine.dbMySQLConnect('fl_trade')
        cursor = conn.cursor()
        df.to_sql(con=conn, name='tradingInfo', if_exists='append', flavor='mysql', index = False)
        conn.close()   

    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def updateTradingDay(self, strategyID, InstrumentID, oldTradingDay, newTradingDay, direction):
        """更新交易日历"""  
        conn = self.ctaEngine.mainEngine.dbMySQLConnect('fl_trade')
        cursor = conn.cursor()
        cursor.execute("""
                        UPDATE positionInfo
                        SET TradingDay = %s
                        WHERE strategyID = %s
                        AND InstrumentID = %s
                        AND TradingDay = %s
                        AND direction = %s
                       """, (newTradingDay, strategyID, InstrumentID, oldTradingDay, direction))
        conn.commit()
        conn.close()

    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def updateTradingOrders(self, event):
        # pass
        # if 15 < datetime.now().hour < 17:
        #     self.failedOrders = {k:self.tradingOrders[k] for k in self.tradingOrders.keys() if k not in self.tradedOrders.keys()}
        self.failedOrders = {k:self.tradingOrders[k] for k in self.tradingOrders.keys() if k not in self.tradedOrders.keys()}

