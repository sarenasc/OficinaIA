FROM python:3.12-slim
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && useradd --uid 10001 --create-home runner
USER 10001:10001
WORKDIR /tmp
CMD ["python", "-c", "print('Sandbox listo')"]
