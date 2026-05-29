# 映效AI工作站 Android 0.1.8 动画优化版

## 发布文件

- Android 通用安装包：`YingXiaoAIWorkstation-mobile-0.1.8-android11-release.apk`
- Android arm64 真机包：`YingXiaoAIWorkstation-mobile-0.1.8-android11-arm64-v8a-release.apk`
- Flutter 移动端源码：`YingXiaoMobileFlutter-0.1.8-source.zip`

## 重点更新

- 页面内容加入错峰进入动画，标题、卡片、表单控件会分段淡入。
- 页面切换继续使用淡入、轻微滑动和缩放组合，并保持左右方向感。
- 模型卡片图标、状态文字和按钮图标改为 AnimatedSwitcher，下载/导入/启用状态变化更顺。
- 版本号升级到 `0.1.8+9`，最低 Android 11 不变。

## 验证

- `flutter analyze --no-pub`
- `flutter test`
- Android debug、通用 release、split-per-abi release APK 构建通过
- APK v2 签名验证通过
