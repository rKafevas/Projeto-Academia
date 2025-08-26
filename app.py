from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import random
import re
import os
from dotenv import load_dotenv
from faker import Faker

# Carrega as variáveis do arquivo .env
load_dotenv()

# Configuração da aplicação
app = Flask(__name__)
app.config['SECRET_KEY'] = 'academia-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///academia.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicialização do banco
db = SQLAlchemy(app)
fake = Faker('pt_BR')

# Modelos do banco de dados
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
    
    def esta_em_atraso(self):
        """Verifica se o cliente está em atraso"""
        hoje = date.today()
        
        pagamento_atual = Pagamento.query.filter_by(
            cliente_id=self.id,
            mes_referencia=hoje.month,
            ano_referencia=hoje.year
        ).first()
        
        if pagamento_atual:
            return False
        
        vencimento = date(hoje.year, hoje.month, self.dia_vencimento)
        return hoje > vencimento
    
    def calcular_meses_atraso(self):
        """Calcula o número de meses em atraso e o valor total devido."""
        hoje = date.today()
        
        ultimo_pagamento = Pagamento.query.filter_by(
            cliente_id=self.id
        ).order_by(Pagamento.data_pagamento.desc()).first()

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

# Rotas da aplicação
@app.route('/')
def dashboard():
    """Página principal com estatísticas"""
    hoje = date.today()
    
    meses_pt = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho',
        7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }
    nome_mes = meses_pt.get(hoje.month, 'Mês Desconhecido')
    
    clientes = Cliente.query.filter_by(ativo=True).all()
    total_clientes = len(clientes)
    
    clientes_pagos = []
    clientes_atrasados = []
    valor_recebido = 0
    valor_total_esperado = 0
    
    for cliente in clientes:
        valor_total_esperado += cliente.valor_mensalidade
        
        pagamento_mes = Pagamento.query.filter_by(
            cliente_id=cliente.id,
            mes_referencia=hoje.month,
            ano_referencia=hoje.year
        ).first()
        
        if pagamento_mes:
            clientes_pagos.append(cliente)
            valor_recebido += pagamento_mes.valor_pago
        elif cliente.esta_em_atraso():
            meses_atraso, valor_devido = cliente.calcular_meses_atraso()
            clientes_atrasados.append({
                'cliente': cliente,
                'meses_atraso': meses_atraso,
                'valor_devido': valor_devido
            })

    stats = {
        'total_clientes': total_clientes,
        'clientes_pagos': len(clientes_pagos),
        'clientes_atrasados': len(clientes_atrasados),
        'valor_recebido': valor_recebido,
        'valor_esperado': valor_total_esperado,
        'valor_pendente': valor_total_esperado - valor_recebido,
        'percentual_pagos': round((len(clientes_pagos) / total_clientes * 100) if total_clientes > 0 else 0, 1)
    }
    
    return render_template('dashboard.html', 
                         stats=stats,
                         hoje=hoje,
                         nome_mes=nome_mes,
                         clientes_atrasados=clientes_atrasados,
                         clientes_pagos=clientes_pagos)


@app.route('/todos_clientes')
def listar_clientes():
    """Lista todos os clientes ativos com informações de status e último pagamento."""
    search_query = request.args.get('q', '').strip()
    
    if search_query:
        # Busca clientes cujo nome contenha o termo de pesquisa
        clientes = Cliente.query.filter(Cliente.ativo==True, Cliente.nome.like(f'%{search_query}%')).all()
    else:
        clientes = Cliente.query.filter_by(ativo=True).all()

    hoje = date.today()
    
    clientes_info = []
    for cliente in clientes:
        ultimo_pagamento = Pagamento.query.filter_by(
            cliente_id=cliente.id
        ).order_by(Pagamento.data_pagamento.desc()).first()
        
        meses_atraso, _ = cliente.calcular_meses_atraso()
        
        status = "Em dia"
        
        # Lógica para determinar o status do cliente
        # Primeiro, verifica se o cliente é novo (matriculado no mês atual)
        if cliente.data_matricula.year == hoje.year and cliente.data_matricula.month == hoje.month:
            status = "Aguardando"
        # Depois, verifica se o cliente tem pagamentos em atraso
        elif meses_atraso > 0:
            status = "Em atraso"
        else:
            # Por fim, verifica o status do mês atual
            pagou_mes_atual = Pagamento.query.filter_by(
                cliente_id=cliente.id,
                mes_referencia=hoje.month,
                ano_referencia=hoje.year
            ).first()
            if not pagou_mes_atual and date(hoje.year, hoje.month, min(cliente.dia_vencimento, 28)) > hoje:
                status = "Aguardando"
            elif not pagou_mes_atual:
                status = "Em atraso"
        
        clientes_info.append({
            'cliente': cliente,
            'ultimo_pagamento': ultimo_pagamento,
            'status': status,
            'pagou_mes_atual': bool(Pagamento.query.filter_by(cliente_id=cliente.id, mes_referencia=hoje.month, ano_referencia=hoje.year).first())
        })
    
    return render_template('listar_clientes.html', clientes_info=clientes_info, search_query=search_query)

@app.route('/cadastrar_cliente', methods=['GET', 'POST'])
def cadastrar_cliente():
    """Cadastra um novo cliente com validação de backend"""
    if request.method == 'POST':
        nome = request.form.get('nome')
        telefone = request.form.get('telefone')
        valor_mensalidade = request.form.get('valor_mensalidade')
        dia_vencimento = request.form.get('dia_vencimento')
        
        if not nome or not telefone or not valor_mensalidade or not dia_vencimento:
            flash('Todos os campos são obrigatórios!', 'error')
            return render_template('cadastrar_cliente.html')

        try:
            valor_mensalidade = float(valor_mensalidade)
            dia_vencimento = int(dia_vencimento)
            if valor_mensalidade <= 0:
                flash('O valor da mensalidade deve ser maior que zero.', 'error')
                return render_template('cadastrar_cliente.html')
            if not 1 <= dia_vencimento <= 31:
                flash('O dia de vencimento deve ser entre 1 e 31.', 'error')
                return render_template('cadastrar_cliente.html')
        except (ValueError, TypeError):
            flash('Valor da mensalidade ou dia de vencimento inválido.', 'error')
            return render_template('cadastrar_cliente.html')
            
        padrao_telefone = r'^\(\d{2}\) \d{4,5}-\d{4}$'
        if not re.match(padrao_telefone, telefone):
            flash('Formato de telefone inválido. Use o formato (XX) XXXXX-XXXX.', 'error')
            return render_template('cadastrar_cliente.html')

        cliente_existente = Cliente.query.filter_by(telefone=telefone).first()
        if cliente_existente:
            flash(f'Já existe um cliente com o telefone {telefone} cadastrado.', 'error')
            return render_template('cadastrar_cliente.html')

        cliente = Cliente(
            nome=nome,
            telefone=telefone,
            valor_mensalidade=valor_mensalidade,
            dia_vencimento=dia_vencimento
        )
        
        db.session.add(cliente)
        db.session.commit()
        
        flash(f'Cliente {nome} cadastrado com sucesso!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('cadastrar_cliente.html')

@app.route('/registrar_pagamento_manual/<int:cliente_id>', methods=['POST'])
def registrar_pagamento_manual(cliente_id):
    """Registra pagamento manual de um cliente com data e valor informados."""
    cliente = Cliente.query.get_or_404(cliente_id)
    try:
        data_pagamento_str = request.form['data_pagamento']
        valor_pago = float(request.form['valor_pago'])
        
        data_pagamento = datetime.strptime(data_pagamento_str, '%Y-%m-%d').date()
        
        mes_referencia = data_pagamento.month
        ano_referencia = data_pagamento.year
        
        pagamento_existente = Pagamento.query.filter_by(
            cliente_id=cliente_id,
            mes_referencia=mes_referencia,
            ano_referencia=ano_referencia
        ).first()

        if pagamento_existente:
            flash(f'Já existe um pagamento registrado para {cliente.nome} no mês {mes_referencia}/{ano_referencia}!', 'warning')
        else:
            pagamento = Pagamento(
                cliente_id=cliente_id,
                data_pagamento=data_pagamento,
                valor_pago=valor_pago,
                mes_referencia=mes_referencia,
                ano_referencia=ano_referencia
            )
            db.session.add(pagamento)
            db.session.commit()
            flash(f'Pagamento de {cliente.nome} registrado com sucesso!', 'success')
    
    except (KeyError, ValueError, TypeError) as e:
        flash('Erro ao registrar o pagamento. Verifique os dados e tente novamente.', 'error')

    return redirect(url_for('dashboard'))

@app.route('/deletar_cliente/<int:cliente_id>', methods=['POST'])
def deletar_cliente(cliente_id):
    """Marca um cliente como inativo em vez de deletá-lo."""
    cliente = Cliente.query.get_or_404(cliente_id)
    cliente.ativo = False
    db.session.commit()
    flash(f'Cliente {cliente.nome} foi desativado com sucesso!', 'success')
    return redirect(url_for('listar_clientes'))

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
    
    hoje = date.today()
    
    return render_template('inadimplentes.html', inadimplentes=inadimplentes, hoje=hoje)

# Rota para exibir o formulário de edição
@app.route('/editar_cliente/<int:cliente_id>', methods=['GET'])
def editar_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    return render_template('editar_cliente.html', cliente=cliente)

# Rota para processar a atualização do cliente
@app.route('/atualizar_cliente/<int:cliente_id>', methods=['POST'])
def atualizar_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    try:
        nome = request.form['nome']
        telefone = request.form['telefone']
        valor_mensalidade = float(request.form['valor_mensalidade'])
        dia_vencimento = int(request.form['dia_vencimento'])

        if not nome or not telefone or valor_mensalidade <= 0 or not 1 <= dia_vencimento <= 31:
            flash('Dados inválidos. Verifique os campos e tente novamente.', 'error')
            return redirect(url_for('editar_cliente', cliente_id=cliente.id))

        cliente.nome = nome
        cliente.telefone = telefone
        cliente.valor_mensalidade = valor_mensalidade
        cliente.dia_vencimento = dia_vencimento
        
        db.session.commit()
        flash('Dados do cliente atualizados com sucesso!', 'success')
        return redirect(url_for('listar_clientes'))
    
    except (KeyError, ValueError, TypeError):
        flash('Erro ao processar a atualização. Verifique os dados e tente novamente.', 'error')
        return redirect(url_for('editar_cliente', cliente_id=cliente.id))

@app.route('/api/stats')
def api_stats():
    """API para estatísticas (para uso futuro com gráficos)"""
    hoje = date.today()
    clientes = Cliente.query.filter_by(ativo=True).all()
    
    pagos = 0
    atrasados = 0
    
    for cliente in clientes:
        pagamento = Pagamento.query.filter_by(
            cliente_id=cliente.id,
            mes_referencia=hoje.month,
            ano_referencia=hoje.year
        ).first()
        
        if pagamento:
            pagos += 1
        
        meses_atraso, _ = cliente.calcular_meses_atraso()
        if meses_atraso > 0:
            atrasados += 1
    
    return jsonify({
        'pagos': pagos,
        'atrasados': atrasados,
        'total': len(clientes)
    })

@app.route('/historico_pagamento/<int:cliente_id>')
def historico_pagamento(cliente_id):
    """Exibe o histórico de pagamentos de um cliente."""
    cliente = Cliente.query.get_or_404(cliente_id)
    pagamentos = Pagamento.query.filter_by(cliente_id=cliente_id).order_by(Pagamento.data_pagamento.desc()).all()
    
    return render_template('historico_pagamento.html', cliente=cliente, pagamentos=pagamentos)

def inicializar_dados():
    """Cria 50 clientes com dados de exemplo, garantindo status variados."""
    if Cliente.query.count() > 0:
        return
        
    print("⏳ Gerando 50 clientes de exemplo e seus pagamentos...")

    clientes = []
    hoje = date.today()

    # Cria clientes "Em dia" e "Em atraso"
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
    
    # Salva todos os clientes de uma vez para que eles tenham um ID
    db.session.commit()

    # Agora, adiciona os pagamentos usando o ID que foi gerado
    for cliente in clientes:
        # Adiciona pagamentos para alguns, criando status "Em dia" e "Em atraso"
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
    
    # Cria clientes "Aguardando"
    aguardando_vencimento = hoje.day + 1
    if aguardando_vencimento > 28: aguardando_vencimento = 1
    
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
    
    print("✅ 50 clientes de exemplo gerados e salvos!")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Se você quiser reiniciar o banco de dados e os dados de exemplo, descomente as linhas abaixo
        # db.drop_all()
        # db.create_all()
        inicializar_dados()
    
    print("🚀 Sistema da Academia iniciado!")
    print("📱 Acesse: http://localhost:5000")
    app.run(debug=True)