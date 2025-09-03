-- Configurações iniciais para o banco de dados
SET NAMES utf8mb4;
SET character_set_client = utf8mb4;

-- Criar o banco se não existir
CREATE DATABASE IF NOT EXISTS academia CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Usar o banco criado
USE academia;

-- As tabelas serão criadas automaticamente pelo Flask-SQLAlchemy