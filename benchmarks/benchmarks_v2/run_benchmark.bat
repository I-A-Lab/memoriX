@echo off
echo ============================================
echo   memoriX Full Benchmark
echo ============================================
echo.

REM Default parameters (edit as needed)
set MODEL=qwen2.5:3b
set SEEDS=42 101
set OUTPUT=%TEMP%\memoriX-benchmarks

REM Parse arguments
if "%~1"=="--report-only" (
    py -3.13 "%~dp0run_full_benchmark.py" --report-only
    goto :end
)

if not "%~1"=="" set MODEL=%~1
if not "%~2"=="" set SEEDS=%~2

echo Model:  %MODEL%
echo Seeds:  %SEEDS%
echo Output: %OUTPUT%
echo.

py -3.13 "%~dp0run_full_benchmark.py" --model %MODEL% --seeds %SEEDS% --output "%OUTPUT%"

:end
echo.
pause
