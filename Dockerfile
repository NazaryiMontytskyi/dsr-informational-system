FROM python:3.11-slim

# LibreOffice (лише Writer + залежності, без Impress/Calc тощо -- менший образ).
# ttf-mscorefonts-installer завантажує СПРАВЖНІ шрифти Microsoft (зокрема
# Times New Roman) із офіційного джерела під час збірки образу (пакет
# лежить у розділі "contrib", тому що ліцензія MS не дозволяє Debian
# розповсюджувати самі файли шрифтів -- лише інсталятор, що приймає EULA
# і тягне їх окремо). fonts-liberation лишаємо як запасний метрично
# сумісний варіант на випадок недоступності мережі під час збірки.
RUN sed -i 's/Components: main$/Components: main contrib/' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && \
    echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | debconf-set-selections && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    libreoffice-writer \
    fontconfig \
    ttf-mscorefonts-installer \
    fonts-liberation \
    fonts-dejavu-core \
    && fc-cache -f \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["sh", "-c", "python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
