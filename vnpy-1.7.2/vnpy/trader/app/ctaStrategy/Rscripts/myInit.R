################################################################################
## myInit.R
## 设置
# __1. 账号、密码__
# 2. 文件路径
# 3. 需要的软件包
# __4. 参数设置__
################################################################################

pkgs <- c("tidyverse", "data.table",
          "RMySQL", "stringr", "bit64", "Rcpp",
          "lubridate",'rjson','magrittr')
##------------------------------------------------------------------------------
if(length(pkgs[!pkgs %in% installed.packages()]) != 0){
  sapply(pkgs[!pkgs %in% installed.packages()], install.packages)
}
##------------------------------------------------------------------------------
sapply(pkgs, require, character.only = TRUE)

##------------------------------------------------------------------------------
options(digits = 12, digits.secs = 6, width = 120,
        datatable.verbose = FALSE, scipen = 8)
##------------------------------------------------------------------------------

vtSetting <- fromJSON(file = "./vnpy/trader/setting/VT_setting.json")

## =============================================================================
suppFunction <- function(x) {
  suppressWarnings({
    suppressMessages({
      x
    })
  })
}


################################################################################
## MySQL
## 链接到 MySQL 数据库，以获取数据
################################################################################

MySQL(max.con = 300)
for( conns in dbListConnections(MySQL()) ){
  dbDisconnect(conns)
}

mysql_user <- 'fl'
mysql_pwd  <- 'abc@123'
mysql_host <- vtSetting$mysqlHost
if (grepl('imwork', mysql_host)) {
  mysql_port <- 24572
} else {
  mysql_port <- 3306
}


#---------------------------------------------------
# mysqlFetch
# 函数，主要输入为
# database
#---------------------------------------------------
mysqlFetch <- function(db,
                       host = mysql_host,
                       port = mysql_port,
                       user = mysql_user,
                       pwd  = mysql_pwd){
  dbConnect(MySQL(),
    dbname   = as.character(db),
    host     = host,
    port     = port,
    user     = user,
    password = pwd)
}
################################################################################


mysqlQuery <- function(db, query,
                       host = mysql_host,
                       port = mysql_port,
                       user = mysql_user,
                       pwd  = mysql_pwd) {
  mysql <- mysqlFetch(db)
  dt <- suppFunction(dbGetQuery(mysql, query)) %>% as.data.table()
  dbDisconnect(mysql)
  return(dt)
}


mysqlWrite <- function(db, tbl, 
                       data, isTruncated = FALSE,
                       host = mysql_host,
                       port = mysql_port,
                       user = mysql_user,
                       pwd  = mysql_pwd) {
  mysql <- mysqlFetch(db)

  if (isTruncated) {
    suppFunction(
      dbSendQuery(mysql, paste('truncate table', tbl))
    )
  }

  suppFunction(
    dbWriteTable(mysql, tbl,
                 data, row.names = F, append = T)
  )

  dbDisconnect(mysql)
}
