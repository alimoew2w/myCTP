################################################################################
## positionInfo
## 策略持仓情况
################################################################################
create table positionInfo(
    strategyID      CHAR(50)     NOT NULL,
    InstrumentID    CHAR(20)     NOT NULL,
    TradingDay      DATE         NOT NULL,
    direction       CHAR(20)     NOT NULL,
    volume          INT          NULL,
    PRIMARY KEY(strategyID, InstrumentID, TradingDay, direction)
);

################################################################################
## fl.tradingIndo
## 策略交易历史情况
################################################################################
create table tradingInfo(
    strategyID      CHAR(50)     NOT NULL,
    InstrumentID    VARCHAR(20)  NOT NULL,
    TradingDay      DATE         NOT NULL,
    tradeTime       DATETIME     NOT NULL,
    direction       CHAR(20)     NOT NULL,
    offset          CHAR(20)     NOT NULL,
    volume          INT           NOT NULL,
    price           DECIMAL(15,5) NOT NULL,
    -- PRIMARY KEY(strategyID, InstrumentID, TradingDay, tradeTime, direction, offset)
    PRIMARY KEY(strategyID, InstrumentID, TradingDay, tradeTime, direction, offset)
);

## orderTime: 下单时间
## offset: 开仓, 平仓


################################################################################
## failedInfo
## 策略交易失败情况
################################################################################
create table failedInfo(
    strategyID      CHAR(50)      NOT NULL,
    InstrumentID    CHAR(20)      NOT NULL,
    TradingDay      DATE          NOT NULL,
    direction       CHAR(20)      NOT NULL,
    offset          CHAR(20)      NOT NULL,
    volume          INT           NOT NULL,
    PRIMARY KEY(strategyID, InstrumentID, TradingDay, direction, offset)
);

################################################################################
## orderInfo
## 记录所有发出去的订单情况
################################################################################
create table orderInfo(
    TradingDay      DATE         NOT NULL,
    strategyID      CHAR(50)     NOT NULL,
    vtOrderID       CHAR(50)     NOT NULL,    
    InstrumentID    CHAR(20)     NOT NULL,
    orderTime       TIME         NOT NULL,
    status          CHAR(50)     ,
    direction       CHAR(20)     ,
    cancelTime      TIME         ,
    tradedVolume    INT          ,
    frontID         SMALLINT     ,
    sessionID       BIGINT       ,
    offset          CHAR(50)     ,
    price           DECIMAL(15,5) ,
    totalVolume     BIGINT       ,
    PRIMARY KEY(TradingDay, strategyID, vtOrderID, InstrumentID)
);
