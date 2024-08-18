@echo off

echo *************** Initialize the project - Run this .bat once only ***************

call (
    pip install virtualenvwrapper-win
    pip install build

    mkvirtualenv neonat
    workon neonat

    python -m build
    pip install -e .
)

echo *************** Initialization is over. ***************

pause
