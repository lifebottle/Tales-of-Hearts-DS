call "..\venv\Scripts\activate.bat"
pushd "../../TOHPython"
python Tales_Exe.py -p "../Tales-of-Hearts-DS/project.json" -g TOH extract -ft Menu
popd
pause