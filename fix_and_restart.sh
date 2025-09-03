#!/bin/bash

echo "=== CORRIGINDO E REINICIANDO O SISTEMA ==="

# Para tudo
echo "1. Parando containers..."
docker-compose down

# Remove containers órfãos
echo "2. Removendo containers órfãos..."
docker-compose down --remove-orphans

# Rebuild sem cache
echo "3. Reconstruindo containers..."
docker-compose build --no-cache

# Inicia novamente
echo "4. Iniciando sistema..."
docker-compose up -d

# Aguarda um pouco
echo "5. Aguardando inicialização..."
sleep 15

# Verifica status
echo "6. Verificando status:"
docker-compose ps

echo
echo "7. Verificando logs do Flask:"
docker-compose logs --tail=20 web

echo
echo "8. Testando conexão:"
if curl -s http://localhost:5000 > /dev/null; then
    echo "✅ Sistema funcionando! Acesse: http://localhost:5000"
else
    echo "❌ Sistema não está respondendo"
    echo
    echo "Para debugar, execute:"
    echo "docker-compose logs web"
    echo
    echo "Para acessar o container manualmente:"
    echo "docker-compose exec web bash"
fi