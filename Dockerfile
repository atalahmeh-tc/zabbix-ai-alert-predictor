FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . /app

CMD ["streamlit", "run", "dashboard/app.py", "--server.address=0.0.0.0"]
