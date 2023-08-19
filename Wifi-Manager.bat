@echo off
git pull
cd /d %~dp0
call myenv\Scripts\activate
python app.py
pause
