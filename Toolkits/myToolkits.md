# 我的开发工具箱

## `Linux` 软件

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
