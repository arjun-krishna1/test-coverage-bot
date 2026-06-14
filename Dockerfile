FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY scripts/ /app/scripts/
COPY examples/ /app/examples/

ENTRYPOINT ["python", "scripts/poll_autotest_issues.py"]
CMD ["--repo", "apache/superset"]
