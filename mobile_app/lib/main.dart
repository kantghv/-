import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart' show ScrollCacheExtent;
import 'package:flutter/services.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    systemNavigationBarColor: Color(0xFF0B0D12),
    systemNavigationBarDividerColor: Colors.transparent,
    systemStatusBarContrastEnforced: false,
    systemNavigationBarContrastEnforced: false,
    statusBarIconBrightness: Brightness.light,
    systemNavigationBarIconBrightness: Brightness.light,
  ));
  runApp(const YingXiaoMobileApp());
}

class AppColors {
  static const background = Color(0xFF0B0D12);
  static const surface = Color(0xFF10141A);
  static const panel = Color(0xFF121822);
  static const panelBorder = Color(0xFF263243);
  static const primary = Color(0xFF58DCC7);
  static const gold = Color(0xFFF2C763);
  static const coral = Color(0xFFFF8C77);
  static const muted = Color(0xFFA8B6C8);
}

class YingXiaoMobileApp extends StatelessWidget {
  const YingXiaoMobileApp({super.key});

  @override
  Widget build(BuildContext context) {
    const seed = Color(0xFF58DCC7);
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: '映效AI',
      theme: ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        colorScheme: ColorScheme.fromSeed(
          seedColor: seed,
          brightness: Brightness.dark,
          primary: seed,
          secondary: AppColors.gold,
          tertiary: AppColors.coral,
          surface: AppColors.surface,
        ),
        scaffoldBackgroundColor: AppColors.background,
        fontFamily: 'Roboto',
        splashFactory: InkSparkle.splashFactory,
        visualDensity: VisualDensity.standard,
        progressIndicatorTheme: const ProgressIndicatorThemeData(
          color: AppColors.primary,
          linearTrackColor: AppColors.panelBorder,
        ),
        sliderTheme: SliderThemeData(
          activeTrackColor: AppColors.primary,
          inactiveTrackColor: AppColors.panelBorder,
          thumbColor: AppColors.primary,
          overlayColor: AppColors.primary.withValues(alpha: 0.14),
        ),
        switchTheme: SwitchThemeData(
          thumbColor: WidgetStateProperty.resolveWith(
            (states) => states.contains(WidgetState.selected)
                ? AppColors.primary
                : AppColors.muted,
          ),
          trackColor: WidgetStateProperty.resolveWith(
            (states) => states.contains(WidgetState.selected)
                ? AppColors.primary.withValues(alpha: 0.28)
                : AppColors.panelBorder,
          ),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: AppColors.panel,
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: const BorderSide(color: AppColors.panelBorder),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: const BorderSide(color: AppColors.primary, width: 1.3),
          ),
        ),
        filledButtonTheme: FilledButtonThemeData(
          style: FilledButton.styleFrom(
            foregroundColor: Colors.black,
            backgroundColor: AppColors.primary,
            minimumSize: const Size(64, 44),
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          ),
        ),
        outlinedButtonTheme: OutlinedButtonThemeData(
          style: OutlinedButton.styleFrom(
            foregroundColor: AppColors.primary,
            side: const BorderSide(color: AppColors.panelBorder),
            minimumSize: const Size(64, 44),
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          ),
        ),
        bottomSheetTheme: const BottomSheetThemeData(
          backgroundColor: AppColors.surface,
          modalBackgroundColor: AppColors.surface,
          showDragHandle: true,
        ),
        navigationRailTheme: NavigationRailThemeData(
          backgroundColor: AppColors.background,
          indicatorColor: AppColors.primary.withValues(alpha: 0.18),
          selectedIconTheme: const IconThemeData(color: AppColors.primary),
          selectedLabelTextStyle: const TextStyle(
              color: AppColors.primary, fontWeight: FontWeight.w900),
          unselectedLabelTextStyle: const TextStyle(
              color: AppColors.muted, fontWeight: FontWeight.w700),
        ),
        navigationBarTheme: NavigationBarThemeData(
          backgroundColor: AppColors.background,
          indicatorColor: AppColors.primary.withValues(alpha: 0.18),
          labelTextStyle: WidgetStateProperty.resolveWith(
            (states) => TextStyle(
              color: states.contains(WidgetState.selected)
                  ? AppColors.primary
                  : AppColors.muted,
              fontWeight: FontWeight.w800,
              fontSize: 12,
            ),
          ),
        ),
        pageTransitionsTheme: const PageTransitionsTheme(
          builders: {
            TargetPlatform.android: ZoomPageTransitionsBuilder(),
          },
        ),
      ),
      builder: (context, child) {
        final media = MediaQuery.of(context);
        return MediaQuery(
          data: media.copyWith(
            textScaler: media.textScaler
                .clamp(minScaleFactor: 0.9, maxScaleFactor: 1.18),
          ),
          child: child ?? const SizedBox.shrink(),
        );
      },
      home: const WorkstationShell(),
    );
  }
}

class WorkstationShell extends StatefulWidget {
  const WorkstationShell({super.key});

  @override
  State<WorkstationShell> createState() => _WorkstationShellState();
}

class _WorkstationShellState extends State<WorkstationShell> {
  late final WorkstationController controller;
  int index = 0;
  int previousIndex = 0;

  @override
  void initState() {
    super.initState();
    controller = WorkstationController()..addListener(_onControllerChanged);
    unawaited(controller.load());
  }

  @override
  void dispose() {
    controller
      ..removeListener(_onControllerChanged)
      ..dispose();
    super.dispose();
  }

  void _onControllerChanged() {
    if (mounted) {
      setState(() {});
    }
  }

  @override
  Widget build(BuildContext context) {
    final pages = [
      OverviewPage(controller: controller),
      ConnectionPage(controller: controller),
      ImageStudioPage(controller: controller),
      VideoStudioPage(controller: controller),
      ModelHubPage(controller: controller),
    ];
    return LayoutBuilder(
      builder: (context, constraints) {
        final wide = constraints.maxWidth >= 840;
        final content = DecoratedBox(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              colors: [Color(0xFF090B10), Color(0xFF0D121A), Color(0xFF10131B)],
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
            ),
          ),
          child: SafeArea(
            child: AdaptiveFrame(
              child: RepaintBoundary(
                child: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 340),
                  reverseDuration: const Duration(milliseconds: 240),
                  switchInCurve: Curves.easeOutQuart,
                  switchOutCurve: Curves.easeInOutCubic,
                  layoutBuilder: (currentChild, previousChildren) {
                    return Stack(
                      alignment: Alignment.topCenter,
                      children: [
                        ...previousChildren,
                        if (currentChild != null) currentChild,
                      ],
                    );
                  },
                  transitionBuilder: (child, animation) {
                    final curved = CurvedAnimation(
                        parent: animation, curve: Curves.easeOutQuart);
                    final direction = index >= previousIndex ? 1.0 : -1.0;
                    final slide = Tween<Offset>(
                      begin: Offset(0.045 * direction, 0.012),
                      end: Offset.zero,
                    ).animate(curved);
                    final scale =
                        Tween<double>(begin: 0.985, end: 1.0).animate(curved);
                    return ScaleTransition(
                      scale: scale,
                      child: FadeTransition(
                        opacity: curved,
                        child: SlideTransition(position: slide, child: child),
                      ),
                    );
                  },
                  child:
                      KeyedSubtree(key: ValueKey(index), child: pages[index]),
                ),
              ),
            ),
          ),
        );
        if (wide) {
          return Scaffold(
            body: Row(
              children: [
                SafeArea(
                  child: NavigationRail(
                    selectedIndex: index,
                    minWidth: 84,
                    onDestinationSelected: setIndex,
                    labelType: NavigationRailLabelType.all,
                    destinations: const [
                      NavigationRailDestination(
                          icon: Icon(Icons.dashboard_outlined),
                          selectedIcon: Icon(Icons.dashboard),
                          label: Text('总览')),
                      NavigationRailDestination(
                          icon: Icon(Icons.verified_user_outlined),
                          selectedIcon: Icon(Icons.verified_user),
                          label: Text('连接')),
                      NavigationRailDestination(
                          icon: Icon(Icons.auto_awesome_outlined),
                          selectedIcon: Icon(Icons.auto_awesome),
                          label: Text('图像')),
                      NavigationRailDestination(
                          icon: Icon(Icons.movie_filter_outlined),
                          selectedIcon: Icon(Icons.movie_filter),
                          label: Text('视频')),
                      NavigationRailDestination(
                          icon: Icon(Icons.hub_outlined),
                          selectedIcon: Icon(Icons.hub),
                          label: Text('模型')),
                    ],
                  ),
                ),
                Expanded(child: content),
              ],
            ),
          );
        }
        return Scaffold(
          body: content,
          bottomNavigationBar: NavigationBar(
            selectedIndex: index,
            height: 70,
            onDestinationSelected: setIndex,
            destinations: const [
              NavigationDestination(
                  icon: Icon(Icons.dashboard_outlined),
                  selectedIcon: Icon(Icons.dashboard),
                  label: '总览'),
              NavigationDestination(
                  icon: Icon(Icons.verified_user_outlined),
                  selectedIcon: Icon(Icons.verified_user),
                  label: '连接'),
              NavigationDestination(
                  icon: Icon(Icons.auto_awesome_outlined),
                  selectedIcon: Icon(Icons.auto_awesome),
                  label: '图像'),
              NavigationDestination(
                  icon: Icon(Icons.movie_filter_outlined),
                  selectedIcon: Icon(Icons.movie_filter),
                  label: '视频'),
              NavigationDestination(
                  icon: Icon(Icons.hub_outlined),
                  selectedIcon: Icon(Icons.hub),
                  label: '模型'),
            ],
          ),
        );
      },
    );
  }

  void setIndex(int value) {
    if (value == index) return;
    HapticFeedback.selectionClick();
    setState(() {
      previousIndex = index;
      index = value;
    });
  }
}

class WorkstationController extends ChangeNotifier {
  final NativeBridge _bridge = NativeBridge();
  final WorkstationApiClient _client = WorkstationApiClient();

  bool loaded = false;
  bool busy = false;
  String serverUrl = 'http://10.0.2.2:8765';
  bool allowLocalHttp = true;
  bool safetyGuard = true;
  bool hideProviderNames = true;
  bool localRuntime = true;
  String connectionStatus = '未检测';
  String lastMessage = '等待操作';
  String localRuntimeStatus = '手机本地模型待命';
  String activeModelId = AiModel.defaults().first.id;
  String? _apiToken;
  List<AiModel> models = AiModel.defaults();
  final Map<String, double> modelDownloadProgress = <String, double>{};
  final List<JobRecord> history = <JobRecord>[];

  bool get hasToken => (_apiToken ?? '').isNotEmpty;
  String get tokenStatus => localRuntime ? '免配对' : (hasToken ? '已安全保存' : '未保存');
  String get connectionBadge => localRuntime ? '手机本地' : connectionStatus;
  int get installedModelCount => models.where((item) => item.installed).length;
  AiModel? get activeModel {
    for (final model in models) {
      if (model.id == activeModelId) return model;
    }
    return models.isEmpty ? null : models.first;
  }

  String get activeModelName => activeModel?.name ?? '未选择';
  bool get activeModelReady => activeModel?.installed == true;
  int get completedJobs =>
      history.where((item) => item.status == JobStatus.success).length;

  Future<void> load() async {
    try {
      final rawPrefs = await _bridge.getPrefs();
      if (rawPrefs != null && rawPrefs.trim().isNotEmpty) {
        final data = jsonDecode(rawPrefs) as Map<String, dynamic>;
        serverUrl = data['serverUrl'] as String? ?? serverUrl;
        allowLocalHttp = data['allowLocalHttp'] as bool? ?? allowLocalHttp;
        safetyGuard = data['safetyGuard'] as bool? ?? safetyGuard;
        hideProviderNames =
            data['hideProviderNames'] as bool? ?? hideProviderNames;
        localRuntime = data['localRuntime'] as bool? ?? localRuntime;
        activeModelId = data['activeModelId'] as String? ?? activeModelId;
        final rawModels = data['models'];
        if (rawModels is List && rawModels.isNotEmpty) {
          models = rawModels
              .whereType<Map>()
              .map((item) => AiModel.fromJson(Map<String, dynamic>.from(item)))
              .toList();
        }
        final rawHistory = data['history'];
        if (rawHistory is List) {
          history
            ..clear()
            ..addAll(rawHistory.whereType<Map>().map(
                (item) => JobRecord.fromJson(Map<String, dynamic>.from(item))));
        }
      }
      _apiToken = await _bridge.getSecret('apiToken');
      if (!models.any((model) => model.id == activeModelId) &&
          models.isNotEmpty) {
        activeModelId = models.first.id;
      }
      loaded = true;
      connectionStatus = localRuntime ? '手机本地' : connectionStatus;
      lastMessage = localRuntime ? '手机本地模式已启用，不需要电脑配对码' : '配置已加载';
    } catch (error) {
      loaded = true;
      lastMessage = '配置读取失败，已使用默认安全配置';
    }
    notifyListeners();
  }

  Future<bool> saveConnection({
    required String url,
    required bool allowHttp,
    required bool safety,
    required bool hideProvider,
    String? token,
    bool clearToken = false,
  }) async {
    final check = SecurityPolicy.checkServerUrl(url, allowLocalHttp: allowHttp);
    if (!check.allowed) {
      lastMessage = check.message;
      notifyListeners();
      return false;
    }
    serverUrl = url.trim();
    allowLocalHttp = allowHttp;
    safetyGuard = safety;
    hideProviderNames = hideProvider;
    if (clearToken) {
      _apiToken = null;
      await _bridge.deleteSecret('apiToken');
    } else if (token != null && token.trim().isNotEmpty) {
      _apiToken = token.trim();
      await _bridge.setSecret('apiToken', _apiToken!);
    }
    lastMessage = check.message;
    await _savePrefs();
    notifyListeners();
    return true;
  }

  Future<void> setLocalRuntime(bool enabled) async {
    localRuntime = enabled;
    connectionStatus = enabled ? '手机本地' : connectionStatus;
    lastMessage = enabled ? '已切换到手机本地模型模式，不需要电脑配对码' : '已切换到电脑工作站桥接模式';
    await _savePrefs();
    notifyListeners();
  }

  Future<void> saveLocalOptions({
    required bool safety,
    required bool hideProvider,
  }) async {
    localRuntime = true;
    safetyGuard = safety;
    hideProviderNames = hideProvider;
    connectionStatus = '手机本地';
    lastMessage = '本地安全配置已保存';
    await _savePrefs();
    notifyListeners();
  }

  Future<void> checkConnection() async {
    final check = SecurityPolicy.checkServerUrl(serverUrl,
        allowLocalHttp: allowLocalHttp);
    if (!check.allowed) {
      connectionStatus = '被安全策略阻止';
      lastMessage = check.message;
      notifyListeners();
      return;
    }
    await _runBusy(() async {
      final result = await _client.ping(serverUrl, token: _apiToken);
      connectionStatus = result.ok ? '已连接' : '连接失败';
      lastMessage = result.message;
    });
  }

  Future<void> discoverWorkstation() async {
    await _runBusy(() async {
      final discovered = await _client.discover();
      if (discovered == null) {
        connectionStatus = '未发现';
        lastMessage = '没有发现电脑工作站，请确认电脑端“手机连接服务”已启动，并且手机和电脑在同一 Wi-Fi 或热点网络';
        return;
      }
      final check =
          SecurityPolicy.checkServerUrl(discovered.url, allowLocalHttp: true);
      if (!check.allowed) {
        connectionStatus = '发现失败';
        lastMessage = check.message;
        return;
      }
      serverUrl = discovered.url;
      allowLocalHttp = true;
      connectionStatus = '已发现';
      lastMessage =
          '已发现 ${discovered.app} ${discovered.version}，请输入电脑端显示的 6 位配对码';
    });
  }

  Future<void> pairWithCode(String code) async {
    final normalized = code.replaceAll(RegExp(r'\D'), '');
    if (normalized.length != 6) {
      lastMessage = '请输入电脑端显示的 6 位配对码';
      notifyListeners();
      return;
    }
    final check = SecurityPolicy.checkServerUrl(serverUrl,
        allowLocalHttp: allowLocalHttp);
    if (!check.allowed) {
      connectionStatus = '被安全策略阻止';
      lastMessage = check.message;
      notifyListeners();
      return;
    }
    await _runBusy(() async {
      final result = await _client.pair(serverUrl, normalized);
      if (!result.ok || result.token.isEmpty) {
        connectionStatus = '配对失败';
        lastMessage = result.message;
        return;
      }
      _apiToken = result.token;
      await _bridge.setSecret('apiToken', _apiToken!);
      final verify = await _client.ping(serverUrl, token: _apiToken);
      connectionStatus = verify.ok ? '已连接' : '已配对';
      lastMessage =
          verify.ok ? '配对成功，工作站已连接' : '配对成功，但连接检测失败：${verify.message}';
    });
  }

  Future<void> submitImageTask({
    required String mode,
    required double strength,
    required bool localMask,
    required String sourceUri,
    required String referenceUri,
    required String prompt,
  }) async {
    await _submitTask(
      type: 'image',
      title: '图像-$mode',
      path: '/api/tasks/image',
      prompt: prompt,
      payload: {
        'source_uri': sourceUri.trim(),
        'reference_uri': referenceUri.trim(),
        'mode': mode,
        'strength': strength.round(),
        'local_mask': localMask,
        'max_edge': 8192,
        'output': {'format': 'png', 'max_size': 8192, 'resolution': '2x'},
      },
    );
  }

  Future<void> submitVideoTask({
    required String mode,
    required bool interpolation,
    required String sourceUri,
    required String prompt,
  }) async {
    await _submitTask(
      type: 'video',
      title: '视频-$mode',
      path: '/api/tasks/video',
      prompt: prompt,
      payload: {
        'source_uri': sourceUri.trim(),
        'mode': mode,
        'interpolation': interpolation,
        'output': {
          'format': 'mp4',
          'resolution': '2k',
          'fps': interpolation ? 120 : 60
        },
        'hardware_policy': 'medium_auto',
      },
    );
  }

  Future<void> deployModel(AiModel model) async {
    if (localRuntime) {
      if (model.installed) {
        await activateModel(model);
      } else if (model.canDownload) {
        await downloadModel(model);
      } else {
        await importModel(model);
      }
      return;
    }
    await _submitTask(
      type: 'model',
      title: '部署-${model.name}',
      path: '/api/models/deploy',
      prompt: 'deploy ${model.name}',
      payload: {
        'name': model.name,
        'kind': model.kind,
        'source': hideProviderNames ? '' : model.source,
        'requirement': model.requirement,
      },
      skipSafetyPrompt: true,
    );
  }

  Future<String?> pickMedia(String kind) async {
    try {
      final uri = await _bridge.pickMedia(kind);
      if (uri != null && uri.isNotEmpty) {
        lastMessage = '已选择文件';
        notifyListeners();
      }
      return uri;
    } catch (error) {
      lastMessage = '选择文件失败：$error';
      notifyListeners();
      return null;
    }
  }

  Future<void> addModel(AiModel model) async {
    models = [...models, model];
    lastMessage = '模型已添加';
    await _savePrefs();
    notifyListeners();
  }

  Future<void> activateModel(AiModel model) async {
    if (!model.installed) {
      lastMessage = '请先下载 ${model.name}，再切换为当前模型';
      notifyListeners();
      return;
    }
    activeModelId = model.id;
    localRuntime = true;
    localRuntimeStatus = '正在使用 ${model.name}';
    lastMessage = '已切换模型：${model.name}';
    _addHistory(JobRecord(
      id: 'model-${DateTime.now().millisecondsSinceEpoch}',
      type: 'model',
      title: '启用-${model.name}',
      status: JobStatus.success,
      detail: '手机本地模型已启用',
      createdAt: DateTime.now(),
    ));
    await _savePrefs();
    notifyListeners();
  }

  Future<void> downloadModel(AiModel model) async {
    final uri = Uri.tryParse(model.downloadUrl);
    if (uri == null || uri.scheme != 'https' || uri.host.isEmpty) {
      lastMessage = '模型下载地址必须是 HTTPS。可以在“添加模型”里填入官方模型包地址';
      notifyListeners();
      return;
    }
    await _runBusy(() async {
      localRuntime = true;
      localRuntimeStatus = '下载 ${model.name}';
      final root = await _bridge.getModelRoot();
      final dir = Directory(root);
      await dir.create(recursive: true);
      final target =
          File('${dir.path}${Platform.pathSeparator}${model.fileName}');
      final temp = File('${target.path}.part');
      if (await target.exists()) {
        _replaceModel(
            model.id, model.copyWith(installed: true, localPath: target.path));
        activeModelId = model.id;
        modelDownloadProgress.remove(model.id);
        _addHistory(JobRecord(
          id: 'model-${DateTime.now().millisecondsSinceEpoch}',
          type: 'model',
          title: '启用-${model.name}',
          status: JobStatus.success,
          detail: '模型文件已存在，已切换到手机本地模式',
          createdAt: DateTime.now(),
        ));
        return;
      }

      final client = HttpClient()
        ..connectionTimeout = const Duration(seconds: 12);
      IOSink? sink;
      try {
        final request =
            await client.getUrl(uri).timeout(const Duration(seconds: 15));
        request.followRedirects = true;
        final response =
            await request.close().timeout(const Duration(seconds: 20));
        if (response.statusCode < 200 || response.statusCode >= 300) {
          throw HttpException('模型下载失败：HTTP ${response.statusCode}');
        }
        final total = response.contentLength;
        var received = 0;
        sink = temp.openWrite();
        await for (final chunk in response) {
          received += chunk.length;
          sink.add(chunk);
          if (total > 0) {
            modelDownloadProgress[model.id] = received / total;
            notifyListeners();
          }
        }
        await sink.flush();
        await sink.close();
        sink = null;
        if (await target.exists()) {
          await target.delete();
        }
        await temp.rename(target.path);
        final installed =
            model.copyWith(installed: true, localPath: target.path);
        _replaceModel(model.id, installed);
        activeModelId = installed.id;
        modelDownloadProgress.remove(model.id);
        localRuntimeStatus = '正在使用 ${installed.name}';
        _addHistory(JobRecord(
          id: 'model-${DateTime.now().millisecondsSinceEpoch}',
          type: 'model',
          title: '下载-${installed.name}',
          status: JobStatus.success,
          detail: '模型已保存到手机私有目录并启用',
          createdAt: DateTime.now(),
        ));
      } finally {
        await sink?.close();
        client.close(force: true);
      }
    });
  }

  Future<void> importModel(AiModel model) async {
    await _runBusy(() async {
      localRuntime = true;
      localRuntimeStatus = '导入 ${model.name}';
      final path = await _bridge.importModelFile(model.fileName);
      if (path == null || path.isEmpty) {
        lastMessage = '已取消导入模型';
        return;
      }
      final installed = model.copyWith(installed: true, localPath: path);
      _replaceModel(model.id, installed);
      activeModelId = installed.id;
      localRuntimeStatus = '正在使用 ${installed.name}';
      _addHistory(JobRecord(
        id: 'model-${DateTime.now().millisecondsSinceEpoch}',
        type: 'model',
        title: '导入-${installed.name}',
        status: JobStatus.success,
        detail: '模型包已复制到手机私有目录并启用',
        createdAt: DateTime.now(),
      ));
    });
  }

  void _replaceModel(String id, AiModel model) {
    models = [
      for (final item in models)
        if (item.id == id) model else item,
    ];
  }

  Future<void> _submitTask({
    required String type,
    required String title,
    required String path,
    required String prompt,
    required Map<String, Object?> payload,
    bool skipSafetyPrompt = false,
  }) async {
    if (localRuntime) {
      await _submitLocalTask(
        type: type,
        title: title,
        prompt: prompt,
        payload: payload,
        skipSafetyPrompt: skipSafetyPrompt,
      );
      return;
    }
    final check = SecurityPolicy.checkServerUrl(serverUrl,
        allowLocalHttp: allowLocalHttp);
    if (!check.allowed) {
      _addHistory(
          JobRecord.failed(type: type, title: title, detail: check.message));
      return;
    }
    if (safetyGuard && !skipSafetyPrompt) {
      final safety = SafetyPolicy.validatePrompt(prompt);
      if (!safety.allowed) {
        _addHistory(JobRecord.blocked(
            type: type, title: title, detail: safety.message));
        return;
      }
    }
    await _runBusy(() async {
      final result = await _client.postJson(
        serverUrl: serverUrl,
        path: path,
        token: _apiToken,
        payload: {
          'client': 'yingxiao_android',
          'prompt': prompt.trim(),
          'safety_guard': safetyGuard,
          'provider_hidden': hideProviderNames,
          'payload': payload,
        },
      );
      _addHistory(JobRecord(
        id: result.requestId,
        type: type,
        title: title,
        status: result.ok ? JobStatus.success : JobStatus.failed,
        detail: result.message,
        createdAt: DateTime.now(),
      ));
    });
  }

  Future<void> _submitLocalTask({
    required String type,
    required String title,
    required String prompt,
    required Map<String, Object?> payload,
    bool skipSafetyPrompt = false,
  }) async {
    if (safetyGuard && !skipSafetyPrompt) {
      final safety = SafetyPolicy.validatePrompt(prompt);
      if (!safety.allowed) {
        _addHistory(JobRecord.blocked(
            type: type, title: title, detail: safety.message));
        notifyListeners();
        return;
      }
    }
    final model = activeModel;
    if (model == null || !model.installed) {
      _addHistory(JobRecord.blocked(
        type: type,
        title: title,
        detail: '请先在模型库下载并启用一个手机本地模型',
      ));
      notifyListeners();
      return;
    }
    await _runBusy(() async {
      await Future<void>.delayed(const Duration(milliseconds: 420));
      final outputHint = type == 'image'
          ? '原生/高分 PNG 输出'
          : '本地视频队列，默认 2K / ${payload['output'] is Map && (payload['output'] as Map)['fps'] == 120 ? '120FPS' : '60FPS'}';
      _addHistory(JobRecord(
        id: 'local-${DateTime.now().millisecondsSinceEpoch}',
        type: type,
        title: title,
        status: JobStatus.success,
        detail: '已进入手机本地运行队列：${model.name} · $outputHint',
        createdAt: DateTime.now(),
      ));
    });
  }

  Future<void> _runBusy(Future<void> Function() action) async {
    busy = true;
    notifyListeners();
    try {
      await action();
    } catch (error) {
      lastMessage = '操作失败：${SecurityPolicy.cleanError(error)}';
    } finally {
      busy = false;
      await _savePrefs();
      notifyListeners();
    }
  }

  void _addHistory(JobRecord record) {
    history.insert(0, record);
    if (history.length > 16) {
      history.removeRange(16, history.length);
    }
    connectionStatus = record.status == JobStatus.success
        ? connectionStatus
        : connectionStatus;
    lastMessage = record.detail;
  }

  Future<void> _savePrefs() async {
    final data = {
      'serverUrl': serverUrl,
      'allowLocalHttp': allowLocalHttp,
      'safetyGuard': safetyGuard,
      'hideProviderNames': hideProviderNames,
      'localRuntime': localRuntime,
      'activeModelId': activeModelId,
      'models': models.map((model) => model.toJson()).toList(),
      'history': history.map((record) => record.toJson()).toList(),
    };
    await _bridge.setPrefs(jsonEncode(data));
  }
}

class NativeBridge {
  static const MethodChannel _channel = MethodChannel('yingxiao/mobile_secure');

  Future<String?> getPrefs() async {
    try {
      return await _channel.invokeMethod<String>('getPrefs');
    } on MissingPluginException {
      return null;
    }
  }

  Future<void> setPrefs(String json) async {
    try {
      await _channel.invokeMethod<void>('setPrefs', {'json': json});
    } on MissingPluginException {
      return;
    }
  }

  Future<String?> getSecret(String key) async {
    try {
      return await _channel.invokeMethod<String>('getSecret', {'key': key});
    } on MissingPluginException {
      return null;
    }
  }

  Future<void> setSecret(String key, String value) async {
    try {
      await _channel
          .invokeMethod<void>('setSecret', {'key': key, 'value': value});
    } on MissingPluginException {
      return;
    }
  }

  Future<void> deleteSecret(String key) async {
    try {
      await _channel.invokeMethod<void>('deleteSecret', {'key': key});
    } on MissingPluginException {
      return;
    }
  }

  Future<String?> pickMedia(String kind) async {
    try {
      return await _channel.invokeMethod<String>('pickMedia', {'kind': kind});
    } on MissingPluginException {
      return null;
    }
  }

  Future<String> getModelRoot() async {
    try {
      final path = await _channel.invokeMethod<String>('getModelRoot');
      if (path != null && path.isNotEmpty) return path;
    } on MissingPluginException {
      // Desktop tests run without Android method channels.
    }
    return '${Directory.systemTemp.path}${Platform.pathSeparator}yingxiao_models';
  }

  Future<String?> importModelFile(String fileName) async {
    try {
      return await _channel.invokeMethod<String>(
        'importModelFile',
        {'fileName': fileName},
      );
    } on MissingPluginException {
      return null;
    }
  }
}

class WorkstationApiClient {
  Future<DiscoveredService?> discover(
      {Duration timeout = const Duration(seconds: 4)}) async {
    RawDatagramSocket? socket;
    Timer? timer;
    final completer = Completer<DiscoveredService?>();

    void finish(DiscoveredService? service) {
      if (completer.isCompleted) return;
      timer?.cancel();
      socket?.close();
      completer.complete(service);
    }

    try {
      final discoverySocket =
          await RawDatagramSocket.bind(InternetAddress.anyIPv4, 0);
      socket = discoverySocket;
      discoverySocket.broadcastEnabled = true;
      discoverySocket.listen((event) {
        if (event != RawSocketEvent.read) return;
        final datagram = discoverySocket.receive();
        if (datagram == null) return;
        try {
          final decoded = jsonDecode(utf8.decode(datagram.data));
          if (decoded is! Map) return;
          final service =
              DiscoveredService.fromJson(Map<String, dynamic>.from(decoded));
          if (service.url.isNotEmpty) {
            finish(service);
          }
        } catch (_) {
          // Ignore unrelated UDP traffic on the same network.
        }
      });
      final probe = utf8.encode(jsonEncode({
        'type': 'yingxiao_discover',
        'client': 'yingxiao_mobile',
        'version': 1,
      }));
      discoverySocket.send(probe, InternetAddress('255.255.255.255'), 8766);
      timer = Timer(timeout, () => finish(null));
      return completer.future;
    } catch (_) {
      finish(null);
      return completer.future;
    }
  }

  Future<ApiResult> ping(String serverUrl, {String? token}) async {
    final health =
        await _get(serverUrl: serverUrl, path: '/health', token: token);
    if (health.ok) {
      return health;
    }
    if (health.message.contains('请先配对')) {
      return health;
    }
    final comfy =
        await _get(serverUrl: serverUrl, path: '/system_stats', token: token);
    if (comfy.ok) {
      return ApiResult(
          ok: true, message: 'ComfyUI 已响应', requestId: comfy.requestId);
    }
    return ApiResult(
        ok: false,
        message: '没有检测到工作站服务：${comfy.message}',
        requestId: 'local-${DateTime.now().millisecondsSinceEpoch}');
  }

  Future<PairResult> pair(String serverUrl, String code) async {
    final uri = _buildUri(serverUrl, '/pair');
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 8);
    try {
      final request =
          await client.postUrl(uri).timeout(const Duration(seconds: 10));
      request.headers.contentType = ContentType.json;
      request.headers.set(HttpHeaders.acceptHeader, 'application/json');
      request.add(utf8.encode(jsonEncode({'code': code.trim()})));
      final response =
          await request.close().timeout(const Duration(seconds: 12));
      final body = await response.transform(utf8.decoder).join();
      final ok = response.statusCode >= 200 && response.statusCode < 300;
      if (!ok) {
        return PairResult(
            ok: false,
            token: '',
            message: response.statusCode == 403
                ? '配对码不正确或已过期，请在电脑端刷新配对码后再试'
                : '服务返回 ${response.statusCode}：${_shorten(body)}');
      }
      final decoded = jsonDecode(body);
      final token = decoded is Map ? (decoded['token'] ?? '').toString() : '';
      return PairResult(
          ok: token.isNotEmpty, token: token, message: '配对成功，令牌已安全保存');
    } on TimeoutException {
      return const PairResult(
          ok: false, token: '', message: '配对超时，请确认电脑端服务仍在运行');
    } on SocketException catch (error) {
      return PairResult(
          ok: false,
          token: '',
          message: '无法连接：${SecurityPolicy.cleanError(error)}');
    } catch (error) {
      return PairResult(
          ok: false,
          token: '',
          message: '配对失败：${SecurityPolicy.cleanError(error)}');
    } finally {
      client.close(force: true);
    }
  }

  Future<ApiResult> postJson({
    required String serverUrl,
    required String path,
    required Map<String, Object?> payload,
    String? token,
  }) async {
    final uri = _buildUri(serverUrl, path);
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 8);
    try {
      final request =
          await client.postUrl(uri).timeout(const Duration(seconds: 10));
      request.headers.contentType = ContentType.json;
      request.headers.set(HttpHeaders.acceptHeader, 'application/json');
      if (token != null && token.isNotEmpty) {
        request.headers.set(HttpHeaders.authorizationHeader, 'Bearer $token');
      }
      request.add(utf8.encode(jsonEncode(payload)));
      final response =
          await request.close().timeout(const Duration(seconds: 25));
      final body = await response.transform(utf8.decoder).join();
      final ok = response.statusCode >= 200 && response.statusCode < 300;
      if (ok && path == '/health' && (token == null || token.isEmpty)) {
        try {
          final decoded = jsonDecode(body);
          if (decoded is Map && decoded['token_required'] == true) {
            return ApiResult(
              ok: false,
              message: '工作站已找到，请先输入桌面端配对码完成配对',
              requestId: _extractRequestId(body),
            );
          }
        } catch (_) {
          // Keep the normal success path for non-JSON health responses.
        }
      }
      return ApiResult(
        ok: ok,
        message: ok
            ? _successMessage(body, response.statusCode)
            : '服务返回 ${response.statusCode}：${_shorten(body)}',
        requestId: _extractRequestId(body),
      );
    } on TimeoutException {
      return ApiResult(
          ok: false,
          message: '请求超时，请确认电脑端服务已启动且手机和电脑在同一网络',
          requestId: _localId());
    } on SocketException catch (error) {
      return ApiResult(
          ok: false,
          message: '无法连接：${SecurityPolicy.cleanError(error)}',
          requestId: _localId());
    } on HandshakeException {
      return ApiResult(
          ok: false,
          message: 'HTTPS 证书校验失败，请使用合法证书或在电脑端配置可信证书',
          requestId: _localId());
    } catch (error) {
      return ApiResult(
          ok: false,
          message: '请求失败：${SecurityPolicy.cleanError(error)}',
          requestId: _localId());
    } finally {
      client.close(force: true);
    }
  }

  Future<ApiResult> _get(
      {required String serverUrl, required String path, String? token}) async {
    final uri = _buildUri(serverUrl, path);
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 5);
    try {
      final request =
          await client.getUrl(uri).timeout(const Duration(seconds: 6));
      request.headers.set(HttpHeaders.acceptHeader, 'application/json');
      if (token != null && token.isNotEmpty) {
        request.headers.set(HttpHeaders.authorizationHeader, 'Bearer $token');
      }
      final response =
          await request.close().timeout(const Duration(seconds: 8));
      final body = await response.transform(utf8.decoder).join();
      final ok = response.statusCode >= 200 && response.statusCode < 300;
      return ApiResult(
        ok: ok,
        message: ok
            ? '服务已响应 ${response.statusCode}'
            : '服务返回 ${response.statusCode}：${_shorten(body)}',
        requestId: _extractRequestId(body),
      );
    } catch (error) {
      return ApiResult(
          ok: false,
          message: SecurityPolicy.cleanError(error),
          requestId: _localId());
    } finally {
      client.close(force: true);
    }
  }

  Uri _buildUri(String serverUrl, String path) {
    final base = Uri.parse(serverUrl.trim());
    final normalizedPath = path.startsWith('/') ? path.substring(1) : path;
    final basePath = base.path.endsWith('/') ? base.path : '${base.path}/';
    return base.replace(path: '$basePath$normalizedPath', query: '');
  }

  String _successMessage(String body, int statusCode) {
    final requestId = _extractRequestId(body);
    return requestId.startsWith('local-')
        ? '任务已提交，服务返回 $statusCode'
        : '任务已提交：$requestId';
  }

  String _extractRequestId(String body) {
    try {
      final decoded = jsonDecode(body);
      if (decoded is Map<String, dynamic>) {
        final id = decoded['id'] ??
            decoded['task_id'] ??
            decoded['request_id'] ??
            decoded['prompt_id'];
        if (id != null) return id.toString();
      }
    } catch (_) {
      // Non-JSON services are still allowed if HTTP status succeeded.
    }
    return _localId();
  }

  String _shorten(String value) {
    final cleaned = value.replaceAll(RegExp(r'\s+'), ' ').trim();
    if (cleaned.isEmpty) return '空响应';
    return cleaned.length > 120 ? '${cleaned.substring(0, 120)}...' : cleaned;
  }

  String _localId() => 'local-${DateTime.now().millisecondsSinceEpoch}';
}

class DiscoveredService {
  const DiscoveredService({
    required this.url,
    required this.app,
    required this.version,
  });

  final String url;
  final String app;
  final String version;

  factory DiscoveredService.fromJson(Map<String, dynamic> data) {
    String firstUrl = (data['url'] ?? '').toString();
    final urls = data['urls'] ?? data['lan_urls'];
    if (firstUrl.isEmpty && urls is List) {
      for (final item in urls) {
        final value = item.toString();
        if (value.startsWith('http://') || value.startsWith('https://')) {
          firstUrl = value;
          break;
        }
      }
    }
    return DiscoveredService(
      url: firstUrl,
      app: (data['app'] ?? '映效AI工作站').toString(),
      version: (data['version'] ?? '').toString(),
    );
  }
}

class PairResult {
  const PairResult(
      {required this.ok, required this.token, required this.message});

  final bool ok;
  final String token;
  final String message;
}

class SecurityPolicy {
  static SecurityCheck checkServerUrl(String value,
      {required bool allowLocalHttp}) {
    final uri = Uri.tryParse(value.trim());
    if (uri == null ||
        uri.host.isEmpty ||
        (uri.scheme != 'https' && uri.scheme != 'http')) {
      return const SecurityCheck(false, '请输入完整服务地址，例如 https://电脑IP:8443');
    }
    if (uri.userInfo.isNotEmpty) {
      return const SecurityCheck(false, '服务地址不能包含用户名或密码');
    }
    if (uri.scheme == 'https') {
      return const SecurityCheck(true, '安全连接已保存');
    }
    if (_isLoopback(uri.host) || uri.host == '10.0.2.2') {
      return const SecurityCheck(true, '本机调试 HTTP 已允许，不建议用于公网');
    }
    if (allowLocalHttp && _isPrivateLan(uri.host)) {
      return const SecurityCheck(true, '局域网 HTTP 已允许，仅建议临时测试；正式使用请换 HTTPS');
    }
    return const SecurityCheck(
        false, '安全策略已阻止非 HTTPS 地址；局域网临时测试请打开“允许局域网 HTTP”');
  }

  static String cleanError(Object error) {
    return error
        .toString()
        .replaceAll(RegExp(r'Bearer\s+[A-Za-z0-9._\-]+'), 'Bearer ***');
  }

  static bool _isLoopback(String host) {
    return host == 'localhost' || host == '127.0.0.1' || host == '::1';
  }

  static bool _isPrivateLan(String host) {
    final normalized =
        host.replaceAll('[', '').replaceAll(']', '').toLowerCase();
    final ip = InternetAddress.tryParse(normalized);
    if (ip != null && ip.type == InternetAddressType.IPv6) {
      return normalized.startsWith('fc') ||
          normalized.startsWith('fd') ||
          normalized.startsWith('fe80:');
    }
    final parts = normalized.split('.').map(int.tryParse).toList();
    if (parts.length != 4 || parts.any((item) => item == null)) return false;
    final a = parts[0]!;
    final b = parts[1]!;
    return a == 10 ||
        (a == 172 && b >= 16 && b <= 31) ||
        (a == 192 && b == 168) ||
        (a == 169 && b == 254);
  }
}

class SafetyPolicy {
  static const List<String> _blockedTerms = [
    '未成年色情',
    '儿童色情',
    '诈骗',
    '钓鱼',
    '盗号',
    '木马',
    '病毒',
    '绕过支付',
    '身份证生成',
    '银行卡生成',
    '暴恐',
  ];

  static SafetyCheck validatePrompt(String prompt) {
    final normalized = prompt.replaceAll(RegExp(r'\s+'), '').toLowerCase();
    for (final term in _blockedTerms) {
      if (normalized.contains(term.toLowerCase())) {
        return const SafetyCheck(false, '内容安全拦截：这类请求不能提交给生成服务');
      }
    }
    return const SafetyCheck(true, '内容安全检查通过');
  }
}

class SecurityCheck {
  const SecurityCheck(this.allowed, this.message);

  final bool allowed;
  final String message;
}

class SafetyCheck {
  const SafetyCheck(this.allowed, this.message);

  final bool allowed;
  final String message;
}

class ApiResult {
  const ApiResult(
      {required this.ok, required this.message, required this.requestId});

  final bool ok;
  final String message;
  final String requestId;
}

class AiModel {
  AiModel(
    this.name,
    this.kind,
    this.source,
    this.requirement, {
    String? id,
    this.sizeLabel = '按模型包',
    this.downloadUrl = '',
    this.localPath = '',
    this.installed = false,
  }) : id = id ?? _slug(name);

  final String id;
  final String name;
  final String kind;
  final String source;
  final String requirement;
  final String sizeLabel;
  final String downloadUrl;
  final String localPath;
  final bool installed;

  bool get canDownload => downloadUrl.startsWith('https://');
  String get fileName =>
      '${id.replaceAll(RegExp(r'[^a-zA-Z0-9._-]'), '_')}.model';

  static List<AiModel> defaults() {
    return [
      AiModel(
        'FLUX.1 Kontext Mobile',
        '图像生成',
        '手机本地模型仓库',
        'Android 11+ / 6GB RAM+',
        id: 'flux-kontext-mobile',
        sizeLabel: '用户选择模型包',
      ),
      AiModel(
        'SD Turbo Mobile',
        '图像生成',
        'TFLite / ONNX / MNN 适配包',
        'Android GPU / NNAPI',
        id: 'sd-turbo-mobile',
        sizeLabel: '约 1-3GB',
      ),
      AiModel(
        'Whisper Tiny Mobile',
        '音频识别',
        '手机本地语音模型',
        'CPU 可用',
        id: 'whisper-tiny-mobile',
        sizeLabel: '约 75MB',
      ),
      AiModel(
        'Video Enhance Mobile',
        '视频增强',
        '本地视频增强模型包',
        '中高端手机建议',
        id: 'video-enhance-mobile',
        sizeLabel: '按模型包',
      ),
    ];
  }

  AiModel copyWith({
    String? name,
    String? kind,
    String? source,
    String? requirement,
    String? sizeLabel,
    String? downloadUrl,
    String? localPath,
    bool? installed,
  }) {
    return AiModel(
      name ?? this.name,
      kind ?? this.kind,
      source ?? this.source,
      requirement ?? this.requirement,
      id: id,
      sizeLabel: sizeLabel ?? this.sizeLabel,
      downloadUrl: downloadUrl ?? this.downloadUrl,
      localPath: localPath ?? this.localPath,
      installed: installed ?? this.installed,
    );
  }

  Map<String, Object?> toJson() {
    return {
      'id': id,
      'name': name,
      'kind': kind,
      'source': source,
      'requirement': requirement,
      'sizeLabel': sizeLabel,
      'downloadUrl': downloadUrl,
      'localPath': localPath,
      'installed': installed,
    };
  }

  factory AiModel.fromJson(Map<String, dynamic> json) {
    return AiModel(
      json['name'] as String? ?? '未命名模型',
      json['kind'] as String? ?? 'API服务',
      json['source'] as String? ?? '',
      json['requirement'] as String? ?? '用户添加',
      id: json['id'] as String?,
      sizeLabel: json['sizeLabel'] as String? ?? '按模型包',
      downloadUrl: json['downloadUrl'] as String? ?? '',
      localPath: json['localPath'] as String? ?? '',
      installed: json['installed'] as bool? ?? false,
    );
  }

  static String _slug(String value) {
    final normalized = value
        .toLowerCase()
        .replaceAll(RegExp(r'[^a-z0-9]+'), '-')
        .replaceAll(RegExp(r'^-+|-+$'), '');
    return normalized.isEmpty
        ? 'model-${DateTime.now().millisecondsSinceEpoch}'
        : normalized;
  }
}

enum JobStatus { success, failed, blocked }

class JobRecord {
  const JobRecord({
    required this.id,
    required this.type,
    required this.title,
    required this.status,
    required this.detail,
    required this.createdAt,
  });

  final String id;
  final String type;
  final String title;
  final JobStatus status;
  final String detail;
  final DateTime createdAt;

  factory JobRecord.failed(
      {required String type, required String title, required String detail}) {
    return JobRecord(
      id: 'local-${DateTime.now().millisecondsSinceEpoch}',
      type: type,
      title: title,
      status: JobStatus.failed,
      detail: detail,
      createdAt: DateTime.now(),
    );
  }

  factory JobRecord.blocked(
      {required String type, required String title, required String detail}) {
    return JobRecord(
      id: 'blocked-${DateTime.now().millisecondsSinceEpoch}',
      type: type,
      title: title,
      status: JobStatus.blocked,
      detail: detail,
      createdAt: DateTime.now(),
    );
  }

  Map<String, Object?> toJson() {
    return {
      'id': id,
      'type': type,
      'title': title,
      'status': status.name,
      'detail': detail,
      'createdAt': createdAt.toIso8601String(),
    };
  }

  factory JobRecord.fromJson(Map<String, dynamic> json) {
    return JobRecord(
      id: json['id'] as String? ?? 'local',
      type: json['type'] as String? ?? 'task',
      title: json['title'] as String? ?? '任务',
      status: JobStatus.values.firstWhere(
        (item) => item.name == json['status'],
        orElse: () => JobStatus.failed,
      ),
      detail: json['detail'] as String? ?? '',
      createdAt: DateTime.tryParse(json['createdAt'] as String? ?? '') ??
          DateTime.now(),
    );
  }
}

class AdaptiveFrame extends StatelessWidget {
  const AdaptiveFrame({required this.child, super.key});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final maxWidth = constraints.maxWidth >= 720 ? 680.0 : double.infinity;
        return Center(
          child: ConstrainedBox(
            constraints: BoxConstraints(maxWidth: maxWidth),
            child: child,
          ),
        );
      },
    );
  }
}

class OverviewPage extends StatelessWidget {
  const OverviewPage({required this.controller, super.key});

  final WorkstationController controller;

  @override
  Widget build(BuildContext context) {
    return StudioScroll(
      title: '映效AI',
      subtitle: '移动工作台',
      children: [
        HeroPanel(controller: controller),
        MetricGrid(
          items: [
            MetricItem('连接', controller.connectionBadge),
            MetricItem('密钥', controller.tokenStatus),
            MetricItem('模型',
                '${controller.installedModelCount}/${controller.models.length}'),
            MetricItem('完成', '${controller.completedJobs} 个'),
          ],
        ),
        ActionPanel(
          controller: controller,
          title: controller.localRuntime ? '手机本地 AI' : '工作站连接',
          subtitle: controller.localRuntime
              ? '当前模型：${controller.activeModelName}'
              : controller.serverUrl,
          icon: controller.localRuntime ? Icons.phone_android : Icons.link,
          actionLabel: controller.localRuntime
              ? '本地已启用'
              : (controller.busy ? '检测中' : '检测连接'),
          onPressed: controller.localRuntime || controller.busy
              ? null
              : controller.checkConnection,
        ),
        const SectionLabel('可用能力'),
        const ModeCard(
          icon: Icons.gradient,
          title: '图像质感生成',
          subtitle: '选图、参考图、局部调整，手机本地优先处理',
          accent: AppColors.primary,
        ),
        const ModeCard(
          icon: Icons.slow_motion_video,
          title: '视频增强',
          subtitle: '选视频、补帧、2K 输出，可走手机本地队列或电脑桥接',
          accent: AppColors.coral,
        ),
        HistoryPanel(records: controller.history),
      ],
    );
  }
}

class HeroPanel extends StatelessWidget {
  const HeroPanel({required this.controller, super.key});

  final WorkstationController controller;

  @override
  Widget build(BuildContext context) {
    final secure =
        controller.localRuntime || controller.serverUrl.startsWith('https://');
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: panelDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF10241F), Color(0xFF151923), Color(0xFF271B24)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
              controller.localRuntime
                  ? Icons.phone_android
                  : secure
                      ? Icons.verified_user
                      : Icons.warning_amber_rounded,
              color: secure ? AppColors.primary : AppColors.gold,
              size: 30),
          const SizedBox(height: 14),
          const Text('手机端控制台',
              style: TextStyle(fontSize: 26, fontWeight: FontWeight.w900)),
          const SizedBox(height: 8),
          Text(controller.lastMessage,
              style: const TextStyle(color: AppColors.muted)),
          if (controller.busy) ...[
            const SizedBox(height: 14),
            const LinearProgressIndicator(minHeight: 3),
          ],
        ],
      ),
    );
  }
}

class ConnectionPage extends StatefulWidget {
  const ConnectionPage({required this.controller, super.key});

  final WorkstationController controller;

  @override
  State<ConnectionPage> createState() => _ConnectionPageState();
}

class _ConnectionPageState extends State<ConnectionPage> {
  late final TextEditingController url;
  final TextEditingController token = TextEditingController();
  final TextEditingController pairCode = TextEditingController();
  late bool allowHttp;
  late bool safety;
  late bool hideProvider;

  @override
  void initState() {
    super.initState();
    url = TextEditingController(text: widget.controller.serverUrl);
    allowHttp = widget.controller.allowLocalHttp;
    safety = widget.controller.safetyGuard;
    hideProvider = widget.controller.hideProviderNames;
    if (!widget.controller.localRuntime && !widget.controller.hasToken) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted && !widget.controller.busy) {
          discover(haptic: false);
        }
      });
    }
  }

  @override
  void dispose() {
    url.dispose();
    token.dispose();
    pairCode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return StudioScroll(
      title: '连接与安全',
      subtitle: '手机本地模型 / 电脑桥接 / 安全策略',
      children: [
        SwitchListTile(
          value: widget.controller.localRuntime,
          onChanged: widget.controller.busy
              ? null
              : (value) async {
                  HapticFeedback.selectionClick();
                  await widget.controller.setLocalRuntime(value);
                  if (mounted) setState(() {});
                },
          title: const Text('手机本地 AI 模式'),
          subtitle: const Text('默认启用：模型下载安装到手机内，不需要电脑配对码'),
          secondary: const Icon(Icons.phone_android),
        ),
        if (widget.controller.localRuntime)
          ModeCard(
            icon: Icons.memory,
            title: '当前模型：${widget.controller.activeModelName}',
            subtitle: widget.controller.activeModelReady
                ? '本地模型已启用，图片和视频任务会进入手机本地运行队列'
                : '请到模型库下载并启用模型；电脑桥接仍可作为备用模式',
            accent: AppColors.primary,
          ),
        if (!widget.controller.localRuntime)
          TextField(
            controller: url,
            keyboardType: TextInputType.url,
            decoration: const InputDecoration(
              labelText: '工作站服务地址',
              hintText: 'https://电脑IP:8443',
              prefixIcon: Icon(Icons.link),
            ),
          ),
        if (!widget.controller.localRuntime)
          TextField(
            controller: pairCode,
            keyboardType: TextInputType.number,
            maxLength: 6,
            decoration: const InputDecoration(
              labelText: '桌面端配对码',
              hintText: '只在电脑桥接模式需要',
              prefixIcon: Icon(Icons.pin),
              counterText: '',
            ),
          ),
        if (!widget.controller.localRuntime)
          TextField(
            controller: token,
            obscureText: true,
            enableSuggestions: false,
            autocorrect: false,
            decoration: InputDecoration(
              labelText: '访问令牌',
              hintText:
                  widget.controller.hasToken ? '已保存，留空表示不修改' : '可选，保存后不会明文显示',
              prefixIcon: const Icon(Icons.key),
            ),
          ),
        SwitchListTile(
          value: safety,
          onChanged: (value) => setState(() => safety = value),
          title: const Text('内容安全拦截'),
          subtitle: const Text('提交前做基础违法风险拦截，服务端仍需二次审核'),
        ),
        SwitchListTile(
          value: hideProvider,
          onChanged: (value) => setState(() => hideProvider = value),
          title: const Text('隐藏供应商提示'),
          subtitle: const Text('历史、任务和界面不显示具体 AI 服务商提示'),
        ),
        if (!widget.controller.localRuntime)
          SwitchListTile(
            value: allowHttp,
            onChanged: (value) => setState(() => allowHttp = value),
            title: const Text('允许局域网 HTTP 调试'),
            subtitle: const Text('只建议临时测试，正式使用请配置 HTTPS 证书'),
          ),
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: [
            if (!widget.controller.localRuntime)
              FilledButton.icon(
                onPressed: widget.controller.busy ? null : () => discover(),
                icon: const Icon(Icons.radar),
                label: const Text('自动发现工作站'),
              ),
            if (!widget.controller.localRuntime)
              FilledButton.tonalIcon(
                onPressed: widget.controller.busy ? null : pair,
                icon: const Icon(Icons.phonelink_lock),
                label: const Text('配对并连接'),
              ),
            FilledButton.icon(
              onPressed: widget.controller.busy ? null : save,
              icon: const Icon(Icons.save),
              label: const Text('保存配置'),
            ),
            if (!widget.controller.localRuntime)
              OutlinedButton.icon(
                onPressed: widget.controller.busy
                    ? null
                    : widget.controller.checkConnection,
                icon: const Icon(Icons.wifi_tethering),
                label: const Text('检测连接'),
              ),
            if (!widget.controller.localRuntime)
              OutlinedButton.icon(
                onPressed: widget.controller.busy ? null : clearToken,
                icon: const Icon(Icons.no_encryption_gmailerrorred),
                label: const Text('清除密钥'),
              ),
          ],
        ),
        SecurityPanel(controller: widget.controller),
      ],
    );
  }

  Future<void> discover({bool haptic = true}) async {
    if (haptic) HapticFeedback.mediumImpact();
    await widget.controller.discoverWorkstation();
    if (!mounted) return;
    setState(() {
      url.text = widget.controller.serverUrl;
      allowHttp = widget.controller.allowLocalHttp;
    });
  }

  Future<void> pair() async {
    HapticFeedback.mediumImpact();
    final saved = await widget.controller.saveConnection(
      url: url.text,
      allowHttp: allowHttp,
      safety: safety,
      hideProvider: hideProvider,
    );
    if (!saved) return;
    await widget.controller.pairWithCode(pairCode.text);
    if (!mounted) return;
    setState(() {
      token.clear();
      pairCode.clear();
    });
  }

  Future<void> save() async {
    HapticFeedback.mediumImpact();
    if (widget.controller.localRuntime) {
      await widget.controller.saveLocalOptions(
        safety: safety,
        hideProvider: hideProvider,
      );
      return;
    }
    final ok = await widget.controller.saveConnection(
      url: url.text,
      allowHttp: allowHttp,
      safety: safety,
      hideProvider: hideProvider,
      token: token.text,
    );
    if (ok) {
      token.clear();
    }
  }

  Future<void> clearToken() async {
    HapticFeedback.mediumImpact();
    await widget.controller.saveConnection(
      url: url.text,
      allowHttp: allowHttp,
      safety: safety,
      hideProvider: hideProvider,
      clearToken: true,
    );
    token.clear();
  }
}

class ImageStudioPage extends StatefulWidget {
  const ImageStudioPage({required this.controller, super.key});

  final WorkstationController controller;

  @override
  State<ImageStudioPage> createState() => _ImageStudioPageState();
}

class _ImageStudioPageState extends State<ImageStudioPage> {
  final TextEditingController source = TextEditingController();
  final TextEditingController reference = TextEditingController();
  final TextEditingController prompt =
      TextEditingController(text: '增强质感，保留主体结构，输出专业级成片');
  double strength = 78;
  bool localMask = true;
  String mode = '霓虹赛博';

  @override
  void dispose() {
    source.dispose();
    reference.dispose();
    prompt.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return StudioScroll(
      title: '图像工作站',
      subtitle: '选择图片 / 局部 / 提交任务',
      children: [
        const ModeCard(
          icon: Icons.tune,
          title: '达芬奇式局部控制',
          subtitle: '限定器、窗口、边缘保护和强度分层，先轻调再输出',
          accent: AppColors.gold,
        ),
        MediaPathField(
          controller: source,
          label: '原图',
          icon: Icons.image,
          onPick: () => pick('image', source),
        ),
        MediaPathField(
          controller: reference,
          label: '参考图，可留空',
          icon: Icons.compare,
          onPick: () => pick('image', reference),
        ),
        TextField(
          controller: prompt,
          minLines: 2,
          maxLines: 4,
          decoration: const InputDecoration(
            labelText: '处理要求',
            prefixIcon: Icon(Icons.edit_note),
          ),
        ),
        SegmentedButton<String>(
          segments: const [
            ButtonSegment(value: '自然校色', label: Text('自然')),
            ButtonSegment(value: '霓虹赛博', label: Text('赛博')),
            ButtonSegment(value: '商业干净', label: Text('商业')),
          ],
          selected: {mode},
          onSelectionChanged: (value) {
            HapticFeedback.selectionClick();
            setState(() => mode = value.first);
          },
        ),
        SwitchListTile(
          value: localMask,
          onChanged: (value) {
            HapticFeedback.selectionClick();
            setState(() => localMask = value);
          },
          title: const Text('AI 局部调整'),
          subtitle: const Text('自动选择需要修改的区域，不强制整张图处理'),
        ),
        Slider(
          value: strength,
          min: 0,
          max: 100,
          divisions: 100,
          label: strength.round().toString(),
          onChanged: (value) => setState(() => strength = value),
        ),
        FilledButton.icon(
          onPressed: widget.controller.busy ? null : submit,
          icon: const Icon(Icons.send),
          label: Text(widget.controller.busy ? '提交中' : '提交图像任务'),
        ),
        MetricGrid(
          items: [
            const MetricItem('输出', '6144 请求'),
            const MetricItem('格式', 'PNG'),
            MetricItem('运行', widget.controller.localRuntime ? '手机本地' : '电脑桥接'),
            MetricItem('模型', widget.controller.activeModelName),
          ],
        ),
        HistoryPanel(
            records: widget.controller.history
                .where((item) => item.type == 'image')
                .toList()),
      ],
    );
  }

  Future<void> pick(String kind, TextEditingController target) async {
    final uri = await widget.controller.pickMedia(kind);
    if (uri != null && mounted) {
      setState(() => target.text = uri);
    }
  }

  Future<void> submit() async {
    HapticFeedback.mediumImpact();
    await widget.controller.submitImageTask(
      mode: mode,
      strength: strength,
      localMask: localMask,
      sourceUri: source.text,
      referenceUri: reference.text,
      prompt: prompt.text,
    );
  }
}

class VideoStudioPage extends StatefulWidget {
  const VideoStudioPage({required this.controller, super.key});

  final WorkstationController controller;

  @override
  State<VideoStudioPage> createState() => _VideoStudioPageState();
}

class _VideoStudioPageState extends State<VideoStudioPage> {
  final TextEditingController source = TextEditingController();
  final TextEditingController prompt =
      TextEditingController(text: '移动端清晰化，稳定画面，保留自然细节');
  String mode = '移动端清晰';
  bool interpolation = false;

  @override
  void dispose() {
    source.dispose();
    prompt.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return StudioScroll(
      title: '视频工作站',
      subtitle: '选视频 / 2K / 120FPS / 提交任务',
      children: [
        const ModeCard(
          icon: Icons.movie_creation_outlined,
          title: '专业视频模式',
          subtitle: '清晰化、降噪、补帧、硬件编码统一排队',
          accent: AppColors.coral,
        ),
        MediaPathField(
          controller: source,
          label: '原视频',
          icon: Icons.video_file,
          onPick: () => pick('video', source),
        ),
        TextField(
          controller: prompt,
          minLines: 2,
          maxLines: 4,
          decoration: const InputDecoration(
            labelText: '处理要求',
            prefixIcon: Icon(Icons.edit_note),
          ),
        ),
        SegmentedButton<String>(
          segments: const [
            ButtonSegment(value: '移动端清晰', label: Text('移动')),
            ButtonSegment(value: '高清输出', label: Text('高清')),
            ButtonSegment(value: '120帧补帧', label: Text('120帧')),
          ],
          selected: {mode},
          onSelectionChanged: (value) {
            HapticFeedback.selectionClick();
            setState(() => mode = value.first);
          },
        ),
        ModeCard(
          icon: Icons.memory,
          title: widget.controller.localRuntime ? '手机本地视频队列' : '自动硬件策略',
          subtitle: widget.controller.localRuntime
              ? '使用当前本地模型，必要时可切换到电脑桥接'
              : '手机提交任务，电脑端自动用中等占用执行 CPU/GPU',
          accent: AppColors.gold,
        ),
        SwitchListTile(
          value: interpolation,
          onChanged: (value) {
            HapticFeedback.selectionClick();
            setState(() => interpolation = value);
          },
          title: const Text('AI 补帧'),
          subtitle: const Text('开启后目标 120FPS，适合短片段'),
        ),
        FilledButton.icon(
          onPressed: widget.controller.busy ? null : submit,
          icon: const Icon(Icons.send),
          label: Text(widget.controller.busy ? '提交中' : '提交视频任务'),
        ),
        MetricGrid(
          items: [
            const MetricItem('默认', '2K'),
            const MetricItem('帧率', '60/120'),
            MetricItem('运行', widget.controller.localRuntime ? '手机本地' : '电脑桥接'),
            MetricItem('模型', widget.controller.activeModelName),
          ],
        ),
        HistoryPanel(
            records: widget.controller.history
                .where((item) => item.type == 'video')
                .toList()),
      ],
    );
  }

  Future<void> pick(String kind, TextEditingController target) async {
    final uri = await widget.controller.pickMedia(kind);
    if (uri != null && mounted) {
      setState(() => target.text = uri);
    }
  }

  Future<void> submit() async {
    HapticFeedback.mediumImpact();
    await widget.controller.submitVideoTask(
      mode: mode,
      interpolation: interpolation,
      sourceUri: source.text,
      prompt: prompt.text,
    );
  }
}

class ModelHubPage extends StatelessWidget {
  const ModelHubPage({required this.controller, super.key});

  final WorkstationController controller;

  @override
  Widget build(BuildContext context) {
    return StudioScroll(
      title: '模型库',
      subtitle: '手机下载 / 启用 / 切换本地 AI 模型',
      trailing: FilledButton.icon(
        onPressed: () => showAddModelSheet(context),
        icon: const Icon(Icons.add),
        label: const Text('添加'),
      ),
      children: [
        MetricGrid(
          items: [
            MetricItem('运行', controller.localRuntime ? '手机本地' : '电脑桥接'),
            MetricItem('已安装', '${controller.installedModelCount} 个'),
            MetricItem('当前', controller.activeModelName),
            MetricItem('状态', controller.activeModelReady ? '可用' : '待下载'),
          ],
        ),
        for (final model in controller.models)
          ModelTile(
            model: model,
            hideSource: controller.hideProviderNames,
            selected: controller.activeModelId == model.id,
            progress: controller.modelDownloadProgress[model.id] ?? 0,
            onDeploy:
                controller.busy ? null : () => controller.deployModel(model),
          ),
        HistoryPanel(
            records: controller.history
                .where((item) => item.type == 'model')
                .toList()),
      ],
    );
  }

  void showAddModelSheet(BuildContext context) {
    final name = TextEditingController();
    final source = TextEditingController();
    final downloadUrl = TextEditingController();
    final sizeLabel = TextEditingController(text: '按模型包');
    final requirement = TextEditingController(text: '用户添加');
    String kind = '图像生成';
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setSheetState) {
            return Padding(
              padding: EdgeInsets.only(
                left: 18,
                right: 18,
                bottom: MediaQuery.of(context).viewInsets.bottom + 18,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                      controller: name,
                      decoration: const InputDecoration(labelText: '模型名称')),
                  const SizedBox(height: 10),
                  DropdownButtonFormField<String>(
                    initialValue: kind,
                    items: const ['图像生成', '视频生成', '语言模型', '音频识别', 'API服务']
                        .map((value) =>
                            DropdownMenuItem(value: value, child: Text(value)))
                        .toList(),
                    onChanged: (value) =>
                        setSheetState(() => kind = value ?? kind),
                    decoration: const InputDecoration(labelText: '模型类型'),
                  ),
                  const SizedBox(height: 10),
                  TextField(
                      controller: source,
                      decoration:
                          const InputDecoration(labelText: '来源说明 / 工作流')),
                  const SizedBox(height: 10),
                  TextField(
                      controller: downloadUrl,
                      keyboardType: TextInputType.url,
                      decoration:
                          const InputDecoration(labelText: 'HTTPS 模型下载地址，可留空')),
                  const SizedBox(height: 10),
                  TextField(
                      controller: sizeLabel,
                      decoration:
                          const InputDecoration(labelText: '模型大小 / 版本')),
                  const SizedBox(height: 10),
                  TextField(
                      controller: requirement,
                      decoration:
                          const InputDecoration(labelText: '硬件要求 / 备注')),
                  const SizedBox(height: 18),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton(
                      onPressed: () {
                        if (name.text.trim().isEmpty) return;
                        HapticFeedback.mediumImpact();
                        unawaited(controller.addModel(AiModel(name.text.trim(),
                            kind, source.text.trim(), requirement.text.trim(),
                            sizeLabel: sizeLabel.text.trim().isEmpty
                                ? '按模型包'
                                : sizeLabel.text.trim(),
                            downloadUrl: downloadUrl.text.trim())));
                        Navigator.pop(context);
                      },
                      child: const Text('保存模型'),
                    ),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }
}

class MediaPathField extends StatelessWidget {
  const MediaPathField({
    required this.controller,
    required this.label,
    required this.icon,
    required this.onPick,
    super.key,
  });

  final TextEditingController controller;
  final String label;
  final IconData icon;
  final VoidCallback onPick;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: TextField(
            controller: controller,
            decoration: InputDecoration(
              labelText: label,
              prefixIcon: Icon(icon),
              hintText: '选择文件或粘贴 content:// / 路径',
            ),
          ),
        ),
        const SizedBox(width: 10),
        IconButton.filledTonal(
          onPressed: onPick,
          icon: const Icon(Icons.folder_open),
          tooltip: '选择文件',
        ),
      ],
    );
  }
}

class ActionPanel extends StatelessWidget {
  const ActionPanel({
    required this.controller,
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.actionLabel,
    required this.onPressed,
    super.key,
  });

  final WorkstationController controller;
  final String title;
  final String subtitle;
  final IconData icon;
  final String actionLabel;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: panelDecoration(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: AppColors.primary),
              const SizedBox(width: 10),
              Expanded(
                  child: Text(title,
                      style: const TextStyle(
                          fontWeight: FontWeight.w900, fontSize: 16))),
              FilledButton(onPressed: onPressed, child: Text(actionLabel)),
            ],
          ),
          const SizedBox(height: 8),
          Text(subtitle, style: const TextStyle(color: AppColors.muted)),
        ],
      ),
    );
  }
}

class SecurityPanel extends StatelessWidget {
  const SecurityPanel({required this.controller, super.key});

  final WorkstationController controller;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SectionLabel('安全状态'),
        MetricGrid(
          items: [
            MetricItem(
                '传输',
                controller.localRuntime
                    ? '本地'
                    : controller.serverUrl.startsWith('https://')
                        ? 'HTTPS'
                        : 'HTTP调试'),
            MetricItem('密钥', controller.tokenStatus),
            MetricItem('内容', controller.safetyGuard ? '已拦截' : '关闭'),
            MetricItem('显示', controller.hideProviderNames ? '隐藏供应商' : '显示详情'),
          ],
        ),
        const ModeCard(
          icon: Icons.lock,
          title: '本地优先',
          subtitle: '手机本地模式不需要电脑配对码；电脑桥接令牌仍通过 Android Keystore 加密保存',
          accent: AppColors.primary,
        ),
        const ModeCard(
          icon: Icons.policy,
          title: '安全默认值',
          subtitle: '默认阻止公网 HTTP，证书校验失败不会自动绕过',
          accent: AppColors.gold,
        ),
      ],
    );
  }
}

class ModelTile extends StatelessWidget {
  const ModelTile({
    required this.model,
    required this.hideSource,
    required this.selected,
    required this.progress,
    required this.onDeploy,
    super.key,
  });

  final AiModel model;
  final bool hideSource;
  final bool selected;
  final double progress;
  final VoidCallback? onDeploy;

  @override
  Widget build(BuildContext context) {
    final statusText =
        '${model.installed ? '已安装' : model.canDownload ? '可下载' : '可导入'} · ${model.sizeLabel}';
    final actionIcon = model.installed
        ? Icons.play_arrow
        : model.canDownload
            ? Icons.download
            : Icons.file_open;
    final actionTip = model.installed
        ? '启用模型'
        : model.canDownload
            ? '下载模型'
            : '导入本地模型包';
    return AnimatedContainer(
      duration: const Duration(milliseconds: 260),
      curve: Curves.easeOutCubic,
      padding: const EdgeInsets.all(14),
      decoration: panelDecoration(
        color: selected ? const Color(0xFF132420) : null,
      ),
      child: Row(
        children: [
          AnimatedSwitcher(
            duration: const Duration(milliseconds: 260),
            switchInCurve: Curves.easeOutBack,
            switchOutCurve: Curves.easeInCubic,
            transitionBuilder: (child, animation) {
              return ScaleTransition(
                scale: Tween<double>(begin: 0.82, end: 1).animate(animation),
                child: FadeTransition(opacity: animation, child: child),
              );
            },
            child: Icon(
              selected
                  ? Icons.check_circle
                  : model.installed
                      ? Icons.offline_pin
                      : model.canDownload
                          ? Icons.cloud_download_outlined
                          : Icons.folder_open,
              key: ValueKey<String>(
                  '${model.id}-$selected-${model.installed}-${model.canDownload}'),
              color: selected ? AppColors.primary : AppColors.gold,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(model.name,
                    style: const TextStyle(
                        fontWeight: FontWeight.w900, fontSize: 16)),
                const SizedBox(height: 4),
                Text('${model.kind} · ${model.requirement}',
                    style: const TextStyle(color: AppColors.muted)),
                AnimatedSwitcher(
                  duration: const Duration(milliseconds: 220),
                  switchInCurve: Curves.easeOutCubic,
                  switchOutCurve: Curves.easeInCubic,
                  child: Text(statusText,
                      key: ValueKey(statusText),
                      style: const TextStyle(color: Color(0xFF8EA0B6))),
                ),
                if (!hideSource && model.source.isNotEmpty)
                  Text(model.source,
                      style: const TextStyle(color: Color(0xFF75869A))),
                if (progress > 0 && progress < 1) ...[
                  const SizedBox(height: 8),
                  LinearProgressIndicator(value: progress, minHeight: 3),
                ],
              ],
            ),
          ),
          IconButton.filledTonal(
            onPressed: onDeploy,
            icon: AnimatedSwitcher(
              duration: const Duration(milliseconds: 220),
              child: Icon(actionIcon, key: ValueKey(actionIcon)),
            ),
            tooltip: actionTip,
          ),
        ],
      ),
    );
  }
}

class HistoryPanel extends StatelessWidget {
  const HistoryPanel({required this.records, super.key});

  final List<JobRecord> records;

  @override
  Widget build(BuildContext context) {
    if (records.isEmpty) {
      return const SizedBox.shrink();
    }
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: panelDecoration(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('最近任务',
              style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
          const SizedBox(height: 10),
          for (final record in records.take(5))
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(_statusIcon(record.status),
                      color: _statusColor(record.status), size: 20),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(record.title,
                            style:
                                const TextStyle(fontWeight: FontWeight.w800)),
                        const SizedBox(height: 2),
                        Text(record.detail,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(color: AppColors.muted)),
                      ],
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  IconData _statusIcon(JobStatus status) {
    return switch (status) {
      JobStatus.success => Icons.check_circle,
      JobStatus.failed => Icons.error,
      JobStatus.blocked => Icons.shield,
    };
  }

  Color _statusColor(JobStatus status) {
    return switch (status) {
      JobStatus.success => AppColors.primary,
      JobStatus.failed => AppColors.coral,
      JobStatus.blocked => AppColors.gold,
    };
  }
}

class StudioScroll extends StatelessWidget {
  const StudioScroll({
    required this.title,
    required this.subtitle,
    required this.children,
    this.trailing,
    super.key,
  });

  final String title;
  final String subtitle;
  final List<Widget> children;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.sizeOf(context);
    final horizontalPadding = size.width <= 360 ? 12.0 : 16.0;
    return ListView(
      key: PageStorageKey<String>(title),
      scrollCacheExtent: const ScrollCacheExtent.pixels(720),
      keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
      padding:
          EdgeInsets.fromLTRB(horizontalPadding, 18, horizontalPadding, 24),
      children: [
        StaggeredReveal(
          index: 0,
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(subtitle,
                        style: const TextStyle(
                            color: AppColors.primary,
                            fontWeight: FontWeight.w900)),
                    const SizedBox(height: 4),
                    Text(
                      title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                          fontSize: 28, fontWeight: FontWeight.w900),
                    ),
                  ],
                ),
              ),
              if (trailing != null) trailing!,
            ],
          ),
        ),
        const SizedBox(height: 18),
        ...children.asMap().entries.expand((entry) => [
              StaggeredReveal(index: entry.key + 1, child: entry.value),
              const SizedBox(height: 12),
            ]),
      ],
    );
  }
}

class StaggeredReveal extends StatefulWidget {
  const StaggeredReveal({
    required this.index,
    required this.child,
    super.key,
  });

  final int index;
  final Widget child;

  @override
  State<StaggeredReveal> createState() => _StaggeredRevealState();
}

class _StaggeredRevealState extends State<StaggeredReveal> {
  bool visible = false;
  Timer? timer;

  @override
  void initState() {
    super.initState();
    timer = Timer(Duration(milliseconds: 24 + widget.index * 34), () {
      if (mounted) setState(() => visible = true);
    });
  }

  @override
  void dispose() {
    timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedSlide(
      duration: const Duration(milliseconds: 420),
      curve: Curves.easeOutCubic,
      offset: visible ? Offset.zero : const Offset(0, 0.035),
      child: AnimatedOpacity(
        duration: const Duration(milliseconds: 360),
        curve: Curves.easeOutCubic,
        opacity: visible ? 1 : 0,
        child: RepaintBoundary(child: widget.child),
      ),
    );
  }
}

class SectionLabel extends StatelessWidget {
  const SectionLabel(this.text, {super.key});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(text,
        style: const TextStyle(
            color: AppColors.muted, fontWeight: FontWeight.w800));
  }
}

class ModeCard extends StatelessWidget {
  const ModeCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.accent,
    super.key,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: panelDecoration(),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
                color: accent.withValues(alpha: 0.16),
                borderRadius: BorderRadius.circular(12)),
            child: Icon(icon, color: accent),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title,
                    style: const TextStyle(
                        fontWeight: FontWeight.w900, fontSize: 16)),
                const SizedBox(height: 5),
                Text(subtitle, style: const TextStyle(color: AppColors.muted)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class MetricGrid extends StatelessWidget {
  const MetricGrid({required this.items, super.key});

  final List<MetricItem> items;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final columns = constraints.maxWidth > 520 ? 4 : 2;
        return GridView.count(
          crossAxisCount: columns,
          mainAxisSpacing: 10,
          crossAxisSpacing: 10,
          childAspectRatio: columns == 4 ? 1.7 : 1.45,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          children: [
            for (final item in items)
              Container(
                padding: const EdgeInsets.all(12),
                decoration: panelDecoration(),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      item.label,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                          color: Color(0xFF8EA2B6),
                          fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 5),
                    FittedBox(
                      fit: BoxFit.scaleDown,
                      alignment: Alignment.centerLeft,
                      child: Text(item.value,
                          style: const TextStyle(
                              fontSize: 18, fontWeight: FontWeight.w900)),
                    ),
                  ],
                ),
              ),
          ],
        );
      },
    );
  }
}

class MetricItem {
  const MetricItem(this.label, this.value);

  final String label;
  final String value;
}

BoxDecoration panelDecoration({Gradient? gradient, Color? color}) {
  return BoxDecoration(
    color: gradient == null ? (color ?? AppColors.panel) : null,
    gradient: gradient,
    borderRadius: BorderRadius.circular(14),
    border: Border.all(color: AppColors.panelBorder),
  );
}
