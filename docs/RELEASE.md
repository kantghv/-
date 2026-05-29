# 发布流程

## 桌面端

1. 更新 `main.py` 中的 `APP_VERSION`。
2. 运行基础检查：

```powershell
python -m py_compile main.py
```

3. 构建 Windows 包：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File build_windows.ps1
```

4. 计算发布包 SHA256，并写入 `release/` 下的 manifest。
5. 在 GitHub Release 中上传 ZIP，不把 ZIP 提交到 Git 仓库。

## 移动端

1. 更新 `mobile_app/pubspec.yaml` 中的版本号。
2. 运行：

```powershell
cd mobile_app
flutter analyze
flutter test
flutter build apk --release
```

3. APK 作为 GitHub Release asset 上传，不提交进源码仓库。

## 仓库内容原则

Git 仓库保存源码、脚本和文档。大文件、模型权重、用户输出、安装包和构建缓存放在 Release assets 或外部模型仓库。
