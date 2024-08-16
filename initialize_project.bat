@echo off

echo *************** Initialize the project - Run this .bat once only ***************

call (
    pip install virtualenvwrapper
    pip install build

    mkvirtualenv neonat
    workon neonat

    python -m build
)
mkdir scenario

echo *************** Initialization is over. ***************

pause
