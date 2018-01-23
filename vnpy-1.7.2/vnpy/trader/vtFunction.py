# encoding: UTF-8

"""
包含一些开发中常用的函数
"""

import os,sys
import decimal
import json
from datetime import datetime
from shutil import copyfile

import numpy as np
import pandas as pd
pd.set_option('display.width', 200)
pd.set_option('display.max_rows', 100)
from pandas import DataFrame,Series
from datetime import datetime

import MySQLdb
from pandas.io import sql
import pymysql
from sqlalchemy import create_engine

MAX_NUMBER = 10000000000000
MAX_DECIMAL = 4

from vnpy.trader.vtGlobal import globalSetting

#----------------------------------------------------------------------
def safeUnicode(value):
    """检查接口数据潜在的错误，保证转化为的字符串正确"""
    # 检查是数字接近0时会出现的浮点数上限
    if type(value) is int or type(value) is float:
        if value > MAX_NUMBER:
            value = 0
    
    # 检查防止小数点位过多
    if type(value) is float:
        d = decimal.Decimal(str(value))
        if abs(d.as_tuple().exponent) > MAX_DECIMAL:
            value = round(value, ndigits=MAX_DECIMAL)
    
    return unicode(value)


#----------------------------------------------------------------------
def todayDate():
    """获取当前本机电脑时间的日期"""
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)    


# 图标路径
iconPathDict = {}

path = os.path.abspath(os.path.dirname(__file__))
for root, subdirs, files in os.walk(path):
    for fileName in files:
        if '.ico' in fileName:
            iconPathDict[fileName] = os.path.join(root, fileName)

#----------------------------------------------------------------------
def loadIconPath(iconName):
    """加载程序图标路径"""   
    global iconPathDict
    return iconPathDict.get(iconName, '')    
    


#----------------------------------------------------------------------
def getTempPath(name):
    """获取存放临时文件的路径"""
    tempPath = os.path.join(os.getcwd(), 'temp')
    if not os.path.exists(tempPath):
        os.makedirs(tempPath)
        
    path = os.path.join(tempPath, name)
    return path

## -----------------------------------------------------------------------------
def getLogPath(name):
    """获取存放临时文件的路径"""
    logPath = os.path.join(os.getcwd(), 'trading/log')
    if not os.path.exists(logPath):
        os.makedirs(logPath)
        
    path = os.path.join(logPath, name)
    return path

# JSON配置文件路径
jsonPathDict = {}

#----------------------------------------------------------------------
def getJsonPath(name, moduleFile):
    """
    获取JSON配置文件的路径：
    1. 优先从当前工作目录查找JSON文件
    2. 若无法找到则前往模块所在目录查找
    """
    currentFolder = os.getcwd()
    currentJsonPath = os.path.join(currentFolder, name)
    if os.path.isfile(currentJsonPath):
        jsonPathDict[name] = currentJsonPath
        return currentJsonPath
    
    moduleFolder = os.path.abspath(os.path.dirname(moduleFile))
    moduleJsonPath = os.path.join(moduleFolder, '.', name)
    jsonPathDict[name] = moduleJsonPath
    return moduleJsonPath

################################################################################
## william
## 当前日期所对应的交易所的交易日历: tradingDay
################################################################################
""" 交易日 """
fileName = 'ChinaFuturesCalendar.csv'
############################################################################
## william
path     = os.path.abspath(os.path.dirname(__file__))
ChinaFuturesCalendar = os.path.join(path, fileName)
############################################################################ 
ChinaFuturesCalendar = pd.read_csv(ChinaFuturesCalendar)
ChinaFuturesCalendar = ChinaFuturesCalendar[ChinaFuturesCalendar['days'].fillna(0) >= 20170101].reset_index(drop = True)    
# print ChinaFuturesCalendar.dtypes
ChinaFuturesCalendar.days = ChinaFuturesCalendar.days.apply(str)
ChinaFuturesCalendar.nights = ChinaFuturesCalendar.nights.apply(str)
for i in range(len(ChinaFuturesCalendar)):
    ChinaFuturesCalendar.loc[i, 'nights'] = ChinaFuturesCalendar.loc[i, 'nights'].replace('.0','')
## -----------------------------------------------------------------------------
def tradingDay():
    if 8 <= datetime.now().hour < 17:
        tempRes = datetime.now().strftime("%Y%m%d")
    else:
        temp = ChinaFuturesCalendar[ChinaFuturesCalendar['nights'] <= 
                datetime.now().strftime("%Y%m%d")]['days']
        tempRes = temp.tail(1).values[0]
    return tempRes 
## -----------------------------------------------------------------------------
def tradingDate():
    return datetime.strptime(tradingDay(),'%Y%m%d').date()
## -----------------------------------------------------------------------------
def lastTradingDay():
    return ChinaFuturesCalendar.loc[ChinaFuturesCalendar.days < 
                                    tradingDay(), 'days'].max()
## -----------------------------------------------------------------------------
def lastTradingDate():
    return datetime.strptime(lastTradingDay(),'%Y%m%d').date()


## =========================================================================
## william
## dbMySQLConnect
## -------------------------------------------------------------------------
def dbMySQLConnect(dbName):
    """连接 mySQL 数据库"""
    try:
        conn = MySQLdb.connect(db          = dbName, 
                               host        = globalSetting().vtSetting["mysqlHost"], 
                               port        = globalSetting().vtSetting["mysqlPort"], 
                               user        = globalSetting().vtSetting["mysqlUser"], 
                               passwd      = globalSetting().vtSetting["mysqlPassword"], 
                               use_unicode = True, 
                               charset     = "utf8")
        return conn
    except (MySQLdb.Error, MySQLdb.Warning, TypeError) as e:
        print e
    # finally:
    #     conn.close()
## =============================================================================

## =============================================================================
## william
## 从 MySQL 数据库查询数据
## -----------------------------------------------------------------------------
def dbMySQLQuery(dbName, query):
    """ 从 MySQL 中读取数据 """
    try:
        conn = MySQLdb.connect(db          = dbName, 
                               host        = globalSetting().vtSetting["mysqlHost"], 
                               port        = globalSetting().vtSetting["mysqlPort"], 
                               user        = globalSetting().vtSetting["mysqlUser"], 
                               passwd      = globalSetting().vtSetting["mysqlPassword"], 
                               use_unicode = True, 
                               charset     = "utf8")
        mysqlData = pd.read_sql(str(query), conn)
        return mysqlData
    except (MySQLdb.Error, MySQLdb.Warning, TypeError) as e:
        print e
    finally:
        conn.close()
## =============================================================================



## =============================================================================
## william
## 从 MySQL 数据库查询数据
## -----------------------------------------------------------------------------
def fetchMySQL(db, query):
    ## 用sqlalchemy构建数据库链接 engine
    ## 记得使用 ?charset=utf8 解决中文乱码的问题
    try:
        mysqlInfo = 'mysql+pymysql://{}:{}@{}:{}/{}?charset=utf8'.format(
                        globalSetting().vtSetting["mysqlUser"],
                        globalSetting().vtSetting["mysqlPassword"],
                        globalSetting().vtSetting["mysqlHost"],
                        globalSetting().vtSetting["mysqlPort"],
                        db)
        engine = create_engine(mysqlInfo)
        df = pd.read_sql(query, con = engine)
        return df
    except:
        print u"读取 MySQL 数据库失败"
        None


## =============================================================================
## william
## 写入 MySQL
## -----------------------------------------------------------------------------
def saveMySQL(df, db, tbl, over):
    ## 用sqlalchemy构建数据库链接 engine
    ## 记得使用 ?charset=utf8 解决中文乱码的问题
    try:
        mysqlInfo = 'mysql+pymysql://{}:{}@{}:{}/{}?charset=utf8'.format(
                        globalSetting().vtSetting["mysqlUser"],
                        globalSetting().vtSetting["mysqlPassword"],
                        globalSetting().vtSetting["mysqlHost"],
                        globalSetting().vtSetting["mysqlPort"],
                        db)
        engine = create_engine(mysqlInfo)
        df.to_sql(name      = tbl, 
                  con       = engine, 
                  if_exists = over, 
                  index     = False)
    except:
        print u"写入 MySQL 数据库失败"
        None

## =========================================================================
## 保存合约信息
def saveContractInfo():
    try:
        dataFileOld = os.path.join(globalSetting().vtSetting['DATA_PATH'],
                                   globalSetting.accountID,
                                   'ContractInfo',
                                   tradingDay() + '.csv')
        dataFileNew = os.path.normpath(os.path.join(
                                   globalSetting().vtSetting['ROOT_PATH'],
                                   './temp/contract.csv'))
        if os.path.exists(dataFileOld):
            dataOld = pd.read_csv(dataFileOld)
            dataNew = pd.read_csv(dataFileNew)
            for i in range(dataOld.shape[0]):
                if dataNew.at[i,'symbol'] not in dataOld.symbol.values:
                    dataOld = dataOld.append(dataNew.loc[i], ignore_index = True)
            dataOld.to_csv(dataFileOld, index = False)
        else:    
            copyfile(dataFileNew,dataFileOld)
    except:
        None
## =========================================================================
