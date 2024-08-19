@echo off

call workon neonat

:launch_once_more
echo What is the scenario you want to execute ? Type a name without space, then type 'enter'
set "NAME="
set /p NAME=""
echo If you want to force the process, type "--force" ; if not, type "space" + "enter"
set "FORCE="
set /p FORCE=""

echo %NAME% and %FORCE%
echo Launch calculation ...

IF NOT EXIST scenarios\%NAME% (
    echo ****************************** ATTENTION ******************************
    echo !!! Please create a folder *scenarios/scenario_name* in the folder scenarios
    echo And add a well-filled Excel input file named *input_scenario_name.xls* !!!
    echo ***********************************************************************
    pause
)

python neonat_baby_move.py %NAME% %FORCE%

echo Calculation is over.

echo:
echo If the calculation is unfeasible, please read the log file : scenarios/%NAME%/log_%NAME%.log
echo ***********************************************************************
echo:
SET choice=
SET /p choice=Launch another calculation ? [press 'Y' + 'enter' if Yes, 'N' if No]: 
IF '%choice%'=='' GOTO launch_once_more
IF '%choice%'=='Y' GOTO launch_once_more
IF '%choice%'=='y' GOTO launch_once_more
IF '%choice%'=='N' GOTO no
IF '%choice%'=='n' GOTO no

:no
pause

