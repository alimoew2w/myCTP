# encoding: UTF-8

'''
该模块用于获取　CTP Tick Data　行情记录．
'''
from __future__ import division
import os,json,csv
import pandas as pd
from collections import OrderedDict

from vnpy.event import Event
from vnpy.trader.vtEvent import *
from vnpy.trader import vtFunction
from vnpy.trader.vtObject import *
from vnpy.trader.vtGlobal import globalSetting

from .drBase import *
from .language import text

from datetime import datetime, time, timedelta


########################################################################
class DrEngine(object):
    """数据记录引擎"""

    #----------------------------------------------------------------------
    def __init__(self, mainEngine, eventEngine):
        global globalSetting
        """Constructor"""
        self.mainEngine = mainEngine
        self.eventEngine = eventEngine
        
        # 当前日期
        self.tradingDay = vtFunction.tradingDay()
        self.tradingDate = vtFunction.tradingDate()

        ## 目录
        self.PATH = os.path.abspath(os.path.dirname(__file__))
        
        ## ------------------
        # 载入设置，订阅行情
        self.loadSetting()
        ## ------------------
        
        self.myHeader   = ['timeStamp','date','time','symbol','exchange',
                          'lastPrice','preSettlementPrice','preClosePrice',
                          'openPrice','highestPrice','lowestPrice','closePrice',
                          'upperLimit','lowerLimit','settlementPrice','volume','turnover',
                          'preOpenInterest','openInterest','preDelta','currDelta',
                          'bidPrice1','bidPrice2','bidPrice3','bidPrice4','bidPrice5',
                          'askPrice1','askPrice2','askPrice3','askPrice4','askPrice5',
                          'bidVolume1','bidVolume2','bidVolume3','bidVolume4','bidVolume5',
                          'askVolume1','askVolume2','askVolume3','askVolume4','askVolume5',
                          'averagePrice']
        self.tempFields = ['openPrice','highestPrice','lowestPrice','closePrice',
                          'upperLimit','lowerLimit','openInterest','preDelta','currDelta',
                          'bidPrice1','bidPrice2','bidPrice3','bidPrice4','bidPrice5',
                          'askPrice1','askPrice2','askPrice3','askPrice4','askPrice5',
                          'settlementPrice','averagePrice']
        ########################################################################
        self.DATA_PATH    = os.path.normpath(os.path.join(
                            globalSetting().vtSetting['DATA_PATH'], 
                            globalSetting.accountID, 'TickData'))
        self.dataFile     = os.path.join(self.DATA_PATH,(str(self.tradingDay) + '.csv'))
        if not os.path.exists(self.dataFile):
            with open(self.dataFile, 'w') as f:
                wr = csv.writer(f)
                wr.writerow(self.myHeader)
            f.close()
        ########################################################################

        ## =====================================================================
        self.DAY_START   = time(8, 00)       # 日盘启动和停止时间
        self.DAY_END     = time(15, 30)
        
        self.NIGHT_START = time(20, 00)      # 夜盘启动和停止时间
        self.NIGHT_END   = time(2, 45)
        self.exitCounter = 0
        ## =====================================================================

        # 注册事件监听
        self.registerEvent()  
    
    #----------------------------------------------------------------------
    def loadSetting(self):
        """加载配置"""     
        ## =====================================================================
        if self.mainEngine.subscribeAll:
            try:
                # contractAll  = os.path.normpath(os.path.join(self.PATH,'../../','contractAll.csv'))
                contractAll  = './temp/contractAll.csv'
                contractInfo = pd.read_csv(contractAll)
                self.contractDict = {}
                for i in range(len(contractInfo)):
                    self.contractDict[contractInfo.loc[i]['symbol']] = contractInfo.loc[i].to_dict()
            except:
                self.mainEngine.writeLog(u'未找到需要订阅的合约信息: contractAll.csv',
                                         gatewayName = 'DATA_RECORDER')

            ## -----------------------------------------------------------------
            for k in self.contractDict.keys():
                contract = self.contractDict[k]
                req = VtSubscribeReq()
                req.symbol = contract['symbol']
                req.exchange = contract['exchange']

                if contract['symbol']:
                    self.mainEngine.subscribe(req, contract['gatewayName'])
            ## -----------------------------------------------------------------

        ## =====================================================================


    #----------------------------------------------------------------------
    def procecssTickEvent(self, event):
        """处理行情事件"""
        tick = event.dict_['data']
        # 生成datetime对象
        if not tick.datetime:
            tick.datetime = datetime.strptime(' '.join([tick.date, tick.time]),
                                              '%Y%m%d %H:%M:%S.%f')     
        ## ---------------------------------------------------------------------
        ## william     
        data = [tick.__dict__[k] for k in self.myHeader]  
        ## ---------------------------------------------------------------------
        
        ## =====================================================================
        # if self.mainEngine.printData:
        #     print '\n' + tick.vtSymbol
        #     print data
        ## =====================================================================
 
        ## =====================================================================
        # if self.mainEngine.subscribeAll:
        #     with open(self.dataFile, 'a') as f:
        #         wr = csv.writer(f)
        #         wr.writerow(data)
        
        with open(self.dataFile, 'a') as f:
            wr = csv.writer(f)
            wr.writerow(data)
        ## =====================================================================

    ############################################################################
    ## william
    ## 更新状态，需要订阅
    ############################################################################
    def processTradingStatus(self, event):
        """控制交易开始与停止状态"""
        if (datetime.now().minute % 2 != 0 or
            datetime.now().second % 20 != 0):
            return 
        ## ------------------------
        h = datetime.now().hour
        m = datetime.now().minute
        ## ------------------------

        ## ---------------------------------------------------------------------
        if ((h == self.NIGHT_END.hour and m >= self.NIGHT_END.minute) or 
            (h == self.DAY_END.hour and m >= self.DAY_END.minute) or 
            (h in [self.NIGHT_START.hour, self.DAY_START.hour] and 50 <= m < 55)):
            self.exitCounter += 1
            self.mainEngine.writeLog(u'即将退出系统，计数器：%s' %self.exitCounter,
                                     gatewayName = 'DATA_RECORDER')
            if self.exitCounter >= 3:
                os._exit(0)
        ## ---------------------------------------------------------------------

    #----------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.eventEngine.register(EVENT_TICK, self.procecssTickEvent)
        self.eventEngine.register(EVENT_TIMER, self.processTradingStatus)
