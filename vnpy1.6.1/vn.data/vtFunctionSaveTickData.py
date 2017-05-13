# encoding: UTF-8

################################################################################
## william
## vtFunction 包含的函数可以直接访问,
## 比如 
'''
print todayDate()
'''
## 比如:
## 保存当天的合约信息
'''

'''
################################################################################

"""
包含一些开发中常用的函数
"""

import os
import decimal
import json
import shelve
from datetime import datetime

import numpy as np
import pandas as pd
pd.set_option('display.width', 160)
pd.set_option('display.max_rows', 20)
from pandas import DataFrame,Series

MAX_NUMBER = 10000000000000
MAX_DECIMAL = 4

import vtEngineSaveTickData

################################################################################
## william
import sys
sys.path.append('/home/william/Documents/vnpy/vnpy-1.6.1/vn.trader/')


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
def loadMongoSetting():
    """载入MongoDB数据库的配置"""
    fileName = 'VT_setting.json'
    path     = os.path.abspath(os.path.dirname(__file__)) 
    fileName = os.path.join(path, fileName)  
    
    try:
        f       = file(fileName)
        setting = json.load(f)
        host    = setting['mongoHost']
        port    = setting['mongoPort']
        logging = setting['mongoLogging']
    except:
        host    = 'localhost'
        port    = 27017
        logging = False
        
    return host, port, logging

################################################################################
## william
## MySQL setting
################################################################################
# path = '/home/william/Documents/vnpy/vnpy-1.6.1/vn.trader'
# fileName = os.path.join(path, "VT_setting.json")
# ------------------------------------------------------------------------------
def loadMySQLSetting():
    """载入MongoDB数据库的配置"""
    fileName = 'VT_setting.json'
    path     = os.path.abspath(os.path.dirname(__file__)) 
    fileName = os.path.join(path, fileName)  
    
    try:
        f = file(fileName)
        setting = json.load(f)
        host    = setting['mysqlHost']
        port    = setting['mysqlPort']
    #   db      = setting['mysqlDB']
        user    = setting['mysqlUser']
        passwd  = setting['mysqlPassword']
    except:
        host    = '192.168.1.106'
        port    = 3306
    #   db      = 'china_futures_bar'
        user    = 'fl'
        passwd  = 'abc@123'
        
    return host, port, user, passwd

#----------------------------------------------------------------------
def todayDate():
    """获取当前本机电脑时间的日期"""
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)    

################################################################################
## william
## 保存 CTP md 的数据为 csv
## Ref: http://www.vnpie.com/forum.php?mod=viewthread&tid=964&highlight=%E6%95%B0%E6%8D%AE
################################################################################
'''
'''
def refreshDatarecodeSymbol():
    """ 保存合约信息到 dataRecorder/DR_setting.json """
    contractFileName = 'ContractData.vt'

    contractDict = {}
    ############################################################################
    ## william
    jfile = os.path.join('/home/william/Documents/myCTP/vnpy1.6.1/vn.data/dataRecorder/','DR_settingSaveTickData.json')
    jf    = open(jfile,'w')

    drSetting            = {}
    drSetting['tick']    = []
    drSetting['working'] = True

    f = shelve.open(os.path.join('/home/william/Documents/myCTP/vnpy1.6.1/vn.data/',contractFileName))
    if 'data' in f:
        d = f['data']
        print "全部期货与期权合约数量为:==> ",len(d)
        for key, value in d.items():
            contractDict[key] = value
            # print value.symbol, value.name, value.productClass, value.exchange, value.size, value.priceTick
            drSetting['tick'].append([value.symbol,value.exchange])
    f.close()

    ## print drSetting
    json.dump(drSetting,jf)
    jf.close()


if __name__ == '__main__':
    ## 保存合约信息到 DR_setting.json
    refreshDatarecodeSymbol()

