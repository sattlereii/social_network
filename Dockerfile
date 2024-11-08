# Dockerfile pro Flask aplikaci
FROM python:3.9-slim

# Nastavení pracovního adresáře
WORKDIR /code

# Kopírování requirements.txt a instalace závislostí
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopírování zbytku kódu do pracovního adresáře
COPY . .

# Nastavení příkazu pro spuštění aplikace
CMD ["python", "app.py"]
