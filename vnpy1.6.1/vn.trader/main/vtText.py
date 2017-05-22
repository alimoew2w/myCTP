# encoding: UTF-8

################################################################################
## william
## 
"""
import os
path = "/home/william/Documents/vnpy/vnpy-1.6.1/vn.trader"
os.chdir(path)
print os.getcwd()
"""
################################################################################

from language import text

# 将常量定义添加到vtText.py的局部字典中
d = locals()
for name in dir(text):
    if '__' not in name:
        d[name] = text.__getattribute__(name)
