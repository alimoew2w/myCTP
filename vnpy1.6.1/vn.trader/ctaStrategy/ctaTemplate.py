# encoding: UTF-8

'''
本文件包含了CTA引擎中的策略开发用模板，开发策略时需要继承CtaTemplate类。
'''
from __future__ import division
import os
import sys

from ctaBase import *
from vtConstant import *

## 发送邮件通知
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import codecs
from tabulate import tabulate

import numpy as np
import pandas as pd
from pandas.io import sql
from datetime import *
import time
from eventType import *


########################################################################
class CtaTemplate(object):
    """CTA策略模板"""
    
    # 策略类的名称和作者
    name = EMPTY_UNICODE           # 策略实例名称
    className = 'CtaTemplate'
    strategyID = EMPTY_STRING      ## william:暂时与 className 一样
    author = EMPTY_UNICODE
    
    # MongoDB数据库的名称，K线数据库默认为1分钟
    tickDbName = TICK_DB_NAME
    barDbName = MINUTE_DB_NAME
    ############################################################################
    ## william
    ## 多合约组合
    vtSymbol = EMPTY_STRING     
    productClass = EMPTY_STRING    # 产品类型（只有IB接口需要）
    currency = EMPTY_STRING        # 货币（只有IB接口需要）
    
    ## -------------------------------------------------------------------------
    ## 各种控制条件
    ## 策略的基本变量，由引擎管理
    inited         = False                    # 是否进行了初始化
    trading        = False                    # 是否启动交易，由引擎管理
    tradingOpen    = False                    # 开盘启动交易
    tradingClose   = False                    # 收盘开启交易
    pos            = 0                        # 持仓情况
    sendMailStatus = False                    # 是否已经发送邮件
    tradingClosePositionAll    = False        # 是否强制平仓所有合约
    tradingClosePositionSymbol = False        # 是否强制平仓单个合约
    ## -------------------------------------------------------------------------

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol']
    
    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos']

    ## -------------------------------------------------------------------------
    ## 从 TickData 提取的字段
    ## -------------------------------------------------------------------------
    tickFileds = ['symbol', 'vtSymbol', 'lastPrice', 'bidPrice1', 'askPrice1',
                  'bidVolume1', 'askVolume1', 'upperLimit', 'lowerLimit']
    lastTickData = {}                  # 保留最新的价格数据
    tickTimer    = {}                  # 计时器, 用于记录单个合约发单的间隔时间
    vtSymbolList = []                  # 策略的所有合约存放在这里
    ## -------------------------------------------------------------------------

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        self.ctaEngine = ctaEngine

        ## =====================================================================
        ## 把　MySQL 数据库的　TradingDay　调整为　datetime 格式
        conn = self.ctaEngine.mainEngine.dbMySQLConnect(self.ctaEngine.mainEngine.dataBase)
        cursor = conn.cursor()
        cursor.execute("""
                        ALTER TABLE failedInfo
                        MODIFY TradingDay date not null;
                       """)
        cursor.execute("""
                        ALTER TABLE positionInfo
                        MODIFY TradingDay date not null;
                       """)
        try:
            cursor.execute("""ALTER TABLE positionInfo DROP primary key""")
        except:
            pass
        cursor.execute("""
                        ALTER TABLE positionInfo 
                        ADD PRIMARY key (strategyID,InstrumentID,TradingDay,direction);
                       """)
        conn.commit()
        conn.close()        
        ## =====================================================================

        # 设置策略的参数
        if setting:
            d = self.__dict__
            for key in self.paramList:
                if key in setting:
                    d[key] = setting[key]
    
    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        raise NotImplementedError
    
    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        raise NotImplementedError
    
    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        raise NotImplementedError

    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        raise NotImplementedError

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        raise NotImplementedError
    
    #----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        raise NotImplementedError
    
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        raise NotImplementedError
    
    #----------------------------------------------------------------------
    def buy(self, vtSymbol, price, volume, stop=False):
        """买开"""
        return self.sendOrder(vtSymbol, CTAORDER_BUY, price, volume, stop)
    
    #----------------------------------------------------------------------
    def sell(self, vtSymbol, price, volume, stop=False):
        """卖平"""
        return self.sendOrder(vtSymbol, CTAORDER_SELL, price, volume, stop)       

    #----------------------------------------------------------------------
    def short(self, vtSymbol, price, volume, stop=False):
        """卖开"""
        return self.sendOrder(vtSymbol, CTAORDER_SHORT, price, volume, stop)          
 
    #----------------------------------------------------------------------
    def cover(self, vtSymbol, price, volume, stop=False):
        """买平"""
        return self.sendOrder(vtSymbol, CTAORDER_COVER, price, volume, stop)
        
    #----------------------------------------------------------------------
    def sendOrder(self, vtSymbol, orderType, price, volume, stop=False):
        """发送委托"""
        if self.trading:
            # 如果stop为True，则意味着发本地停止单
            if stop:
                vtOrderID = self.ctaEngine.sendStopOrder(vtSymbol, orderType, price, volume, self)
            else:
                vtOrderID = self.ctaEngine.sendOrder(vtSymbol, orderType, price, volume, self) 
            return vtOrderID
        else:
            # 交易停止时发单返回空字符串
            return ''        
        
    #----------------------------------------------------------------------
    def cancelOrder(self, vtOrderID):
        """撤单"""
        # 如果发单号为空字符串，则不进行后续操作
        if not vtOrderID:
            return
        
        if STOPORDERPREFIX in vtOrderID:
            self.ctaEngine.cancelStopOrder(vtOrderID)
        else:
            self.ctaEngine.cancelOrder(vtOrderID)

        ## ---------------------------------------------------------------------
        ## william
        ## ---------------------------------------------------------------------
        # time.sleep(0)
    
    #----------------------------------------------------------------------
    def insertTick(self, tick):
        """向数据库中插入tick数据"""
        self.ctaEngine.insertData(self.tickDbName, self.vtSymbol, tick)
    
    #----------------------------------------------------------------------
    def insertBar(self, bar):
        """向数据库中插入bar数据"""
        self.ctaEngine.insertData(self.barDbName, self.vtSymbol, bar)
        
    #----------------------------------------------------------------------
    def loadTick(self, days):
        """读取tick数据"""
        return self.ctaEngine.loadTick(self.tickDbName, self.vtSymbol, days)
    
    #----------------------------------------------------------------------
    def loadBar(self, days):
        """读取bar数据"""
        return self.ctaEngine.loadBar(self.barDbName, self.vtSymbol, days)
    
    #----------------------------------------------------------------------
    def writeCtaLog(self, content):
        """记录CTA日志"""
        content = self.name + ':' + content
        self.ctaEngine.writeCtaLog(content)
        
    #---------------------------------------------------------------------------
    def putEvent(self):
        """发出策略状态变化事件"""
        self.ctaEngine.putStrategyEvent(self.name)
        
    #---------------------------------------------------------------------------
    def getEngineType(self):
        """查询当前运行的环境"""
        return self.ctaEngine.engineType
    
    ############################################################################
    ## 收盘发送交易播报的邮件通知
    ############################################################################
    def sendMail(self, event):
        """发送邮件通知给：汉云交易员"""
        if datetime.now().strftime('%H:%M:%S') == '15:05:00' and self.trading:
            self.sendMailStatus = True
        ## -----------  ----------------------------------------------------------
        if self.sendMailStatus and self.trading:
            self.sendMailStatus = False
            ## -----------------------------------------------------------------
            ## -----------------------------------------------------------------
            self.ctaEngine.mainEngine.drEngine.getIndicatorInfo(dbName = self.ctaEngine.mainEngine.dataBase,
                                                                initCapital = self.ctaEngine.mainEngine.initCapital,
                                                                flowCapitalPre = self.ctaEngine.mainEngine.flowCapitalPre,
                                                                flowCapitalToday = self.ctaEngine.mainEngine.flowCapitalToday)
            ## -----------------------------------------------------------------
            ## -----------------------------------------------------------------------------
            sender = self.strategyID + '@hicloud.com'
            ## 公司内部人员
            receiversMain = self.ctaEngine.mainEngine.mailReceiverMain
            ## 其他人员
            receiversOthers = self.ctaEngine.mainEngine.mailReceiverOthers
            ## 抄送
            # ccReceivers = self.ctaEngine.mainEngine.mailCC

            # 三个参数：第一个为文本内容，第二个 plain 设置文本格式，第三个 utf-8 设置编码
            ## 内容，例如
            # message = MIMEText('Python 邮件发送测试...', 'plain', 'utf-8')
            ## -----------------------------------------------------------------------------
            tempFile = os.path.join('/tmp',('tradingRecord_' + self.strategyID + '.txt'))
            with codecs.open(tempFile, "w", "utf-8") as f:
                # f.write('{0}'.format(40*'='))
                f.write('{0}'.format('\n' + 20 * '#'))
                f.write('{0}'.format(u'\n## 策略信息'))
                f.write('{0}'.format('\n' + 20 * '#'))
                f.write('{0}'.format('\n[TradingDay]: ' + self.ctaEngine.tradingDate.strftime('%Y-%m-%d')))
                f.write('{0}'.format('\n[UpdateTime]: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                f.write('{0}'.format('\n[StrategyID]: ' + self.strategyID))
                f.write('{0}'.format('\n[TraderName]: ' + self.author))
                f.write('{0}'.format('\n' + 100*'-' + '\n'))
                ## -------------------------------------------------------------------------
                f.write('{0}'.format('\n' + 20 * '#'))
                f.write('{0}'.format(u'\n## 基金净值'))
                f.write('{0}'.format('\n' + 20 * '#'))
                f.write('{0}'.format('\n' + 100*'-') + '\n')
                f.write(tabulate(self.ctaEngine.mainEngine.drEngine.accountBalance.transpose(),
                                    headers = ['Index','Value'], tablefmt = 'rst'))
                f.write('{0}'.format('\n' + 100*'-') + '\n')
                ## -------------------------------------------------------------------------
                f.write('{0}'.format('\n' + 20 * '#'))
                f.write('{0}'.format(u'\n## 基金持仓'))
                f.write('{0}'.format('\n' + 20 * '#'))
                f.write('{0}'.format('\n' + 100*'-') + '\n')
                f.write('{0}'.format(self.ctaEngine.mainEngine.drEngine.accountPosition))
                f.write('{0}'.format('\n' + 100*'-') + '\n')
                ## -------------------------------------------------------------------------
                f.write('{0}'.format('\n' + 20 * '#'))
                f.write('{0}'.format('\n## 当日已交易'))
                f.write('{0}'.format('\n' + 20 * '#'))
                f.write('{0}'.format('\n' + 100*'-') + '\n')
                if len(self.tradingInfo) != 0:
                    tempTradingInfo = self.tradingInfo
                    tempTradingInfo.index += 1
                    f.write('{0}'.format(tempTradingInfo))
                f.write('{0}'.format('\n' + 100*'-') + '\n')
                ## -------------------------------------------------------------------------
                f.write('{0}'.format('\n' + 20 * '#'))
                f.write('{0}'.format('\n## 当日未交易'))
                f.write('{0}'.format('\n' + 20 * '#'))
                f.write('{0}'.format('\n' + 100*'-') + '\n')
                if len(self.failedOrders) != 0:
                    f.write('{0}'.format(pd.DataFrame(self.failedOrders).transpose()))
                f.write('{0}'.format('\n' + 100*'-') + '\n')

            ## -----------------------------------------------------------------------------
            # message = MIMEText(stratYY.strategyID, 'plain', 'utf-8')
            fp = open(tempFile, "r")
            message = MIMEText(fp.read().decode('string-escape').decode("utf-8"), 'plain', 'utf-8')
            fp.close()

            ## 显示:发件人
            message['From'] = Header(sender, 'utf-8')
            ## 显示:收件人
            message['To']   =  Header('汉云交易员', 'utf-8')

            ## 主题
            subject = self.ctaEngine.tradingDay + u'：云扬1号『' + self.ctaEngine.mainEngine.dataBase + '』交易播报'
            message['Subject'] = Header(subject, 'utf-8')

            try:
                smtpObj = smtplib.SMTP('localhost')
                smtpObj.sendmail(sender, receiversMain, message.as_string())
                print '\n' + '#'*80
                print "邮件发送成功"
                print '#'*80
            except smtplib.SMTPException:
                print '\n' + '#'*80
                print "Error: 无法发送邮件"
                print '#'*80
            ## 间隔 1 秒
            time.sleep(1)

            ## -----------------------------------------------------------------------------
            # message = MIMEText(stratYY.strategyID, 'plain', 'utf-8')
            fp      = open(tempFile, "r")
            lines   = fp.readlines()
            l       = lines[0:([i for i in range(len(lines)) if '当日已交易' in lines[i]][0] - 1)]
            message = MIMEText(''.join(l).decode('string-escape').decode("utf-8"), 'plain', 'utf-8')
            fp.close()

            ## 显示:发件人
            message['From'] = Header(sender, 'utf-8')
            ## 显示:收件人
            message['To']   =  Header('汉云管理员', 'utf-8')

            ## 主题
            subject = self.ctaEngine.tradingDay + u'：云扬1号『' + self.ctaEngine.mainEngine.dataBase + '』交易播报'
            message['Subject'] = Header(subject, 'utf-8')

            try:
                smtpObj = smtplib.SMTP('localhost')
                smtpObj.sendmail(sender, receiversOthers, message.as_string())
                print '\n' + '#'*80
                print "邮件发送成功"
                print '#'*80
            except smtplib.SMTPException:
                print '#'*80
                print "Error: 无法发送邮件"
                print '\n' + '#'*80
            ## 间隔 1 秒
            time.sleep(1)


################################################################################
class TargetPosTemplate(CtaTemplate):
    """
    允许直接通过修改目标持仓来实现交易的策略模板
    
    开发策略时，无需再调用buy/sell/cover/short这些具体的委托指令，
    只需在策略逻辑运行完成后调用setTargetPos设置目标持仓，底层算法
    会自动完成相关交易，适合不擅长管理交易挂撤单细节的用户。    
    
    使用该模板开发策略时，请在以下回调方法中先调用母类的方法：
    onTick
    onBar
    onOrder
    
    假设策略名为TestStrategy，请在onTick回调中加上：
    super(TestStrategy, self).onTick(tick)
    
    其他方法类同。
    """
    
    className = 'TargetPosTemplate'
    author = u'量衍投资'
    
    # 目标持仓模板的基本变量
    tickAdd = 1             # 委托时相对基准价格的超价
    lastTick = None         # 最新tick数据
    lastBar = None          # 最新bar数据
    targetPos = EMPTY_INT   # 目标持仓
    orderList = []          # 委托号列表

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'targetPos']

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(TargetPosTemplate, self).__init__(ctaEngine, setting)
        
    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情推送"""
        self.lastTick = tick
        
        # 实盘模式下，启动交易后，需要根据tick的实时推送执行自动开平仓操作
        if self.trading:
            self.trade()
        
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到K线推送"""
        self.lastBar = bar
    
    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托推送"""
        if order.status == STATUS_ALLTRADED or order.status == STATUS_CANCELLED:
            self.orderList.remove(order.vtOrderID)
    
    #----------------------------------------------------------------------
    def setTargetPos(self, targetPos):
        """设置目标仓位"""
        self.targetPos = targetPos
        
        self.trade()
        
    #----------------------------------------------------------------------
    def trade(self):
        """执行交易"""
        # 先撤销之前的委托
        for vtOrderID in self.orderList:
            self.cancelOrder(vtOrderID)
        self.orderList = []
        
        # 如果目标仓位和实际仓位一致，则不进行任何操作
        posChange = self.targetPos - self.pos
        if not posChange:
            return
        
        # 确定委托基准价格，有tick数据时优先使用，否则使用bar
        longPrice = 0
        shortPrice = 0
        
        if self.lastTick:
            if posChange > 0:
                longPrice = self.lastTick.askPrice1 + self.tickAdd
            else:
                shortPrice = self.lastTick.bidPrice1 - self.tickAdd
        else:
            if posChange > 0:
                longPrice = self.lastBar.close + self.tickAdd
            else:
                shortPrice = self.lastBar.close - self.tickAdd
        
        ########################################################################
        ## william
        ## BackTesting
        ########################################################################
        # 回测模式下，采用合并平仓和反向开仓委托的方式
        if self.getEngineType() == ENGINETYPE_BACKTESTING:
            if posChange > 0:
                vtOrderID = self.buy(longPrice, abs(posChange))
            else:
                vtOrderID = self.short(shortPrice, abs(posChange))
            self.orderList.append(vtOrderID)
        
        ########################################################################
        ## william
        ## Trading
        ########################################################################
        # 实盘模式下，首先确保之前的委托都已经结束（全成、撤销）
        # 然后先发平仓委托，等待成交后，再发送新的开仓委托
        else:
            # 检查之前委托都已结束
            if self.orderList:
                return
            
            # 买入
            if posChange > 0:
                if self.pos < 0:
                    vtOrderID = self.cover(longPrice, abs(self.pos))
                else:
                    vtOrderID = self.buy(longPrice, abs(posChange))
            # 卖出
            else:
                if self.pos > 0:
                    vtOrderID = self.sell(shortPrice, abs(self.pos))
                else:
                    vtOrderID = self.short(shortPrice, abs(posChange))
            self.orderList.append(vtOrderID)
    
