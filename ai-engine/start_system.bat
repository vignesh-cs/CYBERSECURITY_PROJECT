@echo off
echo ========================================
echo    AI Cybersecurity Compliance System
echo ========================================
echo.

REM Create ThreatScan folder if it doesn't exist
if not exist "%USERPROFILE%\ThreatScan" (
    mkdir "%USERPROFILE%\ThreatScan"
    echo Created ThreatScan folder: %USERPROFILE%\ThreatScan
)

echo.
echo 🛡️  THREAT SCANNER ACTIVATED
echo 📁 Monitor this folder for JSON files: %USERPROFILE%\ThreatScan
echo 💡 Drop threat JSON files here for automatic analysis
echo 🌐 Web interface: http://localhost:8000
echo.

REM Create sample threat file
echo Creating sample threat file...
echo {
echo   "id": "sample-threat-001",
echo   "title": "SMB Vulnerability Alert",
echo   "description": "Critical SMBv1 remote code execution vulnerability detected",
echo   "source": "CVE-2023-1234",
echo   "timestamp": "2023-11-15T10:30:00Z"
echo } > "%USERPROFILE%\ThreatScan\sample_threat.json"

echo.
echo 📄 Sample threat file created: ThreatScan\sample_threat.json
echo.

REM Start the main system
echo Starting AI Cybersecurity System...
python app/main.py

pause