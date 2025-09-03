# Sistema Academia - Instalação via Docker

## Pré-requisitos

1. **Docker Desktop** (Windows/Mac) ou **Docker + Docker Compose** (Linux)
   - Windows/Mac: [Download Docker Desktop](https://www.docker.com/products/docker-desktop/)
   - Ubuntu/Debian: `sudo apt-get install docker.io docker-compose`
   - CentOS/RHEL: `sudo yum install docker docker-compose`

## Instalação Rápida

### Windows
1. Execute o arquivo `instalar.bat` como administrador
2. Aguarde a instalação completar

### Linux/Mac
1. Torne o script executável: `chmod +x instalar.sh`
2. Execute: `./instalar.sh`

### Manual
Se preferir instalar manualmente:

```bash
# Construir e iniciar
docker-compose up --build -d

# Ver logs para pegar a senha inicial
docker-compose logs web
```

## Acesso ao Sistema

- **URL:** http://localhost:5000
- **Usuário inicial:** `admin`
- **Senha:** Será exibida nos logs do Docker (execute `docker-compose logs web`)

## Comandos Úteis

```bash
# Parar o sistema
docker-compose down

# Iniciar o sistema
docker-compose up -d

# Ver logs da aplicação
docker-compose logs web

# Ver logs do banco de dados
docker-compose logs db

# Reiniciar apenas a aplicação
docker-compose restart web

# Atualizar o sistema (quando houver nova versão)
docker-compose down
docker-compose pull
docker-compose up --build -d
```

## Backup do Banco de Dados

```bash
# Fazer backup
docker exec academia_db mysqldump -u academia_user -pacademia_password_123 academia > backup.sql

# Restaurar backup
docker exec -i academia_db mysql -u academia_user -pacademia_password_123 academia < backup.sql
```

## Solução de Problemas

### Erro "Port already in use"
```bash
# Parar outros containers que podem estar usando as portas
docker-compose down
docker stop $(docker ps -aq)
```

### Resetar completamente
```bash
# CUIDADO: Isso apagará todos os dados
docker-compose down -v
docker-compose up --build -d
```

### Ver o que está rodando
```bash
docker-compose ps
```

## Arquivos Importantes

- `docker-compose.yml` - Configuração dos containers
- `Dockerfile` - Configuração da aplicação
- Os dados do banco ficam salvos automaticamente

## Suporte

Em caso de problemas, envie:
1. Output do comando `docker-compose logs`
2. Output do comando `docker-compose ps`
3. Descrição do erro encontrado