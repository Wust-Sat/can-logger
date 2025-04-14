FROM ubuntu:noble

ENV DEBIAN_FRONTEND=noninteractive \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR='/var/cache/pypoetry' \
    POETRY_HOME='/usr/local'

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    python3.12 \
    python3.12-venv && \
    rm -rf /var/lib/apt/lists

RUN ln -s /usr/bin/python3.12 /usr/bin/python3

RUN curl -sSL https://install.python-poetry.org | python3 -

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN poetry install --no-root

# CMD ["poetry", "run", "pytest", "test"]
CMD ["python3.12", "-c", "print('hello world')"]
