# -*- coding: UTF-8 -*-
 
import smtplib
from email.mime.text import MIMEText
from email.header import Header
 
## -----------------------------------------------------------------------------
sender = stratYY.strategyID + '@hicloud.com'
# receivers = ['fl@hicloud-investment.com','lhg@hicloud-investment.com']  # 接收邮件
receivers = ['fl@hicloud-investment.com','lhg@hicloud-investment.com']
receivers = ['fl@hicloud-investment.com']
## -----------------------------------------------------------------------------


## -----------------------------------------------------------------------------
# 三个参数：第一个为文本内容，第二个 plain 设置文本格式，第三个 utf-8 设置编码
## 内容
# message = MIMEText('Python 邮件发送测试...', 'plain', 'utf-8')
import codecs
## -----------------------------------------------------------------------------
with codecs.open("/tmp/tradingRecord.txt", "w", "utf-8") as f:
    f.write('{0}'.format(40*'='))
    f.write('{0}'.format(u'\n##[策略信息]: '))
    f.write('{0}'.format('\n[TradingDay]: ' + mainEngine.ctaEngine.tradingDate.strftime('%Y-%m-%d')))
    f.write('{0}'.format('\n[UpdateTime]: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    f.write('{0}'.format('\n[StrategyID]: ' + stratYY.strategyID))
    f.write('{0}'.format('\n[TraderName]: ' + stratYY.author))
    f.write('{0}'.format('\n' + 40*'=' + '\n'))
    ## -------------------------------------------------------------------------
    f.write('{0}'.format(u'\n##[基金净值]: '))
    f.write('{0}'.format('\n' + 120*'-') + '\n')
    f.write('{0}'.format(mainEngine.drEngine.accountBalance))
    f.write('{0}'.format('\n' + 120*'-') + '\n')
    ## -------------------------------------------------------------------------    
    f.write('{0}'.format(u'\n##[基金持仓]: '))
    f.write('{0}'.format('\n' + 120*'-') + '\n')
    f.write('{0}'.format(mainEngine.drEngine.accountPosition))
    f.write('{0}'.format('\n' + 120*'-') + '\n')
    ## -------------------------------------------------------------------------
    f.write('{0}'.format('\n##[当日已交易]: '))
    f.write('{0}'.format('\n' + 120*'-') + '\n')
    if len(stratYY.tradingInfo) != 0:
        f.write('{0}'.format(stratYY.tradingInfo))
    f.write('{0}'.format('\n' + 120*'-') + '\n')
    ## -------------------------------------------------------------------------
    f.write('{0}'.format('\n##[当日未交易]: '))
    f.write('{0}'.format('\n' + 120*'-') + '\n')
    if len(stratYY.failedOrders) != 0:
        f.write('{0}'.format(pd.DataFrame(stratYY.failedOrders).transpose()))
    f.write('{0}'.format('\n' + 120*'-') + '\n')


## -----------------------------------------------------------------------------
# message = MIMEText(stratYY.strategyID, 'plain', 'utf-8')

# fp = codecs.open("/tmp/tradingRecord.txt", "r", "utf-8")
fp = open("/tmp/tradingRecord.txt", "r")
message = MIMEText(fp.read().decode('string-escape').decode("utf-8"), 'plain', 'utf-8')
fp.close()

## 显示:发件人
message['From'] = Header(sender, 'utf-8')
## 显示:收件人
message['To'] =  Header('汉云交易员', 'utf-8')

## 主题
subject = mainEngine.ctaEngine.tradingDay + u' ==> 交易播报'
message['Subject'] = Header(subject, 'utf-8')

try:
    smtpObj = smtplib.SMTP('localhost')
    smtpObj.sendmail(sender, receivers, message.as_string())
    print "邮件发送成功"
except smtplib.SMTPException:
    print "Error: 无法发送邮件"
