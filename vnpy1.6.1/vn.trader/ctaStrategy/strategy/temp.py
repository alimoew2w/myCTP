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
