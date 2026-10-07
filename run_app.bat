@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 (
        echo Hãy cài Python 3.11 trở lên từ python.org rồi chạy lại.
        pause
        exit /b 1
    )
)
".venv\Scripts\python.exe" -c "import streamlit, ortools, openpyxl, pandas" >nul 2>&1
if errorlevel 1 (
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Không cài được thư viện. Kiểm tra kết nối mạng.
        pause
        exit /b 1
    )
)
".venv\Scripts\python.exe" -m streamlit run app.py --server.address 127.0.0.1
pause
