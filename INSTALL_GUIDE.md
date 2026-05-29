# 映效AI工作站安装指南

## Windows

1. 解压 `YingXiaoAIWorkstation-0.4.3-installer-bundle.zip`
2. 双击 `install_windows.bat`
3. 默认安装到 `D:\映效AI工作站`

如果没有 D 盘，安装脚本会改用当前用户程序目录。旧版本目录会自动改名备份，不会直接删除。

## Android

Android 11 及以上手机可以直接安装：

```text
YingXiaoAIWorkstation-mobile-0.1.0-android11-release.apk
```

如果要用 USB 安装：

1. 手机开启开发者模式和 USB 调试
2. 用数据线连接电脑
3. 双击 `install_android_apk.bat`

## 卸载

Windows 安装目录里会生成：

```text
uninstall_windows.ps1
```

它会删除桌面和开始菜单快捷方式。程序目录为了保护用户数据，不会自动删除，需要确认后手动删除。
