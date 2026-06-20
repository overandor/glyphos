FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY crawler_webapp.py layer_crawler_etl.py poptimizer_etl_engine.py ./

RUN mkdir -p /app/data

ENV PORT=7860
EXPOSE 7860

CMD ["python", "crawler_webapp.py"]
