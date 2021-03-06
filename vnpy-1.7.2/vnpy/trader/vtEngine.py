# encoding: UTF-8

import os
import shelve
import logging
from logging import INFO, ERROR
from collections import OrderedDict
from datetime import datetime
from time import sleep
from copy import copy

from pymongo import MongoClient, ASCENDING
from pymongo.errors import ConnectionFailure
## -----------------------------------
import MySQLdb
import numpy as np
import pandas as pd
pd.set_option('display.width', 200)
pd.set_option('display.max_rows', 100)
## -----------------------------------
from vnpy.event import Event
from vnpy.trader.vtGlobal import globalSetting
from vnpy.trader.vtEvent import *
from vnpy.trader.vtGateway import *
from vnpy.trader.language import text
from vnpy.trader import vtFunction
from vnpy.trader.vtObject import VtSubscribeReq, VtCancelOrderReq


########################################################################
class MainEngine(object):
    """主引擎"""

    #----------------------------------------------------------------------
    def __init__(self, eventEngine):
        """Constructor"""
        # 记录今日日期
        self.todayDate = datetime.now().strftime('%Y%m%d')
        self.tradingDay = vtFunction.tradingDay()
        self.tradingDate = vtFunction.tradingDate()
        self.lastTradingDay = vtFunction.lastTradingDay()
        self.lastTradingDate = vtFunction.lastTradingDate()

        # 绑定事件引擎
        self.eventEngine = eventEngine
        self.eventEngine.start()
        
        # 创建数据引擎
        self.dataEngine = DataEngine(self.eventEngine)
        
        ## -----------------------------------------
        ## 是否订阅所有合约
        self.subscribeAll = False
        ## 是否打印合约
        self.printData = False
        ## -----------------------------------------

        ## -------------------------------------------
        ## william
        ## 设置数据库连接初始状态
        # MongoDB数据库相关
        self.dbMongoClient = None    # MongoDB客户端对象
        ## MySQL 数据库相关
        self.dbMySQLClient = None
        ## ------------------------------------------

        # 接口实例
        self.gatewayDict = OrderedDict()  # 使用 mainEngine.gatwwayDict['CTP'] 获取
        self.gatewayDetailList = []
        
        # 应用模块实例
        self.appDict = OrderedDict()
        self.appDetailList = []
        
        # 风控引擎实例（特殊独立对象）
        self.rmEngine = None
        
        # 日志引擎实例
        self.logEngine = None
        self.initLogEngine()

    #----------------------------------------------------------------------
    def addGateway(self, gatewayModule):
        """添加底层接口"""
        gatewayName = gatewayModule.gatewayName
        
        # 创建接口实例
        self.gatewayDict[gatewayName] = gatewayModule.gatewayClass(self.eventEngine, 
                                                                   gatewayName)
        
        # 设置接口轮询
        if gatewayModule.gatewayQryEnabled:
            self.gatewayDict[gatewayName].setQryEnabled(gatewayModule.gatewayQryEnabled)
                
        # 保存接口详细信息
        d = {
            'gatewayName': gatewayModule.gatewayName,
            'gatewayDisplayName': gatewayModule.gatewayDisplayName,
            'gatewayType': gatewayModule.gatewayType
        }
        self.gatewayDetailList.append(d)
        
    #----------------------------------------------------------------------
    def addApp(self, appModule):
        """添加上层应用"""
        appName = appModule.appName
        
        # 创建应用实例
        self.appDict[appName] = appModule.appEngine(self, self.eventEngine)
        
        # 将应用引擎实例添加到主引擎的属性中
        self.__dict__[appName] = self.appDict[appName]
        
        # 保存应用信息
        d = {
            'appName': appModule.appName,
            'appDisplayName': appModule.appDisplayName,
            'appWidget': appModule.appWidget,
            'appIco': appModule.appIco
        }
        self.appDetailList.append(d)
        
    #----------------------------------------------------------------------
    def getGateway(self, gatewayName):
        """获取接口"""
        if gatewayName in self.gatewayDict:
            return self.gatewayDict[gatewayName]
        else:
            self.writeLog(text.GATEWAY_NOT_EXIST.format(gateway=gatewayName))
            return None
        
    #----------------------------------------------------------------------
    def connect(self, accountID, gatewayName = 'CTP'):
        """连接特定名称的接口"""
        gateway = self.getGateway(gatewayName)
        
        if gateway:
            gateway.connect(accountID)
            sleep(1)
            if gatewayName == 'CTP':
                ## -------------------------------------------------------------
                if not self.gatewayDict['CTP'].mdConnected:
                    self.writeLog(content = u'CTP [md] 行情服务器连接失败', 
                                  logLevel = ERROR, 
                                  gatewayName = 'CTP')
                ## -------------------------------------------------------------
                if not self.gatewayDict['CTP'].tdConnected:
                    self.writeLog(content = u'CTP [td] 交易服务器连接失败', 
                                  logLevel = ERROR, 
                                  gatewayName = 'CTP')
                ## -------------------------------------------------------------
                if (not self.gatewayDict['CTP'].mdConnected and
                    not self.gatewayDict['CTP'].tdConnected):
                    self.writeLog(content = u'账户登录失败', 
                                  logLevel = ERROR, 
                                  gatewayName = 'CTP')
            ## -----------------------------------------------------------------
            ## 接口连接后自动执行数据库连接的任务
            ## self.dbMySQLConnect()     
            ## -----------------------------------------------------------------
   

    #----------------------------------------------------------------------
    def subscribe(self, subscribeReq, gatewayName):
        """订阅特定接口的行情"""
        gateway = self.getGateway(gatewayName)
        
        if gateway:
            gateway.subscribe(subscribeReq)
  
    #----------------------------------------------------------------------
    def sendOrder(self, orderReq, gatewayName):
        """对特定接口发单"""
        # 如果创建了风控引擎，且风控检查失败则不发单
        if self.rmEngine and not self.rmEngine.checkRisk(orderReq, gatewayName):
            return ''

        gateway = self.getGateway(gatewayName)
        
        if gateway:
            vtOrderID = gateway.sendOrder(orderReq)
            self.dataEngine.updateOrderReq(orderReq, vtOrderID)     # 更新发出的委托请求到数据引擎中
            return vtOrderID
        else:
            return ''
        
    #----------------------------------------------------------------------
    def cancelOrder(self, cancelOrderReq, gatewayName):
        """对特定接口撤单"""
        gateway = self.getGateway(gatewayName)
        
        if gateway:
            gateway.cancelOrder(cancelOrderReq)   
  
    ############################################################################
    ## william
    ## 一键全部撤单
    ## ref: /vn.trader/uiBasicWidget.py
    ##      cancelOrderAll()
    ############################################################################
    def cancelAll(self):
        """一键撤销所有委托"""
        AllWorkingOrders = self.getAllWorkingOrders()
        for order in AllWorkingOrders:
            req = VtCancelOrderReq()
            req.symbol    = order.symbol
            req.exchange  = order.exchange
            req.frontID   = order.frontID
            req.sessionID = order.sessionID
            req.orderID   = order.orderID 
            self.cancelOrder(req, order.gatewayName)
            self.writeLog(text.CANCEL_ALL)

    ############################################################################
    ## william
    ## 全平
    ############################################################################
    def closeAll(self):
        """一键全平"""
        ## -----------------------------------------------------------------
        ## 先撤销所有的订单
        # try:
        #     self.CtaStrategy.loadSetting()
        # except:
        #     None
        self.cancelAll()
        ## -----------------------------------------------------------------
        
        CTPAccountPosInfo = {k:{u:self.dataEngine.positionInfo[k][u] for u in self.dataEngine.positionInfo[k].keys() if u in ['vtSymbol','position','direction']} for k in self.dataEngine.positionInfo.keys() if int(self.dataEngine.positionInfo[k]['position']) != 0}
        # if not CTPAccountPosInfo:
        #     return

        ## =====================================================================
        CTAORDER_BUY = u'买开'
        CTAORDER_SELL = u'卖平'
        CTAORDER_SHORT = u'卖开'
        CTAORDER_COVER = u'买平'

        ## ---------------------------------------------------------------------
        class strategyClass(object):
            name = 'CLOSE_ALL'
            productClass = ''
            currency = ''
        tempStrategy = strategyClass()
        ## ---------------------------------------------------------------------

        ## ---------------------------------------------------------------------
        ## 订阅合约行情
        ## ---------------------------------------------------------------------
        for i in self.dataEngine.positionInfo.keys():
            req = VtSubscribeReq()
            req.symbol = self.dataEngine.positionInfo[i]['symbol']
            self.subscribe(req, 'CTP')
            if req.symbol not in self.CtaStrategy.subscribeContracts:
                self.CtaStrategy.subscribeContracts.append(req.symbol)
        ## ---------------------------------------------------------------------
        sleep(1)
        ## =====================================================================
        for i in CTPAccountPosInfo.keys():
            ## -----------------------------------------------------------------
            try:
                tempInstrumentID = CTPAccountPosInfo[i]['vtSymbol']
                tempVolume       = CTPAccountPosInfo[i]['position']
                tempPriceTick    = self.getContract(tempInstrumentID).priceTick
                tempLastPrice    = self.gatewayDict['CTP'].lastTickDict[tempInstrumentID]['lastPrice']
                tempUpperLimit   = self.gatewayDict['CTP'].lastTickDict[tempInstrumentID]['upperLimit']
                tempLowerLimit   = self.gatewayDict['CTP'].lastTickDict[tempInstrumentID]['lowerLimit']
                self.writeLog('%s ：全平仓 %0d@%.2f' %(tempInstrumentID, tempVolume, tempLastPrice),
                              gatewayName = 'CTP')
                ## -------------------------------------------------------------
                if CTPAccountPosInfo[i]['direction'] == u'多':
                    self.CtaStrategy.sendOrder(
                        vtSymbol  = tempInstrumentID,
                        orderType = CTAORDER_SELL,
                        price     = self.priceBetweenUpperLower(
                                         max(tempLowerLimit, tempLastPrice - 1*tempPriceTick), 
                                         tempInstrumentID),
                        volume    = tempVolume,
                        strategy  = tempStrategy)
                elif CTPAccountPosInfo[i]['direction'] == u'空':
                    self.CtaStrategy.sendOrder(
                        vtSymbol  = tempInstrumentID,
                        orderType = CTAORDER_COVER,
                        price     = self.priceBetweenUpperLower(
                                         min(tempUpperLimit, tempLastPrice + 1*tempPriceTick),
                                         tempInstrumentID),
                        volume    = tempVolume,
                        strategy  = tempStrategy)
                ## -------------------------------------------------------------
            except:
               # self.writeLog('%s ：平仓失败' %tempInstrumentID, logLevel = ERROR,
               #               gatewayName = 'CTP')
               pass
        ## =====================================================================


    #----------------------------------------------------------------------
    def qryAccount(self, gatewayName):
        """查询特定接口的账户"""
        gateway = self.getGateway(gatewayName)
        
        if gateway:
            gateway.qryAccount()      
        
    #----------------------------------------------------------------------
    def qryPosition(self, gatewayName):
        """查询特定接口的持仓"""
        gateway = self.getGateway(gatewayName)
        
        if gateway:
            gateway.qryPosition()
            
    #----------------------------------------------------------------------
    def exit(self):
        """退出程序前调用，保证正常退出"""        
        # 安全关闭所有接口
        for gateway in self.gatewayDict.values():        
            gateway.close()
        
        # 停止事件引擎
        self.eventEngine.stop()
        
        # 停止上层应用引擎
        for appEngine in self.appDict.values():
            appEngine.stop()
        
        # 保存数据引擎里的合约数据到硬盘
        self.dataEngine.saveContracts()
    
    #----------------------------------------------------------------------
    def writeLog(self, content, logLevel = INFO, gatewayName = 'MAIN_ENGINE'):
        """快速发出日志事件"""
        log = VtLogData()
        # log.logContent = content + '\n'
        log.logContent = content
        log.gatewayName = gatewayName
        log.logLevel = logLevel
        event = Event(type_= EVENT_LOG)
        event.dict_['data'] = log
        self.eventEngine.put(event)        
    
    #----------------------------------------------------------------------
    def dbMongoConnect(self):
        """连接MongoDB数据库"""
        if not self.dbMongoClient:
            # 读取MongoDB的设置
            try:
                # 设置MongoDB操作的超时时间为0.5秒
                self.dbMongoClient = MongoClient(globalSetting().vtSetting['mongoHost'], 
                                                 globalSetting().vtSetting['mongoPort'], 
                                                 connectTimeoutMS=500)
                
                # 调用server_info查询服务器状态，防止服务器异常并未连接成功
                self.dbMongoClient.server_info()

                self.writeLog(text.DATABASE_Mongo_CONNECTING_COMPLETED)
                
                # 如果启动日志记录，则注册日志事件监听函数
                if globalSetting().vtSetting['mongoLogging']:
                    self.eventEngine.register(EVENT_LOG, self.dbMongoLogging)
                    
            except ConnectionFailure:
                self.writeLog(text.DATABASE_Mongo_CONNECTING_FAILED)

    #----------------------------------------------------------------------
    def dbMongoInsert(self, dbName, collectionName, d):
        """向MongoDB中插入数据，d是具体数据"""
        if self.dbMongoClient:
            db = self.dbMongoClient[dbName]
            collection = db[collectionName]
            collection.insert_one(d)
        else:
            self.writeLog(text.DATA_Mongo_INSERT_FAILED)
    
    #----------------------------------------------------------------------
    def dbMongoQuery(self, dbName, collectionName, d, sortKey='', sortDirection=ASCENDING):
        """从MongoDB中读取数据，d是查询要求，返回的是数据库查询的指针"""
        if self.dbMongoClient:
            db = self.dbMongoClient[dbName]
            collection = db[collectionName]
            
            if sortKey:
                cursor = collection.find(d).sort(sortKey, sortDirection)    # 对查询出来的数据进行排序
            else:
                cursor = collection.find(d)

            if cursor:
                return list(cursor)
            else:
                return []
        else:
            self.writeLog(text.DATA_Mongo_QUERY_FAILED)   
            return []
        
    #----------------------------------------------------------------------
    def dbMongoUpdate(self, dbName, collectionName, d, flt, upsert=False):
        """向MongoDB中更新数据，d是具体数据，flt是过滤条件，upsert代表若无是否要插入"""
        if self.dbMongoClient:
            db = self.dbCMongolient[dbName]
            collection = db[collectionName]
            collection.replace_one(flt, d, upsert)
        else:
            self.writeLog(text.DATA_Mongo_UPDATE_FAILED)        
            
    #----------------------------------------------------------------------
    def dbMongoLogging(self, event):
        """向MongoDB中插入日志"""
        log = event.dict_['data']
        d = {
            'content': log.logContent,
            'time': log.logTime,
            'gateway': log.gatewayName
        }
        self.dbMongoInsert(LOG_DB_NAME, self.todayDate, d)


    ## =========================================================================
    ## william
    ## dbMySQLConnect
    ## -------------------------------------------------------------------------
    def dbMySQLConnect(self,  dbName = 'dev'):
        """连接 MySQL 数据库"""
        if not self.dbMySQLClient:
            # 读取 MySQL 的设置
            try:
                conn = MySQLdb.connect(db          = dbName, 
                                       host        = globalSetting().vtSetting["mysqlHost"], 
                                       port        = globalSetting().vtSetting["mysqlPort"], 
                                       user        = globalSetting().vtSetting["mysqlUser"], 
                                       passwd      = globalSetting().vtSetting["mysqlPassword"], 
                                       use_unicode = True, 
                                       charset     = "utf8")
                self.writeLog(text.DATABASE_MySQL_CONNECTING_COMPLETED)
                self.dbMySQLClient = True
                return conn
            except (MySQLdb.Error, MySQLdb.Warning, TypeError) as e:
                print e
                self.writeLog(text.DATABASE_MySQL_CONNECTING_FAILED)    
            finally:
                conn.close()
    ## =========================================================================

    ## =========================================================================
    ## william
    ## 从 MySQL 数据库查询数据
    ## -------------------------------------------------------------------------
    def dbMySQLQuery(self, dbName, query):
        """ 从 MySQL 中读取数据 """
        try:
            conn = MySQLdb.connect(db          = dbName, 
                                   host        = globalSetting().vtSetting["mysqlHost"], 
                                   port        = globalSetting().vtSetting["mysqlPort"], 
                                   user        = globalSetting().vtSetting["mysqlUser"], 
                                   passwd      = globalSetting().vtSetting["mysqlPassword"], 
                                   use_unicode = True, 
                                   charset     = "utf8")
            mysqlData = pd.read_sql(str(query), conn)
            return mysqlData
            self.writeLog(text.DATA_MySQL_QUERY_COMPLETED)
        except (MySQLdb.Error, MySQLdb.Warning, TypeError) as e:
            print e
            self.writeLog(text.DATA_MySQL_QUERY_FAILED)
        finally:
            conn.close()
    ## =========================================================================


    #----------------------------------------------------------------------
    def getContract(self, vtSymbol):
        """查询合约"""
        return self.dataEngine.getContract(vtSymbol)
    
    #----------------------------------------------------------------------
    def getAllContracts(self):
        """查询所有合约（返回列表）"""
        return self.dataEngine.getAllContracts()
    
    #----------------------------------------------------------------------
    def getOrder(self, vtOrderID):
        """查询委托"""
        return self.dataEngine.getOrder(vtOrderID)
    
    #----------------------------------------------------------------------
    def getPositionDetail(self, vtSymbol):
        """查询持仓细节"""
        return self.dataEngine.getPositionDetail(vtSymbol)
    
    #----------------------------------------------------------------------
    def getAllWorkingOrders(self):
        """查询所有的活跃的委托（返回列表）"""
        return self.dataEngine.getAllWorkingOrders()
    
    #----------------------------------------------------------------------
    def getAllOrders(self):
        """查询所有委托"""
        return self.dataEngine.getAllOrders()
    
    #----------------------------------------------------------------------
    def getAllOrdersDataFrame(self):
        """查询所有委托"""
        return self.dataEngine.getAllOrdersDataFrame()

    #----------------------------------------------------------------------
    def getAllPositionDetails(self):
        """查询本地持仓缓存细节"""
        return self.dataEngine.getAllPositionDetails()
    
    #----------------------------------------------------------------------
    def getAllGatewayDetails(self):
        """查询引擎中所有底层接口的信息"""
        return self.gatewayDetailList
    
    #----------------------------------------------------------------------
    def getAllAppDetails(self):
        """查询引擎中所有上层应用的信息"""
        return self.appDetailList
    
    #----------------------------------------------------------------------
    def getApp(self, appName):
        """获取APP引擎对象"""
        return self.appDict[appName]
    
    #----------------------------------------------------------------------
    def initLogEngine(self):
        """初始化日志引擎"""
        if not globalSetting().vtSetting["logActive"]:
            return
        
        # 创建引擎
        self.logEngine = LogEngine()
        
        # 设置日志级别
        levelDict = {
            "debug": LogEngine.LEVEL_DEBUG,
            "info": LogEngine.LEVEL_INFO,
            "warn": LogEngine.LEVEL_WARN,
            "error": LogEngine.LEVEL_ERROR,
            "critical": LogEngine.LEVEL_CRITICAL,
        }
        level = levelDict.get(globalSetting().vtSetting["logLevel"], LogEngine.LEVEL_CRITICAL)
        self.logEngine.setLogLevel(level)
        
        # 设置输出
        if globalSetting().vtSetting['logConsole']:
            self.logEngine.addConsoleHandler()
            
        if globalSetting().vtSetting['logFile']:
            self.logEngine.addFileHandler()
            
        # 注册事件监听
        self.registerLogEvent(EVENT_LOG)
    
    #----------------------------------------------------------------------
    def registerLogEvent(self, eventType):
        """注册日志事件监听"""
        if self.logEngine:
            self.eventEngine.register(eventType, self.logEngine.processLogEvent)
    
    #----------------------------------------------------------------------
    def convertOrderReq(self, req):
        """转换委托请求"""
        return self.dataEngine.convertOrderReq(req)
        
    def priceBetweenUpperLower(self, price, vtSymbol):
        """保证价格在 UpperLimit 和 LowerLimit 之间"""
        tempUpperLimit = self.gatewayDict['CTP'].lastTickDict[vtSymbol]['upperLimit']
        tempLowerLimit = self.gatewayDict['CTP'].lastTickDict[vtSymbol]['lowerLimit']
        return min(max(tempLowerLimit, price), tempUpperLimit)


########################################################################
class DataEngine(object):
    """数据引擎"""
    contractFileName = 'ContractData.vt'
    contractFilePath = vtFunction.getTempPath(contractFileName)

    contractAllFileName = 'contractAll.csv'
    contractAllFilePath = vtFunction.getTempPath(contractAllFileName)
    
    FINISHED_STATUS = [STATUS_ALLTRADED, STATUS_REJECTED, STATUS_CANCELLED]

    #----------------------------------------------------------------------
    def __init__(self, eventEngine):
        """Constructor"""
        self.eventEngine = eventEngine

        self.dataBase = globalSetting.accountID
        
        self.tradingDay = vtFunction.tradingDay()
        self.tradingDate = vtFunction.tradingDate()
        self.lastTradingDay = vtFunction.lastTradingDay()
        self.lastTradingDate = vtFunction.lastTradingDate()        

        # 保存合约详细信息的字典
        self.contractDict = {}
        # 保存委托数据的字典
        self.orderDict = {}
        self.tradeDict = {}
        # 保存活动委托数据的字典（即可撤销）
        self.workingOrderDict = {}
        
        # 持仓细节相关
        self.detailDict = {}                                # vtSymbol:PositionDetail
        self.tdPenaltyList = globalSetting().vtSetting['tdPenalty']     # 平今手续费惩罚的产品代码列表
        
        ########################################################################
        ## william
        ##
        self.accountInfo = VtAccountData()
        ## 多个合约的持仓信息
        ## 返回一个字典,避免重复
        ## key 是 vtGateway/VtPositionData/ 下面的 symbolPosition
        ## symbolPosition 格式:i1709-long(short), 代表合约多空
        self.positionInfo = {}

        self.tradeInfo = VtTradeData()
        ########################################################################


        # 读取保存在硬盘的合约数据
        self.loadContracts()
        
        # 注册事件监听
        self.registerEvent()
    
    #----------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.eventEngine.register(EVENT_CONTRACT, self.processContractEvent)
        self.eventEngine.register(EVENT_ORDER, self.processOrderEvent)
        self.eventEngine.register(EVENT_TRADE, self.processTradeEvent)
        self.eventEngine.register(EVENT_POSITION, self.processPositionEvent)

        self.eventEngine.register(EVENT_ACCOUNT, self.processAccountEvent)
        ## ---------------------------------------------------------------------

    #----------------------------------------------------------------------
    def processContractEvent(self, event):
        """处理合约事件"""
        contract = event.dict_['data']
        self.contractDict[contract.vtSymbol] = contract
        self.contractDict[contract.symbol] = contract       # 使用常规代码（不包括交易所）可能导致重复
    
    #----------------------------------------------------------------------
    def processOrderEvent(self, event):
        """处理委托事件"""
        order = event.dict_['data']      
        self.orderDict[order.vtOrderID] = order
        # 如果订单的状态是全部成交或者撤销，则需要从workingOrderDict中移除
        if order.status in self.FINISHED_STATUS:
            if order.vtOrderID in self.workingOrderDict:
                del self.workingOrderDict[order.vtOrderID]
        # 否则则更新字典中的数据        
        else:
            self.workingOrderDict[order.vtOrderID] = order

        # 更新到持仓细节中
        detail = self.getPositionDetail(order.vtSymbol)
        detail.updateOrder(order)
            
    #----------------------------------------------------------------------
    def processTradeEvent(self, event):
        """处理成交事件"""
        trade = event.dict_['data']

        ## ---------------------------------------------------------------------
        trade.status = self.orderDict[trade.vtOrderID].status
        trade.orderTime   = self.orderDict[trade.vtOrderID].orderTime
        trade.totalVolume = self.orderDict[trade.vtOrderID].totalVolume
        trade.tradedVolume = self.orderDict[trade.vtOrderID].tradedVolume
        self.tradeDict[trade.vtOrderID] = trade
        self.orderDict[trade.vtOrderID].tradeTime = trade.tradeTime
        ## ---------------------------------------------------------------------

        # 更新到持仓细节中
        detail = self.getPositionDetail(trade.vtSymbol)
        detail.updateTrade(trade)        

        ## ---------------------------------------------------------------------
        ## 成交订单
        temp = pd.DataFrame([trade.__dict__.values()], columns = trade.__dict__.keys())
        ## ---------------------------------------------------------------------
        if globalSetting.LOGIN and globalSetting.PRINT_TRADE:
            content = u"成交的详细信息\n%s\n%s\n%s" %('-'*80,
                temp[['vtOrderID','vtSymbol','offset','direction','price', 
                      'tradedVolume','tradeTime','status']].to_string(index=False),
                '-'*80)
            self.writeLog(content, gatewayName = 'CTP')
        ## ---------------------------------------------------------------------


    #----------------------------------------------------------------------
    def processPositionEvent(self, event):
        """处理持仓事件"""
        position = event.dict_['data']

        ## ---------------------------------------------------------------------
        position.datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if position.direction == u"多":
            position.symbolPosition = position.symbol + '-' + 'long'
        elif position.direction == u"空":
            position.symbolPosition = position.symbol + '-' + 'short'
        else:
            position.symbolPosition = position.symbol + '-' + 'unknown'
        ## ---------------------------------------------------------------------

        # 更新到持仓细节中
        detail = self.getPositionDetail(position.vtSymbol)
        detail.updatePosition(position)            

        ## ---------------------------------------------------------------------
        self.positionInfo[position.vtSymbol] = position.__dict__
        ## ---------------------------------------------------------------------
        
    ############################################################################
    ## william
    ## 获取账户信息
    ## def processAccountEvent(self, event):
    ############################################################################
    def processAccountEvent(self, event):
        """处理账户推送"""
        self.accountInfo = event.dict_['data']

        ########################################################################
        # 转化 VtAccount 格式
        self.accountInfo.datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # ----------------------------------------------------------------------

    #----------------------------------------------------------------------
    def getContract(self, vtSymbol):
        """查询合约对象"""
        try:
            return self.contractDict[vtSymbol]
        except KeyError:
            return None
        
    #----------------------------------------------------------------------
    def getAllContracts(self):
        """查询所有合约对象（返回列表）"""
        return self.contractDict.values()
    
    #----------------------------------------------------------------------
    def saveContracts(self):
        """保存所有合约对象到硬盘"""
        f = shelve.open(self.contractFilePath)
        f['data'] = self.contractDict
        f.close()
    
    #----------------------------------------------------------------------
    def loadContracts(self):
        """从硬盘读取合约对象"""
        try:
            f = shelve.open(self.contractFilePath)
            if 'data' in f:
                d = f['data']
                for key, value in d.items():
                    self.contractDict[key] = value
            f.close()
        except:
            # pass
            dfAll = pd.read_csv(self.contractAllFilePath)
            for i in range(len(dfAll)):
                ## -------------------------------------------------------------
                contract = VtContractData()
                contract.symbol = dfAll.at[i,'symbol']
                contract.exchange = dfAll.at[i,'exchange']
                contract.vtSymbol = dfAll.at[i,'vtSymbol']
                contract.name = dfAll.at[i,'name']
                contract.productClass = dfAll.at[i,'productClass']
                contract.size = dfAll.at[i,'size']
                contract.priceTick = dfAll.at[i,'priceTick']
                contract.volumeMultiple = dfAll.at[i,'size']
                contract.longMarginRatio = round(dfAll.at[i,'longMarginRatio'],4)
                contract.shortMarginRatio = round(dfAll.at[i,'shortMarginRatio'],4)
                contract.strikePrice = dfAll.at[i,'strikePrice']
                contract.underlyingSymbol = dfAll.at[i,'underlyingSymbol']
                contract.optionType = dfAll.at[i,'optionType']
                ## -------------------------------------------------------------
                self.contractDict[dfAll.at[i,'vtSymbol']] = contract

    #----------------------------------------------------------------------
    def getOrder(self, vtOrderID):
        """查询委托"""
        try:
            return self.orderDict[vtOrderID]
        except KeyError:
            return None
    
    #----------------------------------------------------------------------
    def getAllWorkingOrders(self):
        """查询所有活动委托（返回列表）"""
        return self.workingOrderDict.values()
    
    #----------------------------------------------------------------------
    def getAllOrders(self):
        """获取所有委托"""
        return self.orderDict.values()

    #----------------------------------------------------------------------
    def getAllOrdersDataFrame(self):
        """获取所有委托"""
        ########################################################################
        ## william
        ########################################################################
        allOrders = self.orderDict.values()

        if len(allOrders) != 0:
            dfHeader = allOrders[0].__dict__.keys()
            dfData   = []
            for i in range(len(allOrders)):
                dfData.append(allOrders[i].__dict__.values())
            df = pd.DataFrame(dfData, columns = dfHeader)
            ## -----------------------------------------------------------------
            return df
        else:
            self.writeLog("没有查询到订单!!!", logLevel = ERROR)
            return pd.DataFrame()

    #----------------------------------------------------------------------
    def getPositionDetail(self, vtSymbol):
        """查询持仓细节"""
        if vtSymbol in self.detailDict:
            detail = self.detailDict[vtSymbol]
        else:
            detail = PositionDetail(vtSymbol)
            self.detailDict[vtSymbol] = detail
            
            # 设置持仓细节的委托转换模式
            contract = self.getContract(vtSymbol)
            
            if contract:
                detail.exchange = contract.exchange
                
                ## -------------------------------------------------------------
                ## william
                ## 对股票的平今、平昨模式进行确认
                ## 上期所合约
                ## -------------------------------------------------------------
                if contract.exchange == EXCHANGE_SHFE:
                    detail.mode = detail.MODE_SHFE
                
                # 检查是否有平今惩罚
                for productID in self.tdPenaltyList:
                    if str(productID) in contract.symbol:
                        detail.mode = detail.MODE_TDPENALTY
                
        return detail
    
    #----------------------------------------------------------------------
    def getAllPositionDetails(self):
        """查询所有本地持仓缓存细节"""
        return self.detailDict.values()
    
    #----------------------------------------------------------------------
    def updateOrderReq(self, req, vtOrderID):
        """委托请求更新"""
        vtSymbol = req.vtSymbol
            
        detail = self.getPositionDetail(vtSymbol)
        detail.updateOrderReq(req, vtOrderID)
    
    #----------------------------------------------------------------------
    def convertOrderReq(self, req):
        """根据规则转换委托请求"""
        detail = self.detailDict.get(req.vtSymbol, None)
        if not detail:
            return [req]
        else:
            return detail.convertOrderReq(req)

    ## +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def getIndicatorInfo(self, dbName, initialCapital, flowCapitalPre, flowCapitalToday):
        """读取指标并写入相应的数据库"""
        ## =====================================================================
        ## 持仓合约信息
        posInfo = copy(self.positionInfo)
        tempPosInfo = {}
        tempPositionFields = ['symbol','direction','price','position','positionProfit','size']
        tempAccountFields  = ['vtAccountID','TradingDay','datetime','preBalance','balance','deltaBalancePct','marginPct','positionProfit','closeProfit','availableMoney','totalMoney','flowMoney','allMoney','commission']
        # ----------------------------------------------------------------------
        if len(posInfo) != 0:
            for key in posInfo.keys():
                if (posInfo[key]['position'] > 0) and (posInfo[key]['price'] != 0):
                    tempPosInfo[key] = {k:posInfo[key][k] for k in tempPositionFields}
                    tempPosInfo[key]['size'] = int(tempPosInfo[key]['size'])
                    tempPosInfo[key]['positionProfit'] = round(tempPosInfo[key]['positionProfit'],3)
                    # ------------------------------------------------------------------------------
                    if tempPosInfo[key]['direction'] == u'多':
                        tempPosInfo[key]['positionPct'] = (tempPosInfo[key]['price'] * tempPosInfo[key]['size'] * self.getContract(tempPosInfo[key]['symbol']).longMarginRatio)
                    elif tempPosInfo[key]['direction'] == u'空':
                        tempPosInfo[key]['positionPct'] = (tempPosInfo[key]['price'] * tempPosInfo[key]['size'] * self.getContract(tempPosInfo[key]['symbol']).shortMarginRatio)
                    # ------------------------------------------------------------------------------
                    if self.accountInfo.balance:
                        tempPosInfo[key]['positionPct'] = round(tempPosInfo[key]['positionPct'] * tempPosInfo[key]['position'] / self.accountInfo.balance * 100, 4)
                    else:
                        tempPosInfo[key]['positionPct'] = 0
        # ----------------------------------------------------------------------
        if len(tempPosInfo) != 0:
            self.accountPosition = pd.DataFrame(tempPosInfo).transpose()
            self.accountPosition['TradingDay'] = self.tradingDate.strftime('%Y-%m-%d')
        else:
            self.accountPosition = pd.DataFrame()

        ## =====================================================================
        ## 账户基金净值
        tempAccountInfo = copy(self.accountInfo)

        ## -------------------------------------------------------------------------
        if len(tempAccountInfo.datetime) != 0:
            try:
                tempAccountInfo.datetime = datetime.strptime(tempAccountInfo.datetime,
                                           '%Y-%m-%d %H:%M:%S').strftime('%H:%M:%S')
            except:
                pass
        ## -------------------------------------------------------------------------

        tempAccountInfo.availableMoney = tempAccountInfo.available
        tempAccountInfo.totalMoney = tempAccountInfo.balance
        tempAccountInfo.flowMoney = flowCapitalPre + flowCapitalToday
        tempAccountInfo.allMoney = tempAccountInfo.totalMoney + tempAccountInfo.flowMoney

        if tempAccountInfo.balance != 0:
            tempAccountInfo.marginPct = tempAccountInfo.margin / tempAccountInfo.balance * 100
        else:
            tempAccountInfo.marginPct = 0

        tempAccountInfo.balance = tempAccountInfo.allMoney / initialCapital
        tempAccountInfo.preBalance = (tempAccountInfo.preBalance + flowCapitalPre) / initialCapital

        if tempAccountInfo.preBalance != 0:
            tempAccountInfo.deltaBalancePct = (tempAccountInfo.balance - 
                                               tempAccountInfo.preBalance) / tempAccountInfo.preBalance * 100
        else:
            tempAccountInfo.deltaBalancePct = 0

        tempAccountInfo.TradingDay = self.tradingDate.strftime('%Y-%m-%d')

        tempFields = ['balance','preBalance','deltaBalancePct','marginPct', 'positionProfit','closeProfit','commission']
        for k in tempFields:
            tempAccountInfo.__dict__[k] = round(tempAccountInfo.__dict__[k],4)
        self.accountBalance = pd.DataFrame([[tempAccountInfo.__dict__[k] for k in tempAccountFields]], columns = tempAccountFields)

        ## =====================================================================
        conn = vtFunction.dbMySQLConnect(dbName)
        cursor = conn.cursor()
        ## ---------------------------------------------------------------------
        if len(tempPosInfo) != 0:
            self.saveMySQL(df   = self.accountPosition, 
                           tbl  = 'report_position', 
                           over = 'replace')
        else:
            cursor.execute('truncate table report_position')
            conn.commit()
        ## ---------------------------------------------------------------------
        ## 保证能够连 CTP 成功
        if len(tempAccountInfo.accountID) != 0:
            self.saveMySQL(df   = self.accountBalance, 
                           tbl  = 'report_account', 
                           over = 'replace')
        ## ---------------------------------------------------------------------
        # if (15 <= datetime.now().hour <= 16) and (datetime.now().minute >= 10):
        if (8 <= datetime.now().hour <= 17) and (len(tempAccountInfo.accountID) != 0):
        # ----------------------------------------------------------------------
            if len(tempPosInfo) != 0:
                ## -------------------------------------------------------------
                try:
                    cursor.execute("""
                                    DELETE FROM report_position_history
                                    WHERE TradingDay = %s
                                   """,[self.tradingDate.strftime('%Y-%m-%d')])
                    conn.commit()
                except:
                    pass
                ## -------------------------------------------------------------
                self.saveMySQL(df   = self.accountPosition, 
                               tbl  = 'report_position_history', 
                               over = 'append')
            # ----------------------------------------------------------------------
            try:
                cursor.execute("""
                                DELETE FROM report_account_history
                                WHERE TradingDay = %s
                               """,[self.tradingDate.strftime('%Y-%m-%d')])
                conn.commit()
            except:
                pass
            ## -----------------------------------------------------------------
            self.saveMySQL(df   = self.accountBalance, 
                           tbl  = 'report_account_history', 
                           over = 'append')
        ## ---------------------------------------------------------------------
        conn.close()


    def printAllOrders(self):
        """查询所有委托（返回列表）"""
        ########################################################################
        ## william
        ########################################################################
        allOrders = self.orderDict.values()

        if len(allOrders) != 0:
            dfHeader = ['vtOrderID','symbol','offset','direction','price',
                        'totalVolume','tradedVolume','orderTime','tradeTime','status']
            dfData   = []
            for i in range(len(allOrders)):
                dfData.append([allOrders[i].__dict__[k] for k in dfHeader])
            df = pd.DataFrame(dfData, columns = dfHeader)
            ## -----------------------------------------------------------------
            print '\n'+'#'*100
            print df
            print '#'*100+'\n'
        else:
            print "没有查询到订单!!!"
            return None

    ############################################################################
    ## 从 MySQL 数据库读取数据
    ############################################################################
    def fetchMySQL(self, query):
        vtFunction.fetchMySQL(db    = self.dataBase, 
                              query = query)

    ############################################################################
    ## 保存数据 DataFrame 格式到 MySQL
    ############################################################################
    def saveMySQL(self, df, tbl, over):
        vtFunction.saveMySQL(df   = df, 
                             db   = self.dataBase, 
                             tbl  = tbl, 
                             over = over)

    ## =========================================================================
    ## william
    ## -------------------------------------------------------------------------
    def writeLog(self, content, logLevel = INFO, gatewayName = 'DATA_ENGINE'):
        """快速发出日志事件"""
        log = VtLogData()
        # log.logContent = content + '\n'
        log.logContent = content
        log.gatewayName = gatewayName
        log.logLevel = logLevel
        event = Event(type_= EVENT_LOG)
        event.dict_['data'] = log
        self.eventEngine.put(event)        
        
########################################################################
class LogEngine(object):
    """日志引擎"""
    
    # 日志级别
    LEVEL_DEBUG = logging.DEBUG
    LEVEL_INFO = logging.INFO
    LEVEL_WARN = logging.WARN
    LEVEL_ERROR = logging.ERROR
    LEVEL_CRITICAL = logging.CRITICAL
    
    # 单例对象
    instance = None
    
    #----------------------------------------------------------------------
    def __new__(cls, *args, **kwargs):
        """创建对象，保证单例"""
        if not cls.instance:
            cls.instance = super(LogEngine, cls).__new__(cls, *args, **kwargs)
        return cls.instance

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.logger = logging.getLogger()        
        self.formatter = logging.Formatter('%(asctime)s  %(levelname)s: %(message)s')
        self.level = self.LEVEL_CRITICAL
        
        self.consoleHandler = None
        self.fileHandler = None
        
        # 添加NullHandler防止无handler的错误输出
        nullHandler = logging.NullHandler()
        self.logger.addHandler(nullHandler)    
        
        # 日志级别函数映射
        self.levelFunctionDict = {
            self.LEVEL_DEBUG: self.debug,
            self.LEVEL_INFO: self.info,
            self.LEVEL_WARN: self.warn,
            self.LEVEL_ERROR: self.error,
            self.LEVEL_CRITICAL: self.critical,
        }
        
    #----------------------------------------------------------------------
    def setLogLevel(self, level):
        """设置日志级别"""
        self.logger.setLevel(level)
        self.level = level
    
    #----------------------------------------------------------------------
    def addConsoleHandler(self):
        """添加终端输出"""
        if not self.consoleHandler:
            self.consoleHandler = logging.StreamHandler()
            self.consoleHandler.setLevel(self.level)
            self.consoleHandler.setFormatter(self.formatter)
            self.logger.addHandler(self.consoleHandler)
            
    ## =========================================================================
    ## william
    ## 保存日志
    ## -------------------------------------------------------------------------
    def addFileHandler(self, filename=''):
        """添加文件输出"""
        if not self.fileHandler:
            if not filename:
                # filename = 'vt_' + datetime.now().strftime('%Y%m%d') + '.log'
                filename = vtFunction.tradingDay() + "_" + globalSetting.accountID + '.log'
            # filepath = vtFunction.getTempPath(filename)
            filepath = vtFunction.getLogPath(filename)
            self.fileHandler = logging.FileHandler(filepath)
            self.fileHandler.setLevel(self.level)
            self.fileHandler.setFormatter(self.formatter)
            self.logger.addHandler(self.fileHandler)
    ## =========================================================================    

    #----------------------------------------------------------------------
    def debug(self, msg):
        """开发时用"""
        self.logger.debug(msg)
        
    #----------------------------------------------------------------------
    def info(self, msg):
        """正常输出"""
        self.logger.info(msg)
        
    #----------------------------------------------------------------------
    def warn(self, msg):
        """警告信息"""
        self.logger.warn(msg)
        
    #----------------------------------------------------------------------
    def error(self, msg):
        """报错输出"""
        self.logger.error(msg)
        
    #----------------------------------------------------------------------
    def exception(self, msg):
        """报错输出+记录异常信息"""
        self.logger.exception(msg)

    #----------------------------------------------------------------------
    def critical(self, msg):
        """影响程序运行的严重错误"""
        self.logger.critical(msg)

    #----------------------------------------------------------------------
    def processLogEvent(self, event):
        """处理日志事件"""
        log = event.dict_['data']
        function = self.levelFunctionDict[log.logLevel]     # 获取日志级别对应的处理函数
        msg = '\t'.join([log.gatewayName, log.logContent])
        function(msg)


########################################################################
class PositionDetail(object):
    """本地维护的持仓信息"""
    WORKING_STATUS = [STATUS_UNKNOWN, STATUS_NOTTRADED, STATUS_PARTTRADED]
    
    MODE_NORMAL = 'normal'          # 普通模式
    MODE_SHFE = 'shfe'              # 上期所今昨分别平仓
    MODE_TDPENALTY = 'tdpenalty'    # 平今惩罚

    #----------------------------------------------------------------------
    def __init__(self, vtSymbol):
        """Constructor"""
        self.vtSymbol = vtSymbol
        
        self.longPos = EMPTY_INT
        self.longYd = EMPTY_INT
        self.longTd = EMPTY_INT
        self.longPosFrozen = EMPTY_INT
        self.longYdFrozen = EMPTY_INT
        self.longTdFrozen = EMPTY_INT
        
        self.shortPos = EMPTY_INT
        self.shortYd = EMPTY_INT
        self.shortTd = EMPTY_INT
        self.shortPosFrozen = EMPTY_INT
        self.shortYdFrozen = EMPTY_INT
        self.shortTdFrozen = EMPTY_INT
        
        self.mode = self.MODE_NORMAL
        self.exchange = EMPTY_STRING
        
        self.workingOrderDict = {}
        
    #----------------------------------------------------------------------
    def updateTrade(self, trade):
        """成交更新"""
        # 多头
        if trade.direction is DIRECTION_LONG:
            # 开仓
            if trade.offset is OFFSET_OPEN:
                self.longTd += trade.volume
            # 平今
            elif trade.offset is OFFSET_CLOSETODAY:
                self.shortTd -= trade.volume
            # 平昨
            elif trade.offset is OFFSET_CLOSEYESTERDAY:
                self.shortYd -= trade.volume
            # 平仓
            elif trade.offset is OFFSET_CLOSE:
                # 上期所等同于平昨
                if self.exchange is EXCHANGE_SHFE:
                    self.shortYd -= trade.volume
                # 非上期所，优先平今
                else:
                    self.shortTd -= trade.volume
                    
                    if self.shortTd < 0:
                        self.shortYd += self.shortTd
                        self.shortTd = 0    
        # 空头
        elif trade.direction is DIRECTION_SHORT:
            # 开仓
            if trade.offset is OFFSET_OPEN:
                self.shortTd += trade.volume
            # 平今
            elif trade.offset is OFFSET_CLOSETODAY:
                self.longTd -= trade.volume
            # 平昨
            elif trade.offset is OFFSET_CLOSEYESTERDAY:
                self.longYd -= trade.volume
            # 平仓
            elif trade.offset is OFFSET_CLOSE:
                # 上期所等同于平昨
                if self.exchange is EXCHANGE_SHFE:
                    self.longYd -= trade.volume
                # 非上期所，优先平今
                else:
                    self.longTd -= trade.volume
                    
                    if self.longTd < 0:
                        self.longYd += self.longTd
                        self.longTd = 0
                    
        # 汇总今昨
        self.calculatePosition()
    
    #----------------------------------------------------------------------
    def updateOrder(self, order):
        """委托更新"""
        # 将活动委托缓存下来
        if order.status in self.WORKING_STATUS:
            self.workingOrderDict[order.vtOrderID] = order
            
        # 移除缓存中已经完成的委托
        else:
            if order.vtOrderID in self.workingOrderDict:
                del self.workingOrderDict[order.vtOrderID]
                
        # 计算冻结
        self.calculateFrozen()
    
    #----------------------------------------------------------------------
    def updatePosition(self, pos):
        """持仓更新"""
        if pos.direction is DIRECTION_LONG:
            self.longPos = pos.position
            self.longYd = pos.ydPosition
            self.longTd = self.longPos - self.longYd
        elif pos.direction is DIRECTION_SHORT:
            self.shortPos = pos.position
            self.shortYd = pos.ydPosition
            self.shortTd = self.shortPos - self.shortYd
            
        #self.output()
    
    #----------------------------------------------------------------------
    def updateOrderReq(self, req, vtOrderID):
        """发单更新"""
        vtSymbol = req.vtSymbol        
            
        # 基于请求生成委托对象
        order = VtOrderData()
        order.vtSymbol = vtSymbol
        order.symbol = req.symbol
        order.exchange = req.exchange
        order.offset = req.offset
        order.direction = req.direction
        order.totalVolume = req.volume
        order.status = STATUS_UNKNOWN
        
        # 缓存到字典中
        self.workingOrderDict[vtOrderID] = order
        
        # 计算冻结量
        self.calculateFrozen()
    
    #----------------------------------------------------------------------
    def calculatePosition(self):
        """计算持仓情况"""
        self.longPos = self.longTd + self.longYd
        self.shortPos = self.shortTd + self.shortYd      
        
        #self.output()
        
    #----------------------------------------------------------------------
    def calculateFrozen(self):
        """计算冻结情况"""
        # 清空冻结数据
        self.longPosFrozen = EMPTY_INT
        self.longYdFrozen = EMPTY_INT
        self.longTdFrozen = EMPTY_INT
        self.shortPosFrozen = EMPTY_INT
        self.shortYdFrozen = EMPTY_INT
        self.shortTdFrozen = EMPTY_INT     
        
        # 遍历统计
        for order in self.workingOrderDict.values():
            # 计算剩余冻结量
            frozenVolume = order.totalVolume - order.tradedVolume
            
            # 多头委托
            if order.direction is DIRECTION_LONG:
                # 平今
                if order.offset is OFFSET_CLOSETODAY:
                    self.shortTdFrozen += frozenVolume
                # 平昨
                elif order.offset is OFFSET_CLOSEYESTERDAY:
                    self.shortYdFrozen += frozenVolume
                # 平仓
                elif order.offset is OFFSET_CLOSE:
                    self.shortTdFrozen += frozenVolume
                    
                    if self.shortTdFrozen > self.shortTd:
                        self.shortYdFrozen += (self.shortTdFrozen - self.shortTd)
                        self.shortTdFrozen = self.shortTd
            # 空头委托
            elif order.direction is DIRECTION_SHORT:
                # 平今
                if order.offset is OFFSET_CLOSETODAY:
                    self.longTdFrozen += frozenVolume
                # 平昨
                elif order.offset is OFFSET_CLOSEYESTERDAY:
                    self.longYdFrozen += frozenVolume
                # 平仓
                elif order.offset is OFFSET_CLOSE:
                    self.longTdFrozen += frozenVolume
                    
                    if self.longTdFrozen > self.longTd:
                        self.longYdFrozen += (self.longTdFrozen - self.longTd)
                        self.longTdFrozen = self.longTd
                        
            # 汇总今昨冻结
            self.longPosFrozen = self.longYdFrozen + self.longTdFrozen
            self.shortPosFrozen = self.shortYdFrozen + self.shortTdFrozen
        
        #self.output()
            
    #----------------------------------------------------------------------
    def output(self):
        """"""
        print self.vtSymbol, '-'*30
        print 'long, total:%s, td:%s, yd:%s' %(self.longPos, self.longTd, self.longYd)
        print 'long frozen, total:%s, td:%s, yd:%s' %(self.longPosFrozen, self.longTdFrozen, self.longYdFrozen)
        print 'short, total:%s, td:%s, yd:%s' %(self.shortPos, self.shortTd, self.shortYd)
        print 'short frozen, total:%s, td:%s, yd:%s' %(self.shortPosFrozen, self.shortTdFrozen, self.shortYdFrozen)        
    
    #----------------------------------------------------------------------
    def convertOrderReq(self, req):
        """转换委托请求"""
        # 普通模式无需转换
        if self.mode is self.MODE_NORMAL:
            return [req]
        
        # 上期所模式拆分今昨，优先平今
        elif self.mode is self.MODE_SHFE:
        # if self.mode is [self.MODE_NORMAL, self.MODE_SHFE]:
            ## -----------------------------------------------------------------
            ## william
            ## 开仓无需转换
            if req.offset is OFFSET_OPEN:
                return [req]
            ## -----------------------------------------------------------------

            ## -----------------------------------------------------------------
            ## william
            ## 平仓需要考虑平今，平昨
            ## 
            ## 多头平仓 --> 空头仓位
            ## -------------------------------
            if req.direction is DIRECTION_LONG:
                posAvailable = self.shortPos - self.shortPosFrozen
                tdAvailable = self.shortTd- self.shortTdFrozen
                ydAvailable = self.shortYd - self.shortYdFrozen            
            ## 空头平仓 --> 多头仓位
            ## -------------------------------
            else:
                posAvailable = self.longPos - self.longPosFrozen
                tdAvailable = self.longTd - self.longTdFrozen
                ydAvailable = self.longYd - self.longYdFrozen
            ## -----------------------------------------------------------------
                
            ## -----------------------------------------------------------------
            # # 平仓量超过总可用，拒绝，返回空列表
            # if req.volume > posAvailable:
            #     return []
            # # 平仓量小于今可用，全部平今
            # elif req.volume <= tdAvailable:
            #     req.offset = OFFSET_CLOSETODAY
            #     return [req]
            # # 平仓量大于今可用，平今再平昨
            # else:
            #     l = []
                
            #     if tdAvailable > 0:
            #         reqTd = copy(req)
            #         reqTd.offset = OFFSET_CLOSETODAY
            #         reqTd.volume = tdAvailable
            #         l.append(reqTd)
                    
            #     reqYd = copy(req)
            #     reqYd.offset = OFFSET_CLOSEYESTERDAY
            #     reqYd.volume = req.volume - tdAvailable
            #     l.append(reqYd)
                
            #     return l
            ## -----------------------------------------------------------------
            
            ## -----------------------------------------------------------------
            # 平仓量超过总可用，拒绝，返回空列表
            if req.volume > posAvailable:
                return []
            # 平仓量小于昨可用，全部平昨
            elif req.volume <= ydAvailable:
                req.offset = OFFSET_CLOSEYESTERDAY
                return [req]
            # 平仓量大于昨可用，先平昨再平今
            else:
                l = []
                
                ## -------------------------------------------------------------
                ## 平昨
                if ydAvailable > 0:
                    reqYd = copy(req)
                    reqYd.offset = OFFSET_CLOSEYESTERDAY
                    reqYd.volume = ydAvailable
                    l.append(reqYd)
                
                ## -------------------------------------------------------------
                ## 平今
                reqTd = copy(req)
                reqTd.offset = OFFSET_CLOSETODAY
                reqTd.volume = req.volume - ydAvailable
                l.append(reqTd)
                
                return l
            ## -----------------------------------------------------------------


        # 平今惩罚模式，没有今仓则平昨，否则锁仓
        elif self.mode is self.MODE_TDPENALTY:
            ## 多头平仓 --> 空头仓位
            ## -------------------------------
            if req.direction is DIRECTION_LONG:
                td = self.shortTd
                ydAvailable = self.shortYd - self.shortYdFrozen
            ## 空头平仓 --> 多头仓位
            ## -------------------------------
            else:
                td = self.longTd
                ydAvailable = self.longYd - self.longYdFrozen
                
            # 这里针对开仓和平仓委托均使用一套逻辑
            
            # 如果有今仓，则只能开仓（或锁仓）
            if td:
                req.offset = OFFSET_OPEN
                return [req]
            # 如果平仓量小于昨可用，全部平昨
            elif req.volume <= ydAvailable:
                if self.exchange is EXCHANGE_SHFE:
                    req.offset = OFFSET_CLOSEYESTERDAY
                else:
                    req.offset = OFFSET_CLOSE
                return [req]
            # 平仓量大于昨可用，平仓再反向开仓
            else:
                l = []
                
                if ydAvailable > 0:
                    reqClose = copy(req)
                    if self.exchange is EXCHANGE_SHFE:
                        req.offset = OFFSET_CLOSEYESTERDAY
                    else:
                        req.offset = OFFSET_CLOSE
                    reqClose.volume = ydAvailable
                    
                    l.append(reqClose)
                    
                reqOpen = copy(req)
                reqOpen.offset = OFFSET_OPEN
                reqOpen.volume = req.volume - ydAvailable
                l.append(reqOpen)
                
                return l
        
        # 其他情况则直接返回空
        return []
