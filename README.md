# SWSTATS
Website for checking Big Data in Summoners War, i.e. most common monsters builds.

## API
SWSTATS exposes an API that contains every contributor monsters, artifact and rune, including builds. The root endpoint is [https://swstats.info/api/](https://swstats.info/api/). Documentation of these
endpoints is available in [Swagger](https://swstats.info/swagger/). This API is free and public but subject to rate 
limits, and any abuse or abnormal use of server resources will see restrictions applied. 

### Monster Report
Since March 2021, API for Monster Report is public, but it's not visible in Docs and root Endpoint because it was intended to be a private API only for Front-End. After many requests to make it public, I've finally decided to share it with community. Here are the instructions on how to use it
```
https://swstats.info/web/reports-generate/<com2us_id>
```
`<com2us_id>` - monster ID Com2uS is using (i.e. 13413 - Lushen) to determine its core. You can get full list of these IDs from [SWARFARM API](https://swarfarm.com/api/v2/monsters/). From this endpoint you get response with `task_id` which is required to ask next endpoint for calculation status and - if it already ended - report data. Worth mentioning that this response is being cached for 15 minutes. Here's the example response.
```json
{
    "status": "PENDING",
    "task_id": "12345678-1234-1234-1234-1234567890ab"
}
```
After getting the `task_id` from above endpoint, you need to call repeatedly this Status endpoint
```
https://swstats.info/web/status/<task_id>
```
Under this endpoint, if `task_id` is provided, you can check current calculation status and - if calcs already ended - get report data. I recommend you calling this API call every second (traffic is being monitored and every more frequent call may result in blocking you) until you get different Status than `PENDING`. This response is being cached for 30 minutes. Example response is quite long, so it's available [here](https://gist.github.com/QuatZo/d44022ff040bc317b24ac96ae72b42c2)
##### What will be returned?
- Charts data
- Condensed Monster data (some base data, most common 2/4/6 build, TOP3 most common sets)
- Condensed Family data (some base data. so people can move easily between family members)
- All records used to generate the report (don't worry, anonymised)
- Monster substats analysis (mean, std, min/max, percentiles)

### API Authentication
No authentication needed.

## Contributing
It's an open-source project, everyone is welcome to contribute. You don't need to code to contribute ideas. If you have a feature request, notice a bug or anything else, submit an issue here on github.

## Setting up for Development
###### [In development] Docker Environment [In development]
It's quite complicated process, because it's not containerized yet
1. Create PostgreSQL User (any username) & Database (`swstats`)
2. Copy `.env.example` to `.env`, changing `DJ_DATABASE_URL` to proper values (change only `user` and `passwd`)
3. Run Redis on your PC
4. Create virtual environment and install requirements `pip install -r requirements.txt`
5. Migrate Django migrations
6. Create super user `python manage.py createsuperuser`
7. Load mixtures `python manage.py loaddata base_data.json`
8. Run Django server
9. If everything works, run Celery workers (example in `dev/celery_worker.bat`, for Windows `dev/celery_worker_solo.bat`)

## Running tests
No tests... yet...

## Built With
* [Python 3.6](https://www.python.org/)
* [Django](https://www.djangoproject.com/) - The web framework
* [Django REST Framework](http://www.django-rest-framework.org/) - REST API for Django
* [Celery](http://www.celeryproject.org/) - Asynchronous task runner
* [Redis](https://redis.io/) - Broker and backend for Celery
* Many other packages. See requirements.txt

## Authors
* [**QuatZo**](https://github.com/QuatZo)

## License
This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details
