FROM python:3.9-slim
RUN apt-get update && apt-get install -y ansible
WORKDIR /ansible
COPY ansible/ .
CMD ["tail", "-f", "/dev/null"]