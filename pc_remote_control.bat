@echo off
rem Claude Code's Remote Control in the MIA folder, so Claude can work on this
rem PC from claude.ai/code or the Claude app. Starts with Windows (a shortcut in
rem the Startup folder); if it stops (no internet yet, a sign-out), it starts
rem again a minute later. Sessions start in auto mode (Claude acts without
rem asking, and a safety check still blocks risky actions). Close this window
rem to stop it.
title Claude Remote Control (MIA)
cd /d "%~dp0"
:again
claude remote-control --name "MIA PC" --permission-mode auto
echo.
echo Remote Control stopped. Starting it again in 60 seconds (close this window to stop).
timeout /t 60 /nobreak >nul
goto again
