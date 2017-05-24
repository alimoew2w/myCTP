# 关于 `vn.api` 编译过程的说明

因为需要在 `Linux` 下编译 `CTP` 接口以生成动态链接库, 具体的步骤如下:

1. 解压 `vn-1.6.1.rar`, 进入文件 `/vn.api/vn.ctp/`
2. 动态编译 `vn.ctp/build.sh`, 脚本会自动把动态链接库 `.so` 复制到 `/vn.trader/gateway/ctpGateway/` 文件夹.
3. 以后我们便可以使用 `/vn.trader/gateway/ctpGateway/` **整个文件夹**
4. 这个只需要在一台电脑执行一次即可.
