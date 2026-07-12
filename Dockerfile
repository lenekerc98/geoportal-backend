# Usaremos la imagen oficial de Ubuntu 22.04 que es sumamente estable
FROM ubuntu:22.04

# Evita que el sistema pida confirmaciones al instalar (evita que Docker se congele)
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar Python, PIP y el motor C++ de GDAL directamente del sistema operativo
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    gdal-bin \
    libgdal-dev \
    python3-gdal \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalarlos
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Comando de arranque
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
