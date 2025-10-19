# reSJTUBBS

这是一个现代的SJTUBBS的备份工具，并附带针对discourse的转换工具，用于在基于discourse的水源社区上使用

## 安装依赖
本项目需要安装`uv`, `direnv` 才能进行使用，安装完成后请使用

```
uv venv
direnv allow .
```
来启用对应依赖并运行`build_deps.sh`对golang的修改版进行编译使用。

## 获取Cookie

由于现代浏览器已经完全弃用TLS 1.0，目前唯一能够登陆该网站的浏览器为`Firefox Developer Edition`，请安装该浏览器，并按照指示在`about:config`中强制开启对TLS1.0的支持，详情可以Google.

注册需要将你的生日填写在1990年代附近，并按照指令填写信息以及附着SJTU校内邮箱，按照指令注册并登陆后并可以获得cookie.

## 使用指令

首先使用`make`构建所有二进制文件，并从config.template.yml设置好sjtubbs的cookie然后重命名为`config.yml`。


```
build/reid_crawler <board> 获取该版面下的所有postid并进行缓存
```

```
build/post_crawler <board> 获取该版面下的所有页面并进行缓存
```

```
uv run python reconstructor.py <board> 获取页面缓存并重建论坛topic/post/author关系存入postgresql中

```
