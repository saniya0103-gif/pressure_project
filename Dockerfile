FROM python:3.11

WORKDIR /app

COPY . .

# If you have requirements.txt, uncomment:
# RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "conversion.py"]

