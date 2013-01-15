## 使用

重命名 `config.sample` 为 `config`, 然后填写信息

    USERNAME="七牛网站用户名"
    PADDWORD="七牛网站密码"
    CDN_PATH="七牛空间绑定域名"

重命名 `zqcms_update.sample.json` 为 `zqcms_update.json`, 然后填写配置

    ``json
    {
        "access_key": "~access_key~",
        "secret_key": "~secret_key~",
        "bucket": "update",
        "sync_dir": "update",
        "domains": ["~domains~"],
        "debug_level": 2
    }
    ``

可执行文件权限，到 http://docs.qiniutek.com/v3/tools/qrsync/[http://docs.qiniutek.com/v3/tools/qrsync/] 下载适合你机器的命令行辅助同步工具，解压然后:

    ``
    chmod +x qrsync
    chmod +x qboxrsctl
    chmod +x pack.sh
    ``

获取ZQCMS代码

    ``git clone https://github.com/fireyy/ZQCMS.git zqcms``

最后执行

    ``./pack.sh``