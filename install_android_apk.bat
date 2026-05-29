@echo off
setlocal

set "ROOT=%~dp0"
set "APK=%ROOT%release\YingXiaoAIWorkstation-mobile-0.1.4-android11-release.apk"
if not exist "%APK%" set "APK=%ROOT%YingXiaoAIWorkstation-mobile-0.1.4-android11-release.apk"

set "ADB="
if defined ANDROID_HOME if exist "%ANDROID_HOME%\platform-tools\adb.exe" set "ADB=%ANDROID_HOME%\platform-tools\adb.exe"
if not defined ADB if defined ANDROID_SDK_ROOT if exist "%ANDROID_SDK_ROOT%\platform-tools\adb.exe" set "ADB=%ANDROID_SDK_ROOT%\platform-tools\adb.exe"
if not defined ADB if exist "E:\1\Documents\AndroidSDK\platform-tools\adb.exe" set "ADB=E:\1\Documents\AndroidSDK\platform-tools\adb.exe"

if not exist "%APK%" (
  echo APK not found:
  echo %APK%
  pause
  exit /b 1
)

if not defined ADB (
  echo adb.exe not found. Please install Android SDK or set ANDROID_HOME.
  pause
  exit /b 1
)

echo Using APK:
echo %APK%
echo.
echo Connected Android devices:
"%ADB%" devices
echo.
echo Installing...
"%ADB%" install -r "%APK%"
echo.
pause
