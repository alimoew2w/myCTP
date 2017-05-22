# `riskManager` 模块

## 设置

风控的设置文件位于 `/main/riskManager/RM_setting.json`.

## 风控功能

1. `流量上限`: 在限定时间内允许下单的最大数量
2. `单笔委托上限`: 
3. `总成交上限`: 在 `mainEngine` 顶层控制的最大成交数量
4. `活动订单上限`: 允许的 `mainEngine.getAllWorkingOrders()` 的最大 **在线订单**
5. `单合约撤单上限`: 
