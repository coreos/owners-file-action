FROM python:3.14-slim

RUN pip install requests pyyaml

COPY entrypoint.py /entrypoint.py

ENTRYPOINT ["python", "/entrypoint.py"]
