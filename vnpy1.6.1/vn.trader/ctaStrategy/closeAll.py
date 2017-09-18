CTAORDER_BUY = u'买开'
CTAORDER_SELL = u'卖平'
CTAORDER_SHORT = u'卖开'
CTAORDER_COVER = u'买平'

########################################################################
class VtSubscribeReq(object):
    """订阅行情时传入的对象类"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.symbol = EMPTY_STRING              # 代码
        self.exchange = EMPTY_STRING            # 交易所
        
        ########################################################################
        ## william
        # 以下为IB相关
        self.productClass = EMPTY_UNICODE       # 合约类型
        self.currency = EMPTY_STRING            # 合约货币
        self.expiry = EMPTY_STRING              # 到期日
        self.strikePrice = EMPTY_FLOAT          # 行权价
        self.optionType = EMPTY_UNICODE         # 期权类型
        ########################################################################

for i in mainEngine.drEngine.positionInfo.keys():
    req = VtSubscribeReq()
    req.symbol = mainEngine.drEngine.positionInfo[i]['symbol']
    mainEngine.subscribe(req, 'CTP')
    if req.symbol not in mainEngine.ctaEngine.subscribeContracts:
        mainEngine.ctaEngine.subscribeContracts.append(req.symbol)
    mainEngine.ctaEngine.tickInfo[req.symbol] = {k:mainEngine.getContract(req.symbol).__dict__[k] for k in ['vtSymbol','priceTick','size','volumeMultiple']}

class strategyClass(object):
    name = 'CLOSE_ALL'
    productClass = ''
    currency = ''
tempStrategy = strategyClass()

accountPosInfo = {k:{u:mainEngine.drEngine.positionInfo[k][u] for u in mainEngine.drEngine.positionInfo[k].keys() if u in ['vtSymbol','position','direction']} for k in mainEngine.drEngine.positionInfo.keys() if int(mainEngine.drEngine.positionInfo[k]['position']) != 0}
print accountPosInfo

if accountPosInfo:
    for i in accountPosInfo.keys():
        # contract = mainEngine.getContract(accountPosInfo[i]['vtSymbol'])
        try:
            tempInstrumentID = accountPosInfo[i]['vtSymbol']
            tempVolume       = accountPosInfo[i]['position']
            tempPriceTick    = mainEngine.ctaEngine.tickInfo[tempInstrumentID]['priceTick']
            tempLastPrice    = mainEngine.ctaEngine.lastTickData[tempInstrumentID]['lastPrice']

            if accountPosInfo[i]['direction'] == u'多':
                mainEngine.ctaEngine.sendOrder(vtSymbol = tempInstrumentID,
                    orderType = CTAORDER_SELL,
                    price = max(mainEngine.ctaEngine.lastTickData[tempInstrumentID]['lowerLimit'],tempLastPrice - 1*tempPriceTick),
                    volume = tempVolume,
                    strategy = tempStrategy)
            elif accountPosInfo[i]['direction'] == u'空':
                mainEngine.ctaEngine.sendOrder(vtSymbol = tempInstrumentID,
                    orderType = CTAORDER_COVER,
                    price = min(mainEngine.ctaEngine.lastTickData[tempInstrumentID]['upperLimit'], tempLastPrice + 1*tempPriceTick),
                    volume = tempVolume,
                    strategy = tempStrategy)
        except:
            print tempInstrumentID,'平仓失败！！！'

"""
tempInstrumentID = accountPosInfo[i]['vtSymbol']
tempVolume       = accountPosInfo[i]['position']
tempPriceTick    = mainEngine.ctaEngine.tickInfo[tempInstrumentID]['priceTick']
tempLastPrice    = mainEngine.ctaEngine.lastTickData[tempInstrumentID]['lastPrice']
mainEngine.ctaEngine.sendOrder(vtSymbol = tempInstrumentID,
    orderType = CTAORDER_COVER,
    price = min(mainEngine.ctaEngine.lastTickData[tempInstrumentID]['upperLimit'], tempLastPrice + 1*tempPriceTick),
    volume = tempVolume,
    strategy = tempStrategy)
"""


