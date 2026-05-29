# 映效AI工作站 发布说明

## 启动方式

- 开发目录启动：运行 `run.bat`
- 正式软件启动：运行 `dist_043/映效AI工作站/映效AI工作站.exe`
- Windows 一键安装：运行 `install_windows.bat`
- 发布包：`release/YingXiaoAIWorkstation-*.zip`
- Flutter 移动端源码包：`release/YingXiaoMobileFlutter-0.1.8-source.zip`
- Android 安装包：`release/YingXiaoAIWorkstation-mobile-0.1.8-android11-release.apk`
- Android arm64 真机包：`release/YingXiaoAIWorkstation-mobile-0.1.8-android11-arm64-v8a-release.apk`

## 已内置能力

- PySide6 Windows 原生桌面界面
- Windows 系统级适配：PerMonitor DPI、任务栏 AppID、Common Controls v6、long path aware
- 系统级性能优化：启动阶段延后硬件扫描、Qt 高频事件压缩、图片预览缓存
- 后台硬件监控：GPU / FFmpeg / 编码器检测运行在 QThread，减少界面卡顿
- 系统级过渡动画：页面滑入、顶部能量线、导航高亮滑块、浮层提示和按钮微交互
- 低负载动效策略：根据设备性能自动降级，避免大面积透明特效拖慢 UI
- 模型库升级：支持用户添加/更新/删除自定义模型，记录模型来源、启动方式和部署记录
- 功能增强：桌面图片默认改为智能2x 输出，并保留跟随原图、处理尺寸、长边4K、长边8K；移动端桥接请求 2x 和 8192 输出上限
- 视频工作站专业化：新增自然增强、电影胶片、霓虹赛博、商业干净、建筑HDR、人像通透、暗调电影等专业模式
- 编码链路打通：H.264/H.265、质量档、封装格式、音频策略和硬件编码器都会进入最终 FFmpeg 命令
- 视频AI自动救援：渲染失败后自动改音频、换 H.264/H.265 编码器、关闭硬件解码并写 FFmpeg 诊断日志
- AI能力增强：模型库新增 DeepSeek API 和 Video AI Rescue 内置条目，方便接入远程/本机模型能力
- Flutter 移动端：已生成 Android / iOS / Windows 平台目录，Android debug 和 release 构建通过
- Android APK：最低 Android 11（SDK 30），目标 Android 36，应用名为“映效AI工作站”，版本 0.1.8
- Android 优化：深色原生启动页、小屏文字保护、手机/平板导航自适应、R8 代码压缩、资源裁剪、split-per-abi 小包
- Android 可用性：默认手机本地 AI 模式免配对码，新增模型 HTTPS 自动下载、本地模型包导入、手机私有目录保存、模型启用/切换、本地任务队列；电脑配对连接保留为桥接模式
- Android 动画优化：页面内容错峰进入，页面切换使用淡入/滑动/缩放组合，模型卡片状态切换使用 AnimatedSwitcher
- Android 安全：访问令牌通过 Android Keystore 加密保存，默认 HTTPS 优先，任务历史不记录密钥
- 手机连接服务：桌面端新增局域网 API 和 UDP 自动发现，提供 `/health`、`/pair`、`/api/tasks/image`、`/api/tasks/video`、`/api/models/deploy`
- 手机连接安全加固：配对码限速、常量时间校验、系统信息接口鉴权、公开健康检查最小化、CORS 默认拒绝非本机网页来源
- 手机连接二次加固：桌面 API 只接受本机和私有局域网地址，配对请求体限制到 4KB，本地令牌配置文件尝试收紧 ACL
- 安装体验优化：Windows 安装脚本默认安装到 D 盘，自动生成桌面和开始菜单入口，旧版本自动备份
- 发布整理：新增 GitHub Release 模板、Android ADB 安装助手和 SHA256 校验清单
- 用户目录适配：输出写入文档目录，缓存和日志写入 LocalAppData
- 菜单入口：打开用户数据目录、打开日志目录、生成桌面快捷方式
- 映效图像工作站
- 达芬奇式局部窗口和限定器调整
- 硬件监控，优先读取 NVIDIA `nvidia-smi`
- 视频工作站，内置完整 FFmpeg，并优先使用 NVENC
- ComfyUI / FLUX 接入状态检测和启动入口
- 模型部署模拟页面

## 用户数据目录

软件运行产生的视频输出、缓存和后续数据默认写入：

`%USERPROFILE%/Documents/映效AI工作站`

这样正式软件目录可以保持干净，也方便以后做安装器和自动更新。

## 重新打包

运行：

`build_windows.bat`

或：

`powershell -NoProfile -ExecutionPolicy Bypass -File build_windows.ps1`
