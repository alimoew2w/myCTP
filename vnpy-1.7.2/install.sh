#!/bin/bash

#Build ctp/lts/ib api
pushd vnpy/api/ctp
bash build.sh
popd

# pushd vnpy/api/lts
# bash build.sh
# popd

# pushd vnpy/api/xtp
# bash build.sh
# popd

# pushd vnpy/api/ib
# bash build.sh
# popd

#Install Ta-Lib
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/
conda config --set show_channel_urls yes
conda install -c quantopian ta-lib=0.4.9

#Install Python Modules
pip install -r requirements.txt

#Install vn.py
# python setup.py install

## =============================================================================
rm -rf /home/william/anaconda2/lib/python2.7/site-packages/vnpy
rm -rf /home/william/anaconda2/lib/python2.7/site-packages/vnpy-1.7.2*
## =============================================================================
