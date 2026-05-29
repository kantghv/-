# 映效AI工作站 0.4.7

## 发布文件

- Windows 原生桌面包：`YingXiaoAIWorkstation-20260529-1917.zip`
- Android 通用安装包：`YingXiaoAIWorkstation-mobile-0.1.6-android11-release.apk`
- Android arm64 真机包：`YingXiaoAIWorkstation-mobile-0.1.6-android11-arm64-v8a-release.apk`
- Flutter 移动端源码：`YingXiaoMobileFlutter-0.1.6-source.zip`

## 重点更新

- Android 默认切换为手机本地 AI 模式，不需要电脑配对码。
- 模型库支持 HTTPS 模型包下载、保存到 App 私有目录、启用和切换当前模型。
- 电脑工作站连接保留为可选桥接模式，原有配对码和令牌安全逻辑继续可用。
- Android 桥接图像任务默认请求原生分辨率输出和 8192 上限。
- Windows 图像输出新增“跟随原图、处理尺寸、长边4K、长边8K、智能2x”策略。
- Windows 图片生成管线会在低内存处理后恢复到目标输出尺寸，降低处理卡顿同时保留交付分辨率。

## 验证

- `python -m py_compile main.py`
- 桌面端原生分辨率/2x 输出回归测试通过
- `flutter analyze --no-pub`
- `flutter test`
- Android debug、通用 release、split-per-abi release APK 构建通过
- APK v2 签名验证通过
- 已安装 Windows 0.4.7 本地 API 验证通过：`/health` 为 0.4.7，`/system_stats` 未授权返回 401，错误配对触发 429 限流
