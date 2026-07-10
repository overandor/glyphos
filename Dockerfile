FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && \
    rm -rf /var/lib/apt/lists/*

COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY hf_space_app.py .
COPY frontend/dist ./frontend/dist

RUN mkdir -p /tmp/systemlake_v4b

ENV PORT=7860
ENV SYSTEMLAKE_DATA_DIR=/tmp/systemlake_v4b
EXPOSE 7860

CMD ["python", "hf_space_app.py"]
