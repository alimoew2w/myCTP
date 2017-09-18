rm(list = ls())

setwd("/home/william/Documents/myCTP")

## =============================================================================
suppressWarnings(
    suppressMessages(
        source("./conf/Rconf/myInit.R")
    )
)
options(width = 150)
## =============================================================================

tradingDay <- '20170908'

## =============================================================================
## 获取交易的价格数据
## -----------------------------------------------------------------------------
mysql <- mysqlFetch('HiCloud', host = '192.168.1.166')
dtOrder <- dbGetQuery(mysql, paste("
        select * from tradingInfo
        where TradingDay = ", tradingDay)) %>%  
        as.data.table() %>% 
        .[, ':='(
            TradingDay = as.Date(TradingDay)
            # , offset     = iconv(offset, from = 'GB18030', to = 'utf8') 
            )]
## =============================================================================

for (i in 1:nrow(dtOrder)) {
  if (abs(dtOrder[i,price]) == 1) {
    dtOrder$price[i] <- 

    
  }
}


## =============================================================================
## 获取 bar 数据
## -----------------------------------------------------------------------------
mysql <- mysqlFetch('china_futures_bar', host = '192.168.1.166')
dtDaily <- dbGetQuery(mysql, paste("
        select TradingDay,InstrumentID,
               OpenPrice
               # ,HighPrice
               # ,LowPrice
               ,ClosePrice
        from daily
        where TradingDay = ", tradingDay,
        "and sector = 'allday'")) %>% as.data.table() %>% 
        .[, ":="(
            TradingDay = as.Date(TradingDay))]

mysql <- mysqlFetch('china_futures_info', host = '192.168.1.166')
dtMultiple <- dbGetQuery(mysql, paste("
        select TradingDay,InstrumentID,VolumeMultiple
        from VolumeMultiple
        where TradingDay = ", tradingDay)) %>% 
        as.data.table() %>% 
        .[, ":="(
            TradingDay = as.Date(TradingDay))]
## =============================================================================

## =============================================================================
## 对比数据
## 1. 如果是 开仓，以 OpenPrice 作为对比标准
## 2. 如果是 平仓，以 ClosePrice 作为对比标准
## -----------------------------------------------------------------------------
dt <- merge(dtOrder, dtDaily, all.x = TRUE, by = c('InstrumentID','TradingDay')) %>% 
      merge(., dtMultiple, all.x = TRUE, by = c('InstrumentID','TradingDay'))
for (i in 1:nrow(dt)) {
    ## -------------------------------------------------------------------------
    if (dt[i, offset == '开仓']) {
        dt[i, err := (price - OpenPrice) / OpenPrice]
        dt[i, pl := ifelse(direction == 'long', -1, 1) * 
                   ((price - OpenPrice) * volume * VolumeMultiple)]
    } else {
        dt[i, err := (price - ClosePrice) / ClosePrice]
        dt[i, pl := ifelse(direction == 'long', -1, 1) * 
                   ((price - ClosePrice) * volume * VolumeMultiple)]
    } 
    ## -------------------------------------------------------------------------
}
dt[, err := round(err,4)]
## =============================================================================


## =============================================================================
## 结果分析
## -----------------------------------------------------------------------------
## 多开，应该少 .002
dt[direction == 'long'][offset == '开仓']

## 空开, 应该多 .002
dt[direction == 'short'][offset == '开仓']

# dt[offset == '平仓']
dt[offset == '平仓'][err == 0]
dt[offset == '平仓'][err != 0]
## =============================================================================
dt[,sum(pl)]




## =============================================================================
## 对比数据
## 1. 如果是 开仓，以 OpenPrice 作为对比标准
## 2. 如果是 平仓，以 ClosePrice 作为对比标准
## -----------------------------------------------------------------------------
dt <- merge(dtOrder, dtDaily, all.x = TRUE, by = c('InstrumentID','TradingDay')) %>% 
      merge(., dtMultiple, all.x = TRUE, by = c('InstrumentID','TradingDay'))
temp <- dt[strategyID == 'OIStrategy'] %>% 
    .[, .(volume = .SD[,sum(volume)], price = .SD[, sum(volume * price) / sum(volume)])
     , by = c('InstrumentID','direction','offset')] %>% 
     merge(., dtMultiple[,.(InstrumentID, VolumeMultiple)], all.x = TRUE, by = c('InstrumentID')) %>% 
     
temp$volume[3] <- 3

res <- temp[, .(pl = (.SD[grep('平仓|平今|平昨',offset), price] - .SD[offset == '开仓', price]) * 
                ifelse(.SD[offset == '开仓', direction == 'long'], 1, -1) *
                .SD[1,VolumeMultiple] * .SD[1,volume]
        )
     , by = c('InstrumentID')]


## =============================================================================
## 对比数据
## -----------------------------------------------------------------------------
mysql <- mysqlFetch('HiCloud', host = '192.168.1.166')

yy1 <- dbGetQuery(mysql, paste("
        select * 
        from report_position_history
        where TradingDay = '2017-08-30'")) %>% 
        as.data.table()  %>% 
        .[,":="(InstrumentID = gsub('-long|-short','',index),
                TradingDay = as.Date(TradingDay))]

yy2 <- dbGetQuery(mysql, paste("
        select * 
        from report_position_history
        where TradingDay = '2017-08-31'")) %>% 
        as.data.table() %>% 
        .[,":="(InstrumentID = gsub('-long|-short','',index),
                TradingDay = as.Date(TradingDay))]

mysql <- mysqlFetch('china_futures_bar', host = '192.168.1.166')
dtDaily1 <- dbGetQuery(mysql, paste("
        select TradingDay,InstrumentID,
               OpenPrice
               # ,HighPrice
               # ,LowPrice
               ,ClosePrice
        from daily
        where TradingDay = 20170830", 
        "and sector = 'allday'")) %>% as.data.table() %>% 
        .[, ":="(
            TradingDay = as.Date(TradingDay))]

dtDaily2 <- dbGetQuery(mysql, paste("
        select TradingDay,InstrumentID,
               OpenPrice
               # ,HighPrice
               # ,LowPrice
               ,ClosePrice
        from daily
        where TradingDay = 20170831", 
        "and sector = 'allday'")) %>% as.data.table() %>% 
        .[, ":="(
            TradingDay = as.Date(TradingDay))]

temp1 <- merge(yy1, dtDaily1, all.x = TRUE, 
               by = c('TradingDay','InstrumentID'))

temp2 <- merge(yy2, dtDaily2, all.x = TRUE, 
               by = c('TradingDay','InstrumentID'))

temp2[, sum(position * ClosePrice * size)] - temp1[, sum(position * ClosePrice * size)]
