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


import numpy as np
import pandas as pd
################################################################################

from eventEngine import *
from vtGateway import *
import vtFunction

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
from dataRecorder.recorderEngine import DrEngine

########################################################################
class MainEngine(object):
    """主引擎"""
    tradingDay = vtFunction.tradingDay()
    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        # 记录今日日期
        self.todayDate = datetime.now().strftime('%Y%m%d')
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
        
        # 调用一个个初始化函数
        self.initGateway()

        # 扩展模块
        self.drEngine = DrEngine(self, self.eventEngine)
        
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
        else:
            print text.GATEWAY_NOT_EXIST.format(gateway=gatewayName)

    #----------------------------------------------------------------------
    def connectCTPAccount(self, accountInfo, gatewayName = 'CTP'):
        """连接特定名称的接口"""
        """
        1. CTP
        """
        if gatewayName in self.gatewayDict:
            gateway = self.gatewayDict[gatewayName]
            gateway.connectCTPAccount(accountInfo)
        else:
            self.writeLog(text.GATEWAY_NOT_EXIST.format(gateway=gatewayName))

    #----------------------------------------------------------------------
    def subscribe(self, subscribeReq, gatewayName):
        """订阅特定接口的行情"""
        if gatewayName in self.gatewayDict:
            gateway = self.gatewayDict[gatewayName]
            gateway.subscribe(subscribeReq)
        else:
            print text.GATEWAY_NOT_EXIST.format(gateway=gatewayName)     
    #----------------------------------------------------------------------

    #----------------------------------------------------------------------
    def exit(self):
        """退出程序前调用，保证正常退出"""        
        # 安全关闭所有接口
        for gateway in self.gatewayDict.values():        
            gateway.close()
        
        # 停止事件引擎
        self.eventEngine.stop()      
        
        # 停止数据记录引擎
        self.drEngine.stop()
        
        # 保存数据引擎里的合约数据到硬盘
        self.dataEngine.saveContracts()
    
    #----------------------------------------------------------------------
    def writeLog(self, content):
        """快速发出日志事件"""
        log = VtLogData()
        log.logContent = content
        event = Event(type_=EVENT_LOG)
        event.dict_['data'] = log
        self.eventEngine.put(event)        

    #---------------------------------------------------------------------------
    def getContract(self, vtSymbol):
        """查询合约"""
        return self.dataEngine.getContract(vtSymbol)
    
    #---------------------------------------------------------------------------
    def getAllContracts(self):
        """查询所有合约（返回列表）"""
        return self.dataEngine.getAllContracts()

    #---------------------------------------------------------------------------
    def getAllGatewayNames(self):
        """查询引擎中所有可用接口的名称"""
        return self.gatewayDict.keys()
    
    def saveContractInfo(self):
        print "\n#######################################################################"
        # mainEngine.dataEngine.contractDict.keys()
        # path = os.path.abspath(os.path.dirname(__file__))
        # main_path = os.path.normpath(os.path.join(path,".."))
        main_path = os.path.abspath(os.path.dirname(__file__))
        contractFileName = 'ContractData.vt'
        f = shelve.open(os.path.join(main_path,contractFileName))
        f['data'] = self.dataEngine.contractDict
        f.close()

        ########################################################################
        ## william
        ## 保存合约信息
        f2 = shelve.open(os.path.normpath(os.path.join(main_path,'..','..','vn.data','ContractInfo',(self.tradingDay + '_' + contractFileName) )))
        # f2['data'] = self.dataEngine.contractDict
        f2['data'] = 'hello, world'
        f2.close()

        print "#######################################################################\n"
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
        # print contract.__dict__
        
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
        

    #------------------------------------------=====----------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.eventEngine.register(EVENT_CONTRACT, self.updateContract)
