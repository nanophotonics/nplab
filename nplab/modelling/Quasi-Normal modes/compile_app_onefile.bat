call cd %~dp0
call env/Scripts/activate.bat
call pyinstaller --noconfirm --add-data "geometries";"geometries" --onefile --add-data "mim/binaries";"mim/binaries" --log-level=DEBUG QNM_viewer.py
