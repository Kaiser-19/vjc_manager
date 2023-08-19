@echo off
cd /d %~dp0
call myenv\Scripts\activate
pip install -U selenium
pause
