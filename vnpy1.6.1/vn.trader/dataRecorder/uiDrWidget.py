# encoding: UTF-8

'''
行情记录模块相关的GUI控制组件
'''
from __future__ import division

import json

from uiBasicWidget import QtGui, QtCore
from eventEngine import *
from language import text

################################################################################
## william

import time
import sys
import shelve
from collections import OrderedDict

import sip
from PyQt4 import QtCore, QtGui
import pyqtgraph as pg

import numpy as np
from pymongo import MongoClient
from pymongo.errors import *
from datetime import datetime, timedelta



########################################################################
class TableCell(QtGui.QTableWidgetItem):
    """居中的单元格"""

    #----------------------------------------------------------------------
    def __init__(self, text=None, mainEngine=None):
        """Constructor"""
        super(TableCell, self).__init__()
        self.data = None
        self.setTextAlignment(QtCore.Qt.AlignCenter)
        if text:
            self.setContent(text)
    
    #----------------------------------------------------------------------
    def setContent(self, text):
        """设置内容"""
        if text == '0' or text == '0.0':
            self.setText('')
        else:
            self.setText(text)


########################################################################
class DrEngineManager(QtGui.QWidget):
    """行情数据记录引擎管理组件"""
    signal = QtCore.pyqtSignal(type(Event()))

    #----------------------------------------------------------------------
    def __init__(self, drEngine, eventEngine, parent=None):
        """Constructor"""
        super(DrEngineManager, self).__init__(parent)
        
        self.drEngine = drEngine
        self.eventEngine = eventEngine
        
        self.initUi()
        self.updateSetting()
        self.registerEvent() 
        
    #----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        self.setWindowTitle(text.DATA_RECORDER)
        
        # 记录合约配置监控
        tickLabel = QtGui.QLabel(text.TICK_RECORD)
        self.tickTable = QtGui.QTableWidget()
        self.tickTable.setColumnCount(2)
        self.tickTable.verticalHeader().setVisible(False)
        self.tickTable.setEditTriggers(QtGui.QTableWidget.NoEditTriggers)
        self.tickTable.horizontalHeader().setResizeMode(QtGui.QHeaderView.Stretch)
        self.tickTable.setAlternatingRowColors(True)
        self.tickTable.setHorizontalHeaderLabels([text.CONTRACT_SYMBOL, text.GATEWAY])
        
        barLabel = QtGui.QLabel(text.BAR_RECORD)
        self.barTable = QtGui.QTableWidget()
        self.barTable.setColumnCount(2)
        self.barTable.verticalHeader().setVisible(False)
        self.barTable.setEditTriggers(QtGui.QTableWidget.NoEditTriggers)
        self.barTable.horizontalHeader().setResizeMode(QtGui.QHeaderView.Stretch)
        self.barTable.setAlternatingRowColors(True)        
        self.barTable.setHorizontalHeaderLabels([text.CONTRACT_SYMBOL, text.GATEWAY])

        activeLabel = QtGui.QLabel(text.DOMINANT_CONTRACT)
        self.activeTable = QtGui.QTableWidget()
        self.activeTable.setColumnCount(2)
        self.activeTable.verticalHeader().setVisible(False)
        self.activeTable.setEditTriggers(QtGui.QTableWidget.NoEditTriggers)
        self.activeTable.horizontalHeader().setResizeMode(QtGui.QHeaderView.Stretch)
        self.activeTable.setAlternatingRowColors(True)        
        self.activeTable.setHorizontalHeaderLabels([text.DOMINANT_SYMBOL, text.CONTRACT_SYMBOL])

        # 日志监控
        self.logMonitor = QtGui.QTextEdit()
        self.logMonitor.setReadOnly(True)
        self.logMonitor.setMinimumHeight(600)
        
        # 设置布局
        grid = QtGui.QGridLayout()
        
        grid.addWidget(tickLabel, 0, 0)
        grid.addWidget(barLabel, 0, 1)
        grid.addWidget(activeLabel, 0, 2)
        grid.addWidget(self.tickTable, 1, 0)
        grid.addWidget(self.barTable, 1, 1)
        grid.addWidget(self.activeTable, 1, 2)        
        
        vbox = QtGui.QVBoxLayout()
        vbox.addLayout(grid)
        vbox.addWidget(self.logMonitor)
        self.setLayout(vbox)

    #----------------------------------------------------------------------
    def updateLog(self, event):
        """更新日志"""
        log = event.dict_['data']
        content = '\t'.join([log.logTime, log.logContent])
        self.logMonitor.append(content)
    
    #----------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.signal.connect(self.updateLog)
        self.eventEngine.register(EVENT_DATARECORDER_LOG, self.signal.emit)
        
    #----------------------------------------------------------------------
    def updateSetting(self):
        """显示引擎行情记录配置"""
        with open(self.drEngine.settingFileName) as f:
            drSetting = json.load(f)
    
            if 'tick' in drSetting:
                l = drSetting['tick']
    
                for setting in l:
                    self.tickTable.insertRow(0)
                    self.tickTable.setItem(0, 0, TableCell(setting[0]))
                    self.tickTable.setItem(0, 1, TableCell(setting[1]))
    
            if 'bar' in drSetting:
                l = drSetting['bar']
    
                for setting in l:
                    self.barTable.insertRow(0)
                    self.barTable.setItem(0, 0, TableCell(setting[0]))
                    self.barTable.setItem(0, 1, TableCell(setting[1])) 
    
            if 'active' in drSetting:
                d = drSetting['active']
    
                for activeSymbol, symbol in d.items():
                    self.activeTable.insertRow(0)
                    self.activeTable.setItem(0, 0, TableCell(activeSymbol))
                    self.activeTable.setItem(0, 1, TableCell(symbol))
    
################################################################################
## william
################################################################################
################################################################################
class BarEngineManager(QtGui.QWidget):
    """用于显示价格走势图"""
    signal = QtCore.pyqtSignal(type(Event()))

    # tick图的相关参数、变量
    listlastPrice = np.empty(1000)

    fastMA = 0
    midMA = 0
    slowMA = 0
    listfastMA = np.empty(1000)
    listmidMA = np.empty(1000)
    listslowMA = np.empty(1000)
    tickFastAlpha = 0.0333    # 快速均线的参数,30
    tickMidAlpha = 0.0167     # 中速均线的参数,60
    tickSlowAlpha = 0.0083    # 慢速均线的参数,120

    ptr = 0
    ticktime = None  # tick数据时间

    # K线图EMA均线的参数、变量
    EMAFastAlpha = 0.0167    # 快速EMA的参数,60
    EMASlowAlpha = 0.0083  # 慢速EMA的参数,120
    fastEMA = 0        # 快速EMA的数值
    slowEMA = 0        # 慢速EMA的数值
    listfastEMA = []
    listslowEMA = []

    # K线缓存对象
    barOpen = 0
    barHigh = 0
    barLow = 0
    barClose = 0
    barTime = None
    barOpenInterest = 0
    num = 0

    # 保存K线数据的列表对象
    listBar = []
    listClose = []
    listHigh = []
    listLow = []
    listOpen = []
    listOpenInterest = []

    # 是否完成了历史数据的读取
    initCompleted = False
    # 初始化时读取的历史数据的起始日期(可以选择外部设置)
    startDate = None
    symbol = 'SR701'

    class CandlestickItem(pg.GraphicsObject):
        def __init__(self, data):
            pg.GraphicsObject.__init__(self)
            self.data = data  ## data must have fields: time, open, close, min, max
            self.generatePicture()

        def generatePicture(self):
            ## pre-computing a QPicture object allows paint() to run much more quickly,
            ## rather than re-drawing the shapes every time.
            self.picture = QtGui.QPicture()
            p = QtGui.QPainter(self.picture)
            p.setPen(pg.mkPen(color='w', width=0.4))  # 0.4 means w*2
            # w = (self.data[1][0] - self.data[0][0]) / 3.
            w = 0.2
            for (t, open, close, min, max) in self.data:
                p.drawLine(QtCore.QPointF(t, min), QtCore.QPointF(t, max))
                if open > close:
                    p.setBrush(pg.mkBrush('g'))
                else:
                    p.setBrush(pg.mkBrush('r'))
                p.drawRect(QtCore.QRectF(t-w, open, w*2, close-open))
            p.end()

        def paint(self, p, *args):
            p.drawPicture(0, 0, self.picture)

        def boundingRect(self):
            ## boundingRect _must_ indicate the entire area that will be drawn on
            ## or else we will get artifacts and possibly crashing.
            ## (in this case, QPicture does all the work of computing the bouning rect for us)
            return QtCore.QRectF(self.picture.boundingRect())

    #----------------------------------------------------------------------
    def __init__(self, eventEngine, mainEngine, parent=None):
        """Constructor"""
        super(BarEngineManager, self).__init__(parent)

        self.__eventEngine = eventEngine
        self.__mainEngine = mainEngine
        # MongoDB数据库相关
        self.__mongoConnected = False
        self.__mongoConnection = None
        self.__mongoTickDB = None

        # 调用函数
        self.__connectMongo()
        self.initUi(startDate=None)
        self.registerEvent()

    #----------------------------------------------------------------------
    def initUi(self, startDate=None):
        """初始化界面"""
        self.setWindowTitle(u'Bar Price')

        self.vbl_1 = QtGui.QVBoxLayout()
        self.initplotTick()  # plotTick初始化

        self.vbl_2 = QtGui.QVBoxLayout()
        self.initplotKline()  # plotKline初始化
        self.initplotTendency()  # plot分时图的初始化

        # 整体布局
        self.hbl = QtGui.QHBoxLayout()
        self.hbl.addLayout(self.vbl_1)
        self.hbl.addLayout(self.vbl_2)
        self.setLayout(self.hbl)

        self.initHistoricalData()  # 下载历史数据

    #----------------------------------------------------------------------
    def initplotTick(self):
        """"""
        self.pw1 = pg.PlotWidget(name='Plot1')
        self.vbl_1.addWidget(self.pw1)
        self.pw1.setRange(xRange=[-360, 0])
        self.pw1.setLimits(xMax=5)
        self.pw1.setDownsampling(mode='peak')
        self.pw1.setClipToView(True)

        self.curve1 = self.pw1.plot()
        self.curve2 = self.pw1.plot()
        self.curve3 = self.pw1.plot()
        self.curve4 = self.pw1.plot()

    #----------------------------------------------------------------------
    def initplotKline(self):
        """Kline"""
        self.pw2 = pg.PlotWidget(name='Plot2')  # K线图
        self.vbl_2.addWidget(self.pw2)
        self.pw2.setDownsampling(mode='peak')
        self.pw2.setClipToView(True)

        self.curve5 = self.pw2.plot()
        self.curve6 = self.pw2.plot()

        self.candle = self.CandlestickItem(self.listBar)
        self.pw2.addItem(self.candle)
        ## Draw an arrowhead next to the text box
        # self.arrow = pg.ArrowItem()
        # self.pw2.addItem(self.arrow)

    #----------------------------------------------------------------------
    def initplotTendency(self):
        """"""
        self.pw3 = pg.PlotWidget(name='Plot3')
        self.vbl_2.addWidget(self.pw3)
        self.pw3.setDownsampling(mode='peak')
        self.pw3.setClipToView(True)
        self.pw3.setMaximumHeight(200)
        self.pw3.setXLink('Plot2')   # X linked with Plot2

        self.curve7 = self.pw3.plot()

    #----------------------------------------------------------------------
    def initHistoricalData(self,startDate=None):
        """初始历史数据"""

        td = timedelta(days=1)     # 读取3天的历史TICK数据

        if startDate:
            cx = self.loadTick(self.symbol, startDate-td)
        else:
            today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
            cx = self.loadTick(self.symbol, today-td)

        if cx:
            for data in cx:
                tick = Tick(data['InstrumentID'])

                tick.openPrice = data['OpenPrice']
                tick.highPrice = data['HighestPrice']
                tick.lowPrice = data['LowestPrice']
                tick.lastPrice = data['LastPrice']

                tick.volume = data['Volume']
                tick.openInterest = data['OpenInterest']

                tick.upperLimit = data['UpperLimitPrice']
                tick.lowerLimit = data['LowerLimitPrice']

                tick.time = data['UpdateTime']
                tick.ms = data['UpdateMillisec']

                tick.bidPrice1 = data['BidPrice1']
                tick.bidPrice2 = data['BidPrice2']
                tick.bidPrice3 = data['BidPrice3']
                tick.bidPrice4 = data['BidPrice4']
                tick.bidPrice5 = data['BidPrice5']

                tick.askPrice1 = data['AskPrice1']
                tick.askPrice2 = data['AskPrice2']
                tick.askPrice3 = data['AskPrice3']
                tick.askPrice4 = data['AskPrice4']
                tick.askPrice5 = data['AskPrice5']

                tick.bidVolume1 = data['BidVolume1']
                tick.bidVolume2 = data['BidVolume2']
                tick.bidVolume3 = data['BidVolume3']
                tick.bidVolume4 = data['BidVolume4']
                tick.bidVolume5 = data['BidVolume5']

                tick.askVolume1 = data['AskVolume1']
                tick.askVolume2 = data['AskVolume2']
                tick.askVolume3 = data['AskVolume3']
                tick.askVolume4 = data['AskVolume4']
                tick.askVolume5 = data['AskVolume5']

                self.onTick(tick)

        self.initCompleted = True    # 读取历史数据完成
        # pprint('load historic data completed')

    #----------------------------------------------------------------------
    def plotTick(self):
        """画tick图"""
        if self.initCompleted:
            self.curve1.setData(self.listlastPrice[:self.ptr])
            self.curve2.setData(self.listfastMA[:self.ptr], pen=(255, 0, 0), name="Red curve")
            self.curve3.setData(self.listmidMA[:self.ptr], pen=(0, 255, 0), name="Green curve")
            self.curve4.setData(self.listslowMA[:self.ptr], pen=(0, 0, 255), name="Blue curve")
            self.curve1.setPos(-self.ptr, 0)
            self.curve2.setPos(-self.ptr, 0)
            self.curve3.setPos(-self.ptr, 0)
            self.curve4.setPos(-self.ptr, 0)

    #----------------------------------------------------------------------
    def plotKline(self):
        """K线图"""
        if self.initCompleted:
            # 均线
            self.curve5.setData(self.listfastEMA, pen=(255, 0, 0), name="Red curve")
            self.curve6.setData(self.listslowEMA, pen=(0, 255, 0), name="Green curve")

            # 画K线
            self.pw2.removeItem(self.candle)
            self.candle = self.CandlestickItem(self.listBar)
            self.pw2.addItem(self.candle)
            self.plotText()   # 显示开仓信号位置

    #----------------------------------------------------------------------
    def plotTendency(self):
        """"""
        if self.initCompleted:
            self.curve7.setData(self.listOpenInterest, pen=(255, 255, 255), name="White curve")

    #----------------------------------------------------------------------
    def plotText(self):
        lenClose = len(self.listClose)

        if lenClose >= 5:                                       # Fractal Signal
            if self.listClose[-1] > self.listClose[-2] and self.listClose[-3] > self.listClose[-2] and self.listClose[-4] > self.listClose[-2] and self.listClose[-5] > self.listClose[-2] and self.listfastEMA[-1] > self.listslowEMA[-1]:
                ## Draw an arrowhead next to the text box
                # self.pw2.removeItem(self.arrow)
                self.arrow = pg.ArrowItem(pos=(lenClose-1, self.listLow[-1]), angle=90, brush=(255, 0, 0))
                self.pw2.addItem(self.arrow)
            elif self.listClose[-1] < self.listClose[-2] and self.listClose[-3] < self.listClose[-2] and self.listClose[-4] < self.listClose[-2] and self.listClose[-5] < self.listClose[-2] and self.listfastEMA[-1] < self.listslowEMA[-1]:
                ## Draw an arrowhead next to the text box
                # self.pw2.removeItem(self.arrow)
                self.arrow = pg.ArrowItem(pos=(lenClose-1, self.listHigh[-1]), angle=-90, brush=(0, 255, 0))
                self.pw2.addItem(self.arrow)

    #----------------------------------------------------------------------
    def updateMarketData(self, event):
        """更新行情"""
        data = event.dict_['data']
        symbol = data['InstrumentID']
        tick = Tick(symbol)
        tick.openPrice = data['OpenPrice']
        tick.highPrice = data['HighestPrice']
        tick.lowPrice = data['LowestPrice']
        tick.lastPrice = data['LastPrice']

        tick.volume = data['Volume']
        tick.openInterest = data['OpenInterest']

        tick.upperLimit = data['UpperLimitPrice']
        tick.lowerLimit = data['LowerLimitPrice']

        tick.time = data['UpdateTime']
        tick.ms = data['UpdateMillisec']

        tick.bidPrice1 = data['BidPrice1']
        tick.bidPrice2 = data['BidPrice2']
        tick.bidPrice3 = data['BidPrice3']
        tick.bidPrice4 = data['BidPrice4']
        tick.bidPrice5 = data['BidPrice5']

        tick.askPrice1 = data['AskPrice1']
        tick.askPrice2 = data['AskPrice2']
        tick.askPrice3 = data['AskPrice3']
        tick.askPrice4 = data['AskPrice4']
        tick.askPrice5 = data['AskPrice5']

        tick.bidVolume1 = data['BidVolume1']
        tick.bidVolume2 = data['BidVolume2']
        tick.bidVolume3 = data['BidVolume3']
        tick.bidVolume4 = data['BidVolume4']
        tick.bidVolume5 = data['BidVolume5']

        tick.askVolume1 = data['AskVolume1']
        tick.askVolume2 = data['AskVolume2']
        tick.askVolume3 = data['AskVolume3']
        tick.askVolume4 = data['AskVolume4']
        tick.askVolume5 = data['AskVolume5']

        self.onTick(tick)  # tick数据更新

        # # 将数据插入MongoDB数据库，实盘建议另开程序记录TICK数据
        # self.__recordTick(data)

    #----------------------------------------------------------------------
    def onTick(self, tick):
        """tick数据更新"""
        from datetime import time

        # 首先生成datetime.time格式的时间（便于比较）,从字符串时间转化为time格式的时间
        hh, mm, ss = tick.time.split(':')
        self.ticktime = time(int(hh), int(mm), int(ss), microsecond=tick.ms)

        # 计算tick图的相关参数
        if self.ptr == 0:
            self.fastMA = tick.lastPrice
            self.midMA = tick.lastPrice
            self.slowMA = tick.lastPrice
        else:
            self.fastMA = (1-self.tickFastAlpha) * self.fastMA + self.tickFastAlpha * tick.lastPrice
            self.midMA = (1-self.tickMidAlpha) * self.midMA + self.tickMidAlpha * tick.lastPrice
            self.slowMA = (1-self.tickSlowAlpha) * self.slowMA + self.tickSlowAlpha * tick.lastPrice
        self.listlastPrice[self.ptr] = tick.lastPrice
        self.listfastMA[self.ptr] = self.fastMA
        self.listmidMA[self.ptr] = self.midMA
        self.listslowMA[self.ptr] = self.slowMA

        self.ptr += 1
        # pprint("----------")
        # pprint(self.ptr)
        if self.ptr >= self.listlastPrice.shape[0]:
            tmp = self.listlastPrice
            self.listlastPrice = np.empty(self.listlastPrice.shape[0] * 2)
            self.listlastPrice[:tmp.shape[0]] = tmp

            tmp = self.listfastMA
            self.listfastMA = np.empty(self.listfastMA.shape[0] * 2)
            self.listfastMA[:tmp.shape[0]] = tmp

            tmp = self.listmidMA
            self.listmidMA = np.empty(self.listmidMA.shape[0] * 2)
            self.listmidMA[:tmp.shape[0]] = tmp

            tmp = self.listslowMA
            self.listslowMA = np.empty(self.listslowMA.shape[0] * 2)
            self.listslowMA[:tmp.shape[0]] = tmp

        # K线数据
        # 假设是收到的第一个TICK
        if self.barOpen == 0:
            # 初始化新的K线数据
            self.barOpen = tick.lastPrice
            self.barHigh = tick.lastPrice
            self.barLow = tick.lastPrice
            self.barClose = tick.lastPrice
            self.barTime = self.ticktime
            self.barOpenInterest = tick.openInterest
            self.onBar(self.num, self.barOpen, self.barClose, self.barLow, self.barHigh, self.barOpenInterest)
        else:
            # 如果是当前一分钟内的数据
            if self.ticktime.minute == self.barTime.minute:
                if self.ticktime.second >= 30 and self.barTime.second < 30: # 判断30秒周期K线
                    # 先保存K线收盘价
                    self.num += 1
                    self.onBar(self.num, self.barOpen, self.barClose, self.barLow, self.barHigh, self.barOpenInterest)
                    # 初始化新的K线数据
                    self.barOpen = tick.lastPrice
                    self.barHigh = tick.lastPrice
                    self.barLow = tick.lastPrice
                    self.barClose = tick.lastPrice
                    self.barTime = self.ticktime
                    self.barOpenInterest = tick.openInterest
                # 汇总TICK生成K线
                self.barHigh = max(self.barHigh, tick.lastPrice)
                self.barLow = min(self.barLow, tick.lastPrice)
                self.barClose = tick.lastPrice
                self.barTime = self.ticktime
                self.listBar.pop()
                self.listfastEMA.pop()
                self.listslowEMA.pop()
                self.listOpen.pop()
                self.listClose.pop()
                self.listHigh.pop()
                self.listLow.pop()
                self.listOpenInterest.pop()
                self.onBar(self.num, self.barOpen, self.barClose, self.barLow, self.barHigh, self.barOpenInterest)
            # 如果是新一分钟的数据
            else:
                # 先保存K线收盘价
                self.num += 1
                self.onBar(self.num, self.barOpen, self.barClose, self.barLow, self.barHigh, self.barOpenInterest)
                # 初始化新的K线数据
                self.barOpen = tick.lastPrice
                self.barHigh = tick.lastPrice
                self.barLow = tick.lastPrice
                self.barClose = tick.lastPrice
                self.barTime = self.ticktime
                self.barOpenInterest = tick.openInterest

    #----------------------------------------------------------------------
    def onBar(self, n, o, c, l, h, oi):
        self.listBar.append((n, o, c, l, h))
        self.listOpen.append(o)
        self.listClose.append(c)
        self.listHigh.append(h)
        self.listLow.append(l)
        self.listOpenInterest.append(oi)

        #计算K线图EMA均线
        if self.fastEMA:
            self.fastEMA = c*self.EMAFastAlpha + self.fastEMA*(1-self.EMAFastAlpha)
            self.slowEMA = c*self.EMASlowAlpha + self.slowEMA*(1-self.EMASlowAlpha)
        else:
            self.fastEMA = c
            self.slowEMA = c
        self.listfastEMA.append(self.fastEMA)
        self.listslowEMA.append(self.slowEMA)

        # 调用画图函数
        self.plotTick()      # tick图
        self.plotKline()     # K线图
        self.plotTendency()  # K线副图，持仓量

    #----------------------------------------------------------------------
    def __connectMongo(self):
        """连接MongoDB数据库"""
        try:
            self.__mongoConnection = MongoClient()
            self.__mongoConnected = True
            self.__mongoTickDB = self.__mongoConnection['TickDB']
        except ConnectionFailure:
            pass

    #----------------------------------------------------------------------
    def __recordTick(self, data):
        """将Tick数据插入到MongoDB中"""
        if self.__mongoConnected:
            symbol = data['InstrumentID']
            data['date'] = self.today
            self.__mongoTickDB[symbol].insert(data)

    #----------------------------------------------------------------------
    def loadTick(self, symbol, startDate, endDate=None):
        """从MongoDB中读取Tick数据"""
        if self.__mongoConnected:
            collection = self.__mongoTickDB[symbol]

            # 如果输入了读取TICK的最后日期
            if endDate:
                cx = collection.find({'date': {'$gte': startDate, '$lte': endDate}})
            else:
                cx = collection.find({'date': {'$gte': startDate}})
            return cx
        else:
            return None

    #----------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.signal.connect(self.updateMarketData)
        self.__eventEngine.register(EVENT_MARKETDATA, self.signal.emit)



    
    
