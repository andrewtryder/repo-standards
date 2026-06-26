FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
    && curl -fsSL https://deb.nodesource.com/setup_24.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install \
    coverage==7.6.10 \
    pytest==8.3.4 \
    pyyaml==6.0.2 \
    ruff==0.8.6

WORKDIR /work

CMD ["python3"]
