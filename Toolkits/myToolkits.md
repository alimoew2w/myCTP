# 我的开发工具箱

## `Linux` 软件

- `Sublime Text 3`: 一款集成的 `IDE` 环境, 目前我主要在上面开发 `R` 和 `python`. 通过安装各种增强插件, 以及可自定义的快捷键, 让其功能变得异常的强大. 常用的插件有:

  - R-Box
  - R-snippets
  - R_comments
  - sendCode
  - Sublime REPL
  - SFTP
  - Material Theme
  - SideBarEnhancements
  - MarkdownLivePreview: alt+m
  - Markdown Extended 
  - 解决中文乱码：GBK Support, ConvertToUTF8, Codecs33
  - AutoPEP8：python 规范化
  - SublimeCodeIntel：实现语法自动高亮
  - Python BreakPoint
  - sudo apt install npm && sudo npm install -g markmon
  - Markdown 预览： markmon
  - Git + Github：Git, GithubTools
  - StatusBarTime: 在状态栏显示系统时间
  - GitGutter
  - Auto-save: 通过设置 keybinds:{ "keys": ["ctrl+shift+s"], "command": "auto_save" }
  - C++ Completes

  整体的界面非常的优雅:

  ![sublime](/Toolkits/pic/sublime.png)

  通过 `REPL` 运行代码:

  ![sublime_2](/Toolkits/pic/sublime_2.png)

- `mycli`: 这是一款配合 `MySQL` 自动补全的命令行工具, 可以实现在 `terminal` 自动跳出补全的可用命令. 具体的使用方法可以通过帮助文档获取.

        sudo apt install mycli
        mycli --help

        Usage: mycli [OPTIONS] [DATABASE]       

        Options:
          -h, --host TEXT               Host address of the database.
          -P, --port INTEGER            Port number to use for connection. Honors
                                        $MYSQL_TCP_PORT
          -u, --user TEXT               User name to connect to the database.
          -S, --socket TEXT             The socket file to use for connection.
          -p, --password TEXT           Password to connect to the database
          --pass TEXT                   Password to connect to the database
          -v, --version                 Version of mycli.
          -D, --database TEXT           Database to use.
          -R, --prompt TEXT             Prompt format (Default: "\t \u@\h:\d> ")
          -l, --logfile FILENAME        Log every query and its results to a file.
          --defaults-group-suffix TEXT  Read config group with the specified suffix.
          --defaults-file PATH          Only read default options from the given file
          --login-path TEXT             Read this path from the login file.
          --help                        Show this message and exit.

        mycli -h hostsite -P portNumber -u user -p password

- `terminator`: Linux 系统下的 `terminal` 模仿 IDE, 具备在屏幕下切割多个窗口的功能.

        sudo apt install terminator 

  ![terminator](/Toolkits/pic/terminator.png)

- 'navicate': 这是一款 `MySQL 可视化操作` 的 GUI, 可以很方便的用来查看数据库, 而且支持对多种数据库的连接. 在 `Linux` 可以有一个 *14* 天的试用期. 届时到期了, 可以通过以下方法延期使用:
    - 一种方法是删除在 `/home/william/.navicat64` 的整个文件夹, 然后再重新安装 `navicat112_premium_en_x64/start.sh`, 即可恢复 *14* 天的试用期了.
    - 另一种方法, 我没有具体操作过, 就是删除 `/home/william/.navicat64/system.reg`, 这是一个计算使用时间的文件, 每次安装好 `navicat` 在启动前, 都先删除了, 就可以一直使用了.
