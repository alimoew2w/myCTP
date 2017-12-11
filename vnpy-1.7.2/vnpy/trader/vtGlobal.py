# encoding: UTF-8

"""
通过VT_setting.json加载全局配置
"""

## =============================================================================
import sys,os,subprocess
os.putenv('DISPLAY', ':0.0')
reload(sys)
sys.setdefaultencoding('utf8')
## =============================================================================

import traceback
import json
from .vtFunction import getJsonPath

## =============================================================================
# 判断操作系统
import re,datetime,time,csv
from datetime import datetime,time
## =============================================================================

## =============================================================================
## william
##　判断当天是否有交易
## -----------------------------------------------------------------------------
TradingDay = []
with open('./trading/ChinaFuturesCalendar.csv') as f:
    ChinaFuturesCalendar = csv.reader(f)
    for row in ChinaFuturesCalendar:
        if row[1] >= '20170101':
            TradingDay.append(row[1])
TradingDay.pop(0)

if datetime.now().strftime("%Y%m%d") not in TradingDay:
    print '#'*80
    sys.exit("启禀圣上，今日赌场不开张!!!")
    print '#'*80
## =============================================================================


settingFileName = "setting/VT_setting.json"
settingFilePath = getJsonPath(settingFileName, __file__)

globalSetting = {}      # 全局配置字典

try:
    with open(settingFilePath, 'rb') as f:
        setting = f.read()
        if type(setting) is not str:
            setting = str(setting, encoding='utf8')
        globalSetting = json.loads(setting)
except:
    traceback.print_exc()
    
