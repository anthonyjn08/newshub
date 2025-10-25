FROM pypy:latest
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN pypy manage.py collectstatic --noinput || true
EXPOSE 8000
ENV DOCKER_ENV=true
CMD ["pypy", "manage.py", "runserver", "0.0.0.0:8000"]