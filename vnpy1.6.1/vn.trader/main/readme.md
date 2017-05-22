# `main` 主函数入口

## 模块列表

### 主函数相关

- [X] `myTest.py`: 主函数入口
- [X] `vtPath.py`: 加载路径
- [X] `vtFunction.py`: 基本的常用函数定义
- [X] `vtConstant.py`: 常用的变量名称, 参考 `/main/language/chinese/text.py`
- [X] `vtText.py`: 将常量定义添加到 `vtText.py` 的局部字典中
- [ ] `vtEngine.py`: 主引擎
- [ ] `vtGateway.py`: 主要接口封装

### 接口模块相关

- [X] `/main/language/`: 语言模块, **不需要更改**
- [X] `/main/riskManager/`: 风控模块
- [ ] `/main/dataRecorder/`: 数据接收与处理, 参考 `/vn.data/`, 主要负责处理从 `CTP` 相关的 `MdApi` 和 `TdApi` 回调数据
- [X] `/main/gateway/`: 对各种数据接口 `API` 的封装与暴露:
    - [X] `ctpGateway`: 上期所 `CTP API` 
