# encoding: UTF-8
"""
################################################################################
@william

布林通道策略的实现
@param: (20, 2, 0)

@date: 2017-05-13
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
class LHGStrategy(CtaTemplate):
    """ Bollinger Band 线交易策略"""
    ############################################################################
    ## william
    # 策略类的名称和作者
    name         = 'Bollinger Band(minute)'
    className    = 'BBStrategy'
    strategyID   = 'BBStragegy'
    author       = 'william'
    vtSymbolList = ["i1709", "rb1710", "cu1707", "MA709", "SR709", "FG709", "J1709"]

    ############################################################################
    ## william
    trading   = False                   # 是否启动交易

    ############################################################################
    ## william
    ## vtOrderIDList 是一个 vtOrderID 的集合,只保存当前策略的交易信息
    vtOrderIDList = []                      # 保存委托代码的列表
    
    ############################################################################
    ## william
    # 策略参数 -----------------------------------------------------------------#
    nDay  = 1                           # 提前 2 日移动平均
    nMinute = 20                        # 20 分钟
    nSD   = 2                           # 2 个标准差
    nLag  = 0                           # 时间滞后 0 天
 
    startDate = EMPTY_STRING            # 开始载入的时间
    endDate   = EMPTY_STRING            # 结束载入的时间

    ############################################################################
    ## william
    signalValue = {}
    signalBuy   = {}
    signalSell  = {}

    lastTickData = {}
    ############################################################################
    ## william
    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'nDay',
                 'nMinute',
                 'nSD']    

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'signalValue',
               'signalBuy',
               'signalSell'
               ]  
    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(BBStrategy, self).__init__(ctaEngine, setting)

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
        # print u"today:"
        # print tempToday
        temp         = tempCalendar[tempCalendar['days'] <= tempToday]
        tempRes      = temp.loc[(temp.shape[0] - self.nDay) :].reset_index(drop=True)
        # print tempRes
        startDate    = tempRes.loc[0,'days']
        endDate      = tempRes.loc[tempRes.shape[0]-1,'days']
        ########################################################################
        ## william
        ## 加载历史的分钟数据
        for vtSymbol in self.vtSymbolList:
            tempRes = self.ctaEngine.loadMySQLMinuteData(vtSymbol,
                startDate.strftime('%Y%m%d'), endDate.strftime('%Y%m%d'))
            self.minuteData = self.minuteData.append(tempRes, ignore_index=True) 
        ########################################################################
        ## william
        ## 先把 minuteData 的格式转化以下
        ## 需要参考下面的 tempRes.dtypes
        self.minuteData.TradingDay = self.minuteData.TradingDay.apply(str)
        self.minuteData.Volume = self.minuteData.Volume.apply(int)

        for i in range(len(self.minuteData)):
            try:
                self.minuteData.loc[i,'TradingDay'] = str(self.minuteData.loc[i,'TradingDay']).replace('-','')
                self.minuteData.loc[i,'Minute'] = str(self.minuteData.loc[i,'Minute']).split(' ')[2]
            except:
                pass
        ## =====================================================================
        ## william
        ## 策略启动的时候需要从 MySQL 的数据库 fl.positionInfo 载入各个策略的持仓情况
        self.dbMySQLStratPosInfo()

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
        tickDate = tick.datetime.strftime('%Y%m%d')    
        tickMinute = tick.datetime.strftime('%H:%M:00') 
        tickSecond = int(tick.datetime.strftime("%S"))
        # print tickMinute

        if 0 <= tick.datetime.hour < 20:
            tickNumericExchTime = tick.datetime.hour * 3600 + tick.datetime.minute * 60 + tick.datetime.second
        else:
            tickNumericExchTime = tick.datetime.hour * 3600 + tick.datetime.minute * 60 + tick.datetime.second - 24*3600
        # print tickNumericExchTime
        # print tickDate
        # print tickMinute  
        # print tick.datetime.date()
        # print tick.datetime.minute
        # print tick.datetime.strftime('%H:%M:%S')
        # print "\n#######################################################################"
        # print u"这个 Tick 到底是什么鬼: tick:-->", tick
        tempFields = ['openPrice','highestPrice','lowestPrice','closePrice',\
                      'upperLimit','lowerLimit',\
                      'bidPrice1','bidPrice2','bidPrice3','bidPrice4','bidPrice5',\
                      'askPrice1','askPrice2','askPrice3','askPrice4','askPrice5',\
                      'settlementPrice','averagePrice']   
        for i in tempFields:
            if tick.__dict__[i] > 1.79e+99:
                tick.__dict__[i] = 0
        # print tick.__dict__

        md = self.minuteData

        if tick.vtSymbol in self.vtSymbolList:
            ####################################################################
            ## william
            ## 先进行 onBar 的交易
            self.lastTickData[tick.vtSymbol] = tick.__dict__
            
            if tick.askVolume1 > 10 and tick.bidVolume1 > 10:    ###### 出于流动性的考虑
                self.minuteBar[tick.vtSymbol] = md[md.TradingDay == tickDate][md.InstrumentID == tick.vtSymbol].sort_values(by = ['TradingDay','NumericExchTime'], ascending = [1,1]).reset_index(drop = True)
                if len(self.minuteBar[tick.vtSymbol]) > self.nMinute and tickSecond >= 58:
                    self.minuteBar[tick.vtSymbol] = self.minuteBar[tick.vtSymbol][-self.nMinute:].reset_index(drop = True)
                    # print self.minuteBar[tick.vtSymbol]
                    self.onBar(self.minuteBar[tick.vtSymbol])
            ####################################################################

            ####################################################################
            ## william
            ## 实盘中用不到的数据可以选择不算，从而加快速度
            # if tick.vtSymbol in self.lastTickData.keys():
            #     lastTick = self.lastTickData[tick.vtSymbol]
            #     deltaVolume = tick.volume - lastTick['volume']
            #     deltaTurnover = tick.turnover - lastTick['turnover']
            # else:
            #     deltaVolume = 0
            #     deltaTurnover = 0
            ####################################################################

            ####################################################################
            
            ####################################################################

            ####################################################################
            ## william
            ####################################################################
            
            # print tickDate
            tempMD = md[md.TradingDay == tickDate][md.InstrumentID == tick.vtSymbol][md.Minute == tickMinute].reset_index(drop = True)
            # print tempMD

            if (tickDate in md['TradingDay'].unique()) and (tempMD.shape[0] != 0):
                # print tempMD.loc[0,'HighPrice']
                md.loc[(md.TradingDay == tickDate) & (md.InstrumentID == tick.vtSymbol) & (md.Minute == tickMinute),'HighPrice'] = max(tick.lastPrice, tempMD.loc[0,'HighPrice'])
                md.loc[(md.TradingDay == tickDate) & (md.InstrumentID == tick.vtSymbol) & (md.Minute == tickMinute),'LowPrice'] = min(tick.lastPrice, tempMD.loc[0,'LowPrice'])
                md.loc[(md.TradingDay == tickDate) & (md.InstrumentID == tick.vtSymbol) & (md.Minute == tickMinute),'ClosePrice'] = tick.lastPrice
                md.loc[(md.TradingDay == tickDate) & (md.InstrumentID == tick.vtSymbol) & (md.Minute == tickMinute),'NumericExchTime'] = tickNumericExchTime
                # md[md['InstrumentID'] == tick.vtSymbol]['Minute' == tickMinute].loc[0,'Volume'] += addVolume
                # md[md['InstrumentID'] == tick.vtSymbol]['Minute' == tickMinute].loc[0,'Turnover'] += addTurnover
            else:
                bar = CtaMySQLMinuteData()
                bar.TradingDay = tickDate
                bar.InstrumentID = tick.vtSymbol
                bar.Minute = tickMinute
                bar.NumericExchTime = tickNumericExchTime
                # bar.NumericExchTime
                bar.OpenPrice = tick.lastPrice
                bar.HighPrice = tick.lastPrice
                bar.LowPrice = tick.lastPrice
                bar.ClosePrice = tick.lastPrice
                # bar.Volume = tempRes.loc[0,'Volume'] + addVolume
                # bar.Turnover = tempRes.loc[0,'Turnover'] + addTurnover

                temp = bar.__dict__
                tempRes = pd.DataFrame([temp.values()], columns = temp.keys())
                tempRes = tempRes[self.minuteDataHeader]
                # print tempRes

                self.minuteData = self.minuteData.append(tempRes, ignore_index=True)
                self.minuteData = self.minuteData.sort_values(by = ['TradingDay','NumericExchTime','InstrumentID'], ascending = [1,1,1]).reset_index(drop = True)

    #---------------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
    
        ########################################################################
        ## william
        # print "\n#######################################################################"
        # # print self.lastTickData{}
        # instrumentID = bar.InstrumentID.unique()
        # print instrumentID
        # print self.lastTickData[instrumentID[0]]
        # print "#######################################################################\n"
        instrumentID = bar.InstrumentID.unique()[0]
        instrumentTick = self.lastTickData[instrumentID]

        barClose = self.minuteBar[instrumentID].ClosePrice
        # print barClose

        posInfo = self.stratPosInfo[self.stratPosInfo.instrumentID == instrumentID]
        # print posInfo

        barClose = self.minuteBar[instrumentID].ClosePrice     

        signalSell = barClose.mean() + 3 * barClose.std()
        signalBuy = barClose.mean() + 1 * barClose.std()
        signalCover = barClose.mean() - 1 * barClose.std()
        signalShort = barClose.mean() - 3 * barClose.std()
        # print signalBuy, signalSell     

        if instrumentTick['lastPrice'] > signalSell:
            signalValue = 'short'
        elif  signalBuy <= instrumentTick['lastPrice'] <= signalSell:
            signalValue = 'cover'
        elif signalCover <= instrumentTick['lastPrice'] <= signalBuy:
            signalValue = None
        elif signalShort <= instrumentTick['lastPrice'] <= signalCover:
            signalValue = 'sell'
        else:
            signalValue = 'buy'

        # 撤销之前发出的尚未成交的委托（包括限价单和停止单）
        if self.signalValue:
            for orderID in self.vtOrderIDList:
                self.cancelOrder(orderID)

        # # ################################################################################
        if signalValue == 'buy':
            if posInfo[posInfo.direction == 'short'].shape[0] != 0:
                vtOrderID = self.cover(vtSymbol = instrumentID, price = instrumentTick['askrice1'], volume = int(posInfo.loc[posInfo.direction == 'short','volume'].values))
                self.vtOrderIDList.append(vtOrderID)
            elif posInfo[posInfo.direction == 'long'].shape[0] == 0:
                vtOrderID = self.buy(vtSymbol = instrumentID, price = instrumentTick['askPrice1'], volume = 5)
                self.vtOrderIDList.append(vtOrderID)
            else:
                pass
        elif signalValue == 'sell':
            if posInfo[posInfo.direction == 'long'].shape[0] != 0:
                vtOrderID = self.sell(vtSymbol = instrumentID, price = instrumentTick['bidPrice1'], volume = int(posInfo.loc[posInfo.direction == 'long','volume'].values))
                self.vtOrderIDList.append(vtOrderID)
            else:
                pass
        elif signalValue == 'cover':
            if posInfo[posInfo.direction == 'short'].shape[0] != 0:
                vtOrderID = self.cover(vtSymbol = instrumentID, price = instrumentTick['askPrice1'], volume = int(posInfo.loc[posInfo.direction == 'short','volume'].values))
                self.vtOrderIDList.append(vtOrderID)      
            else:
                pass      
        elif signalValue == 'short':
            if posInfo[posInfo.direction == 'long'].shape[0] != 0:
                vtOrderID = self.sell(vtSymbol = instrumentID, price = instrumentTick['bidPrice1'], volume = int(posInfo.loc[posInfo.direction == 'long','volume'].values))
                self.vtOrderIDList.append(vtOrderID)  
            elif posInfo[posInfo.direction == 'short'].shape[0] == 0:
                vtOrderID = self.short(vtSymbol = instrumentID, price = instrumentTick['bidPrice1'], volume = 5)
                self.vtOrderIDList.append(vtOrderID)
            else:
                pass
        else:
            pass
        # # ################################################################################

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

            ## -----------------------------------------
            if stratTrade['direction'] == u'多':
                tempDirection = 'long'
            else:
                tempDirection = 'short'
            ## -----------------------------------------        

            ## 2. stratPosInfo
            instrumentID = stratTrade['vtSymbol']
            if self.stratPosInfo[self.stratPosInfo.instrumentID == instrumentID].shape[0] == 0:
                ''' 如果没有持仓,则直接添加到持仓 '''
                tempRes = pd.DataFrame([[stratTrade['strategyID'], stratTrade['vtSymbol'], tempDirection,stratTrade['volume']]], columns = ['strategyID','instrumentID','direction','volume'])
                self.stratPosInfo = self.stratPosInfo.append(tempRes)
            else:
                ''' 如果有持仓, 则需要更新数据 '''
                if self.stratPosInfo[self.stratPosInfo.instrumentID == instrumentID].reset_index(drop = True).loc[0,'direction'] != tempDirection:
                    self.stratPosInfo.loc[self.stratPosInfo.instrumentID == instrumentID,'volume'] -= stratTrade['volume']
                else:
                    self.stratPosInfo.loc[self.stratPosInfo.instrumentID == instrumentID,'volume'] += stratTrade['volume']

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

