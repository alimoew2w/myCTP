## 发送邮件通知
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import codecs
from tabulate import tabulate

stratYY.ctaEngine.mainEngine.drEngine.getIndicatorInfo(dbName = stratYY.ctaEngine.mainEngine.dataBase,
                                                    initCapital = stratYY.ctaEngine.mainEngine.initCapital,
                                                    flowCapitalPre = stratYY.ctaEngine.mainEngine.flowCapitalPre,
                                                    flowCapitalToday = stratYY.ctaEngine.mainEngine.flowCapitalToday)
## -----------------------------------------------------------------
## -----------------------------------------------------------------------------

## 如果是多策略，使用数据库
## 如果是单个策略，使用策略名称
if stratYY.ctaEngine.mainEngine.multiStrategy:
    tempID = stratYY.ctaEngine.mainEngine.dataBase
else:
    tempID = stratYY.strategyID

sender = tempID + '@hicloud.com'

if stratYY.ctaEngine.mainEngine.multiStrategy:
    stratYY.tradingInfo = stratYY.ctaEngine.mainEngine.dbMySQLQuery(
        stratYY.ctaEngine.mainEngine.dataBase,
        """
        SELECT *
        FROM tradingInfo
        WHERE TradingDay = '%s'
        """ %(stratYY.ctaEngine.tradingDay))

## 公司内部人员
receiversMain = stratYY.ctaEngine.mainEngine.mailReceiverMain
## 其他人员
receiversOthers = stratYY.ctaEngine.mainEngine.mailReceiverOthers
## 抄送
# ccReceivers = stratYY.ctaEngine.mainEngine.mailCC

# 三个参数：第一个为文本内容，第二个 plain 设置文本格式，第三个 utf-8 设置编码
## 内容，例如
# message = MIMEText('Python 邮件发送测试...', 'plain', 'utf-8')
## -----------------------------------------------------------------------------
tempFile = os.path.join('/tmp',('tradingRecord_' + tempID + '.txt'))
with codecs.open(tempFile, "w", "utf-8") as f:
    # f.write('{0}'.format(40*'='))
    f.write('{0}'.format('\n' + 20 * '#'))
    f.write('{0}'.format(u'\n## 策略信息'))
    f.write('{0}'.format('\n' + 20 * '#'))
    f.write('{0}'.format('\n[TradingDay]: ' + stratYY.ctaEngine.tradingDate.strftime('%Y-%m-%d')))
    f.write('{0}'.format('\n[UpdateTime]: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    f.write('{0}'.format('\n[StrategyID]: ' + tempID))
    f.write('{0}'.format('\n[TraderName]: ' + stratYY.author))
    f.write('{0}'.format('\n' + 100*'-' + '\n'))
    ## -------------------------------------------------------------------------
    f.write('{0}'.format('\n' + 20 * '#'))
    f.write('{0}'.format(u'\n## 基金净值'))
    f.write('{0}'.format('\n' + 20 * '#'))
    f.write('{0}'.format('\n' + 100*'-') + '\n')
    f.write(tabulate(stratYY.ctaEngine.mainEngine.drEngine.accountBalance.transpose(),
                        headers = ['Index','Value'], tablefmt = 'rst'))
    f.write('{0}'.format('\n' + 100*'-') + '\n')
    ## -------------------------------------------------------------------------
    f.write('{0}'.format('\n' + 20 * '#'))
    f.write('{0}'.format(u'\n## 基金持仓'))
    f.write('{0}'.format('\n' + 20 * '#'))
    f.write('{0}'.format('\n' + 100*'-') + '\n')
    f.write('{0}'.format(stratYY.ctaEngine.mainEngine.drEngine.accountPosition))
    f.write('{0}'.format('\n' + 100*'-') + '\n')
    ## -------------------------------------------------------------------------
    f.write('{0}'.format('\n' + 20 * '#'))
    f.write('{0}'.format('\n## 当日已交易'))
    f.write('{0}'.format('\n' + 20 * '#'))
    f.write('{0}'.format('\n' + 100*'-') + '\n')
    if len(stratYY.tradingInfo) != 0:
        tempTradingInfo = stratYY.tradingInfo
        tempTradingInfo.index += 1
        f.write('{0}'.format(tempTradingInfo))
    f.write('{0}'.format('\n' + 100*'-') + '\n')
    ## -------------------------------------------------------------------------
    f.write('{0}'.format('\n' + 20 * '#'))
    f.write('{0}'.format('\n## 当日未交易'))
    f.write('{0}'.format('\n' + 20 * '#'))
    f.write('{0}'.format('\n' + 100*'-') + '\n')
    if len(stratYY.failedOrders) != 0:
        f.write('{0}'.format(pd.DataFrame(stratYY.failedOrders).transpose()))
    f.write('{0}'.format('\n' + 100*'-') + '\n')

## -----------------------------------------------------------------------------
# message = MIMEText(stratYY.strategyID, 'plain', 'utf-8')
fp = open(tempFile, "r")
message = MIMEText(fp.read().decode('string-escape').decode("utf-8"), 'plain', 'utf-8')
fp.close()

## 显示:发件人
message['From'] = Header(sender, 'utf-8')
## 显示:收件人
message['To']   =  Header('汉云交易员', 'utf-8')

## 主题
subject = stratYY.ctaEngine.tradingDay + u'：云扬1号『' + stratYY.ctaEngine.mainEngine.dataBase + '』交易播报'
message['Subject'] = Header(subject, 'utf-8')

try:
    smtpObj = smtplib.SMTP('localhost')
    smtpObj.sendmail(sender, receiversMain, message.as_string())
    print '\n' + '#'*80
    print "邮件发送成功"
    print '#'*80
except smtplib.SMTPException:
    print '\n' + '#'*80
    print "Error: 无法发送邮件"
    print '#'*80
## 间隔 1 秒
time.sleep(1)

## -----------------------------------------------------------------------------
# message = MIMEText(stratYY.strategyID, 'plain', 'utf-8')
fp      = open(tempFile, "r")
lines   = fp.readlines()
l       = lines[0:([i for i in range(len(lines)) if '当日已交易' in lines[i]][0] - 1)]
message = MIMEText(''.join(l).decode('string-escape').decode("utf-8"), 'plain', 'utf-8')
fp.close()

## 显示:发件人
message['From'] = Header(sender, 'utf-8')
## 显示:收件人
message['To']   =  Header('汉云管理员', 'utf-8')

## 主题
subject = stratYY.ctaEngine.tradingDay + u'：云扬1号『' + stratYY.ctaEngine.mainEngine.dataBase + '』交易播报'
message['Subject'] = Header(subject, 'utf-8')

try:
    smtpObj = smtplib.SMTP('localhost')
    smtpObj.sendmail(sender, receiversOthers, message.as_string())
    print '\n' + '#'*80
    print "邮件发送成功"
    print '#'*80
except smtplib.SMTPException:
    print '#'*80
    print "Error: 无法发送邮件"
    print '\n' + '#'*80
## 间隔 1 秒
time.sleep(1)
