@echo off
rem hotfix119 - put the dashboard menu files (ROOM SIZE / books) into the dashboard folder.
rem Finds the dashboard folder (the one with dashboard.html): dragged folder, this folder, or the parent folder.
setlocal
set "HERE=%~dp0"
set "DASH=%~1"
if "%DASH%"=="" if exist "%HERE%dashboard.html" set "DASH=%HERE%."
if "%DASH%"=="" if exist "%HERE%..\dashboard.html" set "DASH=%HERE%.."
if "%DASH%"=="" goto ask
goto check
:ask
echo Dashboard folder not found next to this file.
echo Drag the dashboard folder (the folder with dashboard.html) onto this file,
echo or type the folder path below (no quotes), e.g. C:\Claude\Dashboard
set /p "DASH=Dashboard folder: "
:check
for %%I in ("%DASH%") do set "DASH=%%~fI"
if not exist "%DASH%\dashboard.html" goto nodash
call :put space || goto failed
call :put books || goto failed
echo.
echo Done. Dashboard folder: %DASH%
echo In the dashboard press Ctrl+F5, then open the ROOM SIZE menu.
echo The ROOM SIZE screen should now show the 3D buttons.
pause
exit /b 0
:put
if /i "%HERE%apps\%1\index.html"=="%DASH%\apps\%1\index.html" (
  echo OK  apps\%1\index.html is already in place
  exit /b 0
)
if not exist "%DASH%\apps\%1" mkdir "%DASH%\apps\%1"
if exist "%DASH%\apps\%1\index.html" copy /y "%DASH%\apps\%1\index.html" "%DASH%\apps\%1\index.html.before_hotfix119" >nul
copy /y "%HERE%apps\%1\index.html" "%DASH%\apps\%1\index.html" >nul
if errorlevel 1 exit /b 2
echo OK  %DASH%\apps\%1\index.html
exit /b 0
:nodash
echo [STOP] dashboard.html not found in: %DASH%
pause
exit /b 1
:failed
echo [STOP] copy failed - is the file open or read-only?
pause
exit /b 2
