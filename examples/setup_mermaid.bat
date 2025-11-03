@echo off
echo Checking Node.js installation...
"C:\Program Files\nodejs\node.exe" --version
if %errorlevel% neq 0 (
    echo Node.js is not working properly
    exit /b 1
)

echo.
echo Checking npm...
"C:\Program Files\nodejs\npm.cmd" --version
if %errorlevel% neq 0 (
    echo npm is not working properly
    exit /b 1
)

echo.
echo Installing Mermaid CLI...
"C:\Program Files\nodejs\npm.cmd" install -g @mermaid-js/mermaid-cli
if %errorlevel% neq 0 (
    echo Failed to install Mermaid CLI
    exit /b 1
)

echo.
echo Verifying Mermaid CLI installation...
"%APPDATA%\npm\mmdc.cmd" --version
if %errorlevel% neq 0 (
    echo Mermaid CLI installation verification failed
    exit /b 1
)

echo.
echo Setup completed successfully!
pause
