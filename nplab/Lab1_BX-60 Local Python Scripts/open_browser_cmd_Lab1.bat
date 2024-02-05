REM run python file 'open_browser_cmd' from within nplab and pass the file location
call conda.bat activate base
cd C:\Users\Hera\Documents\GitHub\nplab
python -m nplab.ui.open_browser_cmd %1

cmd /k 