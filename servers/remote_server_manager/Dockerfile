FROM python:3.12-slim

WORKDIR /app

ARG VERSION
ENV APP_VERSION=${VERSION}

# Copy only dependency metadata first (layer caching)
COPY pyproject.toml /app/pyproject.toml

# Copy the actual package sources needed for install
COPY shared/ /app/shared/
COPY servers/remote_server_manager/ /app/servers/remote_server_manager/

# Install the project (reads deps from pyproject.toml)
RUN pip install --no-cache-dir .

CMD ["python", "-m", "servers.remote_server_manager.main"]