################################################################################
## fl.positionInfo
## 策略持仓情况
################################################################################
create table positionInfo(
    strategyID      VARCHAR(100) NOT NULL,
    InstrumentID    VARCHAR(20)  NOT NULL,
    TradingDay      DATE         NOT NULL,
    direction       VARCHAR(20)  NOT NULL,
    volume          INT          NULL,
    PRIMARY KEY(strategyID, InstrumentID, TradingDay, direction)
);

################################################################################
## fl.tradingIndo
## 策略交易历史情况
################################################################################
create table tradingInfo(
    strategyID      VARCHAR(100) NOT NULL,
    InstrumentID    VARCHAR(20)  NOT NULL,
    TradingDay      DATE         NOT NULL,
    tradeTime       DATETIME     NOT NULL,
    direction       VARCHAR(20)  NOT NULL,
    offset          VARCHAR(20)  NOT NULL,
    volume          INT           NOT NULL,
    price           DECIMAL(15,5) NOT NULL,
    -- PRIMARY KEY(strategyID, InstrumentID, TradingDay, tradeTime, direction, offset)
    PRIMARY KEY(strategyID, InstrumentID, TradingDay, tradeTime, direction, offset)
);

## orderTime: 下单时间
## offset: 开仓, 平仓


################################################################################
## fl.failedInfo
## 策略交易失败情况
################################################################################
create table failedInfo(
    strategyID      VARCHAR(100) NOT NULL,
    InstrumentID    VARCHAR(20)  NOT NULL,
    TradingDay      DATE         NOT NULL,
    direction       VARCHAR(20)  NOT NULL,
    offset          VARCHAR(20)  NOT NULL,
    volume          INT           NOT NULL,
    PRIMARY KEY(strategyID, InstrumentID, TradingDay, direction, offset)
);
