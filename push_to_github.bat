@echo off
REM ============================================================
REM  把本地知识库推送到 https://github.com/ericwuname/AIGCvideo
REM  用法：双击本文件即可
REM  前置：Windows 凭据管理器里已有 github.com 的账号凭据
REM        （首次推送若弹出登录框，填 GitHub 用户名 + Personal Access Token）
REM ============================================================
setlocal
cd /d "%~dp0"

echo.
echo [1/3] 校验本地提交...
git rev-parse --verify HEAD >nul 2>&1
if errorlevel 1 (
    echo [FAIL] 不是 git 仓库，请先在项目根目录执行 git init
    goto :end
)
git status --short
echo.

echo [2/3] 推送到 origin/main...
git push -u origin main
if errorlevel 1 (
    echo.
    echo [FAIL] 推送失败。常见原因：
    echo   1) 没登录 —— 首次推送会弹窗，要填 GitHub 用户名 + Personal Access Token
    echo      Token 在 https://github.com/settings/tokens 生成，勾选 repo 权限即可
    echo   2) 仓库是空的但远端已有 README —— 先执行下面这行再重试：
    echo      git push -u origin main --force
    echo.
    pause
    goto :end
)

echo.
echo [OK] 推送完成 -> https://github.com/ericwuname/AIGCvideo
echo.

:end
pause
