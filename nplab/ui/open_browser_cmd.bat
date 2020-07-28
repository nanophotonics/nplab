REM run python file 'open_browser_cmd' from within nplab and pass the file location
call conda.bat activate base
python -m nplab.ui.open_browser_cmd %1

cmd /k 