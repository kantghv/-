# 映效AI工作站 0.4.8

## 发布文件

- Windows 原生桌面包：`YingXiaoAIWorkstation-20260529-1950.zip`
- Android 通用安装包：`YingXiaoAIWorkstation-mobile-0.1.7-android11-release.apk`
- Android arm64 真机包：`YingXiaoAIWorkstation-mobile-0.1.7-android11-arm64-v8a-release.apk`
- Flutter 移动端源码：`YingXiaoMobileFlutter-0.1.7-source.zip`

## 重点更新

- Android 模型库修复：默认模型没有下载地址时，按钮会改为导入本地模型包，不再卡在无效下载。
- Android 原生层新增模型包导入：系统文件选择器选择模型后，会复制到 App 私有目录 `local_models` 并自动启用。
- Android 动画优化：页面切换改为更慢一点的淡入、滑动、缩放组合，模型卡片增加选中和状态过渡。
- Windows 图片输出默认改为“智能2x”，生成后会主动提高分辨率。
- 手机桥接图像任务默认请求 `2x` 输出和 `8192` 上限。

## 验证

- `python -m py_compile main.py`
- 桌面端 2x 输出回归测试通过
- `flutter analyze --no-pub`
- `flutter test`
- Android debug、通用 release、split-per-abi release APK 构建通过
- APK v2 签名验证通过
- 已安装 Windows 0.4.8 本地 API 验证通过
