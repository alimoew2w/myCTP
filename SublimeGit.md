# 使用 `Sublime Git` 管理项目

1. 在 `www.github.com` 建立一个 `repository`,并克隆到本地的文件路径下面:
 
    git clone https://github.com/williamlfang/myCTP.git

2. 编辑 `Readme.md` 文件,在这里对项目背景进行详细的描述,需要进行操作的步骤,配置等,方便以后进行可重复的研究.

3. 通过 `github.com` 推送更改, 在终端 `Terminal` 运行命令:

        cd /home/william/Documents/myCTP
        git add . -A
        git commit -m "updates"
        git push

4. 如果想要 `push` 的时候不需要输入密码,可以在当前的 `project` **根目录** 下面执行命令:
        
        vim .git-credentials
        https://{username}:{password}@github.com
        git config --global credential.helper store

5. 当然,也最保险的方法,是把 `SSH keys` 的 `id_rsa.pub` 的密钥复制到 `Github` 的 `SSH and GPG keys`,就可以实现无密码推送了.

6. 在 `Sublime Text3` 使用 `git`,需要做如下步骤的设置(参考步骤4,需要开启密码):

    - vim .git-credentials: 把帐号,密码输入到以下:https://{username}:{password}@github.com
    - 设置: git config --global credential.helper store
    - 在 `Sublime Text3` 的 `Package Control` 安装插件: 
        
        - `Sublime Git`: 把 `git` 融合到 `Sublime`
        - `Sublime GitGutter`: 可以在左边显示修改的标记
        
    - 使用步骤,通过调用 `Shift+Control+P` 来调用命令行:
        
            git add: 添加文件
            git commit: 在弹出的文件里面输入需要提交的信息,写好后直接关闭就可以了,不需要保存. `Sublime` 会自动标记好.
            git push: 就可以推送了.

7. 如果想要把某个文件夹上传, 但是不要上传里面的具体文件, 比如我的 `/vn.data/Tickdata`, 我想要保留这个文件结构, 但是里面的数据是实时更新的, 也非常的大,这个就不适合上传到 `Git`. 因此, 可以选择忽略里面的具体文件. 具体的[做法](http://stackoverflow.com/questions/4250063/how-to-gitignore-all-files-folder-in-a-folder-but-not-the-folder-itself)如下:

    - 在需要忽略的文件夹下面新建一个文件, 命名为 `.gitignore`
    - 在里面写入
        
            *
            */
            */*
            !.gitignore
            ! 其他的文件

    - The * line tells git to ignore all files in the folder, but !.gitignore tells git to still include the .gitignore file. This way, your local repository and any other clones of the repository all get both the empty folder and the .gitignore it needs.

8. `Sublime Text 3` 的设置, 可以参考我的[配置方案](https://github.com/williamlfang/myCTP/tree/master/SublimeText-3/Packages).

================================================================================

@williamlfang
