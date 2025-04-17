# Dockerfile
FROM python:3.11-slim

# Establece el directorio de trabajo
WORKDIR /app

# Copia dependencias y las instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto de la app
COPY . .

# Expone el puerto (ajusta si es otro)
EXPOSE 8000

# Comando para ejecutar la app (ajusta según sea main.py o run.py)
CMD ["python", "run.py"]
