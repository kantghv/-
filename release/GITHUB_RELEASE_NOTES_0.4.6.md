# 映效AI工作站 0.4.6

## 下载

- Windows 安全加固服务包：`YingXiaoAIWorkstation-20260529-1753.zip`
- Android 通用安装包：`YingXiaoAIWorkstation-mobile-0.1.5-android11-release.apk`
- Android arm64 真机包：`YingXiaoAIWorkstation-mobile-0.1.5-android11-arm64-v8a-release.apk`
- Flutter 移动端源码：`YingXiaoMobileFlutter-0.1.5-source.zip`

## 本版变化

- 桌面端升级到 0.4.6，手机端升级到 0.1.5+6。
- 桌面手机 API 现在只接受本机、私有局域网和链路本地地址访问。
- UDP 自动发现只回应局域网客户端，避免跨网段误暴露。
- 配对接口请求体限制为 4KB，任务上传接口独立限制为 96MB。
- 本地 `mobile_api.json` 写入后会尝试收紧 Windows ACL，降低令牌文件被其他本机账户读取的风险。
- 图片输出升级：桌面端默认输出上限从 2400 提升到 4096，最高可选 8192；Android 默认请求 6144 输出上限。
- Android 连接安全策略拒绝带用户名/密码的服务 URL，并补充 link-local / IPv6 私网判断。

## 安全提醒

内置连接服务仍只适合局域网使用。不要把 `8765/TCP` 或 `8766/UDP` 映射到公网；公网必须加 HTTPS 反向代理、强鉴权和访问日志。
