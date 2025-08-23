#!/bin/bash

# start specific fluxIAM process depending on parameter 
if [ -z "$1" ]
  then
    echo "No argument supplied: service|worker|dashboard"
    exit 0
fi

case $1 in 
    service) 
      poetry run uvicorn hobbes.main:app --host 0.0.0.0 --port 8000
      ;;
    worker)  
      celery -A hobbes.worker.celery_app worker $2
      ;;
    dashboard)  
      celery flower --port=5555 $2
      ;;
    *)
      echo "unknown"
      exit 0
      ;;
esac
