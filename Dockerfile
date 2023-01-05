FROM python:3.8.10

WORKDIR /code

COPY requirements.txt .

RUN apt-get update && apt-get -y install cmake protobuf-compiler
RUN apt-get install -y ffmpeg libsm6 libxext6
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .

CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "--chdir", "/code/src", "app:app", "--bind", "0.0.0.0:9090", "--workers", "2", "--log-level", "info"]

EXPOSE 9090
