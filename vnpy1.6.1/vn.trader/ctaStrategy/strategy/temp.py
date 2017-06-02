print strat.minuteData
print strat.minuteData.dtypes

print strat.stratPosInfo

print dir(mainEngine.ctaEngine)
print mainEngine.ctaEngine.strategyDict
print mainEngine.ctaEngine.tickStrategyDict
print mainEngine.ctaEngine.tradeSet
print mainEngine.ctaEngine.orderStrategyDict

print strat.vtOrderIDList

print strat.stratPosInfo
################################################################################
instrumentID = 'i1709'
instrumentTick = strat.lastTickData[instrumentID]

barClose = strat.minuteBar[instrumentID].ClosePrice
# print barClose

posInfo = strat.stratPosInfo[strat.stratPosInfo.instrumentID == instrumentID]
print posInfo

barClose = strat.minuteBar[instrumentID].ClosePrice     

signalBuy = barClose.mean() + 0.2 * barClose.std()
signalSell = barClose.mean() - 0.2 * barClose.std()
print instrumentTick['lastPrice']
print signalBuy, signalSell     

signalSell = barClose.mean() + 2 * barClose.std()
signalBuy = barClose.mean() + 1 * barClose.std()
signalCover = barClose.mean() - 1 * barClose.std()
signalShort = barClose.mean() - 2 * barClose.std()
# print signalBuy, signalSell     

if instrumentTick['lastPrice'] > signalSell:
    signalValue = 'sell'
elif  signalBuy <= instrumentTick['lastPrice'] <= signalSell:
    signalValue = 'buy'
elif signalCover <= instrumentTick['lastPrice'] <= signalBuy:
    signalValue = None
elif signalShort <= instrumentTick['lastPrice'] <= signalCover:
    signalValue = 'short'
else:
    signalValue = 'cover'  

# strat.vtOrderIDList = []

# ################################################################################
if signalValue == 'long':
    if posInfo[posInfo.direction == 'short'].shape[0] != 0:
        ## 有多有空 + 无多有空
        ## cover
        vtOrderID = strat.cover(vtSymbol = instrumentID, price = instrumentTick['lastPrice'], volume = 1)
        strat.vtOrderIDList.append(vtOrderID)
    elif posInfo[posInfo.direction == 'long'].shape[0] == 0:
        ## 无多无空
        ## buy
        vtOrderID = strat.buy(vtSymbol = instrumentID, price = instrumentTick['lastPrice'], volume = 1)
        strat.vtOrderIDList.append(vtOrderID)
    else:
        pass
else:
    if posInfo[posInfo.direction == 'long'].shape[0] != 0:
        ## 有多有空 + 有多无空
        ## sell
        vtOrderID = strat.sell(vtSymbol = instrumentID, price = instrumentTick['lastPrice'], volume = 1)
        strat.vtOrderIDList.append(vtOrderID)
    elif posInfo[posInfo.direction == 'short'].shape[0] == 0:
        ## 无多无空
        ## short
        vtOrderID = strat.short(vtSymbol = instrumentID, price = instrumentTick['lastPrice'], volume = 1)
        strat.vtOrderIDList.append(vtOrderID)
    else:
        pass
# ################################################################################
print strat.vtOrderIDList

stratTrade = {'orderID': '3', 'direction': u'\u7a7a', 'gatewayName': 'CTP', 'tradeID': '       22099', 'exchange': 'DCE', 'symbol': 'i1709', 'volume': 1, 'tradeTime': '22:11:55', 'rawData': None, 'vtTradeID': 'CTP.       22099', 'offset': u'\u5f00\u4ed3', 'vtOrderID': 'CTP.3', 'strategyID': '', 'tradeStatus': u'', 'price': 468.0, 'vtSymbol': 'i1709'}
print u"stratTrade:==>", stratTrade

if stratTrade['vtOrderID'] in strat.vtOrderIDList:
    ## 1. strategyID
    stratTrade['strategyID'] = strat.strategyID

    ## -----------------------------------------
    if stratTrade['direction'] == u'多':
        tempDirection = 'long'
    else:
        tempDirection = 'short'
    ## -----------------------------------------

    ## 2. stratPosInfo
    if strat.stratPosInfo[strat.stratPosInfo.instrumentID == instrumentID].shape[0] == 0:
        ''' 如果没有持仓,则直接添加到持仓'''
        tempRes = pd.DataFrame([[stratTrade['strategyID'], stratTrade['vtSymbol'], tempDirection,stratTrade['volume']]], columns = ['strategyID','instrumentID','direction','volume'])
        strat.stratPosInfo = strat.stratPosInfo.append(tempRes)
    else:
        ''' 如果有持仓, 则需要更新数据'''
        if strat.stratPosInfo[strat.stratPosInfo.instrumentID == instrumentID].loc[0,'direction'] != tempDirection:
            strat.stratPosInfo.loc[strat.stratPosInfo.instrumentID == instrumentID,'volume'] -= stratTrade['volume']
        else:
            strat.stratPosInfo.loc[strat.stratPosInfo.instrumentID == instrumentID,'volume'] += stratTrade['volume']
strat.stratPosInfo = strat.stratPosInfo[strat.stratPosInfo.volume != 0]
print strat.stratPosInfo
strat.updateStratPosInfo(strat.stratPosInfo)

################################################################################
## william
## 信号发出
print strat.stratPosInfo

instrumentID = 'i1709'
print strat.stratPosInfo[strat.stratPosInfo.instrumentID == instrumentID].reset_index(drop = True).loc[0,'']


.reset_index(drop = True).loc[0,'volume']

posInfo[posInfo.direction == 'short', 'volume']


import pandas as pd
df = pd.DataFrame([[1,2,3],[4,5,6]], columns = list('abc'))
print df

print df[df.a == 1, 'b']


print posInfo[posInfo.direction == 'long'].reset_index(drop = True).loc[0,'volume']



if signalValue == 'buy':
    if posInfo[posInfo.direction == 'short'].shape[0] != 0:
        vtOrderID = strat.cover(vtSymbol = instrumentID, price = instrumentTick['lastPrice'], volume = 1)
        strat.vtOrderIDList.append(vtOrderID)
    elif posInfo[posInfo.direction == 'long'].shape[0] == 0:
        vtOrderID = strat.buy(vtSymbol = instrumentID, price = instrumentTick['lastPrice'], volume = 1)
        strat.vtOrderIDList.append(vtOrderID)
    else:
        pass

signalValue = 'sell'

if signalValue:
    print 'hello'



import pandas as pd
df = pd.DataFrame([[1,2],[3,4]], columns = list('ab'))
print df

x = df.loc[df.a == 3, 'b'].values

if x == 4:
    print 'hello'
else:
    print 'world'

vtSymbolList = mainEngine.dbMySQLQuery('lhg_trade', 'select InstrumentID from lhg_open_t;').InstrumentID

for i in vtSymbolList:
    print i
    print type(i)

mainEngine.ctaEngine.ChinaFuturesCalendar

from datetime import datetime
print vtFunction.tradingDay()

lastTradingDay = mainEngine.ctaEngine.ChinaFuturesCalendar.loc[mainEngine.ctaEngine.ChinaFuturesCalendar.days < datetime.strptime(vtFunction.tradingDay(), '%Y%m%d').date(), 'days'].max()
print lastTradingDay

mainContracts = mainEngine.dbMySQLQuery('china_futures_bar',"""select * from main_contract_daily where TradingDay = '%s';""" % lastTradingDay)

print mainEngine.ctaEngine.mainContracts.Main_contract.values

print mainEngine.ctaEngine.mainContracts


positionContracts =mainEngine.dbMySQLQuery('fl',"""select * from positionInfo;""")
print positionContracts
signalContracts =mainEngine.dbMySQLQuery('lhg_trade',"""select * from lhg_open_t;""")
print signalContracts

print mainContracts.Main_contract.values
print positionContracts.InstrumentID.values
print signalContracts.InstrumentID.values

x = list(mainContracts.Main_contract.values, positionContracts.InstrumentID.values)


x = set(mainContracts.Main_contract.values, positionContracts.InstrumentID.values)


x = list(set(mainContracts.Main_contract.values)|set(positionContracts.InstrumentID.values)|set(signalContracts.InstrumentID.values))
print x

a = ['a','b']
b = ['a','c']
print list(set(a) & set(b))




tradingOrderSeq = {}
for i in tradingInfo.InstrumentID.values:
    if tradingInfo.loc[tradingInfo.InstrumentID == i, 'direction'].values == 1:
        tempDirection = 'long'
    elif tradingInfo.loc[tradingInfo.InstrumentID == i, 'direction'].values == -1:
        tempDirection = 'short'
    else:
        pass

    tradingOrderSeq[i] = {'direction':tempDirection,
                          'volume':tradingInfo.loc[tradingInfo.InstrumentID == i, 'volume'].values}
print tradingOrderSeq

for i in  range(len(mainEngine.getAllWorkingOrders())):
    x = mainEngine.getAllWorkingOrders()[i]
    x = mainEngine.getAllWorkingOrders()[i].__dict__
    print pd.DataFrame([x.values()], columns = x.keys())




settingFileName = '/home/william/Documents/myCTP/vnpy1.6.1/vn.trader/ctaStrategy/CTA_setting.json'
with open(settingFileName) as f:
    l = json.load(f)

if 'vtSymbol' in l[1].keys():
    print 'in'
    print len(l[1]['vtS'])

tempInstrumentID = i
tempPriceTick    = mainEngine.getContract(tempInstrumentID).priceTick
tempDirection    = stratYY.tradingOrderSeq[tempInstrumentID]['direction']
tempVolume       = stratYY.tradingOrderSeq[tempInstrumentID]['volume']


print stratYY.lastTickData[tempInstrumentID]['askPrice1']





for i in  range(len(mainEngine.getAllWorkingOrders())):
    x = mainEngine.getAllWorkingOrders()[i]
    x = mainEngine.getAllWorkingOrders()[i].__dict__
    print pd.DataFrame([x.values()], columns = x.keys())

stratWorkingOrders = {}
strategyID = stratYY.strategyID
for i in  range(len(mainEngine.getAllWorkingOrders())):
    tempWorkingOrder = mainEngine.getAllWorkingOrders()[i]
    if tempWorkingOrder.strategyID == strategyID and tempWorkingOrder.status == u'未成交':
        stratWorkingOrders[tempWorkingOrder.OrderID] = {'status': tempWorkingOrder.status}
print stratWorkingOrders


if datetime.now().hour == 14:
    print 'hello'
    pass
else:
    print 'world'

print 'dsfjsdlfj'


try:
    if datetime.now().hour == 14:
        print 'hello, 14'
except:
    pass
print 'hello

stratTradedOrders = mainEngine.getAllOrders()[mainEngine.getAllOrders().strategyID == stratYY.strategyID].vtSymbol.values
print stratTradedOrders

stratTradedOrders
stratYY.tradingOrderSeq.keys()

print [i for i in stratYY.tradingOrderSeq.keys() if i not in stratTradedOrders]



stratTradedOrders = []
for orderID in stratYY.vtOrderIDList:
    tempTradedOrder = mainEngine.getAllOrders()[mainEngine.getAllOrders().status == u'全部成交'].orderID.values
    stratTradedOrders.append(orderID)
print stratTradedOrders




print mainEngine.getAllOrders()[mainEngine.getAllOrders().status == u'全部成交'].orderID.values


stratWorkingOrders = []
tratTradedOrders = []

for orderID in strat.vtOrderIDList:
    tempWorkingOrder = self.ctaEngine.mainEngine.getAllOrders()[self.ctaEngine.mainEngine.getAllOrders().orderID == orderID & self.ctaEngine.mainEngine.getAllOrders().status == u'未成交'].orderID.values
    stratWorkingOrders.append(tempWorkingOrder)

    tempTradedOrder = self.ctaEngine.mainEngine.getAllOrders()[self.ctaEngine.mainEngine.getAllOrders().orderID == orderID & self.ctaEngine.mainEngine.getAllOrders().status == u'全部成交'].orderID.values
    stratTradedOrders.append(tempTradedOrder)


for orderID in stratWorkingOrders:
    stratYY.cancelOrder(orderID)



        
for i in range(len(mainEngine.ctaEngine.ChinaFuturesCalendar)):
    mainEngine.ctaEngine.ChinaFuturesCalendar.loc[i, 'nights'] = str(mainEngine.ctaEngine.ChinaFuturesCalendar.loc[i, 'nights']).replace('-','')
    mainEngine.ctaEngine.ChinaFuturesCalendar.loc[i, 'days'] = str(mainEngine.ctaEngine.ChinaFuturesCalendar.loc[i, 'days']).replace('-','')

        


mainEngine.dbMySQLQuery('china_futures_bar',"""select * from main_contract_daily where TradingDay = '%s';""" %lastTradingDay)


orderTime = '20170526'

mainEngine.tradingDay


print mainEngine.ctaEngine.ChinaFuturesCalendar[mainEngine.ctaEngine.ChinaFuturesCalendar.days.between(orderTime,mainEngine.tradingDay, inclusive = True)].shape[0] - 1


stratPosInfo = mainEngine.ctaEngine.mainEngine.dbMySQLQuery('fl',"""select * from positionInfo where strategyID = '%s' """ %stratYY.strategyID)




tradingInfo = stratYY.ctaEngine.mainEngine.dbMySQLQuery('lhg_trade', 'select * from lhg_open_t')
tradingOrderSeq = {}
stratPosInfo = stratYY.stratPosInfo


print tradingInfo
print stratPosInfo

x = list(set(tradingInfo.InstrumentID.values) & set(stratPosInfo.InstrumentID.values))
print x
if len(x) != 0:
    for i in x:
        tempVolume = int(tradingInfo.loc[tradingInfo.InstrumentID == i, 'volume'].values)

        if stratPosInfo.loc[stratPosInfo.InstrumentID == i, 'direction'].values == 'long':
            if tradingInfo.loc[tradingInfo.InstrumentID == i, 'direction'].values == 1:
                pass
            else:
                tempDirection = 'sell'
                tradingOrderSeq[i] = {'direction':tempDirection,
                                      'volume':tempVolume}
        else:
            if tradingInfo.loc[tradingInfo.InstrumentID == i, 'direction'].values == 1:
                tempDirection = 'cover'
                tradingOrderSeq[i] = {'direction':tempDirection,
                                      'volume':tempVolume}
            else:
                pass

print tradingOrderSeq

y = [i for i in stratPosInfo.InstrumentID.values if i not in tradingInfo.InstrumentID.values]
print y
if len(y) != 0:
    for i in y:
        tempOrderTime = pd.to_datetime(stratPosInfo.loc[stratPosInfo.InstrumentID == i, 'orderTime'].values[0]).strftime('%Y%m%d')
        tempHoldingDays = mainEngine.ctaEngine.ChinaFuturesCalendar[mainEngine.ctaEngine.ChinaFuturesCalendar.days.between(tempOrderTime,mainEngine.tradingDay, inclusive = True)].shape[0] - 1
        if tempHoldingDays >= 2:
            tempVolume = int(stratPosInfo.loc[stratPosInfo.InstrumentID == i, 'volume'].values)

            if stratPosInfo.loc[stratPosInfo.InstrumentID == i, 'direction'].values == 'long':
                tempDirection = 'sell'
            else:
                tempDirection = 'cover'
            
            tradingOrderSeq[i] = {'direction':tempDirection, 'volume':tempVolume}
print tradingOrderSeq

z = [i for i in tradingInfo.InstrumentID.values if i not in stratPosInfo.InstrumentID.values]
print z
if len(z) != 0:
    for i in z:
        if tradingInfo.loc[tradingInfo.InstrumentID == i, 'direction'].values == 1:
            tempDirection = 'buy'
        elif tradingInfo.loc[tradingInfo.InstrumentID == i, 'direction'].values == -1:
            tempDirection = 'short'
        else:
            pass
        tempVolume = int(tradingInfo.loc[tradingInfo.InstrumentID == i, 'volume'].values)
        tradingOrderSeq[i] = {'direction':tempDirection, 'volume':tempVolume}
print tradingOrderSeq


print tradingOrderSeq


print stratYY.tradingOrderSeq

print stratYY.tradingOrderSeq
print stratYY.lastTickData


print len(stratYY.vtSymbolList) == len(stratYY.lastTickData.keys())

stratYY.onStop()


stratWorkingOrders = []
stratTradedOrders  = []
stratTradedSymbols  = []
orderID = 'CTP.8'
for orderID in stratYY.vtOrderIDList:
    tempWorkingOrder = stratYY.ctaEngine.mainEngine.getAllOrders()[stratYY.ctaEngine.mainEngine.getAllOrders().vtOrderID == orderID][stratYY.ctaEngine.mainEngine.getAllOrders().status == u'未成交'].vtOrderID.values
    if len(tempWorkingOrder) != 0:
        stratWorkingOrders.append(tempWorkingOrder[0])

    tempTradedOrder = stratYY.ctaEngine.mainEngine.getAllOrders()[stratYY.ctaEngine.mainEngine.getAllOrders().vtOrderID == orderID][stratYY.ctaEngine.mainEngine.getAllOrders().status == u'全部成交'].vtOrderID.values
    if len(tempTradedOrder) != 0:
        stratTradedOrders.append(tempTradedOrder[0])

    tempTradedSymbol = stratYY.ctaEngine.mainEngine.getAllOrders()[stratYY.ctaEngine.mainEngine.getAllOrders().vtOrderID == orderID][stratYY.ctaEngine.mainEngine.getAllOrders().status == u'全部成交'].symbol.values
    if len(tempTradedSymbol) != 0:
        stratTradedSymbols.append(tempTradedSymbol[0])

print stratWorkingOrders
print stratTradedOrders
print stratTradedSymbols

stratYY.ctaEngine.mainEngine.getAllOrders()[stratYY.ctaEngine.mainEngine.getAllOrders().status == u'未成交']


stratYY.ctaEngine.mainEngine.getAllOrders()[stratYY.ctaEngine.mainEngine.getAllOrders().status == u'全部成交'][stratYY.ctaEngine.mainEngine.getAllOrders().vtOrderID == orderID].vtOrderID.values[0]

mainEngine.dbMySQLQuery('fl','select * from positionInfo')


################################################################################
print stratYY.tradingInfo
print stratYY.tradingOrderSeq


tempTradingInstrumentID = [k for k in stratYY.tradingOrderSeq.keys() if k not in stratTradedOrders]
print tempTradingInstrumentID

x = {'orderID': '', 'optionType': u'', 'direction': u'\u7a7a', 'tradeStatus': u'', 'exchange': 'DCE', 'symbol': 'i1709', 'productClass': u'', 'strikePrice': 0.0, 'expiry': '', 'volume': 1, 'currency': u'', 'multiplier': '', 'offset': u'\u5e73\u4ed3', 'lastTradeDateOrContractMonth': '', 'orderTime': '', 'price': 431.5, 'priceType': u'\u9650\u4ef7'}


stratWorkingOrders  = []
stratTradedSymbols  = []

for orderID in stratYY.vtOrderIDList:
    tempWorkingOrder = stratYY.ctaEngine.mainEngine.getAllOrders()[stratYY.ctaEngine.mainEngine.getAllOrders().vtSymbol == vtSymbol][stratYY.ctaEngine.mainEngine.getAllOrders().orderID == orderID][stratYY.ctaEngine.mainEngine.getAllOrders().status == u'未成交'].orderID.values
    if len(tempWorkingOrder) != 0 and tempWorkingOrder not in stratWorkingOrders:
        stratWorkingOrders.append(tempWorkingOrder[0])

    tempTradedSymbol = stratYY.ctaEngine.mainEngine.getAllOrders()[stratYY.ctaEngine.mainEngine.getAllOrders().vtSymbol == vtSymbol][stratYY.ctaEngine.mainEngine.getAllOrders().vtOrderID == orderID][stratYY.ctaEngine.mainEngine.getAllOrders().status == u'全部成交'].vtSymbol.values
    if len(tempTradedSymbol) != 0 and tempTradedSymbol not in stratTradedSymbols:
        stratTradedSymbols.append(tempTradedSymbol[0])


if len(stratWorkingOrders) != 0:
    print 'hello'
elif len(stratWorkingOrders) == 0 and vtSymbol in stratTradedSymbols:
    print 'world'
