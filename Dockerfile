FROM python:3.11-slim

COPY requirements.txt /app/requirements.txt
RUN pip3 install gunicorn -r /app/requirements.txt

COPY gunicorn.conf.py /app/gunicorn.conf.py
COPY ironic_bug_dashboard /app/ironic_bug_dashboard
WORKDIR /app

ENV PROJECT_NAME=ironic

ENTRYPOINT ["gunicorn", "ironic_bug_dashboard:app"]
