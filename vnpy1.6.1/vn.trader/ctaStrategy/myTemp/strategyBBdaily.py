# encoding: UTF-8

"""
################################################################################
@william

布林通道策略的实现

@param
(20, 2, 0)

@date: 2017-05-13

"""

################################################################################
## @william
import os
import sys
## cta_strategy_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
## trader_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

cta_strategy_path = '/home/william/Documents/vnpy/vnpy-1.6.1/vn.trader/ctaStrategy'
trader_path       = '/home/william/Documents/vnpy/vnpy-1.6.1/vn.trader'
sys.path.append(cta_strategy_path)
################################################################################

import talib
import numpy as np

from ctaBase import *
from ctaTemplate import CtaTemplate

import pandas as pd
from datetime import datetime


################################################################################
class BBStrategy(CtaTemplate):
    """ Bollinger Band 线交易策略"""

    # 策略类的名称和作者
    name      = 'Bollinger Band'
    className = 'BBStrategy'
    author    = u'william'

    ############################################################################
    ## william
    trading   = False                   # 是否启动交易

    # 策略变量
    '''
    bar = None                  # K线对象
    barMinute = EMPTY_STRING    # K线当前的分钟

    bufferSize = 100                    # 需要缓存的数据的大小
    bufferCount = 0                     # 目前已经缓存了的数据的计数
    highArray = np.zeros(bufferSize)    # K线最高价的数组
    lowArray = np.zeros(bufferSize)     # K线最低价的数组
    closeArray = np.zeros(bufferSize)   # K线收盘价的数组
    
    atrCount = 0                        # 目前已经缓存了的ATR的计数
    atrArray = np.zeros(bufferSize)     # ATR指标的数组
    atrValue = 0                        # 最新的ATR指标数值
    atrMa = 0                           # ATR移动平均的数值

    rsiValue = 0                        # RSI指标的数值
    rsiBuy = 0                          # RSI买开阈值
    rsiSell = 0                         # RSI卖开阈值
    intraTradeHigh = 0                  # 移动止损用的持仓期内最高价
    intraTradeLow = 0                   # 移动止损用的持仓期内最低价
    '''

    orderList = []                      # 保存委托代码的列表

    
    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'nDay',
                 'nSD',
                 'nLag',
                 'atrLength',
                 'atrMaLength',
                 'rsiLength',
                 'rsiEntry',
                 'trailingPercent']    

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'priceSeq',
               # 'signalValue',
               # 'signalBuy',
               # 'signalSell',
               'atrValue',
               'atrMa',
               'rsiValue',
               'rsiBuy',
               'rsiSell']  
    

    ############################################################################
    ## william

    # 策略参数 -----------------------------------------------------------------#
    nDay  = 3                           # 20 日移动平均
    nSD   = 2                           # 2 个标准差
    nLag  = 0                           # 时间滞后 0 天
 
    startDate = EMPTY_STRING            # 开始载入的时间
    endDate   = EMPTY_STRING            # 结束载入的时间

    # 策略变量 -----------------------------------------------------------------#
    # 策略参数
    atrLength = 22          # 计算ATR指标的窗口数   
    atrMaLength = 10        # 计算ATR均线的窗口数
    rsiLength = 5           # 计算RSI的窗口数
    rsiEntry = 16           # RSI的开仓信号
    trailingPercent = 0.8   # 百分比移动止损
    initDays = 10           # 初始化数据所用的天数
    fixedSize = 1           # 每次交易的数量
    
    # 策略变量
    bar = None                  # K线对象
    barMinute = EMPTY_STRING    # K线当前的分钟

    bufferSize = 100                    # 需要缓存的数据的大小
    bufferCount = 0                     # 目前已经缓存了的数据的计数
    highArray = np.zeros(bufferSize)    # K线最高价的数组
    lowArray = np.zeros(bufferSize)     # K线最低价的数组
    closeArray = np.zeros(bufferSize)   # K线收盘价的数组
    
    atrCount = 0                        # 目前已经缓存了的ATR的计数
    atrArray = np.zeros(bufferSize)     # ATR指标的数组
    atrValue = 0                        # 最新的ATR指标数值
    atrMa = 0                           # ATR移动平均的数值

    rsiValue = 0                        # RSI指标的数值
    rsiBuy = 0                          # RSI买开阈值
    rsiSell = 0                         # RSI卖开阈值
    intraTradeHigh = 0                  # 移动止损用的持仓期内最高价
    intraTradeLow = 0                   # 移动止损用的持仓期内最低价

    ############################################################################
    priceSeq = np.zeros(nDay)           # 需要保留的价格序列

    ############################################################################
    signalValue = {}
    signalBuy   = {}
    signalSell  = {}

    '''
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'nDay',
                 'nSD',
                 'nLag']

    varList   = ['inited',
                 'trading',
                 'pos',
                 'priceSeq',
                 'signalValue',
                 'signalBuy',
                 'signalSell']
    '''

    dailyDataHeader = ['TradingDay', 'Sector', 'InstrumentID',
                       'OpenPrice', 'HighPrice', 'LowPrice', 'ClosePrice',
                       'Volume', 'Turnover',
                       # 'OpenOpenInterest', 'HighOpenInterest',  'LowOpenInterest', 'CloseOpenInterest',
                       'UpperLimitPrice', 'LowerLimitPrice', 'SettlementPrice']
    dailyData = pd.DataFrame([], columns = dailyDataHeader)

    minuteDataHeader = ['TradingDay','InstrumentID','Minute','NumericExchTime',
                        'OpenPrice','HighPrice','LowPrice','ClosePrice',
                        'Volume','Turnover',
                        # 'OpenOpenInterest', 'HighOpenInterest',  'LowOpenInterest', 'CloseOpenInterest',
                        'UpperLimitPrice','LowerLimitPrice']
    minuteData = pd.DataFrame([], columns = minuteDataHeader)

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(BBStrategy, self).__init__(ctaEngine, setting)

        ########################################################################
        ## william
        # self.mainEngine = mainEngine
        # self.eventEngine = eventEngine
        # self.ctaEngine = ctaEngine
        
        # 注意策略类中的可变对象属性（通常是list和dict等），在策略初始化时需要重新创建，
        # 否则会出现多个策略实例之间数据共享的情况，有可能导致潜在的策略逻辑错误风险，
        # 策略类中的这些可变对象属性可以选择不写，全都放在__init__下面，写主要是为了阅读
        # 策略时方便（更多是个编程习惯的选择）        

    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略初始化' %self.name)
    
        # 初始化

        # 载入历史数据，并采用回放计算的方式初始化策略数值
        
        '''
        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onBar(bar)
        '''

        vtSymbolList = ["i1709", "rb1710", "cu1709"]

        tempCalendar = self.ctaEngine.ChinaFuturesCalendar
        tempToday    = self.ctaEngine.today.date()
        print u"today:"
        print tempToday
        temp         = tempCalendar[tempCalendar['days'] < tempToday]
        tempRes      = temp.loc[(temp.shape[0] - self.nDay) :].reset_index(drop=True)
        # print tempRes
        startDate    = tempRes.loc[0,'days']
        endDate      = tempRes.loc[tempRes.shape[0]-1,'days']
        '''
        for vtSymbol in vtSymbolList:
            tempRes = self.ctaEngine.loadMySQLDailyData(vtSymbol,
                startDate.strftime('%Y%m%d'), endDate.strftime('%Y%m%d'))

            tempMean = tempRes['ClosePrice'].mean()
            tempSD   = tempRes['ClosePrice'].std()
            self.signalBuy[vtSymbol]  = tempMean + self.nSD * tempSD
            self.signalSell[vtSymbol] = tempMean - self.nSD * tempSD

            self.dailyData = self.dailyData.append(tempRes, ignore_index=True)
        '''
        for vtSymbol in vtSymbolList:
            tempRes = self.ctaEngine.loadMySQLMinuteData(vtSymbol,
                startDate.strftime('%Y%m%d'), endDate.strftime('%Y%m%d'))

            tempMean = tempRes['ClosePrice'].mean()
            tempSD   = tempRes['ClosePrice'].std()
            self.signalBuy[vtSymbol]  = tempMean + self.nSD * tempSD
            self.signalSell[vtSymbol] = tempMean - self.nSD * tempSD

            self.dailyData = self.dailyData.append(tempRes, ignore_index=True)      
        # print self.dailyData
        ########################################################################
        ## william
        print '#################################################################'
        print u"@william 策略初始化成功 !!!"
        print vtSymbolList
        print self.dailyData
        print '#################################################################'

        ########################################################################
        ## william

        self.putEvent()

    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        print '#################################################################'
        print u'%s策略启动' %self.name
        print '#################################################################'
        self.writeCtaLog(u'%s策略启动' %self.name)
        self.putEvent()

    #---------------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        print '#################################################################'
        print u"@william 策略初始化成功 !!!"
        print vtSymbolList
        print '#################################################################'
        self.writeCtaLog(u'%s策略停止' %self.name)
        self.putEvent()

    #---------------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        vtSymbolList = ["i1709", "rb1710", "cu1709"]

        ## tick
        if tick.vtSymbol in vtSymbolList:
            for 


        


        

    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        # 撤销之前发出的尚未成交的委托（包括限价单和停止单）
        for orderID in self.orderList:
            self.cancelOrder(orderID)
        self.orderList = []

        # 保存K线数据
        self.closeArray[0:self.bufferSize-1] = self.closeArray[1:self.bufferSize]
        self.highArray[0:self.bufferSize-1] = self.highArray[1:self.bufferSize]
        self.lowArray[0:self.bufferSize-1] = self.lowArray[1:self.bufferSize]
        
        self.closeArray[-1] = bar.close
        self.highArray[-1] = bar.high
        self.lowArray[-1] = bar.low
        
        self.bufferCount += 1
        if self.bufferCount < self.bufferSize:
            return

        # 计算指标数值
        self.atrValue = talib.ATR(self.highArray, 
                                  self.lowArray, 
                                  self.closeArray,
                                  self.atrLength)[-1]
        self.atrArray[0:self.bufferSize-1] = self.atrArray[1:self.bufferSize]
        self.atrArray[-1] = self.atrValue

        self.atrCount += 1
        if self.atrCount < self.bufferSize:
            return

        self.atrMa = talib.MA(self.atrArray, 
                              self.atrMaLength)[-1]
        self.rsiValue = talib.RSI(self.closeArray, 
                                  self.rsiLength)[-1]

        # 判断是否要进行交易
        
        # 当前无仓位
        if self.pos == 0:
            self.intraTradeHigh = bar.high
            self.intraTradeLow = bar.low

            # ATR数值上穿其移动平均线，说明行情短期内波动加大
            # 即处于趋势的概率较大，适合CTA开仓
            if self.atrValue > self.atrMa:
                # 使用RSI指标的趋势行情时，会在超买超卖区钝化特征，作为开仓信号
                if self.rsiValue > self.rsiBuy:
                    # 这里为了保证成交，选择超价5个整指数点下单
                    self.buy(bar.close+5, self.fixedSize)

                elif self.rsiValue < self.rsiSell:
                    self.short(bar.close-5, self.fixedSize)

        # 持有多头仓位
        elif self.pos > 0:
            # 计算多头持有期内的最高价，以及重置最低价
            self.intraTradeHigh = max(self.intraTradeHigh, bar.high)
            self.intraTradeLow = bar.low
            # 计算多头移动止损
            longStop = self.intraTradeHigh * (1-self.trailingPercent/100)
            # 发出本地止损委托，并且把委托号记录下来，用于后续撤单
            orderID = self.sell(longStop, abs(self.pos), stop=True)
            self.orderList.append(orderID)

        # 持有空头仓位
        elif self.pos < 0:
            self.intraTradeLow = min(self.intraTradeLow, bar.low)
            self.intraTradeHigh = bar.high

            shortStop = self.intraTradeLow * (1+self.trailingPercent/100)
            orderID = self.cover(shortStop, abs(self.pos), stop=True)
            self.orderList.append(orderID)

        # 发出状态更新事件
        self.putEvent()

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        # 发出状态更新事件
        self.putEvent()

if __name__ == '__main__':
    # 提供直接双击回测的功能
    # 导入PyQt4的包是为了保证matplotlib使用PyQt4而不是PySide，防止初始化出错
    from ctaBacktesting import *
    from PyQt4 import QtCore, QtGui
    
    # 创建回测引擎
    engine = BacktestingEngine()
    
    # 设置引擎的回测模式为K线
    engine.setBacktestingMode(engine.BAR_MODE)

    # 设置回测用的数据起始日期
    engine.setStartDate('20120101')
    
    # 设置产品相关参数
    engine.setSlippage(0.2)     # 股指1跳
    engine.setRate(0.3/10000)   # 万0.3
    engine.setSize(300)         # 股指合约大小 
    engine.setPriceTick(0.2)    # 股指最小价格变动
    
    # 设置使用的历史数据库
    engine.setDatabase(MINUTE_DB_NAME, 'IF0000')
    
    # 在引擎中创建策略对象
    d = {'atrLength': 11}
    engine.initStrategy(AtrRsiStrategy, d)
    
    # 开始跑回测
    engine.runBacktesting()
    
    # 显示回测结果
    engine.showBacktestingResult()
    
    ## 跑优化
    #setting = OptimizationSetting()                 # 新建一个优化任务设置对象
    #setting.setOptimizeTarget('capital')            # 设置优化排序的目标是策略净盈利
    #setting.addParameter('atrLength', 12, 20, 2)    # 增加第一个优化参数atrLength，起始11，结束12，步进1
    #setting.addParameter('atrMa', 20, 30, 5)        # 增加第二个优化参数atrMa，起始20，结束30，步进1
    #setting.addParameter('rsiLength', 5)            # 增加一个固定数值的参数
    
    ## 性能测试环境：I7-3770，主频3.4G, 8核心，内存16G，Windows 7 专业版
    ## 测试时还跑着一堆其他的程序，性能仅供参考
    #import time    
    #start = time.time()
    
    ## 运行单进程优化函数，自动输出结果，耗时：359秒
    #engine.runOptimization(AtrRsiStrategy, setting)            
    
    ## 多进程优化，耗时：89秒
    ##engine.runParallelOptimization(AtrRsiStrategy, setting)     
    
    #print u'耗时：%s' %(time.time()-start)
