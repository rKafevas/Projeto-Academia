#!/bin/bash

echo "=== DEBUG DO SISTEMA ACADEMIA ==="
echo "Data: $(date)"
echo

echo "1. Status dos containers:"
docker-compose ps
echo

echo "2. Logs do container web (últimas 50 linhas):"
docker-compose logs --tail=50 web
echo

echo "3. Logs do container db (últimas 20 linhas):"
docker-compose logs --tail=20 db
echo

echo "4. Verificando se o Flask está rodando:"
docker-compose exec web ps aux | grep python || echo "Processo Python não encontrado"
echo

echo "5. Verificando portas em uso no container:"
docker-compose exec web netstat -tlpn 2>/dev/null || echo "netstat não disponível"
echo

echo "6. Testando conexão com o banco:"
docker-compose exec web python -c "
import os
import pymysql
try:
    conn = pymysql.connect(
        host='db',
        user='academia_user', 
        password='academia_password_123',
        database='academia'
    )
    print('Conexão com banco: OK')
    conn.close()
except Exception as e:
    print(f'Erro na conexão: {e}')
"
echo

echo "7. Variáveis de ambiente no container web:"
docker-compose exec web env | grep -E "(FLASK|DB|DATABASE)" | sort
echo

echo "8. Conteúdo do diretório /app:"
docker-compose exec web ls -la /app/
echo

echo "9. Verificando se app.py existe e é executável:"
docker-compose exec web ls -la /app/app.py
echo

echo "10. Tentando executar app.py manualmente:"
docker-compose exec web python /app/app.py &
sleep 5
echo "Verificando se iniciou:"
curl -s http://localhost:5000 > /dev/null && echo "Flask respondendo OK" || echo "Flask não respondendo"

echo
echo "=== FIM DO DEBUG ==="