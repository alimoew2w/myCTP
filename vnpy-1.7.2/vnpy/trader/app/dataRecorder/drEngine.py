# encoding: UTF-8

'''
本文件中实现了行情数据记录引擎，用于汇总TICK数据，并生成K线插入数据库。

使用DR_setting.json来配置需要收集的合约，以及主力合约代码。
'''
from __future__ import division
import os,json,csv
import pandas as pd
from collections import OrderedDict
from Queue import Queue, Empty
from threading import Thread

from vnpy.event import Event
from vnpy.trader.vtEvent import *
from vnpy.trader import vtFunction
from vnpy.trader.vtObject import *
from vnpy.trader.app.ctaStrategy.ctaTemplate import BarManager
from vnpy.trader.vtGlobal import globalSetting

from .drBase import *
from .language import text

from datetime import datetime, time, timedelta


########################################################################
class DrEngine(object):
    """数据记录引擎"""
    
    # settingFileName = 'DR_setting.json'
    # settingFilePath = vtFunction.getJsonPath(settingFileName, __file__)  

    #----------------------------------------------------------------------
    def __init__(self, mainEngine, eventEngine):
        global globalSetting
        # print globalSetting().accountID
        """Constructor"""
        self.mainEngine = mainEngine
        self.eventEngine = eventEngine
        
        # 当前日期
        self.tradingDay = vtFunction.tradingDay()
        self.tradingDate = vtFunction.tradingDate()

        ## 目录
        self.PATH = os.path.abspath(os.path.dirname(__file__))
        
        # 主力合约代码映射字典，key为具体的合约代码（如IF1604），value为主力合约代码（如IF0000）
        self.activeSymbolDict = {}
        # Tick对象字典
        self.tickSymbolSet = set()
        # K线合成器字典
        self.bmDict = {}
        # 配置字典
        self.settingDict = OrderedDict()

        # 负责执行数据库插入的单独线程相关
        self.active = False                     # 工作状态
        self.queue = Queue()                    # 队列
        self.thread = Thread(target=self.run)   # 线程
        
        # 载入设置，订阅行情
        self.loadSetting()
        
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
        self.DAY_START   = time(8, 30)       # 日盘启动和停止时间
        self.DAY_END     = time(15, 30)
        
        self.NIGHT_START = time(20, 30)      # 夜盘启动和停止时间
        self.NIGHT_END   = time(2, 45)
        ## =====================================================================


        # 启动数据插入线程
        self.start()
        # 注册事件监听
        self.registerEvent()  
    
    #----------------------------------------------------------------------
    def loadSetting(self):
        """加载配置"""     
        ## ---------------------------------------------------------------------
        if self.mainEngine.subscribeAll:
            try:
                # contractAll  = os.path.normpath(os.path.join(self.PATH,'../../','contractAll.csv'))
                contractAll  = './temp/contractAll.csv'
                contractInfo = pd.read_csv(contractAll)
                self.contractDict = {}
                for i in range(len(contractInfo)):
                    self.contractDict[contractInfo.loc[i]['symbol']] = contractInfo.loc[i].to_dict()
            except:
                None

            for k in self.contractDict.keys():
                contract = self.contractDict[k]
                req = VtSubscribeReq()
                req.symbol = contract['symbol']
                req.exchange = contract['exchange']

                if contract['symbol']:
                    self.mainEngine.subscribe(req, contract['gatewayName'])
                    self.mainEngine.writeLog(u'合约 %s 订阅成功' %contract['symbol'],
                                             gatewayName = 'DATA_RECORDER')
                else:
                    pass

        ## ---------------------------------------------------------------------

    #----------------------------------------------------------------------
    def getSetting(self):
        """获取配置"""
        return self.settingDict, self.activeSymbolDict

    #----------------------------------------------------------------------
    def procecssTickEvent(self, event):
        """处理行情事件"""
        tick = event.dict_['data']
        vtSymbol = tick.vtSymbol
        # 生成datetime对象
        if not tick.datetime:
            tick.datetime = datetime.strptime(' '.join([tick.date, tick.time]),
                                              '%Y%m%d %H:%M:%S.%f')     
        ## ---------------------------------------------------------------------
        # self.onTick(tick)       
        ## ---------------------------------------------------------------------
        ## william
        if self.mainEngine.printData:
            print '\n' + tick.vtSymbol
            print [tick.__dict__[k] for k in self.myHeader]
 
        ## =====================================================================
        if self.mainEngine.subscribeAll:
            with open(self.dataFile, 'a') as f:
                wr = csv.writer(f)
                wr.writerow([tick.__dict__[k] for k in self.myHeader])
        ## =====================================================================

    ############################################################################
    ## william
    ## 更新状态，需要订阅
    ############################################################################
    def processTradingStatus(self, event):
        """控制交易开始与停止状态"""
        if datetime.now().second % 30 != 0:
            return 

        currentTime = datetime.now().time()
        if not ((self.DAY_START <= currentTime <= self.DAY_END) or
            (currentTime >= self.NIGHT_START) or
            (currentTime <= self.NIGHT_END)):
            # ## ----------
            os._exit(0)
            # ## ----------


    #----------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.eventEngine.register(EVENT_TICK, self.procecssTickEvent)
        self.eventEngine.register(EVENT_TIMER, self.processTradingStatus)
 
    #----------------------------------------------------------------------
    def run(self):
        """运行插入线程"""
        pass
        # while self.active:
        #     try:
        #         dbName, collectionName, d = self.queue.get(block=True, timeout=1)
                
        #         # 这里采用MongoDB的update模式更新数据，在记录tick数据时会由于查询
        #         # 过于频繁，导致CPU占用和硬盘读写过高后系统卡死，因此不建议使用
        #         #flt = {'datetime': d['datetime']}
        #         #self.mainEngine.dbMongoUpdate(dbName, collectionName, d, flt, True)
                
        #         # 使用insert模式更新数据，可能存在时间戳重复的情况，需要用户自行清洗
        #         # self.mainEngine.dbMongoInsert(dbName, collectionName, d)
        #     except Empty:
        #         pass
            
    #----------------------------------------------------------------------
    def start(self):
        """启动"""
        self.active = True
        self.thread.start()
        
    #----------------------------------------------------------------------
    def stop(self):
        """退出"""
        if self.active:
            self.active = False
            self.thread.join()
        
    #----------------------------------------------------------------------
    def writeDrLog(self, content):
        """快速发出日志事件"""
        log = VtLogData()
        log.logContent = content
        event = Event(type_=EVENT_DATARECORDER_LOG)
        event.dict_['data'] = log
        self.eventEngine.put(event)   
