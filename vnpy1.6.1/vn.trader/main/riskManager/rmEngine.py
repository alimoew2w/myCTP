# encoding: UTF-8

'''
本文件中实现了风控引擎，用于提供一系列常用的风控功能：
1. 委托流控（单位时间内最大允许发出的委托数量）
2. 总成交限制（每日总成交数量限制）
3. 单笔委托的委托数量控制
'''
from __future__ import division

import json
import os
import platform

from eventEngine import *
from vtConstant import *
from vtGateway import VtLogData


########################################################################
class RmEngine(object):
    """风控引擎"""
    settingFileName = 'RM_setting.json'
    path = os.path.abspath(os.path.dirname(__file__))
    settingFileName = os.path.join(path, settingFileName)

    name = u'风控模块'

    #----------------------------------------------------------------------
    def __init__(self, mainEngine, eventEngine):
        """Constructor"""
        self.mainEngine = mainEngine
        self.eventEngine = eventEngine

        # 是否启动风控
        self.active = False

        # 流控相关
        self.orderFlowCount = EMPTY_INT     # 单位时间内委托计数
        self.orderFlowLimit = EMPTY_INT     # 委托限制
        self.orderFlowClear = EMPTY_INT     # 计数清空时间（秒）
        self.orderFlowTimer = EMPTY_INT     # 计数清空时间计时

        # 单笔委托相关
        self.orderSizeLimit = EMPTY_INT     # 单笔委托最大限制

        # 成交统计相关
        self.tradeCount = EMPTY_INT         # 当日成交合约数量统计
        self.tradeLimit = EMPTY_INT         # 当日成交合约数量限制

        # 单品种撤单统计
        self.orderCancelLimit = EMPTY_INT   # 撤单总次数限制
        self.orderCancelDict = {}           # 单一合约对应撤单次数的字典

        # 活动合约相关
        self.workingOrderLimit = EMPTY_INT  # 活动合约最大限制

        ########################################################################
        ## william
        self.marginRatio = EMPTY_FLOAT
        self.marginRatioLimit = EMPTY_FLOAT # 保证金与可用资金的比例上限

        self.loadSetting()
        self.registerEvent()

    #----------------------------------------------------------------------
    def loadSetting(self):
        """读取配置"""
        with open(self.settingFileName) as f:
            d = json.load(f)

            ####################################################################
            ## william
            ## 把风控模块设置为激活状态
            # 设置风控参数
            self.active = d['active']

            self.orderFlowLimit = d['orderFlowLimit']
            self.orderFlowClear = d['orderFlowClear']

            self.orderSizeLimit = d['orderSizeLimit']

            self.tradeLimit = d['tradeLimit']

            self.workingOrderLimit = d['workingOrderLimit']

            self.orderCancelLimit = d['orderCancelLimit']

            self.marginRatioLimit = d['marginRatioLimit']

    #----------------------------------------------------------------------
    def saveSetting(self):
        """保存风控参数"""
        with open(self.settingFileName, 'w') as f:
            # 保存风控参数
            d = {}

            d['active'] = self.active

            d['orderFlowLimit'] = self.orderFlowLimit
            d['orderFlowClear'] = self.orderFlowClear

            d['orderSizeLimit'] = self.orderSizeLimit

            d['tradeLimit'] = self.tradeLimit

            d['workingOrderLimit'] = self.workingOrderLimit

            d['orderCancelLimit'] = self.orderCancelLimit

            d['marginRatioLimit'] = self.marginRatioLimit

            # 写入json
            jsonD = json.dumps(d, indent=4)
            f.write(jsonD)

    #---------------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.eventEngine.register(EVENT_TRADE, self.updateTrade)
        self.eventEngine.register(EVENT_TIMER, self.updateTimer)
        self.eventEngine.register(EVENT_ORDER, self.updateOrder)
        
    #---------------------------------------------------------------------------
    def updateOrder(self, event):
        """更新成交数据"""
        # 只需要统计撤单成功的委托
        order = event.dict_['data']
        if order.status != STATUS_CANCELLED:
            return
        
        if order.symbol not in self.orderCancelDict:
            self.orderCancelDict[order.symbol] = 1
        else:
            self.orderCancelDict[order.symbol] += 1

    #----------------------------------------------------------------------
    def updateTrade(self, event):
        """更新成交数据"""
        trade = event.dict_['data']
        self.tradeCount += trade.volume

    #----------------------------------------------------------------------
    def updateTimer(self, event):
        """更新定时器"""
        self.orderFlowTimer += 1

        # 如果计时超过了流控清空的时间间隔，则执行清空
        if self.orderFlowTimer >= self.orderFlowClear:
            self.orderFlowCount = 0
            self.orderFlowTimer = 0

    #----------------------------------------------------------------------
    def writeRiskLog(self, content):
        """快速发出日志事件"""
        # 发出报警提示音

        if platform.uname() == 'Windows':
            import winsound
            winsound.PlaySound("SystemHand", winsound.SND_ASYNC)

        # 发出日志事件
        log = VtLogData()
        log.logContent = content
        log.gatewayName = self.name
        event = Event(type_=EVENT_LOG)
        event.dict_['data'] = log
        self.eventEngine.put(event)

    ############################################################################
    ## william
    ## 当策略下单时, 需要优先检查是否符合风控政策.
    ############################################################################
    #---------------------------------------------------------------------------
    def checkRisk(self, orderReq):
        """检查风险"""
        # 如果没有启动风控检查，则直接返回成功
        if not self.active:
            return True

        ## =====================================================================
        # 检查委托数量
        if orderReq.volume > self.orderSizeLimit:
            print "\n"+"#"*80
            print '单笔委托数量%s，超过限制%s' %(orderReq.volume, self.orderSizeLimit)
            self.writeRiskLog(u'单笔委托数量%s，超过限制%s'
                              %(orderReq.volume, self.orderSizeLimit))
            print "#"*80+"\n"
            return False

        ## =====================================================================
        # 检查成交合约量
        if self.tradeCount >= self.tradeLimit:
            print "\n"+"#"*80
            print '今日总成交合约数量%s，超过限制%s' %(self.tradeCount, self.tradeLimit)
            self.writeRiskLog(u'今日总成交合约数量%s，超过限制%s'
                              %(self.tradeCount, self.tradeLimit))
            print "#"*80+"\n"
            return False

        ## =====================================================================
        # 检查流控
        if self.orderFlowCount >= self.orderFlowLimit:
            print "\n"+"#"*80
            print '委托流数量%s，超过限制每%s秒%s' %(self.orderFlowCount, self.orderFlowClear, self.orderFlowLimit)
            self.writeRiskLog(u'委托流数量%s，超过限制每%s秒%s'
                              %(self.orderFlowCount, self.orderFlowClear, self.orderFlowLimit))
            print "#"*80+"\n"
            return False

        ## =====================================================================
        # 检查总活动合约
        workingOrderCount = len(self.mainEngine.getAllWorkingOrders())
        if workingOrderCount >= self.workingOrderLimit:
            print "\n"+"#"*80
            print '当前活动委托数量%s，超过限制%s' %(workingOrderCount, self.workingOrderLimit)
            self.writeRiskLog(u'当前活动委托数量%s，超过限制%s'
                              %(workingOrderCount, self.workingOrderLimit))
            print "#"*80+"\n"
            return False

        ## =====================================================================
        # 检查撤单次数
        if orderReq.symbol in self.orderCancelDict and self.orderCancelDict[orderReq.symbol] >= self.orderCancelLimit:
            print "\n"+"#"*80
            print '当日%s撤单次数%s，超过限制%s' %(orderReq.symbol, self.orderCancelDict[orderReq.symbol], self.orderCancelLimit)
            self.writeRiskLog(u'当日%s撤单次数%s，超过限制%s'
                              %(orderReq.symbol, self.orderCancelDict[orderReq.symbol], self.orderCancelLimit))
            print "#"*80+"\n"
            return False
        
        ## =====================================================================
        # 对于通过风控的委托，增加流控计数
        self.orderFlowCount += 1

        ## =====================================================================
        ## william
        ## 保证金与可用资金的比例上限
        self.marginRatio = self.mainEngine.drEngine.accountInfo.margin / self.mainEngine.drEngine.accountInfo.available
        # print 'orderReq'
        # print orderReq.__dict__
        #  and orderReq.offset == u'开仓'
        ########################################################################
        ## william
        ## 对于开仓的订单, 需要检查以下两项风控:
        ## 1. 保证金比例
        ## 2. 开仓, 如果是平仓, 就不需要了
        if self.marginRatio > self.marginRatioLimit and orderReq.offset == u'开仓':
            print "\n"+"#"*80
            print '当前账户 %s 保证金比例 %0.2f 超过 %0.2f' %(self.name, self.marginRatio, self.marginRatioLimit)
            self.writeRiskLog(u'当前账户保证金比例 %0.2f 超过 %0.2f' %(self.marginRatio, self.marginRatioLimit))
            print "#"*80+"\n"
            return False

        return True

    #----------------------------------------------------------------------
    def clearOrderFlowCount(self):
        """清空流控计数"""
        self.orderFlowCount = 0
        self.writeRiskLog(u'清空流控计数')

    #----------------------------------------------------------------------
    def clearTradeCount(self):
        """清空成交数量计数"""
        self.tradeCount = 0
        self.writeRiskLog(u'清空总成交计数')

    #----------------------------------------------------------------------
    def setOrderFlowLimit(self, n):
        """设置流控限制"""
        self.orderFlowLimit = n

    #----------------------------------------------------------------------
    def setOrderFlowClear(self, n):
        """设置流控清空时间"""
        self.orderFlowClear = n

    #----------------------------------------------------------------------
    def setOrderSizeLimit(self, n):
        """设置委托最大限制"""
        self.orderSizeLimit = n

    #----------------------------------------------------------------------
    def setTradeLimit(self, n):
        """设置成交限制"""
        self.tradeLimit = n

    #----------------------------------------------------------------------
    def setWorkingOrderLimit(self, n):
        """设置活动合约限制"""
        self.workingOrderLimit = n

    #----------------------------------------------------------------------
    def setOrderCancelLimit(self, n):
        """设置单合约撤单次数上限"""
        self.orderCancelLimit = n

    #---------------------------------------------------------------------------
    ############################################################################
    ## william
    def setMarginRatioLimit(self, n):
        """账户保证金比例上限"""
        self.marginRatioLimit = n

    #----------------------------------------------------------------------
    def switchEngineStatus(self):
        """开关风控引擎"""
        self.active = not self.active

        if self.active:
            self.writeRiskLog(u'风险管理功能启动')
        else:
            self.writeRiskLog(u'风险管理功能停止')
