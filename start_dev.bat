@echo off
rem ----------------------------------------------------------------------
rem  ASCII bootstrap.  cmd.exe reads a .bat file chunk by chunk using the
rem  active code page; if the code page changes in the middle of the file,
rem  the read offset drifts and later lines get mis-parsed (Chinese text in
rem  a UTF-8 file starts being executed as commands).  So: keep everything
rem  up to here pure ASCII, switch the console to UTF-8, then re-exec this
rem  file with the _u8 flag -- the rest of the file is read as UTF-8 from
rem  the very first byte and stays intact.
rem ----------------------------------------------------------------------
setlocal enabledelayedexpansion
if not "%~1"=="_u8" (
  for /f "tokens=2 delims=:" %%A in ('chcp') do set "CP0=%%A"
  echo %cmdcmdline% | findstr /i /c:"%~nx0" >nul && set "ZDBLOG_DD=1"
  chcp 65001 >nul
  cmd /c ""%~f0" _u8 !CP0! %*"
  exit /b !errorlevel!
)
rem ---- below runs in the UTF-8 child process ----
set "OLD_CP=%~2"
shift
shift

rem ============================================================
rem  zdblog 开发环境一键启动（Windows）
rem
rem   双击本文件              启动 后端 + C端 + S端，每个服务一个窗口
rem   start_dev.bat stop      停止全部服务（释放 8000 / 5173 / 5174）
rem   start_dev.bat -b        只启动后端
rem   start_dev.bat -f        只启动前端（C端 + S端）
rem   start_dev.bat --help    显示本帮助
rem
rem   可选环境变量：
rem     BACKEND_PORT / CLIENT_PORT / ADMIN_PORT   覆盖默认端口
rem     ZDBLOG_PYTHON                            指定 python.exe 的完整路径
rem
rem   日志：每个服务窗口本身就是实时日志（窗口标题 zdblog-backend 等）；
rem         启动器脚本与解释器缓存放在 logs\ 下
rem ============================================================

cd /d "%~dp0"

set "ROOT=%~dp0"
set "BACKEND_DIR=%ROOT%zdblog-master"
set "CLIENT_DIR=%ROOT%zdblog-vue-c"
set "ADMIN_DIR=%ROOT%zdblog-vue-s"
set "LOG_DIR=%ROOT%logs"
set "PY_CACHE=%LOG_DIR%\.python"
set "ENV_LIST=%LOG_DIR%\.conda-envs"

if not defined BACKEND_PORT set "BACKEND_PORT=8000"
if not defined CLIENT_PORT  set "CLIENT_PORT=5173"
if not defined ADMIN_PORT   set "ADMIN_PORT=5174"

set "START_BACKEND=1"
set "START_FRONTEND=1"
set "ACTION=start"
set "EXIT_CODE=0"

rem ---- 双击运行时结束前要 pause，否则窗口一闪而过（由引导段传入）----
set "DOUBLECLICK="
if defined ZDBLOG_DD set "DOUBLECLICK=1"
if defined DOUBLECLICK title zdblog 开发环境

rem ---------------- 解析参数 ----------------
:parse_args
if "%~1"=="" goto args_done
set "ARG=%~1"
set "MATCHED=0"
if /i "!ARG!"=="stop"   (set "ACTION=stop"      & set "MATCHED=1")
if /i "!ARG!"=="-b"     (set "START_FRONTEND=0" & set "MATCHED=1")
if /i "!ARG!"=="-f"     (set "START_BACKEND=0"  & set "MATCHED=1")
if /i "!ARG!"=="--help" goto usage
if /i "!ARG!"=="-h"     goto usage
if /i "!ARG!"=="-?"     goto usage
if "!MATCHED!"=="0" goto bad_arg
shift
goto parse_args
:args_done

if /i "%ACTION%"=="stop" goto stop_all

rem ---------------- 基本检查 ----------------
if not exist "%BACKEND_DIR%\manage.py" (set "MSG=找不到后端项目：%BACKEND_DIR%" & goto die)
if "%START_FRONTEND%"=="1" (
  if not exist "%CLIENT_DIR%\package.json" (set "MSG=找不到 C 端项目：%CLIENT_DIR%" & goto die)
  if not exist "%ADMIN_DIR%\package.json"  (set "MSG=找不到 S 端项目：%ADMIN_DIR%" & goto die)
)

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1

echo.
echo ============================================
echo   zdblog 开发环境一键启动
echo ============================================
if "%START_BACKEND%"=="1"  echo   后端    http://localhost:%BACKEND_PORT%/
if "%START_FRONTEND%"=="1" echo   C 端    http://localhost:%CLIENT_PORT%/
if "%START_FRONTEND%"=="1" echo   S 端    http://localhost:%ADMIN_PORT%/admin/
echo ============================================
echo.

rem ---------------- 后端解释器 ----------------
if "%START_BACKEND%"=="1" (
  call :detect_python
  if not defined PY (
    echo.
    echo [错误] 没找到可用的 Python 解释器
    echo     要求：能 import django, rest_framework, corsheaders, psycopg
    echo     已尝试：ZDBLOG_PYTHON，再 PATH 里的 python，再 conda 里的 zblog-master / zblog
    echo     可手动指定后重试，例如：
    echo         set ZDBLOG_PYTHON=D:\CondaEnvs\zblog\python.exe
    echo         start_dev.bat
    set "MSG=后端无法启动"
    goto die
  )
)

rem ---------------- 前端依赖 ----------------
if "%START_FRONTEND%"=="1" (
  where npm >nul 2>&1
  if errorlevel 1 (set "MSG=没找到 npm，请先安装 Node.js" & goto die)
  for %%D in ("%CLIENT_DIR%" "%ADMIN_DIR%") do (
    if not exist "%%~D\node_modules" (
      echo [提示] %%~nxD 缺少依赖，正在 npm install ...
      pushd "%%~D"
      call npm install
      popd
      if not exist "%%~D\node_modules" echo [警告] %%~nxD 依赖安装似乎失败，请在该目录手动执行 npm install
    )
  )
)

rem ---------------- 端口占用提示 ----------------
if "%START_BACKEND%"=="1"  call :warn_busy %BACKEND_PORT% 后端
if "%START_FRONTEND%"=="1" call :warn_busy %CLIENT_PORT% "C 端"
if "%START_FRONTEND%"=="1" call :warn_busy %ADMIN_PORT% "S 端"

rem ---------------- 启动服务 ----------------
echo [1/2] 启动服务 ...
if "%START_BACKEND%"=="1" (
  set "SVC_NAME=backend"
  set "SVC_DIR=%BACKEND_DIR%"
  set SVC_CMD="%PY%" manage.py ensure_database ^&^& "%PY%" manage.py migrate --noinput ^&^& "%PY%" manage.py runserver %BACKEND_PORT%
  call :gen_run
  start "zdblog-backend" "%LOG_DIR%\run-backend.bat"
)
if "%START_FRONTEND%"=="1" (
  set "SVC_NAME=vue-c"
  set "SVC_DIR=%CLIENT_DIR%"
  rem npm 是 npm.cmd：不加 call，窗口在 vite 退出时会直接关掉，看不到报错
  rem --port 让 CLIENT_PORT 真正生效（默认值与 vite.config.js 一致）
  set "SVC_CMD=call npm run dev -- --port %CLIENT_PORT%"
  call :gen_run
  start "zdblog-vue-c" "%LOG_DIR%\run-vue-c.bat"

  set "SVC_NAME=vue-s"
  set "SVC_DIR=%ADMIN_DIR%"
  set "SVC_CMD=call npm run dev -- --port %ADMIN_PORT%"
  call :gen_run
  start "zdblog-vue-s" "%LOG_DIR%\run-vue-s.bat"
)

rem ---------------- 等待端口就绪 ----------------
echo [2/2] 等待服务监听端口，最长 30 秒 ...
set "RD_B=0"
set "RD_C=0"
set "RD_S=0"
set /a TRIES=0
:wait_loop
set "PENDING="
if "%START_BACKEND%"=="1"  if "%RD_B%"=="0" set "PENDING=1"
if "%START_FRONTEND%"=="1" if "%RD_C%"=="0" set "PENDING=1"
if "%START_FRONTEND%"=="1" if "%RD_S%"=="0" set "PENDING=1"
if not defined PENDING goto summary
set /a TRIES+=1
if !TRIES! gtr 30 goto summary
ping -n 2 127.0.0.1 >nul
if "%START_BACKEND%"=="1"  call :check_ready %BACKEND_PORT% RD_B
if "%START_FRONTEND%"=="1" call :check_ready %CLIENT_PORT%  RD_C
if "%START_FRONTEND%"=="1" call :check_ready %ADMIN_PORT%   RD_S
goto wait_loop

:summary
echo.
echo ================ 服务状态 ================
if "%START_BACKEND%"=="1"  call :report 后端 "http://localhost:%BACKEND_PORT%/"          "!RD_B!"
if "%START_FRONTEND%"=="1" call :report "C 端" "http://localhost:%CLIENT_PORT%/"         "!RD_C!"
if "%START_FRONTEND%"=="1" call :report "S 端" "http://localhost:%ADMIN_PORT%/admin/"    "!RD_S!"
echo =========================================
echo.
echo 提示：停止服务运行 stop_dev.bat，也可以直接关闭各服务窗口
echo       只重启某个服务：关掉它的窗口，再运行 start_dev.bat -b 或 -f
if defined DOUBLECLICK (
  echo.
  echo 按任意键关闭本窗口（各服务窗口不受影响）...
  pause >nul
)
call :restore_cp
exit /b 0

rem ============================================================
rem                        子过程
rem ============================================================

rem ---- 找 Python：环境变量 -> 缓存 -> PATH -> conda 环境 ----
:detect_python
set "PY="
if defined ZDBLOG_PYTHON call :try_python "%ZDBLOG_PYTHON%"
if not defined PY if exist "%PY_CACHE%" (
  set /p PY=<"%PY_CACHE%"
  call :verify_python
)
if not defined PY call :try_python "python"
if not defined PY call :try_python "python3"
if not defined PY call :scan_conda
if not defined PY goto :eof
echo [OK] Python: !PY!
>"%PY_CACHE%" echo !PY!
goto :eof

rem ---- %1 = 候选解释器；可用则设 PY ----
:try_python
set "CAND=%~1"
if not defined CAND goto :eof
if not exist "%CAND%" for %%P in ("%CAND%") do set "CAND=%%~$PATH:P"
if not defined CAND goto :eof
if not exist "%CAND%" goto :eof
"%CAND%" -c "import django, corsheaders, rest_framework, psycopg" >nul 2>&1
if errorlevel 1 goto :eof
set "PY=%CAND%"
goto :eof

rem ---- 校验缓存的 PY 是否还能用 ----
:verify_python
if not defined PY goto :eof
if not exist "%PY%" (
  set "PY="
  goto :eof
)
"%PY%" -c "import django, corsheaders, rest_framework, psycopg" >nul 2>&1
if errorlevel 1 set "PY="
goto :eof

rem ---- 扫描 conda 环境（先项目常用的，再任意可用的）----
:scan_conda
where conda >nul 2>&1 || goto :eof
rem conda 在 Windows 上是 conda.bat，不加 call 会顶替掉本脚本（静默退出）
call conda env list > "%ENV_LIST%" 2>nul
if not exist "%ENV_LIST%" goto :eof
for %%W in (zblog-master zblog) do (
  if not defined PY for /f "usebackq tokens=1,*" %%A in ("%ENV_LIST%") do (
    if not defined PY if /i "%%~A"=="%%~W" call :try_conda_line "%%A" "%%B"
  )
)
if not defined PY for /f "usebackq tokens=1,*" %%A in ("%ENV_LIST%") do (
  if not defined PY call :try_conda_line "%%A" "%%B"
)
goto :eof

rem ---- %1 = 环境名  %2 = 该行剩下的内容（可能带 * 标记）----
:try_conda_line
set "ENAME=%~1"
if "!ENAME:~0,1!"=="#" goto :eof
set "EPATH=%~2"
if "!EPATH:~0,1!"=="*" set "EPATH=!EPATH:~1!"
for /f "tokens=* delims= " %%X in ("!EPATH!") do set "EPATH=%%X"
if not exist "!EPATH!\python.exe" goto :eof
call :try_python "!EPATH!\python.exe"
goto :eof

rem ---- %1 = 端口  %2 = 服务名；占用则提示 ----
:warn_busy
call :port_listening %~1
if "!LISTENING!"=="1" (
  echo [警告] 端口 %~1 已被占用：%~2 可能已经在运行
  echo        要清空重来，先运行 stop_dev.bat
)
goto :eof

rem ---- %1 = 端口；结果写进 LISTENING ----
rem      不带 -p tcp：S 端的 vite 只监听 IPv6 的 [::1]:5174，
rem      限制成 -p tcp 会看不到它
:port_listening
set "LISTENING=0"
netstat -ano 2>nul | findstr /R /C:":%~1 " | findstr /C:"LISTENING" >nul 2>&1
if not errorlevel 1 set "LISTENING=1"
goto :eof

rem ---- %1 = 端口  %2 = 标志变量名 ----
:check_ready
call :port_listening %~1
if "!LISTENING!"=="1" set "%2=1"
goto :eof

rem ---- %1 = 服务名  %2 = 地址  %3 = 就绪标志 ----
:report
if "%~3"=="1" (
  echo [OK]   %~1   %~2
) else (
  echo [警告] %~1   %~2  尚未就绪，请看该服务窗口的输出
)
goto :eof

rem ---- 生成 logs\run-<名称>.bat：在独立窗口里跑服务并保留最后输出 ----
rem      这里是纯 ASCII：切换代码页时若文件里夹着中文，cmd 会按旧代码页
rem      解出来的字数为准往下读，行会被截断着执行（title/echo 全乱套）
:gen_run
(
  echo @echo off
  echo chcp 65001 ^>nul
  echo title zdblog-!SVC_NAME!
  echo cd /d "!SVC_DIR!"
  echo !SVC_CMD!
  echo echo.
  echo echo --------------------------------------------
  echo echo  [zdblog-!SVC_NAME!] exited - last output above
  echo echo  press any key to close this window
  echo echo --------------------------------------------
  echo pause ^>nul
) > "%LOG_DIR%\run-!SVC_NAME!.bat"
goto :eof

rem ---- 停止：按端口杀进程树，再关掉遗留窗口 ----
:stop_all
echo ============================================
echo   停止 zdblog 开发环境
echo ============================================
echo.
set "FOUND=0"
for %%P in (%BACKEND_PORT% %CLIENT_PORT% %ADMIN_PORT%) do call :kill_port %%P
taskkill /F /T /FI "WINDOWTITLE eq zdblog-backend" >nul 2>&1
taskkill /F /T /FI "WINDOWTITLE eq zdblog-vue-c"   >nul 2>&1
taskkill /F /T /FI "WINDOWTITLE eq zdblog-vue-s"   >nul 2>&1
echo.
if "%FOUND%"=="0" (
  echo [OK] 没有发现运行中的 zdblog 服务
) else (
  echo [OK] 已停止
)
if defined DOUBLECLICK (
  echo.
  echo 按任意键关闭本窗口...
  pause >nul
)
call :restore_cp
exit /b 0

rem ---- %1 = 端口（含 IPv6 监听）----
:kill_port
set "N=0"
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%~1 " ^| findstr /C:"LISTENING"') do (
  echo   端口 %~1  结束进程 PID %%P
  taskkill /F /T /PID %%P >nul 2>&1
  set "N=1"
  set "FOUND=1"
)
if "%N%"=="1" echo   端口 %~1 已释放
goto :eof

rem ---- 恢复控制台原来的代码页 ----
:restore_cp
if defined OLD_CP chcp !OLD_CP! >nul 2>&1
goto :eof

rem ============================================================
rem                        帮助 / 错误
rem ============================================================
:bad_arg
echo.
echo [错误] 无法识别的参数：%ARG%
echo        为避免误启动，这里不做任何事；可用参数见下
set "EXIT_CODE=1"

:usage
echo.
echo zdblog 开发环境一键启动
echo.
echo   start_dev.bat           启动 后端 + C端 + S端，每个服务一个窗口
echo   start_dev.bat stop      停止全部服务（释放 8000 / 5173 / 5174）
echo   start_dev.bat -b        只启动后端
echo   start_dev.bat -f        只启动前端（C端 + S端）
echo   start_dev.bat --help    显示本帮助
echo.
echo 可选环境变量：
echo   BACKEND_PORT / CLIENT_PORT / ADMIN_PORT   覆盖默认端口
echo   ZDBLOG_PYTHON                            指定 python.exe 的完整路径
if defined DOUBLECLICK (
  echo.
  echo 按任意键关闭本窗口...
  pause >nul
)
call :restore_cp
exit /b !EXIT_CODE!

:die
echo.
echo [错误] %MSG%
echo.
pause
call :restore_cp
exit /b 1
