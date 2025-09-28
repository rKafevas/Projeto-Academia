# Documentação do Sistema de Gestão de Academia

## 1. Visão Geral

O sistema desenvolvido é uma aplicação web voltada para **gestão financeira e administrativa de uma academia**, com foco no controle de alunos, colaboradores e inadimplência. O acesso é restrito apenas aos administradores e colaboradores da academia, sem disponibilidade pública.

A aplicação foi desenvolvida utilizando **Flask (Python)** no backend, **HTML/CSS/Bootstrap** no frontend e banco de dados relacional (**SQLite em desenvolvimento**, com possibilidade de migração para **MySQL em produção**).

---

## 2. Funcionalidades Principais

### 2.1 Gestão de Usuários

* Cadastro de administradores e colaboradores.
* Login e autenticação de usuários.
* Diferenciação de permissões:


  * **Administrador**: acesso total ao sistema.
  * **Colaborador**: restrição a algumas funcionalidades (por exemplo, não pode cadastrar novos usuários, mas pode gerenciar alunos).

### 2.2 Gestão de Alunos

* Cadastro de alunos com dados pessoais e financeiros.
* Edição e exclusão de cadastros.
* Acompanhamento de situação financeira dos alunos.

### 2.3 Controle Financeiro

* Registro de pagamentos.
* Definição de status de alunos: **Em dia** ou **Inadimplente**.
* Atualização automática de inadimplência quando o pagamento não é realizado na data estipulada.

### 2.4 Dashboard

* Exibição de informações gerais, incluindo:

  * Total de alunos cadastrados.
  * Quantidade de alunos em dia.
  * Quantidade de inadimplentes.

---

## 3. Tecnologias Utilizadas

* **Backend**: Flask (Python)
* **Frontend**: HTML, CSS, Bootstrap
* **Banco de Dados**: SQLite (desenvolvimento), MySQL (opção para produção)
* **Controle de Dependências**: Feito através da containerização via Docker
* **Hospedagem**: Execução local com Docker

---

## 4. Fluxo de Uso do Sistema

1. O administrador acessa a tela de login.
2. Após autenticação, é direcionado ao **dashboard**.
3. Do dashboard, pode navegar para:

   * Cadastro e gerenciamento de alunos.
   * Cadastro e gerenciamento de colaboradores.
   * Controle de pagamentos e inadimplência.
4. O sistema atualiza automaticamente o status de cada aluno.
5. O administrador pode visualizar os relatórios financeiros e acompanhar a saúde da academia.

---

## 5. Segurança

* Senhas de usuários são armazenadas com hash (não em texto puro).
* Sessões de login são gerenciadas com cookies seguros.
* O acesso ao sistema é restrito apenas a usuários cadastrados.
* Recomenda-se migrar o banco para MySQL em produção para maior segurança e confiabilidade.

---

## 6. Possíveis Melhorias Futuras

* Implementação de relatórios em PDF.
* Integração com sistemas de pagamento online.
* Notificações por e-mail ou WhatsApp para alunos inadimplentes.
* Implementação de logs de auditoria (quem fez o quê).
* Migração definitiva para MySQL em produção.

---

## 7. Conclusão

Este sistema atende às necessidades iniciais de controle financeiro da academia, oferecendo uma solução simples, de baixo custo e de fácil manutenção. Ele pode ser expandido conforme a demanda da academia crescer.

## 8. Instalação via Docker

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