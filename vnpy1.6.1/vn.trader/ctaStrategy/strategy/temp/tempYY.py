print stratYY.vtSymbolList
print stratYY.lastTickData

print stratYY.positionInfo
print stratYY.tradingOrder

print [stratYY.tradingOrder[k]['vtSymbol'] for k in stratYY.tradingOrder.keys()]


workingOrders = []
tradedOrders = []

for vtOrderID in stratYY.vtOrderIDList:
    tempWorkingOrder = stratYY.ctaEngine.mainEngine.getAllOrders()[stratYY.ctaEngine.mainEngine.getAllOrders().vtSymbol == vtSymbol][stratYY.ctaEngine.mainEngine.getAllOrders().vtOrderID == vtOrderID][stratYY.ctaEngine.mainEngine.getAllOrders().status == u'未成交'].vtOrderID.values
    if len(tempWorkingOrder) != 0:
        for i in range(len(tempWorkingOrder)):
            if tempWorkingOrder[i] not in workingOrders:
                workingOrders.append(tempWorkingOrder[i])

    tempTradedOrder = stratYY.ctaEngine.mainEngine.getAllOrders()[stratYY.ctaEngine.mainEngine.getAllOrders().vtSymbol == vtSymbol][stratYY.ctaEngine.mainEngine.getAllOrders().vtOrderID == vtOrderID][stratYY.ctaEngine.mainEngine.getAllOrders().status == u'全部成交'].vtOrderID.values
    if len(tempTradedOrder) != 0:
        for i in range(len(tempTradedOrder)):
            if tempTradedOrder[i] not in tradedOrders:
                tradedOrders.append(tempTradedOrder[i])

print workingOrders
print tradedOrders

if len(workingOrders) != 0:
    for vtOrderID in workingOrders:
        stratYY.cancelOrder(vtOrderID)
else:
    tempSymbolList = [stratYY.tradingOrder[k]['vtSymbol'] for k in stratYY.tradingOrder.keys()]
    tempSymbolList = [i for i in tempSymbolList if i == vtSymbol]

    tempTradingList = [k for k in stratYY.tradingOrder.keys() if stratYY.tradingOrder[k]['vtSymbol'] == vtSymbol]

    if len(tradedOrders) == 0:
        ## 还没有成交
        ## 不要全部都下单
        for i in tempTradingList:
            print stratYY.tradingOrder[i]
            stratYY.sendTradingOrder(tradingOrderDict = stratYY.tradingOrder[i])
    elif len(tradedOrders) == 1:
        ## 有一个订单成交了
        if len(tempTradingList) == 2:
            ## 但是如果有两个订单
            tempTradedOrder = stratYY.ctaEngine.mainEngine.getAllOrders()[stratYY.ctaEngine.mainEngine.getAllOrders().vtOrderID == tradedOrders[0]]

            if tempTradedOrder.direction.values == u'多':
                if tempTradedOrder.offset.values == u'开仓':
                    tempDirection = 'buy'
                elif tempTradedOrder.offset.values == u'平仓':
                    tempDirection = 'cover'
            elif tempTradedOrder.direction.values == u'空':
                if tempTradedOrder.offset.values == u'开仓':
                    tempDirection = 'short'
                elif tempTradedOrder.offset.values == u'平仓':
                    tempDirection = 'sell'

            tempRes = tempTradedOrder.vtSymbol.values[0] + '-' + tempDirection
            tempTradingList.remove(tempRes)

            for i in tempTradingList:
                print stratYY.tradingOrder[i]
                stratYY.sendTradingOrder(tradingOrderDict = stratYY.tradingOrder[i])

        elif len(tempTradingList) <= 1:
            pass
    elif len(tradedOrders) == 2:
        ## 全部都成交了
        pass



print stratYY.tradingOrder
stratYY.tradingOrder['i1709-sell'] = {'volume': 1, 'direction': 'sell', 'vtSymbol': u'i1709'}
stratYY.tradingOrder['i1709-cover'] = {'volume': 1, 'direction': 'cover', 'vtSymbol': u'i1709'}
print stratYY.tradingOrder
vtSymbol = 'i1709'


temp = [stratYY.tradingOrder[k]['vtSymbol'] for k in stratYY.tradingOrder.keys()]
print temp

print [i for i in tempList if i == 'i1709']


stratYY.positionInfo = stratYY.ctaEngine.mainEngine.dbMySQLQuery('fl',
                            """
                            SELECT * 
                            FROM positionInfo
                            """)

if len(stratYY.positionInfo) != 0:

    for i in range(len(stratYY.positionInfo)):
        tempTradingDay = stratYY.positionInfo.loc[i,'TradingDay']
        tempHoldingDays = stratYY.ctaEngine.ChinaFuturesCalendar[stratYY.ctaEngine.ChinaFuturesCalendar.days.between(tempTradingDay.strftime('%Y%m%d'), stratYY.ctaEngine.mainEngine.tradingDay, inclusive = True)].shape[0] - 1
        stratYY.positionInfo.loc[i,'holdingDays'] = tempHoldingDays

    stratYY.positionInfo = stratYY.positionInfo[stratYY.positionInfo.holdingDays >= 5]

openInfoTradingDay = stratYY.openInfo.TradingDay.unique()
openInfoTradingDayMax = max(openInfoTradingDay).replace()
if len(openInfoTradingDay)


mainEngine.tradingDay

print stratYY.openInfo[stratYY.openInfo.TradingDay == datetime.strptime(mainEngine.tradingDay,'%Y%m%d').date().strftime('%Y-%m-%d')]

datetime.strptime(mainEngine.tradingDay,'%Y%m%d')
positionInfo = mainEngine.dbMySQLQuery('fl',
                            """
                            SELECT * 
                            FROM positionInfo
                            """)

tempTradingDay = mainEngine.ctaEngine.ChinaFuturesCalendar.loc[mainEngine.ctaEngine.ChinaFuturesCalendar.days < mainEngine.tradingDay, 'days'].max()
print tempTradingDay

print stratYY.openInfo[stratYY.openInfo.TradingDay == datetime.strptime(tempTradingDay,'%Y%m%d').date().strftime('%Y-%m-%d')]
