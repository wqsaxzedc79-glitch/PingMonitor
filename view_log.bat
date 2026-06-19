@echo off
chcp 65001 > nul
title PingMonitor - Log Viewer
python "%~dp0view_log.py"
