## =============================================================================
## fail.R
## 在开盘的时候跑脚本
## 处理不同策略的订单
## =============================================================================

# if (! as.numeric(format(Sys.time(),'%H')) %in% c(8,9,20,21)) {
#   stop("不是开盘时间哦！！！")
# }

rm(list = ls())

accountDB <- commandArgs(trailingOnly = TRUE)
# accountDB <- 'FL_SimNow'
setwd("/home/william/Documents/myCTP/vnpy1.6.1/vn.trader")
suppressWarnings(
  suppressMessages(
    source("./ctaStrategy/conf/Rconf/myInit.R")
  )
)

ChinaFuturesCalendar <- fread("./main/ChinaFuturesCalendar.csv")

## 计算交易日历
if (as.numeric(format(Sys.time(),'%H')) < 17) {
    currTradingDay <- ChinaFuturesCalendar[days <= format(Sys.Date(),'%Y%m%d')][.N]
} else {
    currTradingDay <- ChinaFuturesCalendar[nights <= format(Sys.Date(),'%Y%m%d')][.N]
}
lastTradingday <- ChinaFuturesCalendar[days < currTradingDay[.N, days]][.N]

## =============================================================================
## 从 MySQL 数据库提取数据
## =============================================================================
mysql <- mysqlFetch(dbName = accountDB)
dtFailedInfo <- dbGetQuery(mysql,"
        select * from failedInfo
    ") %>% as.data.table() 
# dtFailedInfoOpen <- dtFailedInfo[offset == '开仓']
# dtFailedInfoClose <- dtFailedInfo[offset == '平仓']


dtOrders <- dbGetQuery(mysql,"
        select * from tradingOrders
    ") %>% as.data.table() 
# dtOrdersOpen <- dtOrders[stage == 'open']
# dtOrdersClose <- dtOrders[stage == 'close']

dtPosition <- dbGetQuery(mysql,"
        select * from positionInfo
    ") %>% as.data.table() %>% 
    .[order(TradingDay)]
## =============================================================================



## =============================================================================
## dtFailedInfoOpen vs dtOrdersClose
## =============================================================================
for (i in 1:nrow(dtFailedInfo)) {
    tempInstrumentID <- dtFailedInfo[i,InstrumentID]

    if (! tempInstrumentID %in% dtOrders[,InstrumentID]) next

    tempDirection  <- dtFailedInfo[i, direction]
    tempOffset     <- dtFailedInfo[i,offset]
    tempVolume     <- dtFailedInfo[i,volume]
    tempStrategyID <- dtFailedInfo[i, strategyID]
    tempTradingDay <- dtFailedInfo[i, TradingDay]

    if (tempOffset == '开仓') {
        ## ---------------------------------------------------------------------
        tempOrders <- dtOrders[InstrumentID == tempInstrumentID & 
                               stage == 'close' & 
                               orderType == ifelse(tempDirection == 'long',
                                                   'sell', 'cover')]
        if (nrow(tempOrders) == 0) next

        for (j in 1:nrow(tempOrders)) {
            diffVolume <- tempVolume - tempOrders[j,volume]

            dtFailedInfo[i, volume := ifelse(diffVolume <= 0, 0, diffVolume)]
            dtOrders[strategyID == tempOrders[j,strategyID] &
                     InstrumentID == tempInstrumentID &
                     stage == 'close' &
                     orderType == tempOrders[j,orderType], volume := 
                                    ifelse(diffVolume <= 0, abs(diffVolume), 0)]

            tempTradingInfo1 <- data.table(strategyID = tempStrategyID,
                                  InstrumentID = tempInstrumentID,
                                  TradingDay = tempTradingDay,
                                  tradeTime = format(Sys.time(),'%Y-%m-%d %H:%M:%S'),
                                  direction = tempDirection,
                                  offset = '开仓',
                                  volume = ifelse(diffVolume <= 0, tempVolume, tempOrders[j,volume]),
                                  price = 1)
            tempTradingInfo2 <- data.table(strategyID = tempOrders[j, strategyID],
                                  InstrumentID = tempOrders[j, InstrumentID],
                                  TradingDay = tempOrders[j, TradingDay],
                                  tradeTime = format(Sys.time(),'%Y-%m-%d %H:%M:%S'),
                                  direction = tempOrders[j,orderType],
                                  offset = '平仓',
                                  volume = ifelse(diffVolume <= 0, tempVolume, tempOrders[j,volume]),
                                  price = -1)
            dbWriteTable(mysql, 'tradingInfo',
                        rbind(tempTradingInfo1,tempTradingInfo2), row.names = FALSE, append = TRUE)
            # print(rbind(tempTradingInfo1,tempTradingInfo2))

            mysql <- mysqlFetch(accountDB)
            dtPosition <- dbGetQuery(mysql,"
                        select * from positionInfo
                    ") %>% as.data.table()
            if (nrow(dtPosition[strategyID == tempTradingInfo1[,strategyID] &
                                TradingDay == tempTradingInfo1[,TradingDay] &
                                InstrumentID == tempTradingInfo1[,InstrumentID] &
                                direction == tempTradingInfo1[,direction]]) != 0) {
                dtPosition[strategyID == tempTradingInfo1[,strategyID] &
                                TradingDay == tempTradingInfo1[,TradingDay] &
                                InstrumentID == tempTradingInfo1[,InstrumentID] &
                                direction == tempTradingInfo1[,direction], volume := volume + tempTradingInfo1[,volume]]
                dbSendQuery(mysql,"
                        truncate table positionInfo
                    ")
                dbWriteTable(mysql, 'positionInfo', dtPosition, row.names = FALSE, append = TRUE)
            } else {
                tempRes <- tempTradingInfo1[,.(
                        strategyID,
                        InstrumentID,
                        TradingDay,
                        direction,
                        volume
                    )]
                dbWriteTable(mysql, 'positionInfo', tempRes, row.names = FALSE, append = TRUE)
            }
                    
            # dtFailedInfo <- dtFailedInfo[volume != 0]
            dtOrders <- dtOrders[volume != 0]

            if (diffVolume <= 0) break
        }
        ## ---------------------------------------------------------------------
    } else {
        ## ---------------------------------------------------------------------
        tempOrders <- dtOrders[InstrumentID == tempInstrumentID & 
                               stage == 'open' & 
                               orderType == ifelse(tempDirection == 'long',
                                                   'short', 'buy')]
        if (nrow(tempOrders) == 0) next

        for (j in 1:nrow(tempOrders)) {
            diffVolume <- tempVolume - tempOrders[j,volume]

            dtFailedInfo[i, volume := ifelse(diffVolume <= 0, 0, diffVolume)]
            dtOrders[strategyID == tempOrders[j,strategyID] &
                     InstrumentID == tempInstrumentID &
                     stage == 'open' &
                     orderType == tempOrders[j,orderType], volume := 
                                    ifelse(diffVolume <= 0, abs(diffVolume), 0)]

            tempTradingInfo1 <- data.table(strategyID = tempStrategyID,
                                  InstrumentID = tempInstrumentID,
                                  TradingDay = tempTradingDay,
                                  tradeTime = format(Sys.time(),'%Y-%m-%d %H:%M:%S'),
                                  direction = tempDirection,
                                  offset = '平仓',
                                  volume = ifelse(diffVolume <= 0, diffVolume, tempOrders[j,volume]),
                                  price = -1)
            tempTradingInfo2 <- data.table(strategyID = tempOrders[j, strategyID],
                                  InstrumentID = tempOrders[j, InstrumentID],
                                  TradingDay = tempOrders[j, TradingDay],
                                  tradeTime = format(Sys.time(),'%Y-%m-%d %H:%M:%S'),
                                  direction = tempOrders[j,orderType],
                                  offset = '开仓',
                                  volume = ifelse(diffVolume <= 0, diffVolume, tempOrders[j,volume]),
                                  price = 1)
            dbWriteTable(mysql, 'tradingInfo',
                        rbind(tempTradingInfo1,tempTradingInfo2), row.names = FALSE, append = TRUE)
            # print(rbind(tempTradingInfo1,tempTradingInfo2))

            mysql <- mysqlFetch(accountDB)
            dtPosition <- dbGetQuery(mysql,"
                        select * from positionInfo
                    ") %>% as.data.table()
            if (nrow(dtPosition[strategyID == tempTradingInfo2[,strategyID] &
                                TradingDay == tempTradingInfo2[,TradingDay] &
                                InstrumentID == tempTradingInfo2[,InstrumentID] &
                                direction == tempTradingInfo2[,direction]]) != 0) {
                dtPosition[strategyID == tempTradingInfo2[,strategyID] &
                                TradingDay == tempTradingInfo2[,TradingDay] &
                                InstrumentID == tempTradingInfo2[,InstrumentID] &
                                direction == tempTradingInfo2[,direction], volume := volume + tempTradingInfo2[,volume]]
                dbSendQuery(mysql,"
                        truncate table positionInfo
                    ")
                dbWriteTable(mysql, 'positionInfo', dtPosition, row.names = FALSE, append = TRUE)
            } else {
                tempRes <- tempTradingInfo2[,.(
                        strategyID,
                        InstrumentID,
                        TradingDay,
                        direction,
                        volume
                    )]
                dbWriteTable(mysql, 'positionInfo', tempRes, row.names = FALSE, append = TRUE)
            }
                    
            # dtFailedInfo <- dtFailedInfo[volume != 0]
            dtOrders <- dtOrders[volume != 0]

            if (diffVolume <= 0) break
        }
        ## ---------------------------------------------------------------------
    }
}

mysql <- mysqlFetch(dbName = accountDB)
dbSendQuery(mysql, "
        truncate table failedInfo
    ")
dbWriteTable(mysql, 'failedInfo', dtFailedInfo, row.names = FALSE, append = TRUE)

dbSendQuery(mysql, "
        truncate table tradingOrders
    ")
dbWriteTable(mysql, 'tradingOrders', dtOrders, row.names = FALSE, append = TRUE)
