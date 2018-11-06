FROM python:3.6-alpine

COPY . /app
WORKDIR /app

ENV DATAVAULT_URI 'sqlite:///mydatabase.db'

RUN pip install pipenv gunicorn
RUN pipenv install --system --deploy

EXPOSE 5000
ENTRYPOINT gunicorn -b :5000 --access-logfile - --error-logfile - app:app