FROM python:latest

RUN mkdir app

RUN mkdir app/main

RUN mkdir app/main/images

COPY . app/main/

WORKDIR app/

RUN python -m pip install --upgrade pip

RUN python -m pip install -r ./main/requirements.txt

RUN chmod +x ./main/wait-for-it.sh

CMD ./main/wait-for-it.sh postgres:5432 -- uvicorn main.app:app --host 0.0.0.0 --port 8000
