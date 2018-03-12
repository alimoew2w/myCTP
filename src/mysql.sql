################################################################################
## positionInfo
## 策略持仓情况
################################################################################
create table positionInfo(
    strategyID      VARCHAR(50)     NOT NULL,
    InstrumentID    VARCHAR(30)     NOT NULL,
    TradingDay      DATE            NOT NULL,
    direction       VARCHAR(20)     NOT NULL,
    volume          INT             NULL,
    PRIMARY KEY(strategyID, InstrumentID, TradingDay, direction)
);

################################################################################
## fl.tradingIndo
## 策略交易历史情况
################################################################################
create table tradingInfo(
    strategyID      VARCHAR(50)     NOT NULL,
    InstrumentID    VARCHAR(30)     NOT NULL,
    TradingDay      DATE            NOT NULL,
    tradeTime       DATETIME        NOT NULL,
    direction       VARCHAR(20)     NOT NULL,
    offset          VARCHAR(20)     NOT NULL,
    volume          INT             NOT NULL,
    price           DECIMAL(15,5)   NOT NULL
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
    strategyID      VARCHAR(50)      NOT NULL,
    InstrumentID    VARCHAR(30)      NOT NULL,
    TradingDay      DATE             NOT NULL,
    direction       VARCHAR(20)      NOT NULL,
    offset          VARCHAR(20)      NOT NULL,
    volume          INT              NOT NULL,
    PRIMARY KEY(strategyID, InstrumentID, TradingDay, direction, offset)
);

################################################################################
## orderInfo
## 记录所有发出去的订单情况
################################################################################
create table orderInfo(
    TradingDay      DATE            NOT NULL,
    strategyID      VARCHAR(50)     NOT NULL,
    vtOrderID       VARCHAR(50)     NOT NULL,    
    InstrumentID    VARCHAR(30)     NOT NULL,
    orderTime       TIME            NOT NULL,
    status          VARCHAR(50)     ,
    direction       VARCHAR(20)     ,
    cancelTime      VARCHAR(100)    ,
    tradedVolume    INT          ,
    frontID         SMALLINT     ,
    sessionID       BIGINT       ,
    offset          VARCHAR(50)     ,
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
    TradingDay      DATE            NOT NULL,
    strategyID      VARCHAR(50)     NOT NULL,
    InstrumentID    VARCHAR(30)     NOT NULL,
    orderType       VARCHAR(50)     NOT NULL,
    volume          BIGINT          NOT NULL,
    stage           VARCHAR(20)     NOT NULL,
    PRIMARY KEY(TradingDay, strategyID, InstrumentID, orderType, stage)
);


################################################################################
## workingInfo
## 记录正在进行的订单
################################################################################
create table workingInfo(
    TradingDay      DATE            NOT NULL,
    strategyID      VARCHAR(50)     NOT NULL,
    vtSymbol        VARCHAR(20)     NOT NULL,
    vtOrderIDList   text            NOT NULL,   
    orderType       VARCHAR(50)     NOT NULL,
    volume          BIGINT          NOT NULL,
    stage           VARCHAR(20)     NOT NULL, 
    PRIMARY KEY(TradingDay, strategyID, vtSymbol, orderType, stage)
);

################################################################################
## pnl
## 记录正在进行的订单
################################################################################
create table pnl(
    TradingDay      DATE            NOT NULL,
    strategyID      VARCHAR(50)     NOT NULL,
    InstrumentID    VARCHAR(30)     NOT NULL,
    pnl             DECIMAL(15,3),
    PRIMARY KEY(TradingDay, strategyID, InstrumentID)
);


################################################################################
## signal
## 记录策略信号
################################################################################
create table tradingSignal(
    TradingDay      DATE            NOT NULL,
    strategyID      VARCHAR(50)     NOT NULL,
    InstrumentID    VARCHAR(30)     NOT NULL,
    volume          BIGINT          NOT NULL,
    direction       VARCHAR(20)     NOT NULL,
    param           SMALLINT        NOT NULL,
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
    vtOrderIDList   VARCHAR(100)     NOT NULL,
    direction       VARCHAR(20),
    volume          INT          
);


################################################################################
## winner
## 记录 止盈平仓单 的信息
################################################################################
create table winnerInfo(
    TradingDay      DATE         NOT NULL,
    strategyID      CHAR(50)     NOT NULL,
    InstrumentID    VARCHAR(30)  NOT NULL,
    vtOrderIDList   VARCHAR(100)     NOT NULL,
    direction       VARCHAR(20),
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

################################################################################
## lastInfo
## 保存最新的 tick 级别的数据
################################################################################
create table lastInfo(
    TradingDay      DATE            NOT NULL,
    updateTime      DATETIME        NOT NULL,
    ## -------------------------------------------------------------------------
    vtSymbol        VARCHAR(30)     NOT NULL,
    lastPrice       DECIMAL(10,3)   NOT NULL,
    volume          BIGINT,
    turnover        DECIMAL(30,3),
    openPrice       DECIMAL(10,3),
    highestPrice    DECIMAL(10,3),
    lowestPrice     DECIMAL(10,3),
    bidPrice1       DECIMAL(10,3),
    askPrice1       DECIMAL(10,3),
    bidVolume1      BIGINT,
    askVolume1      BIGINT,
    ## ---------------------------
    upperLimit      DECIMAL(10,3),
    lowerLimit      DECIMAL(10,3),
    PRIMARY KEY(TradingDay, vtSymbol)
);

