@echo off
echo Starting Pragya - Company Law CompanyGPT
echo =====================================
echo.

echo Starting Flask Backend Server...
echo.
start "Flask Backend" cmd /k "cd ..\companies_act_2013 && python app.py"

timeout /t 3 /nobreak > nul

echo Starting Next.js Frontend...
echo.
start "Next.js Frontend" cmd /k "npm run dev"

echo.
echo =====================================
echo Both servers are starting...
echo Flask Backend: http://localhost:5000
echo Next.js Frontend: http://localhost:3000
echo =====================================
echo.
echo Press any key to close this window (servers will keep running in separate windows)
pause > nul
