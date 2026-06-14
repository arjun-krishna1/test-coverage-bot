FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY main.py /app/main.py
COPY src/ /app/src/
COPY examples/ /app/examples/

ENTRYPOINT ["python", "main.py"]
CMD ["--repo", "apache/superset"]
