################################################################################
## positionInfo
## 策略持仓情况
################################################################################
create table positionInfo(
    strategyID      CHAR(50)     NOT NULL,
    InstrumentID    CHAR(30)     NOT NULL,
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
    InstrumentID    VARCHAR(30)  NOT NULL,
    TradingDay      DATE         NOT NULL,
    tradeTime       DATETIME     NOT NULL,
    direction       CHAR(20)     NOT NULL,
    offset          CHAR(20)     NOT NULL,
    volume          INT           NOT NULL,
    price           DECIMAL(15,5) NOT NULL
    -- PRIMARY KEY(strategyID, InstrumentID, TradingDay, tradeTime, direction, offset)
    -- PRIMARY KEY(strategyID, InstrumentID, TradingDay, tradeTime, direction, offset)
);

## orderTime: 下单时间
## offset: 开仓, 平仓


################################################################################
## failedInfo
## 策略交易失败情况
################################################################################
create table failedInfo(
    strategyID      CHAR(50)      NOT NULL,
    InstrumentID    CHAR(30)      NOT NULL,
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
    InstrumentID    CHAR(30)     NOT NULL,
    orderTime       TIME         NOT NULL,
    status          CHAR(50)     ,
    direction       CHAR(20)     ,
    cancelTime      CHAR(100)    ,
    tradedVolume    INT          ,
    frontID         SMALLINT     ,
    sessionID       BIGINT       ,
    offset          CHAR(50)     ,
    price           DECIMAL(15,5) ,
    totalVolume     BIGINT       ,
    PRIMARY KEY(TradingDay, strategyID, vtOrderID, InstrumentID, status)
);

-- alter table orderInfo drop PRIMARY key;
-- alter table orderInfo add primary key (TradingDay, strategyID, vtOrderID, InstrumentID, status)
-- ALTER TABLE orderInfo MODIFY cancelTime      CHAR(100);

################################################################################
## tradingOrders
## 记录所有发出去的订单情况
################################################################################
create table tradingOrders(
    TradingDay      DATE         NOT NULL,
    strategyID      CHAR(50)     NOT NULL,
    InstrumentID    CHAR(30)     NOT NULL,
    orderType       CHAR(50)     NOT NULL,
    volume          BIGINT       NOT NULL,
    stage           CHAR(20)     NOT NULL,
    PRIMARY KEY(TradingDay, strategyID, InstrumentID, orderType, stage)
);


################################################################################
## workingInfo
## 记录正在进行的订单
################################################################################
create table workingInfo(
    TradingDay      DATE         NOT NULL,
    strategyID      CHAR(50)     NOT NULL,
    vtSymbol        CHAR(20)     NOT NULL,
    vtOrderIDList   text         NOT NULL,   
    orderType       CHAR(50)     NOT NULL,
    volume          BIGINT       NOT NULL,
    stage           CHAR(20)     NOT NULL, 
    PRIMARY KEY(TradingDay, strategyID, vtSymbol, orderType, stage)
);

################################################################################
## pnl
## 记录正在进行的订单
################################################################################
create table pnl(
    TradingDay      DATE         NOT NULL,
    strategyID      CHAR(50)     NOT NULL,
    InstrumentID    CHAR(30)     NOT NULL,
    pnl             DECIMAL(15,3),
    PRIMARY KEY(TradingDay, strategyID, InstrumentID)
);


################################################################################
## signal
## 记录策略信号
################################################################################
create table tradingSignal(
    TradingDay      DATE         NOT NULL,
    strategyID      CHAR(50)     NOT NULL,
    InstrumentID    CHAR(30)     NOT NULL,
    volume          BIGINT       NOT NULL,
    direction       CHAR(20)     NOT NULL,
    PRIMARY KEY(TradingDay, strategyID, InstrumentID, direction)
);


################################################################################
## report_account
## 记录策略信号
################################################################################



################################################################################
## nav
## 记录基金净值
################################################################################
create table nav(
    TradingDay      DATE          NOT NULL,
    Futures         DECIMAL(15,5) NOT NULL,
    Currency        DECIMAL(15,5) ,
    Bank            DECIMAL(15,5) ,
    Assets          DECIMAL(15,5) NOT NULL,
    Shares          BIGINT        NOT NULL,
    NAV             DECIMAL(15,5) NOT NULL,
    GrowthRate      DECIMAL(10,5) NOT NULL,
    Remarks         text(1000)
);


################################################################################
## UpperLower
## 记录涨跌停下单平仓的信息
################################################################################
create table UpperLowerInfo(
    TradingDay      DATE         NOT NULL,
    strategyID      CHAR(50)     NOT NULL,
    InstrumentID    VARCHAR(30)  NOT NULL,
    vtOrderIDList   CHAR(50)     NOT NULL,
    direction       CHAR(20)     ,
    volume          INT          
);

################################################################################
## fee
## 记录基金各项手续费
################################################################################
create table fee(
    TradingDay      DATE          NOT NULL,
    Amount          DECIMAL(10,5) NOT NULL,
    Remarks         text(1000)
);

