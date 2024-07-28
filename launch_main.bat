@echo off

call C:\Users\VS5997\Envs\gamspy\Scripts\activate.bat
echo What is the scenario you want to execute ?
set /p NAME=

echo Launch calculation ...

IF NOT EXIST scenarios\%NAME% (
    echo ****************************** ATTENTION ******************************
    echo !!! Please create a folder *scenario_name* in the folder scenarios
    echo And add the well-filled Excel input file named *input_scenario_name.xls* !!!
    echo ***********************************************************************
    pause
)
python neonat_baby_move.py %NAME%

echo Calculation is over.

pause
