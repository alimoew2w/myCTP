# CTA 策略开发

## 步骤

1. 在 `/ctaStragegy/CTA_setting.json` 添加策略信息. 举个栗子:

        {
            "name": "Bollinger Band",
            "className": "BBStrategy",
            "vtSymbol": ["i1709",'rb1710','cu1709']
        }

2. 在 `/ctaStragegy/strategy/` 下面建立策略文件, 命名为 `strategyXXX`.

3. 开始建立策略...
