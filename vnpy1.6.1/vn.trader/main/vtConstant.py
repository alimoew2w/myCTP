# encoding: UTF-8

################################################################################
## william
## from language import constant
language_path = '/home/william/Documents/vnpy/vnpy-1.6.1/vn.trader/language/chinese'
import sys
sys.path.append(language_path)
import constant
################################################################################

# 将常量定义添加到vtConstant.py的局部字典中
d = locals()
for name in dir(constant):
    if '__' not in name:
        d[name] = constant.__getattribute__(name)
