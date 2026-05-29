# 贡献指南

欢迎提交问题、建议和改进代码。为了让项目保持清晰，请尽量遵守下面的约定。

## 开发流程

1. Fork 仓库并创建功能分支。
2. 修改前先确认没有提交本机密钥、模型权重、生成图片、生成视频或安装包。
3. 桌面端修改后运行：

```powershell
python -m py_compile main.py
```

4. 移动端修改后运行：

```powershell
cd mobile_app
flutter analyze
flutter test
```

5. 提交 Pull Request，并说明修改原因、影响范围和验证方式。

## 代码风格

- 桌面端优先保持 PySide6 原生组件和当前页面结构。
- 移动端优先保持 Flutter 原生页面和现有主题。
- 新增 AI 能力时，把模型下载、模型许可、运行端口和安全限制写清楚。
- 新增大文件产物时不要提交到 Git，改用 Release assets 或外部模型仓库。

## 安全

如果发现安全问题，请不要在公开 Issue 中直接贴密钥、漏洞利用代码或用户数据。先按 [SECURITY.md](SECURITY.md) 的方式报告。
