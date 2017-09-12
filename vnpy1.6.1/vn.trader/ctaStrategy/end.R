## =============================================================================
## close.R
## 在收盘的时候跑脚本
## 处理不同策略的订单
## =============================================================================

# if (! as.numeric(format(Sys.time(),'%H')) %in% c(14,15)) {
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
if (as.numeric(format(Sys.time(),'%H')) < 18) {
    currTradingDay <- ChinaFuturesCalendar[days <= format(Sys.Date(),'%Y%m%d')][.N]
} else {
    currTradingDay <- ChinaFuturesCalendar[nights <= format(Sys.Date(),'%Y%m%d')][.N]
}

## =============================================================================
## 
## =============================================================================
mysql <- mysqlFetch(accountDB)
dtPositionOI <- dbGetQuery(mysql,paste("
    select * from positionInfo
    where strategyID = 'OIStrategy'
    and TradingDay = ", currTradingDay[1,gsub('-','',days)])) %>% 
    as.data.table()

if (nrow(dtPositionOI) != 0){
    dtOpenYY <- dbGetQuery(mysql, paste("
        select * from tradingOrders
        where strategyID = 'YYStrategy'
        and stage = 'Open'
        and TradingDay = ", currTradingDay[1,gsub('-','',days)])) %>% 
        as.data.table() %>% 
        .[, direction := ifelse(orderType %in% c('buy','cover'), 'long', 'short')]

    if (nrow(dtOpenYY) != 0) {
      ## ===========================================================================================
      dtEnd <- merge(dtOpenYY[,.(TradingDay,strategyID,InstrumentID,direction,volume, orderType)],
                       dtPositionOI[,.(TradingDay,strategyID,InstrumentID,direction,volume)],
                       by = c('InstrumentID','direction'), all = TRUE) %>% 
      .[, ":="(volume.x = ifelse(is.na(volume.x), 0, volume.x),
               volume.y = ifelse(is.na(volume.y), 0, volume.y))] %>% 
      .[, deltaVolume := volume.x - volume.y] 

      dtUpdateStrategyID <- dtEnd[volume.x != 0 & volume.y != 0]
      if (nrow(dtUpdateStrategyID) != 0) {
          for (i in 1:nrow(dtUpdateStrategyID)) {
              if (dtUpdateStrategyID[i, deltaVolume] >= 0) {
                  sql <- paste("update positionInfo 
                                set strategyID = 'YYStrategy'
                                where strategyID = 'OIStrategy' 
                                and TradingDay = ", currTradingDay[1,gsub('-','',days)],
                                "and InstrumentID = ", paste0("'",dtUpdateStrategyID[i,InstrumentID],"'"),
                                "and direction = ", paste0("'",dtUpdateStrategyID[i,direction],"'")
                                )
                  dbSendQuery(mysql,sql)

                  ## -------------------------------------------------------------
                  ## 把交易的信息写入 tradingInfo
                  ## -------------------------------------------------------------
                  tempResYY <- data.table(strategyID = 'YYStrategy',
                                          InstrumentID = dtUpdateStrategyID[i,InstrumentID],
                                          TradingDay = currTradingDay[1,days],
                                          tradeTime = format(Sys.time(),'%Y-%m-%d %H:%M:%S'),
                                          direction = dtUpdateStrategyID[i,direction],
                                          offset = '开仓',
                                          volume = dtUpdateStrategyID[i,volume.y],
                                          price = 1)
                  tempResOI <- data.table(strategyID = 'OIStrategy',
                                          InstrumentID = dtUpdateStrategyID[i,InstrumentID],
                                          TradingDay = currTradingDay[1,days],
                                          tradeTime = format(Sys.time(),'%Y-%m-%d %H:%M:%S'),
                                          direction = ifelse(dtUpdateStrategyID[i,direction == 'long'],
                                                             'short', 'long'),
                                          offset = '平仓',
                                          volume = dtUpdateStrategyID[i,volume.y],
                                          price = -1)
                  
                  dbWriteTable(mysql, 'tradingInfo',
                              rbind(tempResYY, tempResOI), row.names = FALSE, append = TRUE)

                  ## -------------------------------------------------------------
                  ## 更新 tradingOrders
                  ## -------------------------------------------------------------
                  sql <- paste("update tradingOrders
                                set volume = ",dtUpdateStrategyID[i, deltaVolume],
                                "where strategyID = 'YYStrategy' 
                                and TradingDay = ", currTradingDay[1,gsub('-','',days)],
                                "and InstrumentID = ", paste0("'",dtUpdateStrategyID[i,InstrumentID],"'"),
                                "and orderType = ",paste0("'",dtUpdateStrategyID[i,orderType],"'"),
                                "and stage = 'open'"
                                )
                  dbSendQuery(mysql,sql)
              } else {
                  # sql <- paste("update positionInfo 
                  #   set volume = ",dtUpdateStrategyID[i, volume.x],
                  #   ", strategyID = 'YYStrategy',
                  #   TradingDay = ",currTradingDay[1,gsub('-','',days)],
                  #   "where strategyID = 'OIStrategy'
                  #   and InstrumentID = ", paste0("'",dtUpdateStrategyID[i,InstrumentID],"'",
                  #   "and TradingDay = ", currTradingDay[1,gsub('-','',days)])
                  #   )
                  # dbSendQuery(mysql, sql)

                  # tempRes <- dtUpdateStrategyID[i,.(strategyID = strategyID.x,InstrumentID,
                  #                                  TradingDay = TradingDay.y,
                  #                                  direction,
                  #                                  volume = abs(deltaVolume))]
                  # sql <- paste("delete from positionInfo
                  #                           where strategyID = 'OIStrategy'
                  #                           and InstrumentID = ", paste0("'",tempRes[1,InstrumentID],"'"),
                  #                           "and TradingDay = ", tempRes[1,gsub('-','',TradingDay)],
                  #                           "and direction = ", paste0("'",tempRes[1,direction],"'"))
                  # dbSendQuery(mysql, sql)
                  # dbWriteTable(mysql, 'positionInfo',
                  #             tempRes, row.names = FALSE, append = TRUE)  

                  ## -------------------------------------------------------------
                  sql <- paste("update positionInfo
                    set volume = ",dtUpdateStrategyID[i, abs(deltaVolume)],
                    "where strategyID = 'OIStrategy'
                    and InstrumentID = ", paste0("'",dtUpdateStrategyID[i,InstrumentID],"'"),
                    "and TradingDay = ", dtUpdateStrategyID[i, gsub('-','',TradingDay.x)],
                    "and direction = ", paste0("'",dtUpdateStrategyID[i,direction],"'")
                    )
                  dbSendQuery(mysql, sql)

                  tempRes <- dtUpdateStrategyID[i,.(strategyID = strategyID.x, InstrumentID,
                                                   TradingDay = currTradingDay[1,days],
                                                   direction,
                                                   volume = volume.x)]
                  dbWriteTable(mysql, 'positionInfo',
                              tempRes, row.names = FALSE, append = TRUE)

                  ## -------------------------------------------------------------
                  ## 把交易的信息写入 tradingInfo
                  ## -------------------------------------------------------------
                  tempResYY <- data.table(strategyID = 'YYStrategy',
                                          InstrumentID = dtUpdateStrategyID[i,InstrumentID],
                                          TradingDay = currTradingDay[1,days],
                                          tradeTime = format(Sys.time(),'%Y-%m-%d %H:%M:%S'),
                                          direction = dtUpdateStrategyID[i,direction],
                                          offset = '开仓',
                                          volume = dtUpdateStrategyID[i,volume.x],
                                          price = 1)
                  tempResOI <- data.table(strategyID = 'OIStrategy',
                                          InstrumentID = dtUpdateStrategyID[i,InstrumentID],
                                          TradingDay = currTradingDay[1,days],
                                          tradeTime = format(Sys.time(),'%Y-%m-%d %H:%M:%S'),
                                          direction = ifelse(dtUpdateStrategyID[i,direction == 'long'],
                                                             'short', 'long'),
                                          offset = '平仓',
                                          volume = dtUpdateStrategyID[i,volume.x],
                                          price = -1)
                  
                  dbWriteTable(mysql, 'tradingInfo',
                              rbind(tempResYY, tempResOI), row.names = FALSE, append = TRUE)

              }
          }
      } else {
        NULL
      }

      dtCloseOI <- dtEnd[deltaVolume < 0] %>% 
                  .[, ":="(
                    TradingDay = currTradingDay[1,days],
                    strategyID = 'OIStrategy',
                    orderType = ifelse(direction == 'long', 'sell', 'cover'),
                    volume = abs(deltaVolume),
                    stage = 'close'
                    )]
      tempRes <- dtCloseOI[,.(TradingDay,strategyID,InstrumentID,
                             orderType,volume,stage)]
      mysql <- mysqlFetch(accountDB)
      dbSendQuery(mysql, paste("
          delete from tradingOrders where strategyID = ",
          paste0("'","OIStrategy","'"),
          "and stage = ",
          paste0("'","close","'"),
          "and TradingDay = ", currTradingDay[1,days]))
      dbWriteTable(mysql, 'tradingOrders',
                  tempRes, row.names = FALSE, append = TRUE)

    } else {
      dtCloseOI <- dtPositionOI[, .(
                    TradingDay = currTradingDay[1,days],
                    InstrumentID,
                    strategyID = 'OIStrategy',
                    orderType = ifelse(direction == 'long', 'sell', 'cover'),
                    volume,
                    stage = 'close'
                    )]
      tempRes <- dtCloseOI[,.(TradingDay,strategyID,InstrumentID,
                             orderType,volume,stage)]
      mysql <- mysqlFetch(accountDB)
      dbSendQuery(mysql, paste("
          delete from tradingOrders where strategyID = ",
          paste0("'","OIStrategy","'"),
          "and stage = ",
          paste0("'","close","'"),
          "and TradingDay = ", currTradingDay[1,days]))
      dbWriteTable(mysql, 'tradingOrders',
                  tempRes, row.names = FALSE, append = TRUE)
    }
    ## ===========================================================================================
####################################################################################################
} else {
    NULL
}

mysql <- mysqlFetch(accountDB)
sql <- "delete from tradingOrders
        where volume = 0;"
dbSendQuery(mysql, sql)
