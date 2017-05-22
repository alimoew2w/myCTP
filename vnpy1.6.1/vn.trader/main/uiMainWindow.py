# encoding: UTF-8

import psutil

from gateway import GATEWAY_DICT
from uiBasicWidget import *
from ctaStrategy.uiCtaWidget import CtaEngineManager
from dataRecorder.uiDrWidget import DrEngineManager
################################################################################
## william
from dataRecorder.uiDrWidget import BarEngineManager

from riskManager.uiRmWidget import RmEngineManager

from datetime import datetime

########################################################################
class MainWindow(QtGui.QMainWindow):
    """主窗口"""
    signalStatusBar = QtCore.pyqtSignal(type(Event()))

    #----------------------------------------------------------------------
    def __init__(self, mainEngine, eventEngine):
        """Constructor"""
        super(MainWindow, self).__init__()
        
        self.mainEngine = mainEngine
        self.eventEngine = eventEngine
        
        self.widgetDict = {}    # 用来保存子窗口的字典
        
        self.initUi()
        self.loadWindowSettings('custom')
        
    #----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        self.setWindowTitle('VnTrader')
        self.initCentral()
        self.initMenu()
        self.initStatusBar()
        
    #----------------------------------------------------------------------
    def initCentral(self):
        """初始化中心区域"""
        widgetMarketM, dockMarketM = self.createDock(MarketMonitor, vtText.MARKET_DATA, QtCore.Qt.RightDockWidgetArea)
        widgetLogM, dockLogM = self.createDock(LogMonitor, vtText.LOG, QtCore.Qt.BottomDockWidgetArea)
        widgetErrorM, dockErrorM = self.createDock(ErrorMonitor, vtText.ERROR, QtCore.Qt.BottomDockWidgetArea)
        widgetTradeM, dockTradeM = self.createDock(TradeMonitor, vtText.TRADE, QtCore.Qt.BottomDockWidgetArea)
        widgetOrderM, dockOrderM = self.createDock(OrderMonitor, vtText.ORDER, QtCore.Qt.RightDockWidgetArea)
        widgetPositionM, dockPositionM = self.createDock(PositionMonitor, vtText.POSITION, QtCore.Qt.BottomDockWidgetArea)
        widgetAccountM, dockAccountM = self.createDock(AccountMonitor, vtText.ACCOUNT, QtCore.Qt.BottomDockWidgetArea)
        widgetTradingW, dockTradingW = self.createDock(TradingWidget, vtText.TRADING, QtCore.Qt.LeftDockWidgetArea)
    
        self.tabifyDockWidget(dockTradeM, dockErrorM)
        self.tabifyDockWidget(dockTradeM, dockLogM)
        self.tabifyDockWidget(dockPositionM, dockAccountM)
    
        dockTradeM.raise_()
        dockPositionM.raise_()
    
        # 连接组件之间的信号
        widgetPositionM.itemDoubleClicked.connect(widgetTradingW.closePosition)
        
        # 保存默认设置
        self.saveWindowSettings('default')
    
    ############################################################################
    ## william
    ## 菜单栏
    ############################################################################
    #----------------------------------------------------------------------
    def initMenu(self):
        """初始化菜单"""
        # 创建菜单
        menubar = self.menuBar()
        
        # 设计为只显示存在的接口
        sysMenu = menubar.addMenu(vtText.SYSTEM)

        ########################################################################
        ## william
        ## Futures
        ########################################################################
        for gatewayModule in GATEWAY_DICT.values():
            if gatewayModule.gatewayType == GATEWAYTYPE_FUTURES:
                self.addConnectAction(sysMenu, gatewayModule.gatewayName, 
                                      gatewayModule.gatewayDisplayName)
        
        ########################################################################
        ## william
        ## Equity
        ########################################################################
        sysMenu.addSeparator()
        for gatewayModule in GATEWAY_DICT.values():
            if gatewayModule.gatewayType == GATEWAYTYPE_EQUITY:
                self.addConnectAction(sysMenu, gatewayModule.gatewayName, 
                                      gatewayModule.gatewayDisplayName)  

        ########################################################################
        ## william
        ## International
        ########################################################################
        sysMenu.addSeparator()
        for gatewayModule in GATEWAY_DICT.values():
            if gatewayModule.gatewayType == GATEWAYTYPE_INTERNATIONAL:
                self.addConnectAction(sysMenu, gatewayModule.gatewayName, 
                                      gatewayModule.gatewayDisplayName)  

        ########################################################################
        ## william
        ## Bit Coin
        ########################################################################
        sysMenu.addSeparator()
        for gatewayModule in GATEWAY_DICT.values():
            if gatewayModule.gatewayType == GATEWAYTYPE_BTC:
                self.addConnectAction(sysMenu, gatewayModule.gatewayName, 
                                      gatewayModule.gatewayDisplayName)          

        ########################################################################
        ## william
        ## Wind 万得数据
        ########################################################################
        sysMenu.addSeparator()
        for gatewayModule in GATEWAY_DICT.values():
            if gatewayModule.gatewayType == GATEWAYTYPE_DATA:
                self.addConnectAction(sysMenu, gatewayModule.gatewayName, 
                                      gatewayModule.gatewayDisplayName)          
        
        ########################################################################
        ## william
        ## DataBase:CONNECT_DATABASE
        ## 1.MongoDB:==> CONNECT_DATABASE_Mongo = u'连接 MongoDB'
        ## 2.MySQL  :==> CONNECT_DATABASE_MySQL = u'连接 MySQL'
        ########################################################################
        """
        sysMenu.addSeparator()
        sysMenu.addAction(self.createAction(vtText.CONNECT_DATABASE, self.mainEngine.dbConnect))
        """
        sysMenu.addSeparator()
        sysMenu.addAction(self.createAction(vtText.CONNECT_DATABASE_Mongo, self.mainEngine.dbMongoConnect))

        ########################################################################
        ## william
        ## 连接 MySQL
        ## sysMenu.addSeparator()
        sysMenu.addAction(self.createAction(vtText.CONNECT_DATABASE_MySQL, self.mainEngine.dbMySQLConnect))
        ########################################################################

        ########################################################################
        ## william
        ## '退出'按钮
        sysMenu.addSeparator()
        sysMenu.addAction(self.createAction(vtText.EXIT, self.close))
        ########################################################################

        ########################################################################
        # 功能应用
        ########################################################################
        functionMenu = menubar.addMenu(vtText.APPLICATION)
        ## 1. 合约查询
        functionMenu.addAction(self.createAction(vtText.CONTRACT_SEARCH, self.openContract))

        ## 2. 行情记录
        functionMenu.addAction(self.createAction(vtText.DATA_RECORDER, self.openDr))

        ## 3. 风控管理
        functionMenu.addAction(self.createAction(vtText.RISK_MANAGER, self.openRm))
 
        ########################################################################
        ## william
        ## 4. K 线
        functionMenu.addAction(self.createAction(u'图形', self.openBar))       

        ########################################################################
        ## william
        ## 策略
        # 算法相关
        ## UI 界面从这里启动策略
        ########################################################################
        strategyMenu = menubar.addMenu(vtText.STRATEGY)
        strategyMenu.addAction(self.createAction(vtText.CTA_STRATEGY, self.openCta))
        
        ########################################################################
        # 帮助
        ########################################################################
        helpMenu = menubar.addMenu(vtText.HELP)
        helpMenu.addAction(self.createAction(vtText.RESTORE, self.restoreWindow))
        helpMenu.addAction(self.createAction(vtText.ABOUT, self.openAbout))
        helpMenu.addAction(self.createAction(vtText.TEST, self.test))
    
    #----------------------------------------------------------------------
    def initStatusBar(self):
        """初始化状态栏"""
        self.statusLabel = QtGui.QLabel()
        self.statusLabel.setAlignment(QtCore.Qt.AlignLeft)
        
        self.statusBar().addPermanentWidget(self.statusLabel)
        self.statusLabel.setText(self.getCpuMemory())
        
        self.sbCount = 0
        ########################################################################
        ## william
        # self.sbTrigger = 10     # 10秒刷新一次
        self.sbTrigger = 1    # 10秒刷新一次
        self.signalStatusBar.connect(self.updateStatusBar)
        self.eventEngine.register(EVENT_TIMER, self.signalStatusBar.emit)
    
    ############################################################################
    ## william
    ## CPU Information
    ############################################################################
    #----------------------------------------------------------------------
    def updateStatusBar(self, event):
        """在状态栏更新CPU和内存信息"""
        self.sbCount += 1
        
        if self.sbCount == self.sbTrigger:
            self.sbCount = 0
            self.statusLabel.setText(self.getCpuMemory())
    
    #----------------------------------------------------------------------
    def getCpuMemory(self):
        """获取CPU和内存状态信息"""
        cpuPercent = psutil.cpu_percent()
        memoryPercent = psutil.virtual_memory().percent
        return vtText.CPU_MEMORY_INFO.format(currTime = datetime.now().strftime("%H:%M:%S"), cpu=cpuPercent, memory=memoryPercent)
        
    ############################################################################
    ## william
    ## 连接 API
    ## 显示的连接 API 名称
    ############################################################################
    #----------------------------------------------------------------------
    def addConnectAction(self, menu, gatewayName, displayName=''):
        """增加连接功能"""
        if gatewayName not in self.mainEngine.getAllGatewayNames():
            return
        
        def connect():
            self.mainEngine.connect(gatewayName)
        
        if not displayName:
            displayName = gatewayName
        displayName = gatewayName
        ## 显示的连接 API 名称
        actionName = vtText.CONNECT + displayName
        
        menu.addAction(self.createAction(actionName, connect))
    
    ############################################################################
    ## william
    ## 建立 API 连接
    ############################################################################
    #----------------------------------------------------------------------
    def createAction(self, actionName, function):
        """创建操作功能"""
        action = QtGui.QAction(actionName, self)
        action.triggered.connect(function)
        return action
        
    #----------------------------------------------------------------------
    def test(self):
        """测试按钮用的函数"""
        # 有需要使用手动触发的测试函数可以写在这里
        pass

    #----------------------------------------------------------------------
    def openAbout(self):
        """打开关于"""
        try:
            self.widgetDict['aboutW'].show()
        except KeyError:
            self.widgetDict['aboutW'] = AboutWidget(self)
            self.widgetDict['aboutW'].show()
    
    #----------------------------------------------------------------------
    def openContract(self):
        """打开合约查询"""
        try:
            self.widgetDict['contractM'].show()
        except KeyError:
            self.widgetDict['contractM'] = ContractManager(self.mainEngine)
            self.widgetDict['contractM'].show()
            
    ############################################################################
    ## william
    ## 启动 CTA 策略的菜单
    ############################################################################
    #---------------------------------------------------------------------------
    def openCta(self):
        """打开CTA组件"""
        try:
            self.widgetDict['ctaM'].showMaximized()
        except KeyError:
            self.widgetDict['ctaM'] = CtaEngineManager(self.mainEngine.ctaEngine, self.eventEngine)
            self.widgetDict['ctaM'].showMaximized()
            
    #----------------------------------------------------------------------
    def openDr(self):
        """打开行情数据记录组件"""
        try:
            self.widgetDict['drM'].showMaximized()
        except KeyError:
            self.widgetDict['drM'] = DrEngineManager(self.mainEngine.drEngine, self.eventEngine)
            self.widgetDict['drM'].showMaximized()
            
    #----------------------------------------------------------------------
    def openRm(self):
        """打开组件"""
        try:
            self.widgetDict['rmM'].show()
        except KeyError:
            self.widgetDict['rmM'] = RmEngineManager(self.mainEngine.rmEngine, self.eventEngine)
            self.widgetDict['rmM'].show()      

    ############################################################################
    ## william
    ## 图形
    #----------------------------------------------------------------------
    def openBar(self):
        """打开组件"""
        try:
            self.widgetDict['barM'].show()
        except KeyError:
            self.widgetDict['barM'] = BarEngineManager(self.mainEngine.drEngine, self.eventEngine)
            self.widgetDict['barM'].show()      
    

    #----------------------------------------------------------------------
    def closeEvent(self, event):
        """关闭事件"""
        reply = QtGui.QMessageBox.question(self, vtText.EXIT,
                                           vtText.CONFIRM_EXIT, QtGui.QMessageBox.Yes | 
                                           QtGui.QMessageBox.No, QtGui.QMessageBox.No)

        if reply == QtGui.QMessageBox.Yes: 
            for widget in self.widgetDict.values():
                widget.close()
            self.saveWindowSettings('custom')
            
            self.mainEngine.exit()
            event.accept()
        else:
            event.ignore()
            
    #----------------------------------------------------------------------
    def createDock(self, widgetClass, widgetName, widgetArea):
        """创建停靠组件"""
        widget = widgetClass(self.mainEngine, self.eventEngine)
        dock = QtGui.QDockWidget(widgetName)
        dock.setWidget(widget)
        dock.setObjectName(widgetName)
        dock.setFeatures(dock.DockWidgetFloatable|dock.DockWidgetMovable)
        self.addDockWidget(widgetArea, dock)
        return widget, dock
    
    #----------------------------------------------------------------------
    def saveWindowSettings(self, settingName):
        """保存窗口设置"""
        settings = QtCore.QSettings('vn.trader', settingName)
        settings.setValue('state', self.saveState())
        settings.setValue('geometry', self.saveGeometry())
        
    #----------------------------------------------------------------------
    def loadWindowSettings(self, settingName):
        """载入窗口设置"""
        settings = QtCore.QSettings('vn.trader', settingName)
        # 这里由于PyQt4的版本不同，settings.value('state')调用返回的结果可能是：
        # 1. None（初次调用，注册表里无相应记录，因此为空）
        # 2. QByteArray（比较新的PyQt4）
        # 3. QVariant（以下代码正确执行所需的返回结果）
        # 所以为了兼容考虑，这里加了一个try...except，如果是1、2的情况就pass
        # 可能导致主界面的设置无法载入（每次退出时的保存其实是成功了）
        try:
            self.restoreState(settings.value('state').toByteArray())
            self.restoreGeometry(settings.value('geometry').toByteArray())    
        except AttributeError:
            pass
        
    #----------------------------------------------------------------------
    def restoreWindow(self):
        """还原默认窗口设置（还原停靠组件位置）"""
        self.loadWindowSettings('default')
        self.showMaximized()


########################################################################
class AboutWidget(QtGui.QDialog):
    """显示关于信息"""

    #----------------------------------------------------------------------
    def __init__(self, parent=None):
        """Constructor"""
        super(AboutWidget, self).__init__(parent)

        self.initUi()

    #----------------------------------------------------------------------
    def initUi(self):
        """"""
        self.setWindowTitle(vtText.ABOUT + 'VnTrader')

        text = u"""
            Developed by Traders, for Traders.

            License：MIT
            
            Website：www.vnpy.org

            Github：www.github.com/vnpy/vnpy
            
            """

        label = QtGui.QLabel()
        label.setText(text)
        label.setMinimumWidth(500)

        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(label)

        self.setLayout(vbox)
