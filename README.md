# 映效 AI 工作站

可以让图片自动生成你想要的样子。

映效 AI 工作站是一个原生桌面 + 移动端的 AI 图片/视频创作工作站。桌面端使用 Python + PySide6，不依赖 Gradio、Streamlit 或 Web 界面；移动端使用 Flutter，面向 Android 11 及以上设备。

项目目标是把“图片参考、局部精修、视频处理、模型部署、硬件监控”放在同一个清晰的软件框架里，方便继续接入 ComfyUI、FLUX.1 Kontext Dev、Whisper 和其他本地模型。

## 当前能力

- Windows 原生桌面软件：菜单栏、状态栏、左侧导航、右侧多页面工作区。
- 图片工作站：原图/参考图导入、专业预设、局部调整思路、智能推荐、对比预览、PNG 输出。
- 超清输出：智能 2x、4K、8K、最高 16K 长边策略，0.4.9 起加入原图边缘/纹理引导的细节重建，减少“高分辨率但发糊”。
- 视频工作站：视频导入、专业模式、帧率/分辨率/锐化/降噪/补帧参数、硬件编码检测接口。
- 硬件监控：CPU、内存、GPU 温度、GPU 使用率、显存占用。
- 模型部署：模型选择、一键部署、异步进度、日志输出，预留 ComfyUI + FLUX.1 Kontext Dev 工作流。
- Android 移动端：模型库、模型下载/导入/切换、手机本地 AI 任务队列、移动端动画和安全提示。

## 项目结构

```text
.
├── main.py                     # Windows PySide6 主程序
├── requirements.txt            # 桌面端 Python 依赖
├── build_windows.ps1           # Windows 打包脚本
├── install_windows.ps1         # Windows 安装脚本
├── windows/                    # ComfyUI/FLUX 启动和模型脚本
├── assets/                     # 图标和静态资源
├── mobile_app/                 # Flutter 移动端工程
├── release/                    # 版本说明、manifest、校验文件；二进制产物不入库
└── docs/                       # 架构、发布、安全扩展文档
```

## Windows 开发运行

```powershell
python -m pip install -r requirements.txt
python main.py
```

也可以使用批处理：

```bat
install_requirements.bat
run.bat
```

## Windows 打包

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File build_windows.ps1
```

安装到本机：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File install_windows.ps1
```

默认安装目录为 `D:\映效AI工作站`。没有 D 盘时会回退到当前用户程序目录。安装脚本会创建桌面和开始菜单快捷方式，并备份旧版本目录。

## Android 开发运行

先确认 Flutter SDK 已配置，然后进入移动端工程：

```powershell
cd mobile_app
flutter pub get
flutter analyze
flutter test
flutter build apk --release
```

项目最低目标为 Android 11。iOS 目录保留为后续适配入口。

## ComfyUI + FLUX.1 Kontext Dev

启动 ComfyUI：

```bat
windows\启动ComfyUI_FLUX中等占用.bat
```

下载 FLUX.1 Kontext Dev 常用模型文件：

```bat
windows\下载FLUX1_Kontext模型.bat
```

模型下载可能需要先在 Hugging Face 接受对应许可。软件只连接本机 `http://127.0.0.1:8188`，不会绕过模型许可。

## 安全原则

- 不在仓库中提交 API Key、Token、Cookie、私钥或本机配置。
- 不把用户生成的图片、视频、模型权重、打包产物直接提交到 Git。
- AI 结果需要遵守当地法律法规和模型服务条款。
- 本地服务默认绑定 `127.0.0.1`，避免无意暴露到公网。

更多说明见 [SECURITY.md](SECURITY.md)。

## 版本

当前桌面端：`0.4.9`

当前移动端：`0.1.8+9`

发布说明见 [release_notes.md](release_notes.md) 和 `release/` 下的版本 manifest。

## 许可证

本项目使用 MIT License。详见 [LICENSE](LICENSE)。
