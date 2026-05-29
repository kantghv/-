# 映效AI工作站移动端

这是移动端源码工程，面向 Android 和 iOS。当前已用 Flutter 3.44.0 构建通过 Android 11+ 安装包；安装 Flutter 后可在本目录执行：

```powershell
flutter create .
flutter pub get
flutter run
```

## 已包含

- 手机底部导航：总览、图像、视频、模型库
- 手机/平板自适应：窄屏底部导航，宽屏自动切换 NavigationRail
- 丝滑页面过渡：`AnimatedSwitcher` + slide/fade
- Android 原生启动页：深色启动主题，避免启动闪白
- 发布优化：R8 代码压缩、资源裁剪、Material Icons 按需裁剪
- 手机本地 AI：默认免配对码，模型下载安装到手机私有目录，可在软件内下载、导入、启用和切换
- 工作站连接：作为可选桥接模式，支持局域网 UDP 自动发现、6 位配对码、保存服务地址、检测 `/health`
- 真实任务提交：本地模式进入手机本地运行队列；桥接模式通过 HTTP API 发送 JSON
- 安全存储：访问令牌通过 Android Keystore 加密保存，不写入任务历史
- 媒体选择：通过 Android 系统文件选择器选择图片和视频
- 图像模式：参考图、局部调整、专业输出，默认向桌面端请求原生分辨率和 8192 输出上限
- 视频模式：移动端清晰、2K、120FPS、多线程
- 模型库：内置模型 + 用户添加模型入口 + HTTPS 自动下载 + 本地模型包导入 + 本地启用/切换

## 发布包

- 通用 APK：`../release/YingXiaoAIWorkstation-mobile-0.1.8-android11-release.apk`
- 常见真机 arm64 APK：`../release/YingXiaoAIWorkstation-mobile-0.1.8-android11-arm64-v8a-release.apk`
- 源码包：`../release/YingXiaoMobileFlutter-0.1.8-source.zip`

## API 约定

- `GET /health`：检测工作站服务
- `POST /pair`：用桌面端 6 位配对码换取访问令牌
- `POST /api/tasks/image`：提交图像任务
- `POST /api/tasks/video`：提交视频任务
- `POST /api/models/deploy`：提交模型部署任务

自动发现使用 UDP `8766`，工作站 API 默认使用 HTTP `8765`。如果连接 ComfyUI，检测页也会尝试 `GET /system_stats`。

默认不需要电脑端。手机端进入“模型库”后，可以填入 HTTPS 模型包地址自动下载，也可以直接导入手机里已有的模型包；需要电脑桥接时，再到“连接与安全”关闭手机本地 AI 模式并使用配对码连接。

0.1.8 继续优化过渡动画：页面内容会错峰进入，页面切换保留方向感，模型卡片的图标、状态文字和按钮会平滑切换。

后续可以把桌面端的模型库 JSON、ComfyUI 服务和本机工作站 API 接入到 `ModelHubPage` 与各任务页面。
