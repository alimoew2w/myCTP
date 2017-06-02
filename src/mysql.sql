################################################################################
## fl.positionInfo
## 策略持仓情况
################################################################################
create table fl.positionInfo(
    strategyID      VARCHAR(100) NOT NULL,
    InstrumentID    VARCHAR(20)  NOT NULL,
    TradingDay      DATE         NOT NULL,
    tradeTime       DATETIME     NOT NULL,
    direction       VARCHAR(20)  NOT NULL,
    volume          INT          NULL,
    PRIMARY KEY(strategyID, instrumentID, direction)
);

################################################################################
## fl.tradingIndo
## 策略交易历史情况
################################################################################
create table fl.tradingInfo(
    strategyID      VARCHAR(100) NOT NULL,
    InstrumentID    VARCHAR(20)  NOT NULL,
    TradingDay      DATE         NOT NULL,
    tradeTime       DATETIME     NOT NULL,
    direction       VARCHAR(20)  NOT NULL,
    offset          VARCHAR(20)  NOT NULL,
    volume          INT           NOT NULL,
    price           DECIMAL(15,5) NOT NULL
);

## orderTime: 下单时间
## offset: 开仓, 平仓
