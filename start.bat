@echo off
chcp 65001 >nul
REM ============================================================
REM  一键启动脚本（自动用当前局域网地址打开浏览器）
REM  用法：
REM    双击 start.bat  或在终端执行  start.bat
REM  说明：
REM    - 服务绑定所有网卡，localhost / 局域网 IP / 手机等设备都能访问
REM    - 局域网 IP 由路由器 DHCP 自动分配、可能变化（例如
REM      192.168.2.103 -> 192.168.2.102），因此脚本每次启动时
REM      自动探测当前 IP 并用它打开浏览器，不写死地址
REM    - 若服务已在运行，则直接打开浏览器，不重复启动
REM ============================================================
setlocal
cd /d "%~dp0"

REM ---- 探测当前局域网 IPv4（优先 192.168.*，排除回环/链路本地/虚拟网卡）----
for /f "delims=" %%i in ('powershell -NoProfile -Command "$ips = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.PrefixOrigin -ne 'WellKnown' -and $_.IPAddress -ne '127.0.0.1' -and -not $_.IPAddress.StartsWith('169.254.') }; $ip = ($ips | Where-Object { $_.IPAddress -like '192.168.*' } | Select-Object -First 1).IPAddress; if (-not $ip) { $ip = ($ips | Select-Object -First 1).IPAddress }; Write-Output $ip"') do set "LAN_IP=%%i"

if "%LAN_IP%"=="" (
  echo [警告] 未探测到局域网 IP，将使用 localhost 打开。
  set "LAN_IP=localhost"
)
echo [信息] 当前局域网 IP: %LAN_IP%

REM ---- 若服务已在运行，直接打开浏览器 ----
curl.exe --noproxy "*" -s -o nul --max-time 2 http://127.0.0.1:8501/_stcore/health
if not errorlevel 1 (
  echo [信息] 服务已在运行，直接打开浏览器...
  start "" http://%LAN_IP%:8501
  goto :eof
)

REM ---- 新窗口启动服务（关闭该窗口或 Ctrl+C 即停止服务）----
echo [启动] 正在启动 Streamlit...
start "employment-planning-streamlit" python -m streamlit run frontend_streamlit/app.py --server.headless true --server.port 8501

REM ---- 等待服务就绪（最多 30 秒）----
set /a tries=0
:wait_ready
curl.exe --noproxy "*" -s -o nul --max-time 2 http://127.0.0.1:8501/_stcore/health
if not errorlevel 1 goto ready
set /a tries+=1
if %tries% geq 30 (
  echo [警告] 服务 30 秒内未就绪，仍尝试打开浏览器...
  goto open
)
timeout /t 1 /nobreak >nul
goto wait_ready

:ready
echo [就绪] 服务已启动。

:open
start "" http://%LAN_IP%:8501
echo [完成] 浏览器已打开 http://%LAN_IP%:8501
echo [提示] 停止服务：关闭标题为 employment-planning-streamlit 的窗口。
endlocal
