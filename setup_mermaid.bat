@echo off
echo Checking Node.js installation...
where node >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Node.js is not in your PATH. Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

where npm >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo npm is not in your PATH. Please ensure Node.js is properly installed.
    pause
    exit /b 1
)

echo Node.js version:
node -v
echo.
echo npm version:
npm -v
echo.

echo Installing Mermaid CLI globally...
npm install -g @mermaid-js/mermaid-cli

if %ERRORLEVEL% neq 0 (
    echo Failed to install Mermaid CLI. Please try running this script as Administrator.
    pause
    exit /b 1
)

echo.
echo Mermaid CLI installation complete!
echo Testing Mermaid CLI...
mmdc --version

echo.
echo If you see a version number above, Mermaid CLI is installed correctly.
echo You can now run the Python application to render Mermaid diagrams.

echo.
pause
