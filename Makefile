export PYTHON_VERSION=3.13.11


WEBSERVER_PID=airflow-webserver-monitor.pid
TRIGGERER_PID=airflow-triggerer.pid
SCHEDULER_PID=airflow-scheduler.pid
WORKER_PID=airflow-worker.pid
FLOWER_PID=airflow-flower.pid

init:
	pyenv install ${PYTHON_VERSION}
	pyenv global $(PYTHON_VERSION)
	pyenv virtualenv ${PYTHON_VERSION} workflows
	pyenv activate workflows
	export AIRFLOW_HOME=${PWD}

start: compose sleep airflow

sleep:
	sleep 5

buckets:
	docker compose up -d create_buckets

airflow:
	airflow db init
	airflow webserver -D
	airflow triggerer -D
	airflow scheduler -D
	airflow celery worker -D
	airflow celery flower -D
	echo -e "\033[0;32m Airflow Started. \033[0m"

compose:
	docker compose up -d redis postgres sftp ftp s3 create_buckets

create_user:
	airflow users create \
		--username admin \
		--password admin \
		--role Admin \
		--firstname FIRST_NAME \
		--lastname LAST_NAME \
		--email admin@worfklows.cern

stop:
	-docker compose down
	-cat $(WEBSERVER_PID) | xargs kill  -9
	-cat $(TRIGGERER_PID) | xargs kill -9
	-cat $(SCHEDULER_PID) | xargs kill -9
	-cat $(WORKER_PID) | xargs kill -9
	-cat $(FLOWER_PID) | xargs kill -9
	-rm *.out *.err *.log *.pid
	-kill -9 $(lsof -ti:8080)
	echo -e "\033[0;32m Airflow Stoped. \033[0m"
