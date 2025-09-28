# app.py (versão reforçada)
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import pymysql
import random
import re
import os
import calendar
import secrets
from dotenv import load_dotenv
from faker import Faker
from flask_wtf import CSRFProtect
from forms import CriarUsuarioForm  
from forms import TrocarSenhaForm


# Carrega variáveis do .env
load_dotenv()

# Configuração da aplicação
pymysql.install_as_MySQLdb()

# Configuração da aplicação
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'chave_padrao_para_dev')

# Conexão com MySQL local (Docker)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# Configurações de cookie de sessão (segurança)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=False if os.getenv('FLASK_DEBUG', '1') == '1' else True,
    SESSION_COOKIE_SAMESITE='Lax'
)

# Inicializações
fake = Faker('pt_BR')
csrf = CSRFProtect(app)

# --- Limiter simples em memória (apenas para desenvolvimento) ---
failed_logins = {}
MAX_ATTEMPTS = 5
LOCK_MINUTES = 15

# Função para obter o usuário logado
def get_current_user():
    user_id = session.get('user_id')  # ou o campo que você usa para armazenar o ID do usuário na sessão
    if user_id:
        return Usuario.query.get(user_id)
    return None

# Disponibiliza a função para todos os templates

def _get_client_key():
    # Usa IP + username opcional para chave. Em produção considere cabeçalhos e proxy.
    ip = request.remote_addr or 'unknown'
    username = request.form.get('username') or request.args.get('username') or ''
    return f"{ip}:{username}"

def check_rate_limit():
    key = _get_client_key()
    entry = failed_logins.get(key)
    now = datetime.utcnow()
    if entry:
        locked_until = entry.get('locked_until')
        if locked_until and now < locked_until:
            return False, (locked_until - now).total_seconds()
    return True, 0

def record_failed_attempt():
    key = _get_client_key()
    now = datetime.utcnow()
    entry = failed_logins.get(key)
    if not entry:
        failed_logins[key] = {'count': 1, 'first_attempt': now, 'locked_until': None}
        return
    entry['count'] += 1
    # se passou janela (> LOCK_MINUTES) reset
    window = timedelta(minutes=LOCK_MINUTES)
    if now - entry['first_attempt'] > window:
        # reset
        failed_logins[key] = {'count': 1, 'first_attempt': now, 'locked_until': None}
        return
    if entry['count'] >= MAX_ATTEMPTS:
        entry['locked_until'] = now + timedelta(minutes=LOCK_MINUTES)

def reset_failed_attempts():
    key = _get_client_key()
    if key in failed_logins:
        del failed_logins[key]

# --- Modelos ---
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    nome_completo = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(200), nullable=False)
    tipo_permissao = db.Column(db.String(20), nullable=False, default='colaborador')  # 'admin' ou 'colaborador'
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_login = db.Column(db.DateTime)
    must_reset_password = db.Column(db.Boolean, default=False)  # força troca no primeiro login
    session_token = db.Column(db.String(128), nullable=True)  # token para validar sessão

    def __repr__(self):
        return f'<Usuario {self.username}>'

    def set_password(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_password(self, senha):
        return check_password_hash(self.senha_hash, senha)

    def is_admin(self):
        return self.tipo_permissao == 'admin'

@app.context_processor
def inject_user():
    def get_current_user():
        user_id = session.get('user_id')
        if user_id:
            return Usuario.query.get(user_id)
        return None
    return dict(get_current_user=get_current_user)


class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    data_matricula = db.Column(db.Date, nullable=False, default=date.today)
    valor_mensalidade = db.Column(db.Float, nullable=False)
    dia_vencimento = db.Column(db.Integer, nullable=False)  # dia do mês (1-31)
    ativo = db.Column(db.Boolean, default=True)
    pagamentos = db.relationship('Pagamento', backref='cliente', lazy=True)

    def __repr__(self):
        return f'<Cliente {self.nome}>'

    # (mantive suas funções de atraso/calculo — sem alteração funcional importante)
    def esta_em_atraso(self):
        hoje = date.today()
        pagamento_atual = Pagamento.query.filter_by(
            cliente_id=self.id,
            mes_referencia=hoje.month,
            ano_referencia=hoje.year
        ).first()
        if pagamento_atual:
            return False
        vencimento = date(hoje.year, hoje.month, min(self.dia_vencimento, 28))
        return hoje > vencimento

    def calcular_meses_atraso(self):
        hoje = date.today()
        ultimo_pagamento = Pagamento.query.filter_by(cliente_id=self.id).order_by(Pagamento.data_pagamento.desc()).first()
        data_referencia = self.data_matricula
        if ultimo_pagamento:
            data_referencia = ultimo_pagamento.data_pagamento
        meses_atraso = 0
        valor_devido = 0
        data_verificacao = data_referencia + relativedelta(months=1)
        while data_verificacao.year < hoje.year or (data_verificacao.year == hoje.year and data_verificacao.month <= hoje.month):
            data_verificacao_ajustada = date(data_verificacao.year, data_verificacao.month, min(self.dia_vencimento, 28))
            if data_verificacao.year == hoje.year and data_verificacao.month == hoje.month and hoje < data_verificacao_ajustada:
                break
            pagamento_existente = Pagamento.query.filter_by(
                cliente_id=self.id,
                mes_referencia=data_verificacao.month,
                ano_referencia=data_verificacao.year
            ).first()
            if not pagamento_existente:
                meses_atraso += 1
                valor_devido += self.valor_mensalidade
            data_verificacao += relativedelta(months=1)
        return meses_atraso, valor_devido

    def proximo_vencimento(self):
        hoje = date.today()
        if hoje.day <= self.dia_vencimento:
            return date(hoje.year, hoje.month, self.dia_vencimento)
        else:
            proximo_mes = hoje + relativedelta(months=1)
            return date(proximo_mes.year, proximo_mes.month, self.dia_vencimento)



class Pagamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    data_pagamento = db.Column(db.Date, nullable=False, default=date.today)
    valor_pago = db.Column(db.Float, nullable=False)
    mes_referencia = db.Column(db.Integer, nullable=False)
    ano_referencia = db.Column(db.Integer, nullable=False)
    observacoes = db.Column(db.Text)

    def __repr__(self):
        return f'<Pagamento {self.cliente.nome} - {self.mes_referencia}/{self.ano_referencia}>'

# --- Helpers de segurança ---
def password_strong_enough(password: str) -> (bool, str):
    """Regra mínima de senha: >=8 chars, maiúscula, minúscula, número, caractere especial."""
    if len(password) < 8:
        return False, "A senha deve ter ao menos 8 caracteres."
    if not re.search(r'[A-Z]', password):
        return False, "A senha deve conter ao menos uma letra maiúscula."
    if not re.search(r'[a-z]', password):
        return False, "A senha deve conter ao menos uma letra minúscula."
    if not re.search(r'\d', password):
        return False, "A senha deve conter ao menos um número."
    if not re.search(r'[^A-Za-z0-9]', password):
        return False, "A senha deve conter ao menos um caractere especial."
    return True, ""

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or 'session_token' not in session:
            flash('Você precisa fazer login para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        # Validar token de sessão contra DB
        usuario = Usuario.query.get(session.get('user_id'))
        if not usuario or usuario.session_token != session.get('session_token') or not usuario.ativo:
            # sessão inválida
            session.clear()
            flash('Sessão inválida. Faça login novamente.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or 'session_token' not in session:
            flash('Você precisa fazer login para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        usuario = Usuario.query.get(session.get('user_id'))
        if not usuario or usuario.session_token != session.get('session_token') or not usuario.is_admin():
            flash('Acesso negado. Esta área é restrita para administradores.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    if 'user_id' in session and 'session_token' in session:
        u = Usuario.query.get(session['user_id'])
        if u and u.session_token == session.get('session_token'):
            return u
    return None

def calcular_status_cliente(cliente):
    """Retorna o status do cliente: 'Em dia', 'Aguardando', 'Em atraso' ou 'Inativo'"""
    from datetime import date
    hoje = date.today()

    if not cliente.ativo:
        return "Inativo"

    # Verifica se o cliente já fez algum pagamento
    tem_pagamento = Pagamento.query.filter_by(cliente_id=cliente.id).first()
    
    # Se nunca pagou nada, está "Aguardando" (cliente novo)
    if not tem_pagamento:
        return "Aguardando"

    # Verifica se pagou o mês atual
    pagou_mes_atual = Pagamento.query.filter_by(
        cliente_id=cliente.id,
        mes_referencia=hoje.month,
        ano_referencia=hoje.year
    ).first()

    if pagou_mes_atual:
        return "Em dia"

    # Calcula a data de vencimento do mês atual
    try:
        import calendar
        ultimo_dia_mes = calendar.monthrange(hoje.year, hoje.month)[1]
        dia_vencimento_mes = min(cliente.dia_vencimento, ultimo_dia_mes)
        vencimento_atual = date(hoje.year, hoje.month, dia_vencimento_mes)
    except:
        vencimento_atual = date(hoje.year, hoje.month, 28)

    # Se já tem histórico de pagamentos mas não pagou este mês
    # e o vencimento já passou, está em atraso
    if hoje > vencimento_atual:
        return "Em atraso"
    
    # Se o vencimento ainda não chegou mas já tem histórico de pagamentos
    # tecnicamente ainda pode pagar no prazo, mas como já é cliente antigo
    # que não pagou, considero em atraso (você pode ajustar essa lógica)
    return "Em atraso"

# --- Rotas de autenticação ---
@app.route('/login', methods=['GET', 'POST'])
@csrf.exempt  # Se você usa forms com token, REMOVA este decorator. Está aqui só para evitar erro se template não tiver token.
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        # rate limit check
        allowed, wait_seconds = check_rate_limit()
        if not allowed:
            flash(f'Tentativas excedidas. Tente novamente em {int(wait_seconds // 60)+1} minutos.', 'error')
            return render_template('login.html')

        username = request.form.get('username', '').strip()
        senha = request.form.get('senha', '')

        if not username or not senha:
            flash('Usuário e senha são obrigatórios.', 'error')
            return render_template('login.html')

        usuario = Usuario.query.filter_by(username=username).first()
        if usuario and usuario.ativo and usuario.check_password(senha):
            # reset rate limiter
            reset_failed_attempts()

            # criar token de sessão e salvar no db
            token = secrets.token_urlsafe(32)
            usuario.session_token = token
            usuario.ultimo_login = datetime.utcnow()
            db.session.commit()

            # Armazenar APENAS user_id e token na sessão
            session.clear()
            session['user_id'] = usuario.id
            session['session_token'] = token

            flash(f'Bem-vindo, {usuario.nome_completo}!', 'success')

            # força troca de senha se necessário
            if usuario.must_reset_password:
                return redirect(url_for('trocar_senha'))

            return redirect(url_for('dashboard'))
        else:
            # registrar tentativa falha
            record_failed_attempt()
            flash('Usuário ou senha inválidos.', 'error')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    usuario = get_current_user()
    nome = usuario.nome_completo if usuario else 'Usuário'
    # invalidar token no banco
    if usuario:
        usuario.session_token = None
        db.session.commit()
    session.clear()
    flash(f'Até logo, {nome}!', 'info')
    return redirect(url_for('login'))

@app.route('/trocar_senha', methods=['GET', 'POST'])
@login_required
def trocar_senha():
    usuario = get_current_user()
    if not usuario:
        flash('Usuário não encontrado.', 'error')
        return redirect(url_for('login'))

    form = TrocarSenhaForm()

    if form.validate_on_submit():
        senha_atual = form.senha_atual.data
        nova_senha = form.nova_senha.data

        if not usuario.check_password(senha_atual):
            flash('Senha atual incorreta.', 'error')
            return render_template('trocar_senha.html', form=form)

        ok, msg = password_strong_enough(nova_senha)
        if not ok:
            flash(msg, 'error')
            return render_template('trocar_senha.html', form=form)

        usuario.set_password(nova_senha)
        usuario.must_reset_password = False
        usuario.session_token = secrets.token_urlsafe(32)
        db.session.commit()

        session['session_token'] = usuario.session_token
        flash('Senha alterada com sucesso!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('trocar_senha.html', form=form)

# --- Gestão de usuários (admin) ---
@app.route('/gerenciar_usuarios')
@admin_required
def gerenciar_usuarios():
    usuarios = Usuario.query.all()
    return render_template(
        'gerenciar_usuarios.html',
        usuarios=usuarios,
        current_user=get_current_user()
    )



@app.route('/criar_usuario', methods=['GET', 'POST'])
@admin_required
def criar_usuario():
    form = CriarUsuarioForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        nome_completo = form.nome_completo.data.strip()
        email = form.email.data.strip()
        senha = form.senha.data
        tipo_permissao = form.tipo_permissao.data

        # Verifica unicidade no backend
        if Usuario.query.filter_by(username=username).first():
            flash('Nome de usuário já existe.', 'error')
            return render_template('criar_usuario.html', form=form)
        if Usuario.query.filter_by(email=email).first():
            flash('E-mail já está em uso.', 'error')
            return render_template('criar_usuario.html', form=form)

        novo_usuario = Usuario(
            username=username,
            nome_completo=nome_completo,
            email=email,
            tipo_permissao=tipo_permissao,
            must_reset_password=False
        )
        novo_usuario.set_password(senha)
        db.session.add(novo_usuario)
        db.session.commit()

        flash(f'Usuário {nome_completo} criado com sucesso!', 'success')
        return redirect(url_for('gerenciar_usuarios'))

    return render_template('criar_usuario.html', form=form)

@app.route('/desativar_usuario/<int:usuario_id>', methods=['POST'])
@admin_required
def desativar_usuario(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    if usuario.id == session['user_id']:
        flash('Você não pode desativar seu próprio usuário.', 'error')
        return redirect(url_for('gerenciar_usuarios'))
    usuario.ativo = False
    usuario.session_token = None
    db.session.commit()
    flash(f'Usuário {usuario.nome_completo} foi desativado.', 'success')
    return redirect(url_for('gerenciar_usuarios'))

@app.route('/ativar_usuario/<int:usuario_id>', methods=['POST'])
@admin_required
def ativar_usuario(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    usuario.ativo = True
    db.session.commit()
    flash(f'Usuário {usuario.nome_completo} foi ativado.', 'success')
    return redirect(url_for('gerenciar_usuarios'))

# Substitua a função cadastrar_cliente() por esta versão:

@app.route('/cadastrar_cliente', methods=['GET', 'POST'])
@login_required
def cadastrar_cliente():
    print("=== FUNÇÃO CADASTRAR_CLIENTE EXECUTADA ===")
    if request.method == 'POST':
        print("=== MÉTODO POST DETECTADO ===")
        
        nome = request.form.get('nome').strip()
        telefone = request.form.get('telefone').strip()
        valor_mensalidade = float(request.form.get('valor_mensalidade'))
        dia_vencimento = int(request.form.get('dia_vencimento'))

        # DEBUG: Mostrar dados recebidos
        print(f"DEBUG - Dados recebidos:")
        print(f"  Nome: '{nome}'")
        print(f"  Telefone original: '{telefone}'")

        # Limpa o telefone removendo formatação para comparação
        telefone_limpo = re.sub(r'\D', '', telefone)
        print(f"  Telefone limpo: '{telefone_limpo}'")
        
        # Validação de telefone
        if len(telefone_limpo) < 10 or len(telefone_limpo) > 11:
            flash('Telefone deve ter entre 10 e 11 dígitos.', 'error')
            return render_template('cadastrar_cliente.html')
        
        # Validação de valor
        if valor_mensalidade < 0 or valor_mensalidade > 999.99:
            flash('O valor da mensalidade deve estar entre R$ 0,00 e R$ 999,99.', 'error')
            return render_template('cadastrar_cliente.html')

        # NOVA VALIDAÇÃO: Buscar TODOS os clientes ativos e comparar telefones
        todos_clientes = Cliente.query.filter_by(ativo=True).all()
        print(f"DEBUG - Total de clientes ativos: {len(todos_clientes)}")
        
        cliente_duplicado = None
        for cliente in todos_clientes:
            # Limpa o telefone do cliente existente
            telefone_cliente_limpo = re.sub(r'\D', '', cliente.telefone)
            print(f"  Comparando: '{telefone_limpo}' com '{telefone_cliente_limpo}' do cliente {cliente.nome}")
            
            if telefone_limpo == telefone_cliente_limpo:
                cliente_duplicado = cliente
                break
        
        if cliente_duplicado:
            print(f"DEBUG - Cliente duplicado encontrado: {cliente_duplicado.nome}")
            flash(f'Já existe um cliente ativo cadastrado com este telefone: {cliente_duplicado.nome}', 'error')
            return render_template('cadastrar_cliente.html')
        else:
            print("DEBUG - Nenhum cliente duplicado encontrado")

        # VALIDAÇÃO por nome (opcional)
        cliente_existente_nome = Cliente.query.filter(
            func.lower(Cliente.nome) == func.lower(nome),
            Cliente.ativo == True
        ).first()
        
        if cliente_existente_nome:
            flash(f'Atenção: Já existe um cliente com nome similar: {cliente_existente_nome.nome}', 'warning')

        print(f"DEBUG - Criando novo cliente...")
        
        # Se passou nas validações, cria o cliente
        novo_cliente = Cliente(
            nome=nome,
            telefone=telefone,
            valor_mensalidade=valor_mensalidade,
            dia_vencimento=dia_vencimento
        )
        db.session.add(novo_cliente)
        db.session.commit()
        
        print(f"DEBUG - Cliente criado com ID: {novo_cliente.id}")
        flash(f'Cliente {nome} cadastrado com sucesso!', 'success')
        return redirect(url_for('listar_clientes'))

    return render_template('cadastrar_cliente.html')

@app.route('/historico_pagamento/<int:cliente_id>')
def historico_pagamento(cliente_id):
    """Exibe o histórico de pagamentos de um cliente."""
    cliente = Cliente.query.get_or_404(cliente_id)
    pagamentos = Pagamento.query.filter_by(cliente_id=cliente_id).order_by(Pagamento.data_pagamento.desc()).all()
    
    return render_template('historico_pagamento.html', cliente=cliente, pagamentos=pagamentos)

# Rota para exibir o formulário de edição
@app.route('/editar_cliente/<int:cliente_id>', methods=['GET'])
def editar_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    return render_template('editar_cliente.html', cliente=cliente)

@app.route('/deletar_cliente/<int:cliente_id>', methods=['POST'])
@login_required
def deletar_cliente(cliente_id):
    """
    Marca um cliente como inativo em vez de deletá-lo.
    Esses clientes poderão ser reativados futuramente.
    """
    cliente = Cliente.query.get_or_404(cliente_id)
    
    if not cliente.ativo:
        flash(f'O cliente {cliente.nome} já está inativo.', 'info')
    else:
        cliente.ativo = False
        db.session.commit()
        flash(f'Cliente {cliente.nome} foi desativado com sucesso!', 'success')
    
    return redirect(url_for('listar_clientes'))

@app.route('/ativar_cliente/<int:cliente_id>', methods=['POST'])
@login_required
def ativar_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    cliente.ativo = True
    db.session.commit()
    flash(f'Cliente {cliente.nome} foi reativado com sucesso!', 'success')
    return redirect(url_for('listar_clientes', status='inativos'))


@app.route('/relatorio_inadimplentes')
def relatorio_inadimplentes():
    """Relatório detalhado de inadimplentes"""
    clientes = Cliente.query.filter_by(ativo=True).all()
    inadimplentes = []
    
    for cliente in clientes:
        meses_atraso, valor_devido = cliente.calcular_meses_atraso()
        
        if meses_atraso > 0:
            dias_atraso = (date.today() - date(date.today().year, date.today().month, cliente.dia_vencimento)).days
            inadimplentes.append({
                'cliente': cliente,
                'meses_atraso': meses_atraso,
                'valor_devido': valor_devido,
                'dias_atraso': max(0, dias_atraso)
            })
    
    inadimplentes.sort(key=lambda x: x['meses_atraso'], reverse=True)
    usuario_atual = get_current_user()
    hoje = date.today()
    
    return render_template('inadimplentes.html', inadimplentes=inadimplentes, hoje=hoje, current_user=usuario_atual)

@app.route('/registrar_pagamento_manual/<int:cliente_id>', methods=['POST'])
@login_required
def registrar_pagamento_manual(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    
    # Pega os dados do formulário
    valor_pago = float(request.form.get('valor_pago'))
    data_pagamento = request.form.get('data_pagamento')
    
    if data_pagamento:
        data_pagamento = datetime.strptime(data_pagamento, '%Y-%m-%d').date()
    else:
        data_pagamento = date.today()
    
    mes_ref = data_pagamento.month
    ano_ref = data_pagamento.year
    
    # Cria o pagamento
    pagamento = Pagamento(
        cliente_id=cliente.id,
        valor_pago=valor_pago,
        data_pagamento=data_pagamento,
        mes_referencia=mes_ref,
        ano_referencia=ano_ref
    )
    
    db.session.add(pagamento)
    db.session.commit()
    
    flash(f'Pagamento registrado para {cliente.nome} com sucesso!', 'success')
    return redirect(url_for('relatorio_inadimplentes'))

@app.route('/atualizar_cliente/<int:cliente_id>', methods=['POST'])
@login_required
def atualizar_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    cliente.nome = request.form.get('nome')
    cliente.telefone = request.form.get('telefone')
    cliente.valor_mensalidade = float(request.form.get('valor_mensalidade'))
    cliente.dia_vencimento = int(request.form.get('dia_vencimento'))
    db.session.commit()
    flash(f'Cliente {cliente.nome} atualizado com sucesso!', 'success')
    return redirect(url_for('listar_clientes'))

@app.route('/')
@login_required
def dashboard():
    usuario_atual = get_current_user()

    # Se for colaborador, redireciona para página de clientes
    if not usuario_atual.is_admin():
        return redirect(url_for('listar_clientes'))

    hoje = date.today()
    meses_pt = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho',
                7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}
    nome_mes = meses_pt.get(hoje.month, 'Mês Desconhecido')

    # Lista apenas clientes ativos para mostrar no dashboard
    clientes = Cliente.query.filter_by(ativo=True).all()
    total_clientes = len(clientes)
    clientes_pagos = []
    clientes_atrasados = []
    valor_total_esperado = 0

    for cliente in clientes:
        valor_total_esperado += cliente.valor_mensalidade

        # Calcula status usando a função centralizada
        status = calcular_status_cliente(cliente)

        if status == "Em dia":
            clientes_pagos.append(cliente)
        elif status == "Em atraso":
            meses_atraso, valor_devido = cliente.calcular_meses_atraso()
            clientes_atrasados.append({
                'cliente': cliente,
                'meses_atraso': meses_atraso,
                'valor_devido': valor_devido
            })
        # "Aguardando" não entra nem em pagos nem em atrasados

    # Calcula o valor recebido considerando todos os pagamentos do mês (clientes ativos ou não)
    valor_recebido = db.session.query(func.sum(Pagamento.valor_pago)).filter(
        Pagamento.mes_referencia == hoje.month,
        Pagamento.ano_referencia == hoje.year
    ).scalar() or 0

    stats = {
        'total_clientes': total_clientes,
        'clientes_pagos': len(clientes_pagos),
        'clientes_atrasados': len(clientes_atrasados),
        'valor_recebido': valor_recebido,
        'valor_esperado': valor_total_esperado,
        'valor_pendente': max(0, valor_total_esperado - valor_recebido),
        'percentual_pagos': round((len(clientes_pagos) / total_clientes * 100) if total_clientes > 0 else 0, 1)
    }

    return render_template('dashboard.html',
                           current_user=usuario_atual,
                           stats=stats,
                           hoje=hoje,
                           nome_mes=nome_mes,
                           clientes_atrasados=clientes_atrasados,
                           clientes_pagos=clientes_pagos)



from flask import render_template, request

@app.route('/todos_clientes')
@login_required
def listar_clientes():
    search_query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', 'todos')  # 'todos', 'Em dia', 'Aguardando', 'Em atraso', 'inativos'

    hoje = date.today()
    clientes_query = Cliente.query

    # Seleciona clientes conforme status_filter
    if status_filter == 'inativos':
        clientes = clientes_query.filter_by(ativo=False).all()
    else:
        clientes = clientes_query.filter_by(ativo=True).all()

    clientes_info = []
    for cliente in clientes:
        # Filtro de busca por nome
        if search_query and search_query.lower() not in cliente.nome.lower():
            continue

        # Último pagamento do cliente
        ultimo_pagamento = Pagamento.query.filter_by(
            cliente_id=cliente.id
        ).order_by(Pagamento.data_pagamento.desc()).first()

        # Status calculado usando a função centralizada
        status = calcular_status_cliente(cliente)

        # Aplica filtro pelo status (exceto "todos" ou "inativos")
        if status_filter not in ['todos', 'inativos'] and status != status_filter:
            continue

        clientes_info.append({
            'cliente': cliente,
            'ultimo_pagamento': ultimo_pagamento,
            'status': status,
            'pagou_mes_atual': status == "Em dia"
        })

    return render_template(
        'listar_clientes.html',
        clientes_info=clientes_info,
        search_query=search_query,
        status_filter=status_filter,
        current_user=get_current_user()
    )




# --- Utilitários de inicialização ---
def criar_usuario_admin_inicial():
    """Cria o primeiro usuário administrador se não existir nenhum, com senha forte gerada."""
    if Usuario.query.count() == 0:
        admin_password = secrets.token_urlsafe(12)  # forte e único
        admin = Usuario(
            username='admin',
            nome_completo='Administrador do Sistema',
            email='admin@academia.com',
            tipo_permissao='admin',
            must_reset_password=True
        )
        admin.set_password(admin_password)
        # gera token de sessão nulo até primeiro login
        admin.session_token = None
        db.session.add(admin)
        db.session.commit()

        # Imprima apenas no console (uma única vez)
        print("🔐 Usuário administrador inicial criado:")
        print("   Usuário: admin")
        print("   Senha temporária (alterar no primeiro login):", admin_password)
        print("   ⚠️  IMPORTANTE: Altere a senha após o primeiro login!")

def inicializar_dados():
    """Gera dados de exemplo"""
    if Cliente.query.count() > 0:
        return

    print("⏳ Gerando clientes de exemplo...")
    clientes = []
    hoje = date.today()

    for _ in range(48):
        nome = fake.name()
        telefone = f"({random.randint(11, 99)}) 9{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"
        valor_mensalidade = round(random.uniform(70.0, 150.0), 2)
        dia_vencimento = random.randint(1, 28)
        data_matricula = hoje - relativedelta(months=random.randint(1, 12))
        cliente = Cliente(
            nome=nome,
            telefone=telefone,
            valor_mensalidade=valor_mensalidade,
            dia_vencimento=dia_vencimento,
            data_matricula=data_matricula
        )
        db.session.add(cliente)
        clientes.append(cliente)

    db.session.commit()

    for cliente in clientes:
        meses_a_pagar = random.sample(range(1, hoje.month + 1), k=random.randint(0, hoje.month))
        for mes in meses_a_pagar:
            if mes != hoje.month:
                db.session.add(Pagamento(
                    cliente_id=cliente.id,
                    valor_pago=cliente.valor_mensalidade,
                    mes_referencia=mes,
                    ano_referencia=hoje.year,
                    data_pagamento=date(hoje.year, mes, random.randint(1, 28))
                ))

    aguardando_vencimento = hoje.day + 1
    if aguardando_vencimento > 28:
        aguardando_vencimento = 1

    aguardando_1 = Cliente(
        nome="Cliente Aguardando 1",
        telefone="(81) 99999-1000",
        valor_mensalidade=95.0,
        dia_vencimento=aguardando_vencimento,
        data_matricula=hoje - relativedelta(months=3)
    )
    db.session.add(aguardando_1)

    aguardando_2 = Cliente(
        nome="Cliente Aguardando 2",
        telefone="(81) 99999-2000",
        valor_mensalidade=105.0,
        dia_vencimento=aguardando_vencimento + 2,
        data_matricula=hoje - relativedelta(months=1)
    )
    db.session.add(aguardando_2)

    db.session.commit()
    print("✅ Dados de exemplo gerados!")

# --- Inicialização do app ---

if __name__ == '__main__':
    print("📦 Iniciando app.py via Docker CMD...")
    with app.app_context():
        db.create_all()
        criar_usuario_admin_inicial()
        

    print("🚀 Sistema da Academia iniciado!")
    print("📱 Acesse: http://localhost:5000")
    
    # Para Docker, precisa bind em todas as interfaces
    print("🚀 Flask prestes a iniciar...")
    app.run(
        host='0.0.0.0',  # Importante para Docker
        port=5000,
        debug=(os.getenv('FLASK_DEBUG', '0') == '1')
    )
