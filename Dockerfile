FROM apache/airflow:2.2.4-python3.8

ENV PYTHONBUFFERED=0 
ENV AIRFLOW_UID=501

COPY requirements.txt ./requirements.txt
COPY requirements-test.txt ./requirements-test.txt
COPY dags ./dags
USER airflow
RUN pip install --upgrade pip &&\
    pip install --no-cache-dir --upgrade setuptools==59.1.1 &&\
    pip install --no-cache-dir --upgrade wheel &&\
    pip install --no-cache-dir --user -r requirements.txt -r requirements-test.txt
