FROM registry.cern.ch/cern-sis/scoap3/airflow-base:3.1.3
USER root
RUN apt-get update && apt-get install -y \
    build-essential \
    libleveldb-dev \
    && rm -rf /var/lib/apt/lists/*
USER airflow
WORKDIR /opt/airflow

ENV PYTHONBUFFERED=0

COPY constraints.txt ./constraints.txt
COPY requirements.txt ./requirements.txt
COPY requirements-test.txt ./requirements-test.txt
COPY requirements-airflow.txt ./requirements-airflow.txt

RUN pip install --upgrade pip
RUN pip install --upgrade setuptools wheel
RUN pip install --no-cache-dir --user -r requirements-airflow.txt
RUN pip install --no-cache-dir --user -r requirements.txt
RUN pip install --no-cache-dir --user -r requirements-test.txt

RUN rm constraints.txt
