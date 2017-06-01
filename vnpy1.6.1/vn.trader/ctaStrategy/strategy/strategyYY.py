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
    strategyID   = 'YYStragegy'
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
    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(YYStrategy, self).__init__(ctaEngine, setting)

        ########################################################################
        ## william
        ## 交易日历
        self.todayDate = self.ctaEngine.today.date()

        ########################################################################
        ## william
        ## 历史的 minuteData
        self.minuteDataHeader = ['TradingDay','InstrumentID','Minute','NumericExchTime',
                                 'OpenPrice','HighPrice','LowPrice','ClosePrice',
                                 'Volume','Turnover',
                                 # 'OpenOpenInterest', 'HighOpenInterest',  'LowOpenInterest', 'CloseOpenInterest',
                                 'UpperLimitPrice','LowerLimitPrice']
        self.minuteData = pd.DataFrame([], columns = self.minuteDataHeader)

        ########################################################################
        ## william
        ## 用于接收多合约的 k 线数据
        ## Usage: key: pd.DataFrame
        self.minuteBar = {}
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
            pass
        else:
        # [如果原来的持仓是空的]
        # 如果原来的持仓是空的,
        # 则只需要处理单日发出的信号
            tradingInfo = self.ctaEngine.mainEngine.dbMySQLQuery('lhg_trade', 'select * from lhg_open_t')

            for i in tradingInfo.InstrumentID.values:
                if tradingInfo.loc[tradingInfo.InstrumentID == i, 'direction'].values == 1:
                    tempDirection = 'buy'
                elif tradingInfo.loc[tradingInfo.InstrumentID == i, 'direction'].values == -1:
                    tempDirection = 'short'
                else:
                    pass
                self.tradingOrderSeq[i] = {'direction':tempDirection,
                                           'volume':tradingInfo.loc[tradingInfo.InstrumentID == i, 'volume'].values}


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
        ########################################################################
        ## william
        ## 这个 tick 已经是 CtaTickData, 已经处理接收的数据
        ## Ref: /ctaStragegy/ class CtaEngine/ def processTickEvent(self, event):
        # 计算K线
        # 14:59:30
        tickDate = tick.datetime.strftime('%Y%m%d')    
        tickHour   = int(tick.datetime.strftime("%H"))
        tickMinute = tick.datetime.strftime('%H:%M:00') 
        tickSecond = int(tick.datetime.strftime("%S"))
        # print tickMinute

        if tickHour != 14:
            pass

        # 14:59:30
        # if int(tick.datetime.strftime("%S")) == 59 and tickSecond > 30 and tick.vtSymbol in self.vtSymbolList:
        if tick.vtSymbol in self.vtSymbolList:
            ####################################################################
            ## william
            ## 先进行 onBar 的交易
            self.lastTickData[tick.vtSymbol] = tick.__dict__

        if int(tick.datetime.strftime("%S")) == 59 and tickSecond > 30 and tick.vtSymbol in self.tradingOrderSeq.keys():
            ## william
            ## 开始发出交易信号
            tempInstrumentID = tick.vtSymbol
            tempPriceTick = self.ctaEngine.mainEngine.getContract(tick.vtSymbol).priceTick
            tempDirection = self.tradingOrderSeq[tick.vtSymbol]['direction']
            tempVolume    = self.tradingOrderSeq[tick.vtSymbol]['volume']

            if tempDirection == 'buy':
                ## 如果是买入, AskPrice 需要增加一个 priceTick 的滑点
                tempPrice = tick.askPrice1 + tempPriceTick
                vtOrderID = self.buy(vtSymbol = tempInstrumentID, price = tempPrice, volume = tempVolume)
                self.vtOrderIDList.append(vtOrderID)
            elif tempDirection == 'short':
                ## 如果是卖出, BidPrice 需要减少一个 priceTick 的滑点
                tempPrice = tick.BidPrice1 - tempPriceTick
                vtOrderID = self.short(vtSymbol = tempInstrumentID, price = tempPrice, volume = tempVolume)
                self.vtOrderIDList.append(vtOrderID)
            ####################################################################
        # 发出状态更新事件
        self.putEvent()


    #---------------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        # 发出状态更新事件
        # self.putEvent()

    #---------------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    #---------------------------------------------------------------------------
    def onTrade(self, trade):
        # 发出状态更新事件
        self.putEvent()

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
            stratTrade['orderTime']  = self.ctaEngine.mainEngine.tradingDay      

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
                tempRes = pd.DataFrame([[stratTrade['strategyID'], stratTrade['vtSymbol'], tempDirection,stratTrade['volume']], stratTrade['orderTime']], columns = ['strategyID','InstrumentID','orderTime','direction','volume'])
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

            ## 4. 更新持仓信息,并写入 mysql
            self.updateStratPosInfo(self.stratPosInfo)

        ########################################################################

        # ################################################################################
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
        conn = self.ctaEngine.mainEngine.dbMySQLConnect('fl')
        cursor = conn.cursor()
        cursor.execute(""" delete from fl.positionInfo where strategyID = '%s' """ %self.strategyID)
        # df = self.stratPosInfo
        df.to_sql(con=conn, name='positionInfo', if_exists='append', flavor='mysql', index = False)
        conn.close()

