# encoding: UTF-8
################################################################################
## william
################################################################################
import os
import shelve
from collections import OrderedDict
from datetime import datetime

################################################################################
## william
## 如果不用 MongoDB, 可以把以下两行注释掉
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
################################################################################
##　william
## 我使用了 MySQL 数据库
import MySQLdb

import numpy as np
import pandas as pd
pd.set_option('display.width', 200)
pd.set_option('display.max_rows', 100)
################################################################################


from eventEngine import *
from vtGateway import *
import vtFunction

################################################################################
## william
## 如果不用 MongoDB, 可以把以下这行注释掉
from vtFunction import loadMongoSetting
################################################################################
##　william
from vtFunction import loadMySQLSetting
################################################################################

################################################################################
## william
## 语言项, 位于 /main/language/chinese 下面, 可以查找相应的命令
from language import text

################################################################################
##　william
## gateway 位于 /main/gateway
## 以后可以在这里增加相应的其他接口 API
## 目前我只使用了 CTP 的接口
## 具体的设计可以看 /gateway/ctpGateway/ctpGateway.py
from gateway import GATEWAY_DICT
################################################################################

################################################################################
## william
## 这里需要注意路径设置的问题
## 具体参考 /main/vtPath/ 对路径的说明
# from ctaStrategy.ctaEngine import CtaEngine
from ctaEngine import CtaEngine
from dataRecorder.drEngine import DrEngine
from riskManager.rmEngine import RmEngine


########################################################################
class MainEngine(object):
    """主引擎"""
    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        # 记录今日日期
        self.todayDate  = datetime.now().strftime('%Y%m%d')
        self.tradingDay = vtFunction.tradingDay()
        
        # 创建事件引擎
        self.eventEngine = EventEngine2()
        self.eventEngine.start()
        
        ########################################################################
        ## william
        ## dataEngine 继承 DataEngine
        ## 因此 mainEngine 可以使用 DataEngine 下面的函数
        ########################################################################
        # 创建数据引擎
        self.dataEngine = DataEngine(self.eventEngine)
        
        # MongoDB数据库相关
        self.dbClient = None    # MongoDB客户端对象
        
        ########################################################################
        ## william
        ## 设置数据库连接初始状态
        # MongoDB数据库相关
        self.dbMongoClient = None    # MongoDB客户端对象

        ## MySQL 数据库相关
        self.dbMySQLClient = None
        ########################################################################

        # 调用一个个初始化函数
        self.initGateway()

        # 扩展模块
        self.ctaEngine = CtaEngine(self, self.eventEngine)
        self.drEngine  = DrEngine(self, self.eventEngine)
        self.rmEngine  = RmEngine(self, self.eventEngine)
        
    #----------------------------------------------------------------------
    def initGateway(self):
        """初始化接口对象"""
        # 用来保存接口对象的字典
        self.gatewayDict = OrderedDict()
        
        # 遍历接口字典并自动创建所有的接口对象
        for gatewayModule in GATEWAY_DICT.values():
            try:
                self.addGateway(gatewayModule.gateway, gatewayModule.gatewayName)
                if gatewayModule.gatewayQryEnabled:
                    self.gatewayDict[gatewayModule.gatewayName].setQryEnabled(True)
            except Exception, e:
                print e

    #----------------------------------------------------------------------
    def addGateway(self, gateway, gatewayName=None):
        """创建接口"""
        self.gatewayDict[gatewayName] = gateway(self.eventEngine, gatewayName)
        
    ############################################################################
    ## william
    ## 启动登录 CTP 账户
    ############################################################################
    #----------------------------------------------------------------------
    def connect(self, gatewayName):
        """连接特定名称的接口"""
        """
        1. CTP
        """
        if gatewayName in self.gatewayDict:
            gateway = self.gatewayDict[gatewayName]
            gateway.connect()
            ####################################################################
            ## william
            ## 如果连接 CTP,
            ## 则默认自动连接 MySQL 数据库
            self.dbMySQLConnect()
            print "#"*80
            ####################################################################
        else:
            self.writeLog(text.GATEWAY_NOT_EXIST.format(gateway=gatewayName))

    #----------------------------------------------------------------------
    def connectCTPAccount(self, accountID, gatewayName = 'CTP'):
        """连接特定名称的接口"""
        """
        1. CTP
        """
        if gatewayName in self.gatewayDict:
            gateway = self.gatewayDict[gatewayName]
            gateway.connectCTPAccount(accountID)
            ####################################################################
            ## william
            ## 如果连接 CTP,
            ## 则默认自动连接 MySQL 数据库
            self.dbMySQLConnect()
            print "#"*80+"\n"
            ####################################################################
        else:
            self.writeLog(text.GATEWAY_NOT_EXIST.format(gateway=gatewayName))


    #----------------------------------------------------------------------
    def subscribe(self, subscribeReq, gatewayName):
        """订阅特定接口的行情"""
        if gatewayName in self.gatewayDict:
            gateway = self.gatewayDict[gatewayName]
            gateway.subscribe(subscribeReq)
        else:
            self.writeLog(text.GATEWAY_NOT_EXIST.format(gateway=gatewayName))        
        
    #----------------------------------------------------------------------
    def sendOrder(self, orderReq, gatewayName):
        """对特定接口发单"""
        ########################################################################
        ## william
        # 如果风控检查失败则不发单
        if not self.rmEngine.checkRisk(orderReq):
            return ''

        if gatewayName in self.gatewayDict:
            gateway = self.gatewayDict[gatewayName]
            return gateway.sendOrder(orderReq)
        else:
            self.writeLog(text.GATEWAY_NOT_EXIST.format(gateway=gatewayName))        
    
    #----------------------------------------------------------------------
    def cancelOrder(self, cancelOrderReq, gatewayName):
        """对特定接口撤单"""
        if gatewayName in self.gatewayDict:
            gateway = self.gatewayDict[gatewayName]
            gateway.cancelOrder(cancelOrderReq)
        else:
            self.writeLog(text.GATEWAY_NOT_EXIST.format(gateway=gatewayName))
    
    ############################################################################
    ## william
    ## 一键全部撤单
    ## ref: /vn.trader/uiBasicWidget.py
    ##      cancelOrderAll()
    ############################################################################
    def cancelOrderAll(self):
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
        
    #----------------------------------------------------------------------
    def qryAccount(self, gatewayName):
        """查询特定接口的账户"""
        if gatewayName in self.gatewayDict:
            gateway = self.gatewayDict[gatewayName]
            gateway.qryAccount()
        else:
            self.writeLog(text.GATEWAY_NOT_EXIST.format(gateway=gatewayName))        
        
    #----------------------------------------------------------------------
    def qryPosition(self, gatewayName):
        """查询特定接口的持仓"""
        if gatewayName in self.gatewayDict:
            gateway = self.gatewayDict[gatewayName]
            gateway.qryPosition()
        else:
            self.writeLog(text.GATEWAY_NOT_EXIST.format(gateway=gatewayName))        
        
    #----------------------------------------------------------------------
    def exit(self):
        """退出程序前调用，保证正常退出"""        
        # 安全关闭所有接口
        for gateway in self.gatewayDict.values():        
            gateway.close()
            ## =====================================================================
            ## william
            ## 保存数据引擎里的合约数据到硬盘
            ## ---------------------------------------------------------------------
            ## 取消所有订单
            print '#'*80 + '\n'
            print "即将取消所有订单......\n"
            for i in range(45):
                print ".",
                time.sleep(.05)
            self.cancelOrderAll()
            print '\n' + '#'*80 
            ## =====================================================================
        
        # 停止事件引擎
        self.eventEngine.stop()      
        
        # 停止数据记录引擎
        self.drEngine.stop()

        ## =====================================================================
        ## william
        ## 保存数据引擎里的合约数据到硬盘
        ## ---------------------------------------------------------------------
        # self.dataEngine.saveContracts()
        ## =====================================================================
    
    #----------------------------------------------------------------------
    def writeLog(self, content):
        """快速发出日志事件"""
        log = VtLogData()
        log.logContent = content
        event = Event(type_=EVENT_LOG)
        event.dict_['data'] = log
        self.eventEngine.put(event)        

    ############################################################################
    ## william
    ## DataBase setting
    ##> Beginnings
    ############################################################################

    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    #'''
    def dbConnect(self):
        """连接MongoDB数据库"""
        if not self.dbClient:
            # 读取MongoDB的设置
            host, port, logging = loadMongoSetting()
                
            try:
                # 设置MongoDB操作的超时时间为0.5秒
                self.dbClient = MongoClient(host, port, connectTimeoutMS=500)
                
                # 调用server_info查询服务器状态，防止服务器异常并未连接成功
                self.dbClient.server_info()
                self.writeLog(text.DATABASE_CONNECTING_COMPLETED)
                
                # 如果启动日志记录，则注册日志事件监听函数
                if logging:
                    self.eventEngine.register(EVENT_LOG, self.dbLogging)
                    
            except ConnectionFailure:
                self.writeLog(text.DATABASE_CONNECTING_FAILED)
    #'''
    #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    #'''
    #---------------------------------------------------------------------------
    def dbInsert(self, dbName, collectionName, d):
        """向MongoDB中插入数据，d是具体数据"""
        if self.dbClient:
            db = self.dbClient[dbName]
            collection = db[collectionName]
            collection.insert_one(d)
        else:
            self.writeLog(text.DATA_INSERT_FAILED)
    #'''
    #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    #'''    
    #---------------------------------------------------------------------------
    def dbQuery(self, dbName, collectionName, d):
        """从MongoDB中读取数据，d是查询要求，返回的是数据库查询的指针"""
        if self.dbClient:
            db = self.dbClient[dbName]
            collection = db[collectionName]
            cursor = collection.find(d)
            if cursor:
                return list(cursor)
            else:
                return []
        else:
            self.writeLog(text.DATA_QUERY_FAILED)   
            return []
    #'''
    #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    #'''
    #---------------------------------------------------------------------------
    def dbUpdate(self, dbName, collectionName, d, flt, upsert=False):
        """向MongoDB中更新数据，d是具体数据，flt是过滤条件，upsert代表若无是否要插入"""
        if self.dbClient:
            db = self.dbClient[dbName]
            collection = db[collectionName]
            collection.replace_one(flt, d, upsert)
        else:
            self.writeLog(text.DATA_UPDATE_FAILED)        
    #'''
    #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    #'''   
    #---------------------------------------------------------------------------
    def dbLogging(self, event):
        """向MongoDB中插入日志"""
        log = event.dict_['data']
        d = {
            'content': log.logContent,
            'time': log.logTime,
            'gateway': log.gatewayName
        }
        self.dbInsert(LOG_DB_NAME, self.todayDate, d)
    #'''
    #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

    ############################################################################
    ## william
    ## DataBase setting
    ## 连接 Mongo
    ## dbMongoConnect
    ############################################################################
    # --------------------------------------------------------------------------
    def dbMongoConnect(self):
        """连接MongoDB数据库"""
        if not self.dbMongoClient:
            # 读取MongoDB的设置
            host, port, logging = loadMongoSetting()
                
            try:
                # 设置MongoDB操作的超时时间为0.5秒
                self.dbMongoClient = MongoClient(host, port, connectTimeoutMS=500)
                
                # 调用server_info查询服务器状态，防止服务器异常并未连接成功
                self.dbMongoClient.server_info()
                self.writeLog(text.DATABASE_CONNECTING_COMPLETED)
                
                # 如果启动日志记录，则注册日志事件监听函数
                if logging:
                    self.eventEngine.register(EVENT_LOG, self.dbLogging)
                ################################################################
                ## william
                ## 打印数据库信息
                print '\n'+"#"*80
                print "Mongo 数据库连接成功!!!"
                print "#"*80+'\n'    
            except ConnectionFailure:
                self.writeLog(text.DATABASE_CONNECTING_FAILED)
                ################################################################
                ## william
                ## 打印数据库信息
                print '\n'+"#"*80
                print "Mongo 数据库连接失败!!!"
                print "#"*80+'\n'

    ############################################################################
    ## william
    ## DataBase setting
    ## 连接 MySQL
    ## dbMySQLConnect
    ############################################################################
    #----------------------------------------------------------------------
    def dbMySQLConnect(self, dbName = 'china_futures_bar'):
        """连接 MySQL 数据库"""
        # 来自 vtFunction,
        # 信息存储于 VT_setting
        # 读取 MySQL 的设置

        if not self.dbMySQLClient:
            """ 连接 MySQL 数据库 """
            host, port, user, passwd = loadMySQLSetting()
                
            try:
                conn = MySQLdb.connect(db = dbName, host = host, port = port, user = user, passwd = passwd, use_unicode = True, charset = "utf8")
                return conn
                self.writeLog(text.DATABASE_MySQL_CONNECTING_COMPLETED)
                print text.DATABASE_MySQL_CONNECTING_COMPLETED
                self.dbMySQLClient = True
            except (MySQLdb.Error, MySQLdb.Warning, TypeError) as e:
                print text.DATABASE_MySQL_CONNECTING_FAILED
                print e
                self.writeLog(text.DATABASE_MySQL_CONNECTING_FAILED)

    #---------------------------------------------------------------------------
    
    ############################################################################
    ## william
    ## 从 MySQL 数据库查询数据
    ############################################################################
    #---------------------------------------------------------------------------
    def dbMySQLQuery(self, dbName, query):
        """ 从 MySQL 中读取数据 """
        host, port, user, passwd = loadMySQLSetting()
        db    = dbName
        query = str(query)

        try:
            conn = MySQLdb.connect(host = host, port = port, db = db, user = user, passwd = passwd, use_unicode = True, charset = "utf8")
            mysqlData = pd.read_sql(query, conn)
            return mysqlData
            self.writeLog(text.DATA_MySQL_QUERY_COMPLETED)
        except (MySQLdb.Error, MySQLdb.Warning, TypeError) as e:
            print(e)
            return None
            self.writeLog(text.DATA_MySQL_QUERY_FAILED)
        finally:
            conn.close()
    #---------------------------------------------------------------------------

    ############################################################################
    ## william
    ## DataBase setting
    ##< Endings
    ############################################################################


    ############################################################################
    ## william
    ## DataEngine 类
    ##> Beginnings
    ############################################################################

    #---------------------------------------------------------------------------
    def getContract(self, vtSymbol):
        """查询合约"""
        return self.dataEngine.getContract(vtSymbol)
    
    #---------------------------------------------------------------------------
    def getAllContracts(self):
        """查询所有合约（返回列表）"""
        return self.dataEngine.getAllContracts()
    
    #---------------------------------------------------------------------------
    def getOrder(self, vtOrderID):
        """查询委托"""
        return self.dataEngine.getOrder(vtOrderID)
    
    #---------------------------------------------------------------------------
    def getAllWorkingOrders(self):
        """查询所有的活跃的委托（返回列表）"""
        return self.dataEngine.getAllWorkingOrders()
    
    ############################################################################
    ## william
    ## 获取所有订单(成交,未成交,已撤单)
    ## getAllOrders()
    #---------------------------------------------------------------------------
    def getAllOrders(self):
        """查询所有的活跃的委托（返回列表）"""
        return self.dataEngine.getAllOrders()
    def printAllOrders(self):
        self.dataEngine.printAllOrders()
    ############################################################################

    #---------------------------------------------------------------------------
    def getAllGatewayNames(self):
        """查询引擎中所有可用接口的名称"""
        return self.gatewayDict.keys()
        
    ############################################################################
    ## william
    ## DataEngine 类
    ##< Endings
    ############################################################################

################################################################################
class DataEngine(object):
    """数据引擎"""
    contractFileName = 'ContractData.vt'

    ############################################################################
    ## william
    ## 用于显示当前路经
    ############################################################################

    #----------------------------------------------------------------------
    def __init__(self, eventEngine):
        """Constructor"""
        self.eventEngine = eventEngine
        
        # 保存合约详细信息的字典
        self.contractDict = {}
        
        # 保存委托数据的字典
        self.orderDict = {}
        
        # 保存活动委托数据的字典（即可撤销）
        self.workingOrderDict = {}
        ########################################################################
        ## william
        ## 通过 loadContracts() 来载入所有合约
        ## 然后通过对象 mainEngine.dataEngine.contractDict 获取
        ########################################################################
        # 读取保存在硬盘的合约数据
        self.loadContracts()
        
        # 注册事件监听
        self.registerEvent()
        
    ############################################################################
    ## william
    ## 更新 Tick Data 的数据
    ############################################################################
    #---------------------------------------------------------------------------
    def updateContract(self, event):
        """更新合约数据"""
        contract = event.dict_['data']
        self.contractDict[contract.vtSymbol] = contract
        self.contractDict[contract.symbol] = contract       # 使用常规代码（不包括交易所）可能导致重复
        
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
    
    ############################################################################
    ## william
    ## 保存合约品种
    ############################################################################
    #---------------------------------------------------------------------------
    def saveContracts(self):
        """保存所有合约对象到硬盘"""
        f = shelve.open(self.contractFileName)
        f['data'] = self.contractDict
        f.close()
    
    ############################################################################
    ## william
    ## 通过 loadContracts() 来载入所有合约
    ## 然后通过对象 mainEngine.dataEngine.contractDict 获取
    ############################################################################
    #----------------------------------------------------------------------
    def loadContracts(self):
        """从硬盘读取合约对象"""
        f = shelve.open(self.contractFileName)
        if 'data' in f:
            d = f['data']
            for key, value in d.items():
                self.contractDict[key] = value
        f.close()

        ## =====================================================================
        
    #----------------------------------------------------------------------
    def updateOrder(self, event):
        """更新委托数据"""
        order = event.dict_['data']        
        self.orderDict[order.vtOrderID] = order
        
        ## =====================================================================
        ## william
        ## =====================================================================
        # 如果订单的状态是全部成交或者撤销，则需要从workingOrderDict中移除
        if (order.status == STATUS_ALLTRADED or 
            order.status == STATUS_CANCELLED or 
            order.status == STATUS_REJECTED):
            if order.vtOrderID in self.workingOrderDict:
                del self.workingOrderDict[order.vtOrderID]
        # 否则则更新字典中的数据        
        else:
            self.workingOrderDict[order.vtOrderID] = order
        
    #--------------------=====--------------------------------------------------
    def getOrder(self, vtOrderID):
        """查询委托"""
        try:
            return self.orderDict[vtOrderID]
        except KeyError:
            return None
    
    #----------------------------------------=====------------------------------
    def getAllWorkingOrders(self):
        """查询所有活动委托（返回列表）"""
        return self.workingOrderDict.values()
    
    ############################################################################
    ## william
    ## 获取所有订单(成交,未成交,已撤单)
    ## getAllOrders()
    #---------------------------------------------------------------------------
    def getAllOrders(self):
        """查询所有委托（返回列表）"""
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
            print "没有查询到订单!!!"
            return None

    def printAllOrders(self):
        """查询所有委托（返回列表）"""
        ########################################################################
        ## william
        ########################################################################
        allOrders = self.orderDict.values()

        if len(allOrders) != 0:
            dfHeader = ['vtOrderID','status','symbol','offset','direction',
                        'orderTime','price','totalVolume','tradedVolume']
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

    #------------------------------------------=====----------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.eventEngine.register(EVENT_CONTRACT, self.updateContract)
        self.eventEngine.register(EVENT_ORDER, self.updateOrder)
