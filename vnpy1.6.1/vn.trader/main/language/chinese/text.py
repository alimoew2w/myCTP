# encoding: UTF-8

SAVE_DATA       = u'保存数据'

CONTRACT_SYMBOL = u'合约代码'
CONTRACT_NAME   = u'名称'
LAST_PRICE      = u'最新价'
PRE_CLOSE_PRICE = u'昨收盘'
VOLUME          = u'成交量'
OPEN_INTEREST   = u'持仓量'
OPEN_PRICE      = u'开盘价'
HIGH_PRICE      = u'最高价'
LOW_PRICE       = u'最低价'
TIME            = u'时间'
GATEWAY         = u'接口'
CONTENT         = u'内容'

ERROR_CODE      = u'错误代码'
ERROR_MESSAGE   = u'错误信息'

TRADE_ID        = u'成交编号'
ORDER_ID        = u'委托编号'
DIRECTION       = u'方向'
OFFSET          = u'开平'
PRICE           = u'成本'
TRADE_TIME      = u'成交时间'

ORDER_VOLUME    = u'委托数量'
TRADED_VOLUME   = u'成交数量'
ORDER_STATUS    = u'委托状态'
ORDER_TIME      = u'委托时间'
## -----------------------------------------------------------------------------
## william
## 成交时间
TRADE_TIME      = u'成交时间'
## -----------------------------------------------------------------------------
CANCEL_TIME     = u'撤销时间'
FRONT_ID        = u'前置编号'
SESSION_ID      = u'会话编号'
POSITION        = u'持仓量'
YD_POSITION     = u'昨持仓'
FROZEN          = u'冻结量'
SIZE            = u'合约乘数'
POSITION_PROFIT = u'持仓盈亏'

ACCOUNT_ID      = u'账户编号'
PRE_BALANCE     = u'昨净值'
BALANCE         = u'净值'
AVAILABLE       = u'可用'
COMMISSION      = u'手续费'
MARGIN          = u'保证金'
CLOSE_PROFIT    = u'平仓盈亏'

TRADING         = u'交易'
PRICE_TYPE      = u'价格类型'
EXCHANGE        = u'交易所'
CURRENCY        = u'货币'
PRODUCT_CLASS   = u'产品类型'
LAST            = u'最新'
SEND_ORDER      = u'发单'

## =============================================================================
CANCEL_ALL        = u'全撤'
CLOSE_ALL         = u'全平'
CONFIRM_CLOSE_ALL = u'确认全平？'

STOP_ALL          = u'停止'
CONFIRM_STOP_ALL  = u'确定停止？'
## =============================================================================

VT_SYMBOL         = u'vt系统代码'
CONTRACT_SIZE     = u'合约大小'
PRICE_TICK        = u'最小价格变动'
STRIKE_PRICE      = u'行权价'
UNDERLYING_SYMBOL = u'标的代码'
OPTION_TYPE       = u'期权类型'

REFRESH           = u'刷新'
SEARCH            = u'查询'
CONTRACT_SEARCH   = u'合约查询'


BID_1 = u'买一'
BID_2 = u'买二'
BID_3 = u'买三'
BID_4 = u'买四'
BID_5 = u'买五'
ASK_1 = u'卖一'
ASK_2 = u'卖二'
ASK_3 = u'卖三'
ASK_4 = u'卖四'
ASK_5 = u'卖五'

BID_PRICE_1 = u'买一价'
BID_PRICE_2 = u'买二价'
BID_PRICE_3 = u'买三价'
BID_PRICE_4 = u'买四价'
BID_PRICE_5 = u'买五价'
ASK_PRICE_1 = u'卖一价'
ASK_PRICE_2 = u'卖二价'
ASK_PRICE_3 = u'卖三价'
ASK_PRICE_4 = u'卖四价'
ASK_PRICE_5 = u'卖五价'

BID_VOLUME_1 = u'买一量'
BID_VOLUME_2 = u'买二量'
BID_VOLUME_3 = u'买三量'
BID_VOLUME_4 = u'买四量'
BID_VOLUME_5 = u'买五量'
ASK_VOLUME_1 = u'卖一量'
ASK_VOLUME_2 = u'卖二量'
ASK_VOLUME_3 = u'卖三量'
ASK_VOLUME_4 = u'卖四量'
ASK_VOLUME_5 = u'卖五量'

MARKET_DATA = u'行情'
LOG         = u'日志'
ERROR       = u'错误'
TRADE       = u'成交'
ORDER       = u'委托'
POSITION    = u'持仓'
ACCOUNT     = u'账户'

SYSTEM      = u'系统'

################################################################################
## william
CONNECT_DATABASE       = u'连接数据库'

CONNECT_DATABASE_Mongo = u'连接 MongoDB'
CONNECT_DATABASE_MySQL = u'连接 MySQL'
################################################################################

EXIT          = u'退出'
APPLICATION   = u'功能'
DATA_RECORDER = u'行情记录'
RISK_MANAGER  = u'风控管理'

STRATEGY      = u'策略'
CTA_STRATEGY  = u'CTA策略'

HELP          = u'帮助'
RESTORE       = u'还原'
ABOUT         = u'关于'
TEST          = u'测试'

################################################################################
## william
## 临时犯了强迫症,一定要在中英文之间加一个空格
## 因此在这里的 '连接' 多加了一个空格
## CONNECT = u'连接'
CONNECT = u'连接 '
################################################################################


CPU_MEMORY_INFO = u'系统时间： {currTime}  CPU使用率：{cpu}%   内存使用率：{memory}%'
CONFIRM_EXIT    = u'确认退出？'



################################################################################
## william
## 添加数据库连接情况说明
## 格式如下:
## DATABASE_Mongo_
## DATABASE_MySQL_
################################################################################
GATEWAY_NOT_EXIST = u'接口不存在：{gateway}'
DATABASE_CONNECTING_COMPLETED       = u'MongoDB连接成功'
DATABASE_CONNECTING_FAILED          = u'MongoDB连接失败'
DATA_INSERT_FAILED                  = u'数据插入失败，MongoDB没有连接'
DATA_QUERY_FAILED                   = u'数据查询失败，MongoDB没有连接'
DATA_UPDATE_FAILED                  = u'数据更新失败，MongoDB没有连接'

## Mongo
DATABASE_Mongo_CONNECTING_COMPLETED = u'MongoDB连接成功'
DATABASE_Mongo_CONNECTING_FAILED    = u'MongoDB连接失败'

DATA_Mongo_INSERT_FAILED            = u'数据插入失败，MongoDB没有连接'
DATA_Mongo_QUERY_FAILED             = u'数据查询失败，MongoDB没有连接'
DATA_Mongo_UPDATE_FAILED            = u'数据更新失败，MongoDB没有连接'


## MySQL
DATABASE_MySQL_CONNECTING_COMPLETED = u'MySQL 连接成功!!!'
DATABASE_MySQL_CONNECTING_FAILED    = u'MySQL 连接失败!!!'

DATA_MySQL_QUERY_COMPLETED          = u'MySQL 查询成功, 返回数据结果!!!'
DATA_MySQL_QUERY_FAILED             = u'MySQL 查询失败，没有数据返回!!!'

DATA_MySQL_NOT_CONNECTED            = u'MySQL 查询失败，数据库没有连接!!!'
