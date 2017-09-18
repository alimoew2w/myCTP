################################################################################
## myInit.R
## 设置
# __1. 账号、密码__
# 2. 文件路径
# 3. 需要的软件包
# __4. 参数设置__
################################################################################

pkgs <- c("tidyverse", "data.table", "parallel",
          "RMySQL", "stringr", "bit64", "Rcpp",
          "lubridate","zoo",'beepr','plotly',
          "fst","xml2",'rjson','printr')
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

vtSetting <- fromJSON(file = "./main/setting/VT_setting.json")
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
mysql_port <- 3306

#---------------------------------------------------
# mysqlFetch
# 函数，主要输入为
# database
#---------------------------------------------------
mysqlFetch <- function(dbName,
                       user = mysql_user,
                       pwd  = mysql_pwd,
                       host = mysql_host,
                       port = mysql_port){
  temp <- dbConnect(MySQL(),
                    dbname   = as.character(dbName),
                    user     = user,
                    password = pwd,
                    host     = host,
                    port     = port
                    )
}
################################################################################
