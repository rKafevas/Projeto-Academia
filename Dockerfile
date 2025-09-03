# Imagem base do Python
FROM python:3.11-slim

# Instalar dependências do sistema necessárias para MySQL
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    build-essential \
    gcc \
    pkg-config \
    mariadb-client \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Definir diretório de trabalho
WORKDIR /app

# Copiar arquivos de dependências primeiro (para cache de layers)
COPY requirements.txt .

# Atualizar pip e instalar dependências Python
RUN pip install --upgrade pip \
    && pip install --default-timeout=100 --no-cache-dir -r requirements.txt

# Copiar o restante do código da aplicação
COPY . .

# Tornar o script wait-for-it.sh executável
RUN chmod +x wait-for-it.sh

# Expor a porta que a aplicação vai usar
EXPOSE 5000

# Variáveis de ambiente do Flask
ENV FLASK_APP=app.py
ENV FLASK_ENV=development
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Comando padrão (pode ser sobrescrito no docker-compose)
CMD ["python", "app.py"]