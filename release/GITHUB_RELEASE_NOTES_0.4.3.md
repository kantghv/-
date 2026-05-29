# 映效AI工作站 0.4.3

## 下载

- Windows 安装包：`YingXiaoAIWorkstation-0.4.3-installer-bundle.zip`
- Windows 手机连接服务包：`YingXiaoAIWorkstation-20260529-1459.zip`
- Android 通用安装包：`YingXiaoAIWorkstation-mobile-0.1.3-android11-release.apk`
- Android arm64 真机包：`YingXiaoAIWorkstation-mobile-0.1.3-android11-arm64-v8a-release.apk`
- Flutter 移动端源码：`YingXiaoMobileFlutter-0.1.3-source.zip`

## Windows 安装

1. 解压 `YingXiaoAIWorkstation-0.4.3-installer-bundle.zip`
2. 双击 `install_windows.bat`
3. 默认安装到 `D:\映效AI工作站`，如果没有 D 盘则安装到当前用户程序目录

安装脚本会创建桌面快捷方式和开始菜单入口。旧版本目录不会直接删除，会重命名成备份目录。

## Android 安装

- 直接把 APK 传到 Android 11 及以上手机安装。
- 或者手机开启 USB 调试后，双击 `install_android_apk.bat` 使用 ADB 安装。

## 本版变化

- 视频渲染失败自动救援：自动换音频、换 H.264、CPU 兼容渲染、低滤镜安全渲染。
- 视频失败时写入 FFmpeg 诊断日志。
- 菜单新增“打开程序目录”和“打开视频诊断目录”。
- Android APK 已设置最低 Android 11，目标 Android 36，应用名为“映效AI工作站”。
- Android 0.1.1 优化了深色原生启动页、小屏布局、底部/侧边导航主题、R8 代码压缩和资源裁剪。
- Android 0.1.2 新增工作站连接、媒体选择、图像/视频任务提交、模型部署请求、历史记录和 Android Keystore 密钥保护。
- Android 0.1.3 修复局域网连接失败：电脑端新增“手机连接服务”HTTP API，安卓默认支持局域网调试连接。
- Flutter Android 工具链已在本机跑通，debug、通用 release、split-per-abi release APK 构建通过。

## 校验

发布资产旁边提供 `checksums-sha256.txt`。
