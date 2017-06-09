# `vn.py` 交易系统开发文档

## 问题与解决方法

> 天王盖地虎, 我自有招数!


### 中文写入 `MySQL` 的时候报错

    把策略的交易记录(`tempTradingInfo`) 写入 `MySQL` 的时候, 无法把中文的 `开仓` 或 `平仓` 顺利写入, 报错为

    UnicodeEncodeError: 'latin-1' codec can't encode characters in position 0-3: ordinal not in range(256)

原来, 这个是 `Python` 把字符写入 `MySQL` 的时候, 需要检测字符编码.

解决办法：

    在创建连接的时候设置一下编码，如在 `main/vtEngine.py/dbMySQLConnect()`：

    conn = MySQLdb.connect(host="localhost", user="root", passwd="root", db="db", use_unicode = True, charset="utf8")

即默认以 `utf8` 的编码进行存储.
