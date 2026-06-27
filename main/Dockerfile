FROM python:3.12-slim

RUN mkdir app

RUN mkdir app/main

RUN mkdir app/main/images

WORKDIR app/

COPY requirements.txt ./main

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r ./main/requirements.txt

COPY . ./main/

RUN chmod +x ./main/wait-for-it.sh

CMD ./main/wait-for-it.sh postgres:5432 -- uvicorn main.app:app --host 0.0.0.0 --port 8000
