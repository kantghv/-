# 映效AI工作站 0.4.4

## 下载

- Windows 手机自动连接服务包：`YingXiaoAIWorkstation-20260529-1645.zip`
- Android 通用安装包：`YingXiaoAIWorkstation-mobile-0.1.4-android11-release.apk`
- Android arm64 真机包：`YingXiaoAIWorkstation-mobile-0.1.4-android11-arm64-v8a-release.apk`
- Android armeabi-v7a 包：`YingXiaoAIWorkstation-mobile-0.1.4-android11-armeabi-v7a-release.apk`
- Android x86_64 包：`YingXiaoAIWorkstation-mobile-0.1.4-android11-x86_64-release.apk`
- Flutter 移动端源码：`YingXiaoMobileFlutter-0.1.4-source.zip`

## Android 安装

- 直接把 APK 传到 Android 11 及以上手机安装。
- 常见真机优先使用 `arm64-v8a` 包；不确定架构时使用通用包。

## 本版变化

- 桌面端“05 / 手机连接”新增 UDP 自动发现服务，默认发现端口 `8766`。
- 桌面端新增 6 位配对码，10 分钟有效；配对后自动刷新，避免长期暴露令牌。
- 手机端“连接与安全”会自动搜索工作站，输入桌面端配对码后自动保存地址和访问令牌。
- 访问令牌继续保存到 Android Keystore，任务历史不记录密钥。
- 保留高级手动模式：仍可手动填写 `http://电脑IP:8765` 和访问令牌。
- Android APK 已验证：versionName `0.1.4`，versionCode `5`，最低 Android 11，目标 Android 36。
- Flutter `test`、纯英文目录 `analyze --no-pub`、debug APK、release APK、split-per-abi release APK 构建通过。

## 安全提醒

内置手机连接服务只建议在同一 Wi-Fi 或手机热点局域网内使用。不要把 `8765` 或 `8766` 直接暴露到公网；公网访问请加 HTTPS 反向代理和额外鉴权。
