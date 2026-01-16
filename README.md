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

`retriever`为使用golang编写的爬虫程序，分阶段从board列表，到reid列表再到post列表不断请求并缓存页面到mongodb数据库中。
```bash
build/retriever help
```
`reimporter.py`为使用python编写的解析器，用于将sjtubbs的页面转译到markdown格式，并重建所有的回复信息。
```bash
uv run python reimporter.py
```
