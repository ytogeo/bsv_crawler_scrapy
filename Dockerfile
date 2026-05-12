FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml scrapy.cfg ./
COPY src ./src
RUN pip install --no-cache-dir -e .

CMD ["python", "-m", "streetview_crawler.cli", "--help"]

