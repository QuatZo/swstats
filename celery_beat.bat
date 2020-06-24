@echo off
pipenv run celery -A website beat -l INFO
pause