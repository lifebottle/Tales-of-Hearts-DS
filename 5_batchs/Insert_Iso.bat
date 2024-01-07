pushd ".."

::python Tales_Exe.py -p "../Tales-of-Rebirth/project.json" -g TOR insert -ft Story
::python Tales_Exe.py -p "../Tales-of-Rebirth/project.json" -g TOR insert -ft Skits
::python Tales_Exe.py -p "../Tales-of-Rebirth/project.json" -g TOR insert -ft Menu
::python Tales_Exe.py -p "../Tales-of-Rebirth/project.json" -g TOR insert -ft Main
::python Tales_Exe.py -p "../Tales-of-Rebirth/project.json" -g TOR insert -ft Asm
::--------------------------------------
::python Tales_Exe.py -p "../Tales-of-Rebirth/project.json" -g TOR insert -ft All --iso "../Tales of Rebirth (Japan)_Original.iso"
::--------------------------------------
python Tales_Exe.py -g TOR -p "../tales-of-rebirth/project.json" insert -ft All --with-editing --with-proofreading --with-problematic --iso "../Tales of Rebirth (Japan)_Original.iso"
::python Tales_Exe.py -g TOR -p "../tales-of-rebirth/project.json" insert -ft All --iso "../Tales of Rebirth (Japan)_Original.iso"

popd
pause