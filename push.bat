@echo off
REM ============================================================
REM  一键推送脚本（实时同步 GitHub）
REM  用法：
REM    push.bat                -> 自动 add + commit(默认消息) + push
REM    push.bat "修复登录bug"  -> 指定提交说明
REM  说明：国内网络默认走本地代理 127.0.0.1:7897（Clash 混合端口），
REM       如无代理可删除下面两行或改成直连。
REM ============================================================
setlocal
set HTTPS_PROXY=http://127.0.0.1:7897
set HTTP_PROXY=http://127.0.0.1:7897
cd /d "%~dp0"

if "%~1"=="" (
  set MSG=update: auto push %date% %time%
) else (
  set MSG=%~1
)

git add -A
git commit -m "%MSG%"
if errorlevel 1 (
  echo [提示] 没有需要提交的更改。
) else (
  echo [提交] %MSG%
)
git push origin main
echo.
echo ===== 推送完成 =====
endlocal
