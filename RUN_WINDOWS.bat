@echo off
setlocal
cd /d "%~dp0"
echo === Setting up EP LiDAR Data Engineering Project ===
python -m venv .venv
if errorlevel 1 goto error
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto error
.venv\Scripts\python.exe src\generate_sample.py
if errorlevel 1 goto error
.venv\Scripts\python.exe src\pipeline.py
if errorlevel 1 goto error
.venv\Scripts\python.exe src\visualize.py
if errorlevel 1 goto error
.venv\Scripts\python.exe -m unittest discover -s tests -v
if errorlevel 1 goto error
echo.
echo SUCCESS! Open data\processed\point_cloud_preview.png and quality_report.json
pause
exit /b 0
:error
echo.
echo ERROR! Please copy the error text and share it for troubleshooting.
pause
exit /b 1
