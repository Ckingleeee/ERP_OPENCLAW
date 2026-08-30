ARG PYTHON_BASE_IMAGE=python:3.12-slim

FROM ${PYTHON_BASE_IMAGE} AS builder

ARG APT_MIRROR=
ARG APT_SECURITY_MIRROR=
ARG PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_TRUSTED_HOST=

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN if [ -n "$APT_SECURITY_MIRROR" ]; then \
        sed -i \
          -e "s|http://deb.debian.org/debian-security|$APT_SECURITY_MIRROR|g" \
          -e "s|https://deb.debian.org/debian-security|$APT_SECURITY_MIRROR|g" \
          -e "s|http://security.debian.org/debian-security|$APT_SECURITY_MIRROR|g" \
          -e "s|https://security.debian.org/debian-security|$APT_SECURITY_MIRROR|g" \
          /etc/apt/sources.list /etc/apt/sources.list.d/*.sources 2>/dev/null || true; \
    fi \
    && if [ -n "$APT_MIRROR" ]; then \
        sed -i \
          -e "s|http://deb.debian.org/debian|$APT_MIRROR|g" \
          -e "s|https://deb.debian.org/debian|$APT_MIRROR|g" \
          /etc/apt/sources.list /etc/apt/sources.list.d/*.sources 2>/dev/null || true; \
    fi \
    && apt-get -o Acquire::Retries=5 update \
    && apt-get install --no-install-recommends -y build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-linux.txt requirements-erp.txt requirements-docker.txt ./
RUN python -m venv /opt/venv \
    && pip_args="--index-url $PIP_INDEX_URL --retries 5 --timeout 60" \
    && if [ -n "$PIP_TRUSTED_HOST" ]; then pip_args="$pip_args --trusted-host $PIP_TRUSTED_HOST"; fi \
    && /opt/venv/bin/python -m pip install $pip_args --upgrade pip \
    && /opt/venv/bin/python -m pip install $pip_args -r requirements-docker.txt

FROM ${PYTHON_BASE_IMAGE} AS runtime

ARG APT_MIRROR=
ARG APT_SECURITY_MIRROR=

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PATH=/opt/venv/bin:$PATH

WORKDIR /app

RUN if [ -n "$APT_SECURITY_MIRROR" ]; then \
        sed -i \
          -e "s|http://deb.debian.org/debian-security|$APT_SECURITY_MIRROR|g" \
          -e "s|https://deb.debian.org/debian-security|$APT_SECURITY_MIRROR|g" \
          -e "s|http://security.debian.org/debian-security|$APT_SECURITY_MIRROR|g" \
          -e "s|https://security.debian.org/debian-security|$APT_SECURITY_MIRROR|g" \
          /etc/apt/sources.list /etc/apt/sources.list.d/*.sources 2>/dev/null || true; \
    fi \
    && if [ -n "$APT_MIRROR" ]; then \
        sed -i \
          -e "s|http://deb.debian.org/debian|$APT_MIRROR|g" \
          -e "s|https://deb.debian.org/debian|$APT_MIRROR|g" \
          /etc/apt/sources.list /etc/apt/sources.list.d/*.sources 2>/dev/null || true; \
    fi \
    && apt-get -o Acquire::Retries=5 update \
    && apt-get install --no-install-recommends -y ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

COPY src ./src

RUN groupadd --gid 10001 erp \
    && useradd --uid 10001 --gid erp --create-home erp \
    && mkdir -p /app/src/download \
    && chown -R erp:erp /app

USER erp

CMD ["python", "-m", "uvicorn", "api_view.web_main:app", "--host", "0.0.0.0", "--port", "8090"]
