# Imagen base oficial de GDAL (Ubuntu-based) que ya tiene Python 3 y osgeo preinstalado
FROM osgeo/gdal:ubuntu-small-3.8.3

# Evita que Python escriba archivos .pyc y fuerza salida sin búfer (mejor para logs)
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar pip3, ya que la imagen de GDAL tiene python3 pero a veces no tiene pip
RUN apt-get update && apt-get install -y python3-pip && rm -rf /var/lib/apt/lists/*

# Copiar requirements y hacer la instalación
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Render provee el puerto mediante la variable de entorno $PORT
# Uvicorn escuchará en el puerto 10000 por defecto si no se inyecta
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
