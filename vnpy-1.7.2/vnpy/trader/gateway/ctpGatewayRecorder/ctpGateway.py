# encoding: UTF-8

'''
vn.ctp的gateway接入
'''

import os,sys
import json,shelve
import pandas as pd
from copy import copy
from datetime import datetime, timedelta
from logging import *

from vnpy.api.ctp import MdApi, TdApi, defineDict
from vnpy.trader.vtGateway import *
from vnpy.trader import vtFunction 
from vnpy.trader.vtConstant import GATEWAYTYPE_FUTURES
from .language import text
from vnpy.trader.vtGlobal import globalSetting

# 以下为一些VT类型和CTP类型的映射字典
# 价格类型映射
priceTypeMap = {}
priceTypeMap[PRICETYPE_LIMITPRICE] = defineDict["THOST_FTDC_OPT_LimitPrice"]
priceTypeMap[PRICETYPE_MARKETPRICE] = defineDict["THOST_FTDC_OPT_AnyPrice"]
priceTypeMapReverse = {v: k for k, v in priceTypeMap.items()} 

# 交易所类型映射
exchangeMap = {}
exchangeMap[EXCHANGE_CFFEX] = 'CFFEX'
exchangeMap[EXCHANGE_SHFE] = 'SHFE'
exchangeMap[EXCHANGE_CZCE] = 'CZCE'
exchangeMap[EXCHANGE_DCE] = 'DCE'
exchangeMap[EXCHANGE_SSE] = 'SSE'
exchangeMap[EXCHANGE_SZSE] = 'SZSE'
exchangeMap[EXCHANGE_INE] = 'INE'
exchangeMap[EXCHANGE_UNKNOWN] = ''
exchangeMapReverse = {v:k for k,v in exchangeMap.items()}

# 产品类型映射
productClassMap = {}
productClassMap[PRODUCT_FUTURES] = defineDict["THOST_FTDC_PC_Futures"]
productClassMap[PRODUCT_OPTION] = defineDict["THOST_FTDC_PC_Options"]
productClassMap[PRODUCT_COMBINATION] = defineDict["THOST_FTDC_PC_Combination"]
productClassMapReverse = {v:k for k,v in productClassMap.items()}
productClassMapReverse[defineDict["THOST_FTDC_PC_ETFOption"]] = PRODUCT_OPTION
productClassMapReverse[defineDict["THOST_FTDC_PC_Stock"]] = PRODUCT_EQUITY

# 全局字典, key:symbol, value:exchange
symbolExchangeDict = {}

# 夜盘交易时间段分隔判断
NIGHT_TRADING = datetime(1900, 1, 1, 20).time()

########################################################################
class CtpGateway(VtGateway):
    """CTP接口"""

    #----------------------------------------------------------------------
    def __init__(self, eventEngine, gatewayName='CTP'):
        """Constructor"""
        super(CtpGateway, self).__init__(eventEngine, gatewayName)
        
        self.mdApi = CtpMdApi(self)     # 行情API
        self.tdApi = CtpTdApi(self)     # 交易API
        
        self.mdConnected = False        # 行情API连接状态，登录完成后为True
        self.tdConnected = False        # 交易API连接状态
        
        self.qryEnabled = False         # 循环查询
        
        self.CTPConnectFile = self.gatewayName + '_connect.json'
        path = os.path.normpath(
            os.path.join(
                os.path.dirname(__file__),
                '..', '..', '..', '..')
            )
        self.CTPConnectPath = os.path.join(path, 'trading', 'account', self.CTPConnectFile)       
        
    #----------------------------------------------------------------------
    def connect(self, accountID):
        """连接"""
        try:
            f = file(self.CTPConnectPath)
        except IOError:
            log = VtLogData()
            log.gatewayName = self.gatewayName
            log.logContent = text.LOADING_ERROR
            self.onLog(log)
            return
        
        # 解析json文件
        info = json.load(f)
        setting = info[accountID]
        try:
            userID = str(setting['userID'])
            password = str(setting['password'])
            brokerID = str(setting['brokerID'])
            tdAddress = str(setting['tdAddress'])
            mdAddress = str(setting['mdAddress'])
            
            # 如果json文件提供了验证码
            if 'authCode' in setting: 
                authCode = str(setting['authCode'])
                userProductInfo = str(setting['userProductInfo'])
                self.tdApi.requireAuthentication = True
            else:
                authCode = None
                userProductInfo = None

        except KeyError:
            log = VtLogData()
            log.gatewayName = self.gatewayName
            log.logContent = text.CONFIG_KEY_MISSING
            self.onLog(log)
            return            
        
        ########################################################################
        ## william
        ## 连接到
        ## 1. MdAPI
        ## 2. TdAPI
        ########################################################################
        # 创建行情和交易接口对象
        # 创建行情和交易接口对象
        self.mdApi.connect(userID, password, brokerID, mdAddress)
        self.tdApi.connect(userID, password, brokerID, tdAddress, authCode, userProductInfo)
        
        # 初始化并启动查询
        self.initQuery()
    
    #----------------------------------------------------------------------
    def subscribe(self, subscribeReq):
        """订阅行情"""
        self.mdApi.subscribe(subscribeReq)
        
    #----------------------------------------------------------------------
    def close(self):
        """关闭"""
        if self.mdConnected:
            self.mdApi.close()
        if self.tdConnected:
            self.tdApi.close()
        
    #----------------------------------------------------------------------
    def initQuery(self):
        """初始化连续查询"""
        if self.qryEnabled:
            # 需要循环的查询函数列表
            self.qryFunctionList = [self.qryAccount, self.qryPosition]
            
            self.qryCount = 0           # 查询触发倒计时
            self.qryTrigger = 2         # 查询触发点
            self.qryNextFunction = 0    # 上次运行的查询函数索引
            
            self.startQuery()
    
    #----------------------------------------------------------------------
    def query(self, event):
        """注册到事件处理引擎上的查询函数"""
        self.qryCount += 1
        
        if self.qryCount > self.qryTrigger:
            # 清空倒计时
            self.qryCount = 0
            
            # 执行查询函数
            function = self.qryFunctionList[self.qryNextFunction]
            function()
            
            # 计算下次查询函数的索引，如果超过了列表长度，则重新设为0
            self.qryNextFunction += 1
            if self.qryNextFunction == len(self.qryFunctionList):
                self.qryNextFunction = 0
    
    #----------------------------------------------------------------------
    def startQuery(self):
        """启动连续查询"""
        self.eventEngine.register(EVENT_TIMER, self.query)
    
    #----------------------------------------------------------------------
    def setQryEnabled(self, qryEnabled):
        """设置是否要启动循环查询"""
        self.qryEnabled = qryEnabled
    

########################################################################
class CtpMdApi(MdApi):
    """CTP行情API实现"""

    #----------------------------------------------------------------------
    def __init__(self, gateway):
        """Constructor"""
        super(CtpMdApi, self).__init__()
        
        self.gateway = gateway                  # gateway对象
        self.gatewayName = gateway.gatewayName  # gateway对象名称
        
        self.reqID = EMPTY_INT                  # 操作请求编号
        
        self.connectionStatus = False           # 连接状态
        self.loginStatus = False                # 登录状态
        
        self.subscribedSymbols = set()          # 已订阅合约代码        
        
        self.userID   = EMPTY_STRING            # 账号
        self.password = EMPTY_STRING            # 密码
        self.brokerID = EMPTY_STRING            # 经纪商代码
        self.address  = EMPTY_STRING            # 服务器地址
        self.tradingDt = None               # 交易日datetime对象
        self.tradingDate = vtFunction.tradingDay()
        self.tradingDay = vtFunction.tradingDay()      # 交易日期
        self.recorderFields = ['openPrice','highestPrice','lowestPrice','closePrice',
                          'upperLimit','lowerLimit','openInterest','preDelta','currDelta',
                          'bidPrice1','bidPrice2','bidPrice3','bidPrice4','bidPrice5',
                          'askPrice1','askPrice2','askPrice3','askPrice4','askPrice5',
                          'settlementPrice','averagePrice']

    #----------------------------------------------------------------------
    def onFrontConnected(self):
        """服务器连接"""
        self.connectionStatus = True
        self.writeLog(text.DATA_SERVER_CONNECTED)
        self.login()
    
    #----------------------------------------------------------------------  
    def onFrontDisconnected(self, n):
        """服务器断开"""
        self.connectionStatus = False
        self.loginStatus = False
        self.gateway.mdConnected = False
        self.writeLog(text.DATA_SERVER_DISCONNECTED)
        
    #---------------------------------------------------------------------- 
    def onHeartBeatWarning(self, n):
        """心跳报警"""
        # 因为API的心跳报警比较常被触发，且与API工作关系不大，因此选择忽略
        pass
    
    #----------------------------------------------------------------------   
    def onRspError(self, error, n, last):
        """错误回报"""
        self.writeError(error['ErrorID'], error['ErrorMsg'])
        
    #----------------------------------------------------------------------
    def onRspUserLogin(self, data, error, n, last):
        """登陆回报"""
        # 如果登录成功，推送日志信息
        if error['ErrorID'] == 0:
            self.loginStatus = True
            self.gateway.mdConnected = True
            
            self.writeLog(text.DATA_SERVER_LOGIN)

            # 重新订阅之前订阅的合约
            for subscribeReq in self.subscribedSymbols:
                self.subscribe(subscribeReq)
            
            # 登录时通过本地时间来获取当前的日期
            self.tradingDt = datetime.now()
            self.tradingDate = self.tradingDt.strftime('%Y%m%d')
                
        # 否则，推送错误信息
        else:
            self.writeError(error['ErrorID'], error['ErrorMsg'])
            

    #---------------------------------------------------------------------- 
    def onRspUserLogout(self, data, error, n, last):
        """登出回报"""
        # 如果登出成功，推送日志信息
        if error['ErrorID'] == 0:
            self.loginStatus = False
            self.gateway.mdConnected = False
            
            self.writeLog(text.DATA_SERVER_LOGOUT)
                
        # 否则，推送错误信息
        else:
            self.writeError(error['ErrorID'], error['ErrorMsg'])

    #----------------------------------------------------------------------  
    def onRspSubMarketData(self, data, error, n, last):
        """订阅合约回报"""
        # 通常不在乎订阅错误，选择忽略
        pass
        
    #----------------------------------------------------------------------  
    def onRspUnSubMarketData(self, data, error, n, last):
        """退订合约回报"""
        # 同上
        pass  
        
    #----------------------------------------------------------------------  
    def onRtnDepthMarketData(self, data):
        """行情推送"""
        ## ---------------------------------------------------------------------
        # 忽略无效的报价单
        if data['LastPrice'] > 1.70e+100 or data['BidPrice1'] > 1.70e+100:
            return
        # 过滤尚未获取合约交易所时的行情推送
        symbol = data['InstrumentID']
        if symbol not in symbolExchangeDict:
            return
        ## ---------------------------------------------------------------------

        # 创建对象
        tick = VtTickData()
        tick.gatewayName = self.gatewayName
        tick.symbol = symbol
        tick.exchange = symbolExchangeDict[tick.symbol]
        tick.vtSymbol = tick.symbol      #'.'.join([tick.symbol, tick.exchange])
        
        tick.timeStamp  = datetime.now().strftime('%Y%m%d %H:%M:%S.%f')
        # 上期所和郑商所可以直接使用，大商所需要转换
        ##################################### tick.date = data['ActionDay']
        tick.date = self.tradingDate
        tick.time = '.'.join([data['UpdateTime'], str(data['UpdateMillisec']/100)])
        # tick.datetime = datetime.strptime(' '.join([tick.date, tick.time]),
        #                                       '%Y%m%d %H:%M:%S.%f')  

        ## 价格信息
        tick.lastPrice          = round(data['LastPrice'],5)
        # tick.preSettlementPrice = data['PreSettlementPrice']
        tick.preClosePrice      = round(data['PreClosePrice'],5)
        tick.openPrice          = round(data['OpenPrice'],5)
        tick.highestPrice       = round(data['HighestPrice'],5)
        tick.lowestPrice        = round(data['LowestPrice'],5)
        tick.closePrice         = round(data['ClosePrice'],5)

        tick.upperLimit         = round(data['UpperLimitPrice'],5)
        tick.lowerLimit         = round(data['LowerLimitPrice'],5)

        ## 成交量, 成交额
        tick.volume   = round(data['Volume'],5)
        tick.turnover = round(data['Turnover'],5)

        ## 持仓数据
        tick.preOpenInterest    = data['PreOpenInterest']
        tick.openInterest       = data['OpenInterest']

        # ## 期权数据
        tick.preDelta           = data['PreDelta']
        tick.currDelta          = data['CurrDelta']

        #! CTP只有一档行情
        tick.bidPrice1  = round(data['BidPrice1'],5)
        tick.bidVolume1 = data['BidVolume1']
        tick.askPrice1  = round(data['AskPrice1'],5)
        tick.askVolume1 = data['AskVolume1']

        tick.bidPrice2  = data['BidPrice2']
        tick.bidVolume2 = data['BidVolume2']
        tick.askPrice2  = data['AskPrice2']
        tick.askVolume2 = data['AskVolume2']

        tick.bidPrice3  = data['BidPrice3']
        tick.bidVolume3 = data['BidVolume3']
        tick.askPrice3  = data['AskPrice3']
        tick.askVolume3 = data['AskVolume3']

        tick.bidPrice4  = data['BidPrice4']
        tick.bidVolume4 = data['BidVolume4']
        tick.AskPrice4  = data['AskPrice4']
        tick.askVolume4 = data['AskVolume4']

        tick.bidPrice5  = data['BidPrice5']
        tick.bidVolume5 = data['BidVolume5']
        tick.askPrice5  = data['AskPrice5']
        tick.askVolume5 = data['AskVolume5']

        ########################################################################
        tick.settlementPrice    = round(data['SettlementPrice'],5)
        tick.averagePrice       = round(data['AveragePrice'],5)
        ########################################################################
        for i in self.recorderFields:
            if tick.__dict__[i] > 1.7e+100:
                tick.__dict__[i] = 0
        ## -------------------------------
        self.gateway.onTick(tick)
        ## ---------------------------------------------------------------------
        
    #----------------------------------------------------------------------
    def connect(self, userID, password, brokerID, address):
        """初始化连接"""
        self.userID   = userID                # 账号
        self.password = password              # 密码
        self.brokerID = brokerID              # 经纪商代码
        self.address  = address               # 服务器地址
        
        # 如果尚未建立服务器连接，则进行连接
        if not self.connectionStatus:
            # 创建C++环境中的API对象，这里传入的参数是需要用来保存.con文件的文件夹路径
            path = vtFunction.getTempPath(self.gatewayName + '_')
            self.createFtdcMdApi(path)
            # 注册服务器地址
            self.registerFront(self.address)
            # 初始化连接，成功会调用onFrontConnected
            self.init()
            
        # 若已经连接但尚未登录，则进行登录
        else:
            if not self.loginStatus:
                self.login()
        
    #----------------------------------------------------------------------
    def subscribe(self, subscribeReq):
        """订阅合约"""
        # 这里的设计是，如果尚未登录就调用了订阅方法
        # 则先保存订阅请求，登录完成后会自动订阅
        if self.loginStatus:
            self.subscribeMarketData(str(subscribeReq.symbol))
        self.subscribedSymbols.add(subscribeReq)   
        
    #----------------------------------------------------------------------
    def login(self):
        """登录"""
        # 如果填入了用户名密码等，则登录
        if self.userID and self.password and self.brokerID:
            req = {}
            req['UserID']   = self.userID
            req['Password'] = self.password
            req['BrokerID'] = self.brokerID
            self.reqID += 1
            self.reqUserLogin(req, self.reqID)    
    
    #----------------------------------------------------------------------
    def close(self):
        """关闭"""
        self.exit()
        
    #---------------------------------------------------------------------------
    def writeLog(self, content, logLevel = INFO):
        """发出日志"""
        log = VtLogData()
        log.gatewayName = self.gatewayName
        log.logContent  = content
        log.logLevel    = logLevel
        self.gateway.onLog(log)     

    #---------------------------------------------------------------------------
    def writeError(self, errorID, errorMsg):
        """发出错误"""
        err = VtErrorData()
        err.gatewayName = self.gatewayName
        err.errorID     = errorID
        err.errorMsg    = errorMsg.decode('gbk')
        self.gateway.onError(err) 
        ## ---------------------------------------------------------------------
        if globalSetting.LOGIN:
            self.writeLog(u"[错误代码]:%s [提示信息] %s" %(err.errorID, err.errorMsg),
                     logLevel = ERROR)


########################################################################
class CtpTdApi(TdApi):
    """CTP交易API实现"""
    
    #----------------------------------------------------------------------
    def __init__(self, gateway):
        """API对象的初始化函数"""
        super(CtpTdApi, self).__init__()
        
        self.gateway     = gateway              # gateway对象
        self.gatewayName = gateway.gatewayName  # gateway对象名称
        
        self.reqID = EMPTY_INT              # 操作请求编号
        
        self.connectionStatus = False       # 连接状态
        self.loginStatus = False            # 登录状态
        self.authStatus = False             # 验证状态
        self.loginFailed = False            # 登录失败（账号密码错误）
        
        self.userID = EMPTY_STRING          # 账号
        self.password = EMPTY_STRING        # 密码
        self.brokerID = EMPTY_STRING        # 经纪商代码
        self.address = EMPTY_STRING         # 服务器地址
        
        self.frontID = EMPTY_INT            # 前置机编号
        self.sessionID = EMPTY_INT          # 会话编号
        
        self.symbolExchangeDict = {}        # 保存合约代码和交易所的印射关系
        self.symbolSizeDict = {}            # 保存合约代码和合约大小的印射关系

        self.requireAuthentication = False
        
        self.contractDict  = {}
        self.dfAll         = pd.DataFrame()
 

    #----------------------------------------------------------------------
    def onFrontConnected(self):
        """服务器连接"""
        self.connectionStatus = True
        self.writeLog(text.TRADING_SERVER_CONNECTED)
        
        if self.requireAuthentication:
            self.authenticate()
        else:
            self.login()
        
    #----------------------------------------------------------------------
    def onFrontDisconnected(self, n):
        """服务器断开"""
        self.connectionStatus = False
        self.loginStatus = False
        self.gateway.tdConnected = False
        self.writeLog(text.TRADING_SERVER_DISCONNECTED)
        
    #----------------------------------------------------------------------
    def onHeartBeatWarning(self, n):
        """"""
        pass
        
    #----------------------------------------------------------------------
    def onRspAuthenticate(self, data, error, n, last):
        """验证客户端回报"""
        if error['ErrorID'] == 0:
            self.authStatus = True
            self.writeLog(text.TRADING_SERVER_AUTHENTICATED)
            self.login()
        else:
            self.writeError(error['ErrorID'], error['ErrorMsg'])
        
    #----------------------------------------------------------------------
    def onRspUserLogin(self, data, error, n, last):
        """登陆回报"""
        # 如果登录成功，推送日志信息
        if error['ErrorID'] == 0:
            self.frontID = str(data['FrontID'])
            self.sessionID = str(data['SessionID'])
            self.loginStatus = True
            self.gateway.tdConnected = True
            
            self.writeLog(text.TRADING_SERVER_LOGIN)
            
            # 确认结算信息
            req = {}
            req['BrokerID'] = self.brokerID
            req['InvestorID'] = self.userID
            self.reqID += 1
            self.reqSettlementInfoConfirm(req, self.reqID)              
                
        # 否则，推送错误信息
        else:
            self.writeError(error['ErrorID'], error['ErrorMsg'])
            ## -----------------------------------------------------------------
            # 标识登录失败，防止用错误信息连续重复登录
            self.loginFailed =  True
        
    #----------------------------------------------------------------------
    def onRspUserLogout(self, data, error, n, last):
        """登出回报"""
        # 如果登出成功，推送日志信息
        if error['ErrorID'] == 0:
            self.loginStatus = False
            self.gateway.tdConnected = False
            self.writeLog(text.TRADING_SERVER_LOGOUT)
        # 否则，推送错误信息
        else:
            self.writeError(error['ErrorID'], error['ErrorMsg'])
        
    #----------------------------------------------------------------------
    def onRspSettlementInfoConfirm(self, data, error, n, last):
        """确认结算信息回报"""
        self.writeLog(text.SETTLEMENT_INFO_CONFIRMED)
        
        # 查询合约代码
        self.reqID += 1
        self.reqQryInstrument({}, self.reqID)
        
    #----------------------------------------------------------------------
    def onRspQryInstrument(self, data, error, n, last):
        """合约查询回报"""
        contract = VtContractData()
        contract.gatewayName = self.gatewayName

        contract.symbol = data['InstrumentID']
        contract.exchange = exchangeMapReverse[data['ExchangeID']]
        contract.vtSymbol = contract.symbol #'.'.join([contract.symbol, contract.exchange])
        contract.name = data['InstrumentName'].decode('GBK')

        # 合约数值
        contract.size = data['VolumeMultiple']
        contract.priceTick = data['PriceTick']
        contract.strikePrice = data['StrikePrice']
        contract.underlyingSymbol = data['UnderlyingInstrID']
        contract.productClass = productClassMapReverse.get(data['ProductClass'], PRODUCT_UNKNOWN)
        contract.expiryDate = data['ExpireDate']
        
        # 期权类型
        if contract.productClass is PRODUCT_OPTION:
            if data['OptionsType'] == '1':
                contract.optionType = OPTION_CALL
            elif data['OptionsType'] == '2':
                contract.optionType = OPTION_PUT

        contract.volumeMultiple = data['VolumeMultiple']

        if data['LongMarginRatio'] < 1e+99 and data['ShortMarginRatio'] < 1e+99:
            contract.longMarginRatio  = round(data['LongMarginRatio'],5)
            contract.shortMarginRatio = round(data['ShortMarginRatio'],5)
        # 缓存代码和交易所的印射关系
        self.symbolExchangeDict[contract.symbol] = contract.exchange
        self.symbolSizeDict[contract.symbol] = contract.size

        # 推送
        self.gateway.onContract(contract)
        ## =====================================================================
        ## william
        ## ---------------------------------------------------------------------
        self.contractDict[contract.symbol]   = contract
        self.contractDict[contract.vtSymbol] = contract
        ## =====================================================================

        # 缓存合约代码和交易所映射
        symbolExchangeDict[contract.symbol] = contract.exchange

        if last:
            # print self.contractDict
            dfHeader = ['symbol','vtSymbol','name','productClass','gatewayName','exchange',
                        'priceTick','size','shortMarginRatio','longMarginRatio',
                        'optionType','underlyingSymbol','strikePrice']
            dfData   = []
            for k in self.contractDict.keys():
                temp = self.contractDict[k].__dict__
                dfData.append([temp[kk] for kk in dfHeader])
            df = pd.DataFrame(dfData, columns = dfHeader)

            reload(sys) # reload 才能调用 setdefaultencoding 方法
            sys.setdefaultencoding('utf-8')

            df.to_csv('./temp/contract.csv', index = False)
            if not os.path.exists('./temp/contractAll.csv'):
                df.to_csv('./temp/contractAll.csv', index = False)

            ## =================================================================
            try:
                self.dfAll = pd.read_csv('./temp/contractAll.csv')
                for i in range(df.shape[0]):
                    if df.at[i,'symbol'] not in self.dfAll.symbol.values:
                        self.dfAll = self.dfAll.append(df.loc[i], ignore_index = True)
                self.dfAll.to_csv('./temp/contractAll.csv', index = False)
            except:
                None
            ## =================================================================
            self.contractFileName = './temp/ContractData.vt'
            f = shelve.open(self.contractFileName)
            f['data'] = self.contractDict
            f.close()
            ## =================================================================
            self.writeLog(text.CONTRACT_DATA_RECEIVED)
            ## 交易合约信息获取是否成功
            globalSetting.LOGIN = True
            self.writeLog(u'账户登录成功')
            
        
    #----------------------------------------------------------------------
    def onRspQryDepthMarketData(self, data, error, n, last):
        """"""
        pass
        
    #----------------------------------------------------------------------
    def onRspQrySettlementInfo(self, data, error, n, last):
        """"""
        pass
        
    #----------------------------------------------------------------------
    def onRspError(self, error, n, last):
        """错误回报"""
        self.writeError(error['ErrorID'], error['ErrorMsg'])

    #----------------------------------------------------------------------
    def onErrRtnOrderAction(self, data, error):
        """撤单错误回报（交易所）"""
        self.writeError(error['ErrorID'], error['ErrorMsg'])

    ## =========================================================================
    ## 这个函数不能删除
    #----------------------------------------------------------------------
    def onRtnInstrumentStatus(self, data):
        """"""
        pass
        
    #----------------------------------------------------------------------
    def connect(self, userID, password, brokerID, address, authCode, userProductInfo):
        """初始化连接"""
        self.userID = userID                # 账号
        self.password = password            # 密码
        self.brokerID = brokerID            # 经纪商代码
        self.address = address              # 服务器地址
        self.authCode = authCode            #验证码
        self.userProductInfo = userProductInfo  #产品信息
        
        # 如果尚未建立服务器连接，则进行连接
        if not self.connectionStatus:
            # 创建C++环境中的API对象，这里传入的参数是需要用来保存.con文件的文件夹路径
            path = vtFunction.getTempPath(self.gatewayName + '_')
            self.createFtdcTraderApi(path)
            
            # 设置数据同步模式为推送从今日开始所有数据
            self.subscribePrivateTopic(0)
            self.subscribePublicTopic(0)            
            
            # 注册服务器地址
            self.registerFront(self.address)
            # 初始化连接，成功会调用onFrontConnected
            self.init()
            
        # 若已经连接但尚未登录，则进行登录
        else:
            if self.requireAuthentication and not self.authStatus:
                self.authenticate()
            elif not self.loginStatus:
                self.login()
    
    #----------------------------------------------------------------------
    def login(self):
        """连接服务器"""
        # 如果之前有过登录失败，则不再进行尝试
        if self.loginFailed:
            return
        
        # 如果填入了用户名密码等，则登录
        if self.userID and self.password and self.brokerID:
            req = {}
            req['UserID'] = self.userID
            req['Password'] = self.password
            req['BrokerID'] = self.brokerID
            self.reqID += 1
            self.reqUserLogin(req, self.reqID)   
            
    #----------------------------------------------------------------------
    def authenticate(self):
        """申请验证"""
        if self.userID and self.brokerID and self.authCode and self.userProductInfo:
            req = {}
            req['UserID'] = self.userID
            req['BrokerID'] = self.brokerID
            req['AuthCode'] = self.authCode
            req['UserProductInfo'] = self.userProductInfo
            self.reqID +=1
            self.reqAuthenticate(req, self.reqID)
        
    #----------------------------------------------------------------------
    def close(self):
        """关闭"""
        self.exit()

    #---------------------------------------------------------------------------
    def writeLog(self, content, logLevel = INFO):
        """发出日志"""
        log = VtLogData()
        log.gatewayName = self.gatewayName
        log.logContent = content
        log.logLevel = logLevel
        self.gateway.onLog(log)     

    #---------------------------------------------------------------------------
    def writeError(self, errorID, errorMsg):
        """发出错误"""
        err = VtErrorData()
        err.gatewayName = self.gatewayName
        err.errorID = errorID
        err.errorMsg = errorMsg.decode('gbk')
        self.gateway.onError(err) 
        ## ---------------------------------------------------------------------
        if globalSetting.LOGIN:
            self.writeLog(u"[错误代码]:%s [提示信息] %s" %(err.errorID, err.errorMsg),
                     logLevel = ERROR)
