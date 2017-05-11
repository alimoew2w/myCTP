# 使用 `Sublime_git` 管理项目

1. 在 `www.github.com` 建立一个 `repository`,并克隆到本地的文件路径下面:
 
    git clone https://github.com/williamlfang/myCTP.git

2. 编辑 `Readme.md` 文件,在这里对项目背景进行详细的描述,需要进行操作的步骤,配置等,方便以后进行可重复的研究.

3. 通过 `github.com` 推送更改, 在终端 `Terminal` 运行命令:

    - cd /home/william/Documents/myCTP
    - git add . -A
    - git commit -m "updates"
    - git remote rm origin
    - git remote add origin git@github.com:williamlfang/finance.git
    - git push origin gh-pages

