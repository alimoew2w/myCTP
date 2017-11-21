# encoding: UTF-8

'''
本文件中实现了CTA策略引擎，针对CTA类型的策略，抽象简化了部分底层接口的功能。

关于平今和平昨规则：
1. 普通的平仓OFFSET_CLOSET等于平昨OFFSET_CLOSEYESTERDAY
2. 只有上期所的品种需要考虑平今和平昨的区别
3. 当上期所的期货有今仓时，调用Sell和Cover会使用OFFSET_CLOSETODAY，否则
   会使用OFFSET_CLOSE
4. 以上设计意味着如果Sell和Cover的数量超过今日持仓量时，会导致出错（即用户
   希望通过一个指令同时平今和平昨）
5. 采用以上设计的原因是考虑到vn.trader的用户主要是对TB、MC和金字塔类的平台
   感到功能不足的用户（即希望更高频的交易），交易策略不应该出现4中所述的情况
6. 对于想要实现4中所述情况的用户，需要实现一个策略信号引擎和交易委托引擎分开
   的定制化统结构（没错，得自己写）
'''

from __future__ import division

import json
import os
import traceback
from collections import OrderedDict
from datetime import datetime, timedelta

from ctaBase import *
from strategy import STRATEGY_CLASS
from eventEngine import *
from vtConstant import *
from vtGateway import VtSubscribeReq, VtOrderReq, VtCancelOrderReq, VtLogData, VtPositionData
from vtFunction import todayDate
################################################################################
## william
import MySQLdb
import vtFunction
import pandas as pd
from datetime import *


####################################################################################################
class CtaEngine(object):
    """CTA策略引擎"""
    
    ## =============================================================================================
    ## CTA 策略配置
    ## -------------------------------------------------------------------------
    settingFileName = 'CTA_setting.json'
    path = os.path.abspath(os.path.dirname(__file__))
    settingFileName = os.path.join(path, settingFileName)
    ## =============================================================================================


    ## =============================================================================================
    def __init__(self, mainEngine, eventEngine):
        """Constructor"""
        self.mainEngine  = mainEngine
        self.eventEngine = eventEngine

        ## =========================================================================================
        ## william
        ## 有关日期的设置
        ## date: 指的是日期, 即 python 里面的 date() 格式, eg: 2017-01-01
        ## day:  是 date 转变过来的字符串格式, eg:'20170101'
        ## ---------------------------------------------------------------------
        ## 期货交易日历表
        ## Usage: mainEngine.ctaEngine.ChinaFuturesCalendar
        ## __格式是 date, 即 2017-01-01, 需要用 date 格式来匹配__
        ## nights: 夜盘日期,
        ## days:   日盘日期,
        self.ChinaFuturesCalendar = self.mainEngine.dbMySQLQuery('dev', 
            """select * from ChinaFuturesCalendar where days >= 20170101;""")
        ## =========================================================================================


        ## =========================================================================================
        ## 交易系统需要使用的交易日历
        ## ---------------------------------------------------------------------
        ## 当前日历的日期
        ## ------------
        self.todayDate       = vtFunction.todayDate().date()
        self.todayDay        = self.todayDate.strftime('%Y%m%d')
        
        ## 当前交易日的日期
        ## --------------
        self.tradingDate     = datetime.strptime(self.mainEngine.tradingDay,'%Y%m%d').date()
        self.tradingDay      = self.tradingDate.strftime('%Y%m%d')
        
        ## 上一个交易日
        self.lastTradingDate = self.ChinaFuturesCalendar.loc[self.ChinaFuturesCalendar.days < self.tradingDate, 'days'].max()
        self.lastTradingDay  = self.lastTradingDate.strftime('%Y%m%d')
        ## =========================================================================================


        ## =========================================================================================
        # 保存策略实例的字典
        # key为策略名称，value为策略实例，注意策略名称不允许重复
        self.strategyDict     = {}
        
        ## 持仓信息
        ## ------
        self.positionInfo     = {}

        ## 持仓合约
        ## -------
        self.accountContracts = []
        ## =========================================================================================
        
        ## =========================================================================================
        ## CTA 策略相关的 Dict
        ## ---------------------------------------------------------------------
        # 保存vtSymbol和策略实例映射的字典（用于推送tick数据）
        # 由于可能多个strategy交易同一个vtSymbol，因此key为vtSymbol
        # value为包含所有相关strategy对象的list
        self.tickStrategyDict = {}
        self.lastTickData     = {}
        self.lastTickFileds   = ['symbol', 'vtSymbol', 'datetime',
                                 'lastPrice', 'bidPrice1', 'askPrice1',
                                 'bidVolume1', 'askVolume1', 'upperLimit', 'lowerLimit', 'openPrice']

        # 保存vtOrderID和strategy对象映射的字典（用于推送order和trade数据）
        # key为vtOrderID，value为strategy对象
        self.orderStrategyDict    = {}
        
        # 本地停止单编号计数
        self.stopOrderCount       = 0
        # stopOrderID             = STOPORDERPREFIX + str(stopOrderCount)
        
        # 本地停止单字典
        # key为stopOrderID，value为stopOrder对象
        self.stopOrderDict        = {}             # 停止单撤销后不会从本字典中删除
        self.workingStopOrderDict = {}             # 停止单撤销后会从本字典中删除
        
        # 持仓缓存字典
        # key为vtSymbol，value为PositionBuffer对象
        self.posBufferDict        = {}
        
        # 成交号集合，用来过滤已经收到过的成交推送
        self.tradeSet             = set()
        ## =========================================================================================


        ## =========================================================================================
        ## william
        ## 有关订阅合约行情
        ## -----------------------------------------------------------------------------------------
        ## 所有的主力合约
        self.mainContracts = self.mainEngine.dbMySQLQuery('china_futures_bar',
            """
            select * 
            from main_contract_daily 
            where TradingDay = %s 
            """ %self.lastTradingDay).Main_contract.values
        ## -----------------------------------------------------------------------------------------
        ## william
        ## 需要订阅的合约
        self.subscribeContracts = []
        for dbName in ['HiCloud','FL_SimNow']:
            for tbName in ['positionInfo','failedInfo','tradingSignal']:
                try:
                    temp = self.fetchInstrumentID(dbName, tbName)
                    self.subscribeContracts = list(set(self.subscribeContracts) | set(temp))
                except:
                    None
        self.subscribeContracts = list(set(self.subscribeContracts) | 
                                       set(self.mainContracts))
        self.tickInfo = {}
        
        ## =========================================================================================
        ## 记录合约相关的 
        ## 1. priceTick
        ## 2. size
        ## ---------------------------------------------------------------------
        for i in self.subscribeContracts:
            try:
                self.tickInfo[i] = {k:self.mainEngine.getContract(i).__dict__[k] 
                                    for k in ['vtSymbol','priceTick','size']}
            except:
                None
        ## =========================================================================================


        ########################################################################
        ## william
        ## Ref: /ctaStrategy/ctaBase.pyse
        ## 1.ENGINETYPE_BACKTESTING = 'backtesting'  # 回测
        ## 2.ENGINETYPE_TRADING = 'trading'          # 实盘
        ## 引擎类型，用于区分当前策略的运行环境
        ########################################################################
        # 引擎类型为实盘
        self.engineType = ENGINETYPE_TRADING

        # 注册事件监听
        self.registerEvent()


    ################################################################################################
    ## 下单指令
    ## sendOrder
    ################################################################################################
    def sendOrder(self, vtSymbol, orderType, price, volume, strategy):
        """发单"""
        ## =====================================================================
        ## william
        ## 这里的 strategy 来自具体的策略
        ## Ref: /stragegy/strategyBBminute.py
        contract = self.mainEngine.getContract(vtSymbol)
        ## =====================================================================

        req          = VtOrderReq()
        req.symbol   = contract.symbol
        req.exchange = contract.exchange
        ########################################################################
        ## william
        ## 这个需要参考最小价格变动单位：　priceTick
        req.price  = self.roundToPriceTick(contract.priceTick, price)
        req.volume = volume

        req.productClass = strategy.productClass
        req.currency     = strategy.currency

        ########################################################################
        ## william
        ## Ref: /vn.trader/language/chinese/constant.py/
        # 设计为CTA引擎发出的委托只允许使用限价单
        req.priceType = PRICETYPE_LIMITPRICE

        # CTA委托类型映射
        if orderType == CTAORDER_BUY:
            req.direction = DIRECTION_LONG
            req.offset    = OFFSET_OPEN

        elif orderType == CTAORDER_SELL:
            req.direction = DIRECTION_SHORT

            ####################################################################
            ## william
            ####################################################################
            # 获取持仓缓存数据
            posBuffer = self.posBufferDict.get(vtSymbol, None)
            # 如果获取持仓缓存失败，则默认平昨
            if not posBuffer:
                req.offset = OFFSET_CLOSE
            elif posBuffer.longYd != 0:
                req.offset = OFFSET_CLOSE
                req.volume = min(req.volume, posBuffer.longYd)
            elif posBuffer.longToday != 0:
                req.offset = OFFSET_CLOSETODAY
                req.volume = min(req.volume, posBuffer.longToday)
            # 其他情况使用平昨
            else:
                req.offset = OFFSET_CLOSE

        elif orderType == CTAORDER_SHORT:
            req.direction = DIRECTION_SHORT
            req.offset    = OFFSET_OPEN

        elif orderType == CTAORDER_COVER:
            req.direction = DIRECTION_LONG

            ####################################################################
            ## william
            ####################################################################
            # 获取持仓缓存数据
            posBuffer = self.posBufferDict.get(vtSymbol, None)
            # 如果获取持仓缓存失败，则默认平昨
            if not posBuffer:
                req.offset = OFFSET_CLOSE
            elif posBuffer.shortYd != 0:
                req.offset = OFFSET_CLOSE
                req.volume = min(req.volume, posBuffer.shortYd)
            elif posBuffer.shortToday != 0:
                req.offset = OFFSET_CLOSETODAY
                req.volume = min(req.volume, posBuffer.shortToday)
            # 其他情况使用平昨
            else:
                req.offset = OFFSET_CLOSE

        ########################################################################
        ## william
        ## 发单
        ## Ref: gateway/ctpGateway.py/class CtpTdApi/def sendOrder(self, orderReq):
        ##１．执行下单命令：　self.reqOrderInsert(req, self.reqID)
        ##2. 并返回订单号（字符串）：vtOrderID，便于某些算法进行动态管理
        ########################################################################

        ## =====================================================================
        print '\n'+'#'*80
        print '策略%s发送委托，%s，%s，%s@%s :==> %s' %(
            strategy.name, vtSymbol, req.direction, 
            volume, price, datetime.now())
        print '-'*80
        ## ---------------------------------------------------------------------
        self.writeCtaLog(u'策略%s发送委托，%s，%s，%s@%s :==> %s'
                         %(strategy.name, vtSymbol, req.direction, 
                           volume, price, datetime.now()))
        ## =====================================================================

        ########################################################################
        ## william
        ## 从主函数口发单,使用 ctpGateway
        vtOrderID = self.mainEngine.sendOrder(req, contract.gatewayName)    # 发单
                                                                            
        ## =====================================================================
        ## 如果是一键全平仓，不要使用以下的命令
        ## =====================================================================
        if strategy.name != 'CLOSE_ALL':
            self.orderStrategyDict[vtOrderID] = strategy        # 保存vtOrderID和策略的映射关系
        ## william
        ## 同样，返回订单号
        return vtOrderID



    ################################################################################################
    ## 撤单指令
    ## cancelOrder
    ################################################################################################
    def cancelOrder(self, vtOrderID):
        """撤单"""
        ## ---------------------------------------------------------------------
        ## 查询报单对象
        ## 1.调用主引擎接口，查询委托单对象
        order = self.mainEngine.getOrder(vtOrderID)

        ## =====================================================================
        # 如果查询成功
        ## =====================================================================
        if order:
            ## -----------------------------------------------------------------
            ## 2.检查是否报单还有效，只有有效时才发出撤单指令
            orderFinished = (order.status == STATUS_ALLTRADED or order.status == STATUS_CANCELLED)
            if not orderFinished:
                req = VtCancelOrderReq()
                req.symbol      = order.symbol
                req.exchange    = order.exchange
                req.frontID     = order.frontID
                req.sessionID   = order.sessionID
                req.orderID     = order.orderID
                self.mainEngine.cancelOrder(req, order.gatewayName)
            else:
                if order.status == STATUS_ALLTRADED:
                    print '委托单({0}已执行，无法撤销'.format(vtOrderID)
                    self.writeCtaLog(u'委托单({0}已执行，无法撤销'.format(vtOrderID))
                if order.status == STATUS_CANCELLED:
                    print '委托单({0}已撤销，无法再次撤销'.format(vtOrderID)
                    self.writeCtaLog(u'委托单({0}已撤销，无法再次撤销'.format(vtOrderID))
        ## =====================================================================
        # 查询不成功
        ## =====================================================================
        else:
            print '委托单({0}不存在'.format(vtOrderID)
            self.writeCtaLog(u'委托单({0}不存在'.format(vtOrderID))

    #----------------------------------------------------------------------
    def sendStopOrder(self, vtSymbol, orderType, price, volume, strategy):
        """发停止单（本地实现）"""
        self.stopOrderCount += 1
        stopOrderID = STOPORDERPREFIX + str(self.stopOrderCount)

        so             = StopOrder()
        so.vtSymbol    = vtSymbol
        so.orderType   = orderType
        so.price       = price
        so.volume      = volume
        so.strategy    = strategy
        so.stopOrderID = stopOrderID
        so.status      = STOPORDER_WAITING

        if orderType == CTAORDER_BUY:
            so.direction = DIRECTION_LONG
            so.offset    = OFFSET_OPEN
        elif orderType == CTAORDER_SELL:
            so.direction = DIRECTION_SHORT
            so.offset    = OFFSET_CLOSE
        elif orderType == CTAORDER_SHORT:
            so.direction = DIRECTION_SHORT
            so.offset    = OFFSET_OPEN
        elif orderType == CTAORDER_COVER:
            so.direction = DIRECTION_LONG
            so.offset    = OFFSET_CLOSE

        # 保存stopOrder对象到字典中
        self.stopOrderDict[stopOrderID] = so
        self.workingStopOrderDict[stopOrderID] = so

        return stopOrderID

    #----------------------------------------------------------------------
    def cancelStopOrder(self, stopOrderID):
        """撤销停止单"""
        # 检查停止单是否存在
        if stopOrderID in self.workingStopOrderDict:
            so = self.workingStopOrderDict[stopOrderID]
            so.status = STOPORDER_CANCELLED
            del self.workingStopOrderDict[stopOrderID]

    #----------------------------------------------------------------------
    def processStopOrder(self, tick):
        """收到行情后处理本地停止单（检查是否要立即发出）"""
        vtSymbol = tick.vtSymbol

        # 首先检查是否有策略交易该合约
        if vtSymbol in self.tickStrategyDict:
            # 遍历等待中的停止单，检查是否会被触发
            for so in self.workingStopOrderDict.values():
                if so.vtSymbol == vtSymbol:
                    longTriggered = so.direction==DIRECTION_LONG and tick.lastPrice>=so.price        # 多头停止单被触发
                    shortTriggered = so.direction==DIRECTION_SHORT and tick.lastPrice<=so.price     # 空头停止单被触发

                    if longTriggered or shortTriggered:
                        # 买入和卖出分别以涨停跌停价发单（模拟市价单）
                        if so.direction==DIRECTION_LONG:
                            price = tick.upperLimit
                        else:
                            price = tick.lowerLimit

                        so.status = STOPORDER_TRIGGERED
                        self.sendOrder(so.vtSymbol, so.orderType, price, so.volume, so.strategy)
                        del self.workingStopOrderDict[so.stopOrderID]

    #----------------------------------------------------------------------
    def processTickEvent(self, event):
        """处理行情推送"""
        tick = event.dict_['data']
        tick.datetime = datetime.strptime(' '.join([tick.date, tick.time]), '%Y%m%d %H:%M:%S.%f')
        ## =====================================================================
        if tick.vtSymbol in self.subscribeContracts:
            self.lastTickData[tick.vtSymbol] = {k:tick.__dict__[k] for k in self.lastTickFileds}
        ## =====================================================================
        # 收到tick行情后，先处理本地停止单（检查是否要立即发出）
        self.processStopOrder(tick)
        ####################################################################
        ## william
        # 推送tick到对应的策略实例进行处理
        if tick.vtSymbol in self.tickStrategyDict:
            # 将vtTickData数据转化为ctaTickData
            ctaTick = CtaTickData()
            d = ctaTick.__dict__
            for key in d.keys():
                if key != 'datetime':
                    d[key] = tick.__getattribute__(key)
            # 添加datetime字段
            ctaTick.datetime = datetime.strptime(' '.join([tick.date, tick.time]), '%Y%m%d %H:%M:%S.%f')

            ####################################################################
            ## william
            # 逐个推送到策略实例中
            l = self.tickStrategyDict[tick.vtSymbol]
            for strategy in l:
                self.callStrategyFunc(strategy, strategy.onTick, ctaTick)
                ## =============================================================
                ## william
                ## 把 TickData 数据推送到策略函数里面
                self.callStrategyFunc(strategy, strategy.onClosePosition, ctaTick)
                ## =============================================================
 
    #----------------------------------------------------------------------
    def processOrderEvent(self, event):
        """处理委托推送"""
        order = event.dict_['data']

        if order.vtOrderID in self.orderStrategyDict:
            strategy = self.orderStrategyDict[order.vtOrderID]
            self.callStrategyFunc(strategy, strategy.onOrder, order)

    #----------------------------------------------------------------------
    def processTradeEvent(self, event):
        """处理成交推送"""
        trade = event.dict_['data']

        # 过滤已经收到过的成交回报
        if trade.vtTradeID in self.tradeSet:
            return
        self.tradeSet.add(trade.vtTradeID)

        # 将成交推送到策略对象中
        if trade.vtOrderID in self.orderStrategyDict:
            strategy = self.orderStrategyDict[trade.vtOrderID]

            # 计算策略持仓
            if trade.direction == DIRECTION_LONG:
                strategy.pos += trade.volume
            else:
                strategy.pos -= trade.volume
            ## =================================================================
            ## william
            self.callStrategyFunc(strategy, strategy.onTrade, trade)

            ## 成交事件的处理
            self.callStrategyFunc(strategy, strategy.stratTradeEvent, trade)
            self.callStrategyFunc(strategy, strategy.closePositionTradeEvent, trade)
            ## =================================================================

        # 更新持仓缓存数据
        if trade.vtSymbol in self.tickStrategyDict:
            posBuffer = self.posBufferDict.get(trade.vtSymbol, None)
            if not posBuffer:
                posBuffer = PositionBuffer()
                posBuffer.vtSymbol = trade.vtSymbol
                self.posBufferDict[trade.vtSymbol] = posBuffer
            posBuffer.updateTradeData(trade)

    #----------------------------------------------------------------------
    def processPositionEvent(self, event):
        """处理持仓推送"""
        pos = event.dict_['data']

        # 更新持仓缓存数据
        if pos.vtSymbol in self.tickStrategyDict:
            posBuffer = self.posBufferDict.get(pos.vtSymbol, None)
            if not posBuffer:
                posBuffer = PositionBuffer()
                posBuffer.vtSymbol = pos.vtSymbol
                self.posBufferDict[pos.vtSymbol] = posBuffer
            posBuffer.updatePositionData(pos)
        ##

        ## =====================================================================
        ## 查询账户持仓
        ## =====================================================================
        tempRes = VtPositionData()
        d = tempRes.__dict__
        for key in d.keys():
            if key != 'datetime':
                d[key] = pos.__getattribute__(key)

        if tempRes.direction == u"多":
            tempRes.symbolPosition = tempRes.symbol + '-' + 'long'
        elif tempRes.direction == u"空":
            tempRes.symbolPosition = tempRes.symbol + '-' + 'short'
        else:
            tempRes.symbolPosition = tempRes.symbol + '-' + 'unknown'

        tempRes.datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        self.positionInfo[tempRes.__dict__['symbolPosition']] = tempRes.__dict__

        self.accountContracts = [self.positionInfo[k]['vtSymbol'] for k in self.positionInfo.keys() if int(self.positionInfo[k]['position']) != 0]
        ## =====================================================================


    ################################################################################################
    ## 注册监听，才能提取相关的数据
    ## event.dict_['data']
    ################################################################################################
    def registerEvent(self):
        """注册事件监听"""
        self.eventEngine.register(EVENT_TICK, self.processTickEvent)
        self.eventEngine.register(EVENT_ORDER, self.processOrderEvent)
        self.eventEngine.register(EVENT_TRADE, self.processTradeEvent)
        self.eventEngine.register(EVENT_POSITION, self.processPositionEvent)
 

    ################################################################################################
    ## mongoDB
    ################################################################################################
    def insertData(self, dbName, collectionName, data):
        """插入数据到数据库（这里的data可以是CtaTickData或者CtaBarData）"""
        self.mainEngine.dbInsert(dbName, collectionName, data.__dict__)

    #----------------------------------------------------------------------
    def loadBar(self, dbName, collectionName, days):
        """从数据库中读取Bar数据，startDate是datetime对象"""
        pass
        # startDate = self.today - timedelta(days)

        # d = {'datetime':{'$gte':startDate}}
        # barData = self.mainEngine.dbQuery(dbName, collectionName, d)

        # l = []
        # for d in barData:
        #     bar = CtaBarData()
        #     bar.__dict__ = d
        #     l.append(bar)
        # return l

    #----------------------------------------------------------------------
    def loadTick(self, dbName, collectionName, days):
        """从数据库中读取Tick数据，startDate是datetime对象"""
        pass
        # startDate = self.today - timedelta(days)

        # d = {'datetime':{'$gte':startDate}}
        # tickData = self.mainEngine.dbQuery(dbName, collectionName, d)

        # l = []
        # for d in tickData:
        #     tick = CtaTickData()
        #     tick.__dict__ = d
        #     l.append(tick)
        # return l

    ############################################################################
    ## william
    ## 从 MySQL 载入数据
    def loadMySQLDailyData(self, symbol, startDate, endDate):
        host, port, user, passwd = vtFunction.loadMySQLSetting()

        dbName = 'china_futures_bar'
        query  = 'select * from daily where InstrumentID = ' + \
                 '"' + str(symbol) + '"' + \
                 ' and (TradingDay between ' + \
                 str(startDate) + ' and ' + str(endDate) + ')' + \
                 ' and sector = "allday"'
        try:
            conn = MySQLdb.connect(host = host, port = port, db = dbName, user = user, passwd = passwd)
            mysqlData = pd.read_sql(query, conn)
            conn.close()
            tempFields = ['TradingDay','Sector','InstrumentID',
                          'OpenPrice','HighPrice','LowPrice','ClosePrice',
                          'Volume','Turnover',
                          # 'OpenOpenInterest','HighOpenInterest','LowOpenInterest','CloseOpenInterest',
                          'UpperLimitPrice','LowerLimitPrice','SettlementPrice']
            print "MySQL 查询成功!!!"
            return mysqlData[tempFields]
        except:
            print "MySQL 查询失败!!!"

    ############################################################################
    ## william
    ## 从 MySQL 载入数据
    def loadMySQLMinuteData(self, symbol, startDate, endDate):
        host, port, user, passwd = vtFunction.loadMySQLSetting()

        dbName = 'china_futures_bar'
        query  = 'select * from minute where InstrumentID = ' + \
                 '"' + str(symbol) + '"' + \
                 ' and (TradingDay between ' + \
                 str(startDate) + ' and ' + str(endDate) + ')'

        try:
            conn = MySQLdb.connect(host = host, port = port, db = dbName, user = user, passwd = passwd)
            mysqlData = pd.read_sql(query, conn)
            conn.close()
            tempFields = ['TradingDay','InstrumentID','Minute','NumericExchTime',
                          'OpenPrice','HighPrice','LowPrice','ClosePrice',
                          'Volume','Turnover',
                          'UpperLimitPrice','LowerLimitPrice']
            print "MySQL 查询成功!!!"
            return mysqlData[tempFields]
        except:
            print "MySQL 查询失败!!!"

    ################################################################################################
    ## 在屏幕上面打印日志
    ################################################################################################
    def writeCtaLog(self, content):
        """快速发出CTA模块日志事件"""
        log                 = VtLogData()
        log.logContent      = content
        event               = Event(type_=EVENT_CTA_LOG)
        event.dict_['data'] = log
        self.eventEngine.put(event)

    ############################################################################
    ## william
    ## 在这里修改多策略,多合约
    ## Ref: /home/william/Documents/vnpy/ref/单策略-多合约/说明.txt
    ############################################################################
    #---------------------------------------------------------------------------
    def loadStrategy(self, setting):
        """载入策略"""
        ## setting = {u'className': u'EmaDemoStrategy', u'name': u'double ema', u'vtSymbol': u'IF1706'}
        try:
            name = setting['name']
            className = setting['className']
        except Exception, e:
            print "\n"+'#'*80
            print '载入策略出错：%s' %e
            print '#'*80+"\n"
            self.writeCtaLog(u'载入策略出错：%s' %e)
            return

        ########################################################################
        ## william
        ## 查看是否在 ctaStrategy/strategy 目录下有策略
        # 获取策略类
        strategyClass = STRATEGY_CLASS.get(className, None)
        if not strategyClass:
            self.writeCtaLog(u'找不到策略类：%s' %className)
            return

        # 防止策略重名
        if name in self.strategyDict:
            print "\n"+'#'*80
            print '策略实例重名：%s' %name
            print '#'*80+"\n"
            self.writeCtaLog(u'策略实例重名：%s' %name)
        else:
            ####################################################################
            ## william
            ## 以下开始正式载入策略
            ####################################################################
            # 创建策略实例
            strategy = strategyClass(self, setting)
            self.strategyDict[name] = strategy

            ####################################################################
            ## william
            ## 在这里修改多合约
            ####################################################################

            ####################################################################
            ## william
            # 保存Tick映射关系
            if 'vtSymbol' in setting.keys() and len(setting['vtSymbol']) != 0:
                vtSymbolSet   = setting['vtSymbol'].replace(" ", "")
                vtSymbolStrat = vtSymbolSet.split(',')
                vtSymbolList  = list(set(self.subscribeContracts) | set(vtSymbolStrat))
            else:
                vtSymbolList  = list(set(self.subscribeContracts))

            for vtSymbol in vtSymbolList:
            #by hw 单个策略订阅多个合约，配置文件中"vtSymbol": "IF1602,IF1603"
                if vtSymbol in self.tickStrategyDict:
                    ############################################################
                    ## william
                    l = self.tickStrategyDict[vtSymbol]
                else:
                    l = []
                    ############################################################
                    ## william
                    self.tickStrategyDict[vtSymbol] = l
                l.append(strategy)

                # 订阅合约
                ################################################################
                ## william
                contract = self.mainEngine.getContract(vtSymbol)
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
                    self.mainEngine.subscribe(req, contract.gatewayName)
                    # self.mainEngine.subscribe(req, contract['gatewayName'])
                    ############################################################
                else:
                    ############################################################
                    ## william
                    print "\n"+'#'*80
                    print '%s的交易合约%s无法找到' %(name, vtSymbol)
                    print '#'*80+"\n"
                    self.writeCtaLog(u'%s的交易合约%s无法找到' %(name, vtSymbol))

    #----------------------------------------------------------------------
    def initStrategy(self, name):
        """初始化策略"""
        if name in self.strategyDict:
            strategy = self.strategyDict[name]

            if not strategy.inited:
                strategy.inited = True
                print "\n"+'#'*80
                print '初始化成功：%s' %name
                print '#'*80+"\n"
                self.callStrategyFunc(strategy, strategy.onInit)
            else:
                print "\n"+'#'*80
                print '请勿重复初始化策略实例：%s' %name
                print '#'*80+"\n"
                self.writeCtaLog(u'请勿重复初始化策略实例：%s' %name)
        else:
            print "\n"+'#'*80
            print '策略实例不存在：%s' %name
            print '#'*80+"\n"
            self.writeCtaLog(u'策略实例不存在：%s' %name)

    #---------------------------------------------------------------------------
    def startStrategy(self, name):
        """启动策略"""
        ## ---------------------------------------------------------------------
        ## 1.判断策略名称是否存在字典中
        if name in self.strategyDict:
            ## -----------------------------------------------------------------
            ## 2.提取策略
            strategy = self.strategyDict[name]
            ## -----------------------------------------------------------------
            ## 3.判断策略是否运行
            if strategy.inited and not strategy.trading:
                ## -----------------------------------------------------------------
                ## 4.设置运行状态
                strategy.trading = True
                ## -----------------------------------------------------------------
                ## 5.启动策略
                self.callStrategyFunc(strategy, strategy.onStart)
        else:
            print "\n"+'#'*80
            print '策略实例不存在：%s' %name
            print '#'*80+"\n"
            # self.writeCtaLog(u'策略实例不存在：%s' %name)

    #----------------------------------------------------------------------
    def stopStrategy(self, name):
        """停止策略"""

        ## ---------------------------------------------------------------------
        ## 1.判断策略名称是否存在字典中
        if name in self.strategyDict:
            ## -----------------------------------------------------------------
            ## 2.提取策略
            strategy = self.strategyDict[name]
            ## -----------------------------------------------------------------
            ## 3.停止交易
            if strategy.trading:
                ## -------------------------------------------------------------
                ## 4.设置交易状态为False
                strategy.trading = False
                ## -------------------------------------------------------------
                ## 5.调用策略的停止方法, onStop
                self.callStrategyFunc(strategy, strategy.onStop)
                ## -------------------------------------------------------------
                ## 6.对该策略发出的所有限价单进行撤单
                for vtOrderID, s in self.orderStrategyDict.items():
                    if s is strategy:
                        self.cancelOrder(vtOrderID)
                ## -------------------------------------------------------------
                ## 7.对该策略发出的所有本地停止单撤单
                for stopOrderID, so in self.workingStopOrderDict.items():
                    if so.strategy is strategy:
                        self.cancelStopOrder(stopOrderID)
        else:
            print "\n"+'#'*80
            print '策略实例不存在：%s' %name
            print '#'*80+"\n"
            # self.writeCtaLog(u'策略实例不存在：%s' %name)

    #----------------------------------------------------------------------
    def saveSetting(self):
        """保存策略配置"""
        with open(self.settingFileName, 'w') as f:
            l = []

            for strategy in self.strategyDict.values():
                setting = {}
                for param in strategy.paramList:
                    setting[param] = strategy.__getattribute__(param)
                l.append(setting)

            jsonL = json.dumps(l, indent=4)
            f.write(jsonL)

    ############################################################################
    ## william
    ## 加载 CTA_setting.json
    #---------------------------------------------------------------------------
    def loadSetting(self):
        """读取策略配置"""
        with open(self.settingFileName) as f:
            l = json.load(f)

            for setting in l:
                ## setting = {u'className': u'EmaDemoStrategy', u'name': u'double ema', u'vtSymbol': u'IF1706'}
                self.loadStrategy(setting)

        self.loadPosition()

        print "\n"+'#'*80
        print "CTA_setting.json 加载成功!!!"
        print '#'*80+"\n"

    #----------------------------------------------------------------------
    def getStrategyVar(self, name):
        """获取策略当前的变量字典"""
        if name in self.strategyDict:
            strategy = self.strategyDict[name]
            varDict = OrderedDict()

            for key in strategy.varList:
                varDict[key] = strategy.__getattribute__(key)

            return varDict
        else:
            print "\n"+'#'*80
            print '策略实例不存在：%s' %name
            print '#'*80+"\n"
            self.writeCtaLog(u'策略实例不存在：' + name)
            return None

    #----------------------------------------------------------------------
    def getStrategyParam(self, name):
        """获取策略的参数字典"""
        if name in self.strategyDict:
            strategy = self.strategyDict[name]
            paramDict = OrderedDict()

            for key in strategy.paramList:
                paramDict[key] = strategy.__getattribute__(key)

            return paramDict
        else:
            print "\n"+'#'*80
            print '策略实例不存在：%s' %name
            print '#'*80+"\n"
            self.writeCtaLog(u'策略实例不存在：' + name)
            return None

    #----------------------------------------------------------------------
    def putStrategyEvent(self, name):
        """触发策略状态变化事件（通常用于通知GUI更新）"""
        event = Event(EVENT_CTA_STRATEGY+name)
        self.eventEngine.put(event)

    #----------------------------------------------------------------------
    def callStrategyFunc(self, strategy, func, params=None):
        """调用策略的函数，若触发异常则捕捉"""
        try:
            if params:
                func(params)
            else:
                func()
        except Exception:
            # 停止策略，修改状态为未初始化
            strategy.trading = False
            strategy.inited = False

            # 发出日志
            content = '\n'.join([u'策略%s触发异常已停止' %strategy.name,
                                traceback.format_exc()])
            print "\n"+'#'*80
            print content
            print '#'*80+"\n"
            self.writeCtaLog(content)

    #----------------------------------------------------------------------
    def savePosition(self):
        """保存所有策略的持仓情况到数据库"""
        for strategy in self.strategyDict.values():
            flt = {'name': strategy.name,
                   'vtSymbol': strategy.vtSymbol}

            d = {'name': strategy.name,
                 'vtSymbol': strategy.vtSymbol,
                 'pos': strategy.pos}

            self.mainEngine.dbUpdate(POSITION_DB_NAME, strategy.className,
                                     d, flt, True)

            content = '策略%s持仓保存成功' %strategy.name
            print "\n"+'#'*80
            print content
            print '#'*80+"\n"
            self.writeCtaLog(content)

    #----------------------------------------------------------------------
    def loadPosition(self):
        """从数据库载入策略的持仓情况"""
        for strategy in self.strategyDict.values():
            flt = {'name': strategy.name,
                   'vtSymbol': strategy.vtSymbol}
            posData = self.mainEngine.dbQuery(POSITION_DB_NAME, strategy.className, flt)

            for d in posData:
                strategy.pos = d['pos']

    #----------------------------------------------------------------------
    def roundToPriceTick(self, priceTick, price):
        """取整价格到合约最小价格变动"""
        if not priceTick:
            return price

        newPrice = round(price/priceTick, 0) * priceTick
        return newPrice

    ################################################################################################
    ## 全平仓
    ## 已在界面实现，具体可以参考 
    ## /main/uiBasicWidget.py
    ################################################################################################
    def closeAll(self):
        """
        一键全平仓
        """
        pass

    ################################################################################################
    ## 获取基金的 InstrumentID
    ################################################################################################
    def fetchInstrumentID(self, dbName, tbName):
        temp = self.mainEngine.dbMySQLQuery(dbName,
            """
            select * from %s
            """ %(tbName))
        return(temp.InstrumentID.values)

########################################################################
class PositionBuffer(object):
    """持仓缓存信息（本地维护的持仓数据）"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.vtSymbol      = EMPTY_STRING
        
        # 多头
        self.longPosition  = EMPTY_INT
        self.longToday     = EMPTY_INT
        self.longYd        = EMPTY_INT
        
        # 空头
        self.shortPosition = EMPTY_INT
        self.shortToday    = EMPTY_INT
        self.shortYd       = EMPTY_INT

    #----------------------------------------------------------------------
    def updatePositionData(self, pos):
        """更新持仓数据"""
        if pos.direction == DIRECTION_LONG:
            self.longPosition = pos.position
            self.longYd       = pos.ydPosition
            self.longToday    = self.longPosition - self.longYd
        else:
            self.shortPosition = pos.position
            self.shortYd       = pos.ydPosition
            self.shortToday    = self.shortPosition - self.shortYd

    #----------------------------------------------------------------------
    def updateTradeData(self, trade):
        """更新成交数据"""
        if trade.direction == DIRECTION_LONG:
            # 多方开仓，则对应多头的持仓和今仓增加
            if trade.offset == OFFSET_OPEN:
                self.longPosition += trade.volume
                self.longToday    += trade.volume
            # 多方平今，对应空头的持仓和今仓减少
            elif trade.offset == OFFSET_CLOSETODAY:
                self.shortPosition -= trade.volume
                self.shortToday    -= trade.volume
            # 多方平昨，对应空头的持仓和昨仓减少
            else:
                self.shortPosition -= trade.volume
                self.shortYd       -= trade.volume
        else:
            # 空头和多头相同
            if trade.offset == OFFSET_OPEN:
                self.shortPosition += trade.volume
                self.shortToday    += trade.volume
            elif trade.offset == OFFSET_CLOSETODAY:
                self.longPosition -= trade.volume
                self.longToday    -= trade.volume
            else:
                self.longPosition -= trade.volume
                self.longYd       -= trade.volume
