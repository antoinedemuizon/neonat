@echo off

call C:\Users\VS5997\Envs\neonat\Scripts\activate.bat
echo What is the scenario you want to execute (type a name without space, then type "enter") ?
set /p NAME=
echo If you want to force the process, type "--force" ; if not, type "enter" directly
set /p FORCE=

echo Launch calculation ...

IF NOT EXIST scenarios\%NAME% (
    echo ****************************** ATTENTION ******************************
    echo !!! Please create a folder *scenario_name* in the folder scenarios
    echo And add the well-filled Excel input file named *input_scenario_name.xls* !!!
    echo ***********************************************************************
    pause
)

python neonat_baby_move.py %NAME% %FORCE%

echo Calculation is over.

pause
