# 映效AI工作站 0.4.5

## 下载

- Windows 安全加固服务包：`YingXiaoAIWorkstation-20260529-1711.zip`
- Android 通用安装包：`YingXiaoAIWorkstation-mobile-0.1.4-android11-release.apk`
- Android arm64 真机包：`YingXiaoAIWorkstation-mobile-0.1.4-android11-arm64-v8a-release.apk`
- Flutter 移动端源码：`YingXiaoMobileFlutter-0.1.4-source.zip`

## 本版安全修复

- `/system_stats` 现在必须带有效 Bearer token，避免局域网内未配对设备读取电脑硬件信息。
- `/health` 公开响应最小化，不再返回本机任务目录路径。
- `/pair` 新增 5 分钟 8 次限速，降低 6 位配对码被暴力尝试的风险。
- 配对码比较改为常量时间校验，减少时序侧信道。
- CORS 默认不再允许任意网页来源，只允许 localhost / 127.0.0.1 调试来源。
- 手机上传的 base64 文件会校验格式，任务记录不再保存原始 base64 内容，减少隐私泄漏和磁盘膨胀。
- Windows 安装脚本修复为优先安装当前 `dist`，并更新版本号到 0.4.5，避免把旧版 0.4.3 装回去。

## 仍需注意

内置手机连接服务仍是局域网工具，只建议在同一 Wi-Fi 或手机热点内使用。不要把 `8765/TCP` 或 `8766/UDP` 暴露到公网；公网部署必须加 HTTPS 反向代理、强鉴权和访问日志。
