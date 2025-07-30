FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the entire application code to the container
COPY src/* ./
COPY mock ./mock

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
