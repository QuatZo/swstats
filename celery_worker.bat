@echo off
pipenv run celery -A website worker --pool=solo -l INFO -E --autoscale=10,3
pause