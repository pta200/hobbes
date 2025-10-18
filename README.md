# Hobbes

The Hobbes is a lab FastAPI RESTFull service with Celery for long running background tasks

## Architecture
The service is built with two components:
* FastAPI RESTFull service 
* PostgreSQL 16
* Celery 5

The sevice is using async scopped SQLAlchemy sessions. The service does the heavy lifting in terms of creating the database tables if none exist. Celery is using gevent concurrency since the tasks are I/O and scopped sqlalchemy sessions

## Development
The repos uses [poetry](https://python-poetry.org/) for dependency management, building. Use the docker compose to run the service.

This will allow you to see the OpenAPI (Swagger) inter fact as http://localhost:8000/docs.
```bash
$ sudo docker compose up -d --build --remove-orphans
```

## Tests
To run the tests run the following
```bash
$ poetry run pytest
```

## Migrations
While the service will create any/all missing tables and start up, migrations are managed using Alembic. Given the service
is likely running inside a container you'll create the migrations inside and copy back out to store in the source code.
When running in different environments make sure the down_revisions match. 

To generate a migration file run the follow command and make sure to confirm the correct information is in the output.
```bash
$ poetry alembic revision --autogenerate -m "<place your revision name here e.g. add table foo>"
```

To execute the migration run the following command:
```bash
$ alembic upgrade head
```

To execute downgrade run the following command
```bash
$ alembic downgrade <revision number e.g. -1>
```