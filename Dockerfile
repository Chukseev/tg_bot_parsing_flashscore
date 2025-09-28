FROM python:3.12-slim
WORKDIR /app
COPY .env_test .env
COPY . .
RUN python -m venv /app/venv
RUN /app/venv/bin/pip install --no-cache-dir -r requirements.txt
CMD ["/app/venv/bin/python3", "test_main.py"]