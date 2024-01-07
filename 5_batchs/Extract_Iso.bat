call "..\venv\Scripts\activate.bat"
pushd "../../TOHPython"
python Tales_Exe.py -p "../Tales-of-Hearts-DS/project.json" -g TOH extract -i "../TOH_Original.nds" -ft Iso 
python Tales_Exe.py -p "../Tales-of-Hearts-DS/project.json" -g TOH extract -ft Story
python Tales_Exe.py -p "../Tales-of-Hearts-DS/project.json" -g TOH extract -ft Skits
python Tales_Exe.py -p "../Tales-of-Hearts-DS/project.json" -g TOH extract -ft Menu
popd
pause