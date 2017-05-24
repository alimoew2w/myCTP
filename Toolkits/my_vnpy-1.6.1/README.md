# vn.py - 基于python的开源交易平台开发框架

---
### 项目捐赠

过去一个季度中收到了开源社区用户相当金额的捐赠，在此深表感谢！所有的捐赠资金都投入到了vn.py社区基金中，用于支持vn.py项目的运作。最近主要的一个支出是相关文档编写，目前来看文档完成的速度和质量都显著超出预期。

先强调一下：**vn.py是开源项目，可以永久免费使用，并没有强制捐赠的要求！！！**

捐赠方式：支付宝3216630132@qq.com（*晓优）

计划长期维护一份捐赠清单，所以请在留言中注明是项目捐赠以及捐赠人的名字（当然想匿名的用户就随意了）。


---
### Quick Start

对于大部分用户来说，无需自行编译API接口，可以直接使用vn.trader进行交易和策略开发：

1. 准备一台Windows 7 64位系统的电脑

2. 安装[Anaconda](http://www.continuum.io/downloads)：下载**Anaconda 4.0.0** Python 2.7 32位版本，**注意必须是32位**

3. 安装[MongoDB](https://www.mongodb.org/downloads#production)：下载Windows 64-bit 2008 R2+版本

4. 安装pymongo：在cmd中运行pip install pymongo

5. 参考[这里](http://jingyan.baidu.com/article/6b97984dbeef881ca2b0bf3e.html)，将MongoDB注册为Windows服务并启动

6. 安装[Visual C++  Redistributable Packages for VS2013](https://www.microsoft.com/en-gb/download/details.aspx?id=40784)，中英文随意

7. 在本页面选择Download ZIP下载项目代码，并解压到C:\vnpy

8. 在[SimNow](http://simnow.com.cn/)注册CTP仿真账号，记下你的**账号、密码、经纪商编号**，然后下载快期查询你的**交易和行情服务器地址**

9. 把C:\vnpy\vn.trader\ctpGateway\CTP_connect.json中的账号、密码、服务器等修改为上一步注册完成后你的信息（注意使用专门的编程编辑器，如Sublime Text等，防止json编码出错）

10. 双击运行C:\vnpy\vn.trader\vtMain.py，开始交易！


对于想研究API封装的用户，可以参考[vnpy.org](http://vnpy.org)上面的教程一步步操作。

其他作者建议使用的软件工具：

* [WingIDE](http://wingware.com/)：非常好用的Python集成开发环境（作者就是用它写的vn.py）

* [Robomongo](https://robomongo.org/)：MongoDB的图形化客户端，方便监控和修改数据

* [Sublime Text](http://www.sublimetext.com/)：针对编程的文本编辑器，当然你也可以使用Vim或者Emacs

* [PyQtGraph](http://www.pyqtgraph.org/)：适用于开发实时更新数据的图表，如Tick图、K线图、期权波动率曲线等（Matplotlib渲染开销太大，用于实盘绘图可能拖慢整个程序）

* [Visual Studio 2013](https://www.visualstudio.com/en-us/downloads/download-visual-studio-vs.aspx)：这个就不多说了（作者编译API封装用的是2013版本）


---

### 项目结构

1. 丰富的Python交易和数据API接口（vn.api），基本覆盖了国内外所有常规交易品种（股票、期货、期权、外汇、外盘、比特币），具体包括：

	- CTP（vn.ctp）

	- 飞马（vn.femas）

	- LTS（vn.lts）

	- 金仕达黄金（vn.ksgold）

	- 金仕达期权（vn.ksotp）

	- 飞鼠（vn.sgit）

	- 飞创（vn.xspeed）

	- QDP（vn.qdp）

	- 上海直达期货（vn.shzd）

	- Interactive Brokers（vn.ib）

	- OANDA（vn.oanda）

	- OKCOIN（vn.okcoin）
	
	- 火币（vn.huobi）

	- 链行（vn.lhang）

	- 通联数据（vn.datayes）

2. 简洁易用的事件驱动引擎（vn.event），作为事件驱动型交易程序的核心

3. 支持服务器端数据推送的RPC框架（vn.rpc），用于实现多进程分布式架构的交易系统

3. 针对如何使用API和事件驱动引擎开发交易程序的示例（vn.demo）

4. 开箱即用的实盘交易平台vn.trader（相比之下vn.demo仅建议学习用），整合了多种交易接口，并针对具体策略算法和功能开发提供了简洁易用的API，功能应用举例：
	
	* 同时登录多个交易接口，在一套界面上监控多种市场的行情和多种资产账户的资金、持仓、委托、成交情况
	
	* 支持跨市场套利（CTP期货和LTS证券）、境内外套利（CTP期货和IB外盘）、多市场数据整合实时预测走势（CTP的股指期货数据、IB的外盘A50数据、Wind的行业指数数据）等策略应用
	
	* CTA策略引擎模块，在保持易用性的同时，允许用户针对CTA类策略运行过程中委托的报撤行为进行细粒度控制（降低交易滑点、实现高频策略）

5. 关于项目在实盘交易中的应用指南vn.tutorial

6. [官网](http://vnpy.org)和[知乎专栏](http://zhuanlan.zhihu.com/vn-py)，内容目前主要是《Python量化交易平台开发教程系列》，以及vn.py项目进展的更新

7. 官方交流QQ群262656087，管理较严格（定期清除长期潜水的成员）

---
### 注意事项

按照以上方式配置后，便可以使用vn.py的CTP, LTS, KSOTP等大多数交易接口，但在启动vtMain.py时， 你可能会遇到以下错误：

```
请先安装WindPy接口
global name 'w' is not defined
No module named ib.ext.Contract
No module named websocket
```

它们分别对应Wind, IB, OKCOIN三个交易接口，如果你不使用这三个接口，可以直接忽略这些错误，不会影响使用。

但如果你需要，可以通过以下方式安装其对应的库：

* WIND - 到[大奖章网站](http://www.dajiangzhang.com/document)注册并下载安装**Wind资讯开放应用接口**个人版即可，使用机构版Wind终端的用户可以直接在终端里安装Python接口

* IB - 参考https://github.com/blampe/IbPy， 基本上是两步：

```
git clone https://github.com/blampe/IbPy.git

cd IbPy
python setup.py install

```
* OKCOIN - ```pip install websocket-client``` or ```conda install websocket-client```

---
### How To Contribute

vn.py使用github托管其源代码，贡献代码使用github的PR(Pull Request)的流程，十分的强大与便利:

1. [创建 Issue](https://github.com/vnpy/vnpy/issues/new) - 对于较大的改动(如新功能，大型重构等)最好先开issue讨论一下，较小的improvement(如文档改进，bugfix等)直接发PR即可

2. Fork [vn.py](https://github.com/vnpy/vnpy) - 点击右上角**Fork**按钮

3. Clone你自己的fork: ```git clone https://github.com/$userid/vnpy.git```

4. 在**dev**修改并将修改push到你的fork上

5. 创建从你的fork的**dev**分支到主项目的**dev**分支的[Pull Request] -  [在此](https://github.com/vnpy/vnpy)点击**Compare & pull request**

6. 等待review, 需要继续改进，或者被Merge!

---
### 联系作者
作者知乎名：用python的交易员，想要联系作者可以通过知乎私信

---
### License
MIT

