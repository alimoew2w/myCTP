# encoding: UTF-8

"""
通过VT_setting.json加载全局配置
"""

## =============================================================================
import sys,os
## =============================================================================

import traceback
import json,csv
import datetime
## =============================================================================
    
class globalSetting(object):
    def __init__(self):
        self.accountID   = ''
        self.accountName = ''
        self.path = os.path.dirname(__file__)

        ## ---------------------------------------------------------------------
        ## vtSetting
        self.vtSettingFile = "VT_setting.json"
        self.vtSettingPath = os.path.join(self.path, 'setting', self.vtSettingFile)

        try:
            with open(self.vtSettingPath, 'rb') as f:
                setting = f.read()
                if type(setting) is not str:
                    setting = str(setting, encoding='utf8')
                self.vtSetting = json.loads(setting)
        except:
            traceback.print_exc()
        ## ---------------------------------------------------------------------

        ## ---------------------------------------------------------------------
        ## CTPAccount
        self.CTPFile = 'CTP_connect.json'
        tempPath     = os.path.normpath(os.path.join(
                       self.path, '..', '..'))
        self.CTPPath = os.path.join(tempPath, 'trading/account', self.CTPFile)

        try:
            with open(self.CTPPath, 'rb') as f:
                account = f.read()
                if type(account) is not str:
                    account = str(account, encoding='utf8')
                self.CTPAccount = json.loads(account)
        except:
            traceback.print_exc()
        ## ---------------------------------------------------------------------   

        ## ---------------------------------------------------------------------   
        ## allTradingDay
        self.allTradingDay = []
        self.calendarFile = 'ChinaFuturesCalendar.csv'
        self.calendarPath = os.path.join(self.path, self.calendarFile)
        with open(self.calendarPath) as f:
            ChinaFuturesCalendar = csv.reader(f)
            for row in ChinaFuturesCalendar:
                if row[1] >= '20170101':
                    self.allTradingDay.append(row[1])
        self.allTradingDay.pop(0)
        ## ---------------------------------------------------------------------   
