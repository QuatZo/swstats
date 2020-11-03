@echo off
pipenv run celery -A website worker -l INFO -E
pause