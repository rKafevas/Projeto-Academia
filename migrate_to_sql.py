#!/usr/bin/env python3
# migrate_to_mysql.py - Script para migrar estrutura do banco para MySQL

import os
import sys
from datetime import datetime, date
from dotenv import load_dotenv
import secrets

# Adicione o diretório atual ao path para importar o app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Carrega as variáveis de ambiente
load_dotenv()

from app import app, db, Usuario, Cliente, Pagamento

def criar_estrutura_banco():
    """Cria todas as tabelas no MySQL"""
    print("Criando estrutura do banco de dados MySQL...")
    
    with app.app_context():
        try:
            # Remove todas as tabelas existentes (cuidado!)
            db.drop_all()
            print("Tabelas antigas removidas.")
            
            # Cria todas as tabelas
            db.create_all()
            print("Tabelas criadas com sucesso!")
            
            return True
        except Exception as e:
            print(f"Erro ao criar estrutura: {e}")
            return False

def criar_usuario_admin():
    """Cria usuário administrador inicial"""
    print("Criando usuário administrador inicial...")
    
    with app.app_context():
        try:
            # Verifica se já existe algum usuário
            if Usuario.query.count() > 0:
                print("Usuário administrador já existe. Pulando...")
                return True
            
            # Gera senha temporária
            admin_password = secrets.token_urlsafe(12)
            
            admin = Usuario(
                username='admin',
                nome_completo='Administrador do Sistema',
                email='admin@academia.com',
                tipo_permissao='admin',
                must_reset_password=True,
                ativo=True
            )
            admin.set_password(admin_password)
            
            db.session.add(admin)
            db.session.commit()
            
            print("Usuário administrador criado com sucesso!")
            print(f"Usuário: admin")
            print(f"Senha temporária: {admin_password}")
            print("IMPORTANTE: Altere a senha no primeiro login!")
            
            return True
        except Exception as e:
            print(f"Erro ao criar usuário admin: {e}")
            return False

def main():
    """Função principal do script de migração"""
    print("=== MIGRAÇÃO PARA MYSQL ===")
    print(f"Ambiente: {os.getenv('FLASK_ENV', 'development')}")
    print(f"Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print()
    
    # Confirmação
    resposta = input("Deseja continuar com a migração? (s/N): ")
    if resposta.lower() != 's':
        print("Migração cancelada.")
        return
    
    print("\nIniciando migração...")
    
    # Passo 1: Criar estrutura
    if not criar_estrutura_banco():
        print("Falha ao criar estrutura. Abortando...")
        return
    
    # Passo 2: Criar usuário admin
    if not criar_usuario_admin():
        print("Falha ao criar usuário admin. Abortando...")
        return
    
    print("\n=== MIGRAÇÃO CONCLUÍDA ===")
    print("Estrutura do banco MySQL criada com sucesso!")
    print("Agora você pode fazer deploy no PythonAnywhere.")

if __name__ == "__main__":
    main()