@echo off
pipenv run celery -A website worker --pool=solo -l INFO