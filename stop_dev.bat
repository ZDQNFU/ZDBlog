@echo off
rem ---------------------------------------------------------------------
rem  Stop every zdblog dev service (same as: start_dev.bat stop).
rem  Kept pure ASCII on purpose: this file must never switch code pages,
rem  otherwise cmd.exe mis-reads the lines after the switch.
rem  Ports can be overridden: set BACKEND_PORT / CLIENT_PORT / ADMIN_PORT
rem ---------------------------------------------------------------------

cd /d "%~dp0"
call "%~dp0start_dev.bat" stop
echo.
echo Press any key to close this window...
pause >nul
