from flask import Blueprint, render_template, redirect, url_for, request, flash, session, jsonify, send_file
from database.models import Usuario, Despesa, Receita, Lembrete, CategoriaPersonalizada, Membro, TextProcessor, MetaFinanceira, Divida, Orcamento, Notificacao
from functools import wraps
import os
import sqlite3
from datetime import datetime, timedelta
import json
from werkzeug.utils import secure_filename
import traceback
from config import Config

# Diretório para salvar os arquivos enviados
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Criação do blueprint
web_bp = Blueprint('web', __name__)

# Middleware para verificar login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('web.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Middleware para verificar plano
def plano_required(planos_permitidos):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Verificar se o usuário está logado
            if 'usuario_id' not in session:
                return redirect(url_for('web.login', next=request.url))
            
            # Verificar se o plano do usuário é permitido
            from config import Config
            usuario_model = Usuario(Config.DATABASE)
            usuario = usuario_model.buscar_por_id(session['usuario_id'])
            
            if usuario and usuario.get('plano') in planos_permitidos:
                return f(*args, **kwargs)
            else:
                flash(f'Esta funcionalidade está disponível apenas para os planos: {", ".join(planos_permitidos)}', 'error')
                return redirect(url_for('web.planos'))
                
        return decorated_function
    return decorator

@web_bp.route('/perfil-empresarial')
@login_required
@plano_required(['familia', 'empresarial'])
def perfil_empresarial():
    # implementação
    pass

# Rota inicial
@web_bp.route('/')
def index():
    """Página inicial do DespeZap"""
    from config import Config
    
    # Verifica se o usuário está logado
    if 'usuario_id' in session:
        return redirect(url_for('web.dashboard'))
    
    # Dados para a página inicial
    whatsapp_code = Config.WHATSAPP_JOIN_CODE
    whatsapp_number = Config.WHATSAPP_NUMBER
    app_name = Config.APP_NAME
    
    return render_template(
        'index.html', 
        app_name=app_name,
        whatsapp_code=whatsapp_code,
        whatsapp_number=whatsapp_number
    )

# Rota do dashboard
@web_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard do usuário"""
    from config import Config
    
    usuario_id = session.get('usuario_id')
    
    # Busca dados do usuário
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    # Busca lembretes próximos
    lembrete_model = Lembrete(Config.DATABASE)
    lembretes = lembrete_model.buscar(
        usuario_id=usuario_id,
        concluido=0
    )
    # Ordena por data e pega os 3 próximos
    if lembretes:
        from datetime import datetime
        lembretes = sorted(lembretes, key=lambda x: x['data'])[:3]
    
    # Busca orçamentos
    orcamento_model = Orcamento(Config.DATABASE)
    orcamentos = orcamento_model.buscar(
        usuario_id=usuario_id,
        tipo_perfil='pessoal'
    )
    
    # Adiciona gastos atuais para orçamentos
    for orcamento in orcamentos:
        try:
            orcamento['gasto_atual'] = orcamento_model.calcular_gasto_atual(
                orcamento_id=orcamento['id']
            )
            # Calcula percentual
            if orcamento['valor_limite'] > 0:
                orcamento['percentual'] = (orcamento['gasto_atual'] / orcamento['valor_limite']) * 100
            else:
                orcamento['percentual'] = 0
        except:
            orcamento['gasto_atual'] = 0
            orcamento['percentual'] = 0
    
    # Busca metas financeiras
    meta_model = MetaFinanceira(Config.DATABASE)
    metas = meta_model.buscar(
        usuario_id=usuario_id,
        tipo_perfil='pessoal'
    )
    
    # Calcula percentual das metas
    for meta in metas:
        if meta['valor_alvo'] > 0:
            meta['percentual'] = (meta['valor_atual'] / meta['valor_alvo']) * 100
        else:
            meta['percentual'] = 0
    
    # Busca dívidas
    divida_model = Divida(Config.DATABASE)
    dividas = divida_model.buscar(
        usuario_id=usuario_id,
        tipo_perfil='pessoal'
    )
    
    # Calcula percentual pago das dívidas
    for divida in dividas:
        if divida['valor_total'] > 0:
            divida['percentual_pago'] = (divida['valor_pago'] / divida['valor_total']) * 100
        else:
            divida['percentual_pago'] = 0
    
    # Busca últimas transações
    despesa_model = Despesa(Config.DATABASE)
    receita_model = Receita(Config.DATABASE)
    
    # Define período (últimos 30 dias)
    from datetime import datetime, timedelta
    hoje = datetime.now()
    data_inicio = (hoje - timedelta(days=30)).strftime("%Y-%m-%d")
    data_fim = hoje.strftime("%Y-%m-%d")
    
    # Busca despesas e receitas recentes
    despesas_recentes = despesa_model.buscar(
        usuario_id=usuario_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        limit=10
    )
    
    receitas_recentes = receita_model.buscar(
        usuario_id=usuario_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        limit=10
    )
    
    # Combina e ordena transações por data
    transacoes = []
    
    for despesa in despesas_recentes:
        transacoes.append({
            'id': despesa['id'],
            'tipo': 'despesa',
            'valor': despesa['valor'],
            'descricao': despesa['descricao'],
            'categoria': despesa['categoria'],
            'data': despesa['data'],
            'data_criacao': despesa['data_criacao']
        })
    
    for receita in receitas_recentes:
        transacoes.append({
            'id': receita['id'],
            'tipo': 'receita',
            'valor': receita['valor'],
            'descricao': receita['descricao'],
            'categoria': receita['categoria'],
            'data': receita['data'],
            'data_criacao': receita['data_criacao']
        })
    
    # Ordena por data de criação (mais recentes primeiro)
    transacoes = sorted(transacoes, key=lambda x: x['data_criacao'], reverse=True)[:10]
    
    # Calcula totais do mês atual
    data_inicio_mes = f"{hoje.year}-{hoje.month:02d}-01"
    
    total_despesas_mes = despesa_model.total_periodo(
        usuario_id=usuario_id,
        data_inicio=data_inicio_mes,
        data_fim=data_fim,
        tipo_perfil='pessoal'
    )
    
    total_receitas_mes = receita_model.total_periodo(
        usuario_id=usuario_id,
        data_inicio=data_inicio_mes,
        data_fim=data_fim,
        tipo_perfil='pessoal'
    )
    
    saldo_mes = total_receitas_mes - total_despesas_mes
    
    # Determina quais funcionalidades o usuário pode acessar com base no plano
    plano = usuario.get('plano', 'gratuito')
    
    # Acesso a perfil empresarial depende do plano
    pode_acesso_empresarial = plano in ['familia', 'empresarial']
    
    return render_template(
        'dashboard.html',
        app_name=Config.APP_NAME,
        usuario=usuario,
        lembretes=lembretes,
        orcamentos=orcamentos,
        metas=metas,
        dividas=dividas,
        transacoes=transacoes,
        total_despesas_mes=total_despesas_mes,
        total_receitas_mes=total_receitas_mes,
        saldo_mes=saldo_mes,
        plano=plano,
        pode_acesso_empresarial=pode_acesso_empresarial
    )
# Rota para recuperar senha (stub para corrigir o erro de url_for)
@web_bp.route('/recuperar_senha', methods=['GET', 'POST'])
def recuperar_senha():
    """Página de recuperação de senha"""
    from config import Config
    
    if request.method == 'POST':
        email = request.form.get('email')
        
        if not email:
            flash('Por favor, informe seu email.', 'error')
            return render_template('recuperar_senha.html', app_name=Config.APP_NAME)
        
        # Verifica se o email existe
        usuario_model = Usuario(Config.DATABASE)
        usuario = usuario_model.buscar_por_email(email)
        
        if not usuario:
            # Não informamos ao usuário se o email existe ou não por questões de segurança
            flash('Se este email estiver cadastrado, enviaremos instruções para recuperar sua senha.', 'success')
            return render_template('recuperar_senha.html', app_name=Config.APP_NAME)
        
        # Aqui você implementaria o envio de email com link para recuperação
        # Para simplificar, apenas exibimos uma mensagem de sucesso
        
        flash('Enviamos instruções para recuperar sua senha. Por favor, verifique seu email.', 'success')
        return render_template('recuperar_senha.html', app_name=Config.APP_NAME)
    
    return render_template('recuperar_senha.html', app_name=Config.APP_NAME)

# Rotas de autenticação
@web_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    from config import Config
    
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        
        if not email or not senha:
            flash('Por favor, preencha todos os campos.', 'error')
            return render_template('login.html', app_name=Config.APP_NAME)
        
        # Valida as credenciais
        usuario_model = Usuario(Config.DATABASE)
        usuario_id = usuario_model.validar_credenciais(email, senha)
        
        if usuario_id:
            # Registra o acesso e cria uma sessão
            usuario_model.registrar_acesso(usuario_id)
            session['usuario_id'] = usuario_id
            
            # Redireciona para o dashboard
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):  # Evita redirecionamento para sites externos
                return redirect(next_page)
            return redirect(url_for('web.dashboard'))
        else:
            flash('Email ou senha incorretos.', 'error')
    
    # Se já estiver logado, redireciona para o dashboard
    if 'usuario_id' in session:
        return redirect(url_for('web.dashboard'))
    
    return render_template('login.html', app_name=Config.APP_NAME)

@web_bp.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    """Página de cadastro"""
    from config import Config
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        celular = request.form.get('celular')
        senha = request.form.get('senha')
        confirma_senha = request.form.get('confirma_senha')
        origem = request.form.get('origem')
        cupom = request.form.get('cupom')
        
        # Validações
        if not nome or not email or not celular or not senha:
            flash('Por favor, preencha todos os campos obrigatórios.', 'error')
            return render_template('cadastro.html', 
                app_name=Config.APP_NAME,
                nome=nome, 
                email=email, 
                celular=celular,
                origem=origem,
                cupom=cupom
            )
        
        if senha != confirma_senha:
            flash('As senhas não coincidem.', 'error')
            return render_template('cadastro.html', 
                app_name=Config.APP_NAME,
                nome=nome, 
                email=email, 
                celular=celular,
                origem=origem,
                cupom=cupom
            )
        
        # Verifica se o email já existe
        usuario_model = Usuario(Config.DATABASE)
        if usuario_model.buscar_por_email(email):
            flash('Este email já está cadastrado.', 'error')
            return render_template('cadastro.html', 
                app_name=Config.APP_NAME,
                nome=nome, 
                celular=celular,
                origem=origem,
                cupom=cupom
            )
        
        # Formata o número de celular (remove caracteres não numéricos)
        celular = ''.join(filter(str.isdigit, celular))
        if celular.startswith('55') and len(celular) > 12:
            # Se já começa com 55, mantém apenas os dígitos
            celular = celular
        else:
            # Adiciona o código do país Brasil (55) se não estiver presente
            celular = '55' + celular if not celular.startswith('55') else celular
        
        # Verifica se o celular já existe
        if usuario_model.buscar_por_celular(celular):
            flash('Este número de celular já está cadastrado.', 'error')
            return render_template('cadastro.html', 
                app_name=Config.APP_NAME,
                nome=nome, 
                email=email,
                origem=origem,
                cupom=cupom
            )
        
        # Cria o usuário
        # Em um sistema real, a senha seria armazenada com hash
        usuario_id = usuario_model.criar(celular, nome, email, senha)
        
        if usuario_id:
            try:
                conn = sqlite3.connect(Config.DATABASE)
                cursor = conn.cursor()
                
                # Registra a origem (referral)
                if origem:
                    data_registro = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute(
                        "INSERT INTO usuario_referral (usuario_id, origem, data_registro) VALUES (?, ?, ?)",
                        (usuario_id, origem, data_registro)
                    )
                
                # Cria categorias padrão para o usuário
                categorias_padrao = [
                    ('Alimentação', 'despesa', '#FF6B6B', 'bi-shop'),
                    ('Transporte', 'despesa', '#4ECDC4', 'bi-bus-front'),
                    ('Moradia', 'despesa', '#45B7D1', 'bi-house'),
                    ('Saúde', 'despesa', '#96CEB4', 'bi-heart-pulse'),
                    ('Lazer', 'despesa', '#FFEAA7', 'bi-camera'),
                    ('Educação', 'despesa', '#DDA0DD', 'bi-book'),
                    ('Roupas', 'despesa', '#F39C12', 'bi-bag'),
                    ('Outros Gastos', 'despesa', '#95A5A6', 'bi-three-dots'),
                    ('Salário', 'receita', '#27AE60', 'bi-briefcase'),
                    ('Freelance', 'receita', '#3498DB', 'bi-laptop'),
                    ('Investimentos', 'receita', '#9B59B6', 'bi-graph-up-arrow'),
                    ('Outros Ganhos', 'receita', '#1ABC9C', 'bi-plus-circle')
                ]
                
                for nome_cat, tipo, cor, icone in categorias_padrao:
                    cursor.execute("""
                        INSERT INTO categorias (usuario_id, nome, tipo, cor, icone)
                        VALUES (?, ?, ?, ?, ?)
                    """, (usuario_id, nome_cat, tipo, cor, icone))
                
                # Atualiza a coluna origem na tabela usuarios
                cursor.execute(
                    "UPDATE usuarios SET origem = ? WHERE id = ?",
                    (origem, usuario_id)
                )
                
                conn.commit()
                conn.close()
                
                # Aplica cupom se fornecido
                if cupom and hasattr(Config, 'APLICAR_CUPOM_FUNC'):
                    # Se houver uma função para aplicar cupom configurada
                    resultado = Config.APLICAR_CUPOM_FUNC(cupom, usuario_id)
                    if resultado.get('sucesso'):
                        flash(resultado.get('mensagem', 'Cupom aplicado com sucesso!'), 'success')
                    else:
                        flash(resultado.get('mensagem', 'Erro ao aplicar cupom.'), 'error')
                
                # Cria a sessão e redireciona para o dashboard
                session['usuario_id'] = usuario_id
                flash('Conta criada com sucesso! Bem-vindo ao Despezap!', 'success')
                return redirect(url_for('web.dashboard'))
                
            except Exception as e:
                flash(f'Erro ao configurar sua conta: {str(e)}', 'error')
                # Mesmo com erro nas configurações extras, o usuário foi criado
                # então vamos fazer login para evitar problemas
                session['usuario_id'] = usuario_id
                return redirect(url_for('web.dashboard'))
        else:
            flash('Erro ao criar usuário. Tente novamente.', 'error')
    
    # Se já estiver logado, redireciona para o dashboard
    if 'usuario_id' in session:
        return redirect(url_for('web.dashboard'))
    
    return render_template('cadastro.html', app_name=Config.APP_NAME)

@web_bp.route('/logout')
def logout():
    """Logout do usuário"""
    session.pop('usuario_id', None)
    return redirect(url_for('web.index'))

# Rota de perfil
@web_bp.route('/perfil', methods=['GET'])
@login_required
def perfil():
    """Página de perfil do usuário"""
    from config import Config
    
    usuario_id = session.get('usuario_id')
    
    # Busca dados do usuário
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    if not usuario:
        flash('Usuário não encontrado.', 'error')
        return redirect(url_for('web.logout'))
    
    # Formata a data de criação
    if usuario.get('data_criacao'):
        data_criacao = datetime.strptime(usuario['data_criacao'], "%Y-%m-%d %H:%M:%S")
        usuario['data_criacao'] = data_criacao.strftime("%d/%m/%Y")
    
    return render_template(
        'perfil.html',
        app_name=Config.APP_NAME,
        usuario=usuario
    )

@web_bp.route('/atualizar_perfil', methods=['POST'])
@login_required
def atualizar_perfil():
    """Atualização de dados do perfil"""
    from config import Config
    
    usuario_id = session.get('usuario_id')
    
    # Obtém os dados do formulário
    nome = request.form.get('nome')
    email = request.form.get('email')
    renda = request.form.get('renda')
    
    # Validações básicas
    if not nome or not email:
        flash('Por favor, preencha todos os campos obrigatórios.', 'error')
        return redirect(url_for('web.perfil'))
    
    # Converte renda para float se fornecida
    if renda:
        try:
            renda = float(renda)
        except ValueError:
            flash('Valor de renda inválido.', 'error')
            return redirect(url_for('web.perfil'))
    else:
        renda = None
    
    # Verifica se o email já está em uso por outro usuário
    usuario_model = Usuario(Config.DATABASE)
    usuario_email = usuario_model.buscar_por_email(email)
    
    if usuario_email and usuario_email['id'] != usuario_id:
        flash('Este email já está sendo usado por outro usuário.', 'error')
        return redirect(url_for('web.perfil'))
    
    # Atualiza os dados do usuário
    usuario_model.atualizar(usuario_id, nome=nome, email=email, renda=renda)
    
    flash('Perfil atualizado com sucesso!', 'success')
    return redirect(url_for('web.perfil'))

@web_bp.route('/alterar_senha', methods=['POST'])
@login_required
def alterar_senha():
    """Alteração de senha do usuário"""
    from config import Config
    
    usuario_id = session.get('usuario_id')
    
    # Obtém os dados do formulário
    senha_atual = request.form.get('senha_atual')
    nova_senha = request.form.get('nova_senha')
    confirma_senha = request.form.get('confirma_senha')
    
    # Validações básicas
    if not senha_atual or not nova_senha or not confirma_senha:
        flash('Por favor, preencha todos os campos.', 'error')
        return redirect(url_for('web.perfil'))
    
    if nova_senha != confirma_senha:
        flash('A nova senha e a confirmação não coincidem.', 'error')
        return redirect(url_for('web.perfil'))
    
    # Verifica se a senha atual está correta
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    if not usuario or usuario['senha'] != senha_atual:
        flash('Senha atual incorreta.', 'error')
        return redirect(url_for('web.perfil'))
    
    # Atualiza a senha
    usuario_model.atualizar(usuario_id, senha=nova_senha)
    
    flash('Senha alterada com sucesso!', 'success')
    return redirect(url_for('web.perfil'))

@web_bp.route('/excluir_conta', methods=['POST'])
@login_required
def excluir_conta():
    """Exclusão da conta do usuário"""
    from config import Config
    
    usuario_id = session.get('usuario_id')
    
    # Exclui o usuário
    usuario_model = Usuario(Config.DATABASE)
    
    # Aqui você implementaria a lógica para excluir o usuário e seus dados
    # Exemplo: usuario_model.excluir(usuario_id)
    
    # Encerra a sessão
    session.pop('usuario_id', None)
    
    flash('Sua conta foi excluída com sucesso.', 'success')
    return redirect(url_for('web.index'))

# Rotas de assinatura
@web_bp.route('/planos')
def planos():
    """Página de planos de assinatura"""
    from config import Config
    
    # Se o usuário estiver logado, obtém o plano atual
    plano_atual = None
    if 'usuario_id' in session:
        usuario_model = Usuario(Config.DATABASE)
        usuario = usuario_model.buscar_por_id(session['usuario_id'])
        if usuario:
            plano_atual = usuario.get('plano', 'gratuito')
    
    # Planos novos, substituindo os da Config para nova estrutura
    plano_gratuito = {
        'nome': 'Gratuito',
        'preco': 0,
        'limite_transacoes': 3000,
        'dashboard': 'básico',
        'categorias': 'limitadas (8)',
        'usuarios': 1,
        'exportacao_dados': False,
        'relatorios_detalhados': False
    }

    plano_premium = {
        'nome': 'Premium',
        'preco': 29.90,
        'transacoes': 'ilimitadas',
        'dashboard': 'completo',
        'categorias': 'personalizadas',
        'usuarios': 3,
        'exportacao_dados': 'CSV',
        'relatorios_detalhados': True
    }
    
    plano_familia = {
        'nome': 'Família',
        'preco': 32.90,
        'transacoes': 'ilimitadas',
        'dashboard': 'completo',
        'categorias': 'personalizadas',
        'usuarios': 5,
        'exportacao_dados': 'CSV/Excel',
        'perfil_empresarial': True,
        'grupos': 'familiares ilimitados',
        'integracao_google': True
    }
    
    plano_empresarial = {
        'nome': 'Empresarial',
        'preco': 39.90,
        'transacoes': 'ilimitadas',
        'dashboard': 'completo',
        'categorias': 'personalizadas',
        'usuarios': 'ilimitados',
        'exportacao_dados': 'todos os formatos',
        'perfil_empresarial': True,
        'grupos': 'ilimitados',
        'api_integracao': True,
        'suporte': 'prioritário'
    }
    
    return render_template(
        'planos.html',
        app_name=Config.APP_NAME,
        plano_gratuito=plano_gratuito,
        plano_premium=plano_premium,
        plano_familia=plano_familia,
        plano_empresarial=plano_empresarial,
        plano_atual=plano_atual
    )

@web_bp.route('/assinatura/<plano>', methods=['GET', 'POST'])
@login_required
def assinatura(plano):
    """Página de pagamento da assinatura"""
    from config import Config
    
    # Verifica se o plano é válido
    planos_validos = ['gratuito', 'premium', 'familia', 'empresarial']
    if plano not in planos_validos:
        flash('Plano inválido.', 'error')
        return redirect(url_for('web.planos'))
    
    # Obtém dados do usuário
    usuario_id = session.get('usuario_id')
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    # Se o usuário já está no plano selecionado
    if usuario and usuario.get('plano') == plano:
        flash(f'Você já está no plano {plano.capitalize()}.', 'info')
        return redirect(url_for('web.perfil'))
    
    # Mapeia os planos com seus preços
    planos_precos = {
        'premium': 29.90,
        'familia': 32.90,
        'empresarial': 39.90
    }
    
    # Processa o formulário de assinatura se for POST
    if request.method == 'POST':
        # Atualiza o plano do usuário
        usuario_model.atualizar(usuario_id, plano=plano)
        
        # Se for um plano pago, registra a assinatura
        if plano != 'gratuito':
            # Dados do pagamento (em um sistema real, seria integrado com um gateway de pagamento)
            payment_method = request.form.get('payment_method', 'credit_card')
            period = request.form.get('period', 'monthly')
            
            # Calcula o valor e data de vencimento
            valor = planos_precos.get(plano, 0)
            if period == 'yearly':
                # Desconto de 20% para pagamento anual
                valor = valor * 12 * 0.8
            
            # Período da assinatura
            data_inicio = datetime.now().strftime("%Y-%m-%d")
            if period == 'monthly':
                data_vencimento = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            else:  # yearly
                data_vencimento = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
            
            # Aqui você registraria a assinatura no seu banco de dados
            # Exemplo: assinatura_model.criar(usuario_id, plano, data_inicio, data_vencimento, valor, payment_method)
            
            # Em um sistema real, você processaria o pagamento com um gateway como Stripe, PagSeguro, etc.
        
        # Mensagem de sucesso
        if plano == 'gratuito':
            flash('Seu plano foi atualizado para Gratuito.', 'success')
        else:
            flash(f'Sua assinatura {plano.capitalize()} foi ativada com sucesso!', 'success')
        
        return redirect(url_for('web.dashboard'))
    
    # Renderiza a página de assinatura
    return render_template(
        'assinatura.html',
        app_name=Config.APP_NAME,
        plano=plano,
        preco=planos_precos.get(plano, 0)
    )

@web_bp.route('/cancelar_assinatura', methods=['POST'])
@login_required
def cancelar_assinatura():
    """Cancelamento de assinatura"""
    from config import Config
    
    usuario_id = session.get('usuario_id')
    
    # Cancela a assinatura
    usuario_model = Usuario(Config.DATABASE)
    # Como adicionamos o método em um comentário na classe Usuario, vamos usar a atualização direta aqui 
    usuario_model.atualizar(usuario_id, plano='gratuito')
    
    flash('Sua assinatura foi cancelada com sucesso. Seu plano será alterado para Gratuito no próximo ciclo de faturamento.', 'success')
    
    return redirect(url_for('web.perfil'))


# Rotas para gerenciamento de lembretes
@web_bp.route('/lembretes')
@login_required
def lembretes():
    """Página de lembretes"""
    from config import Config
    
    usuario_id = session.get('usuario_id')
    
    # Cria instância do modelo de usuário e busca dados do usuário logado
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    # Cria instância do modelo de lembretes
    lembrete_model = Lembrete(Config.DATABASE)
    
    # Busca os lembretes ativos do usuário
    lembretes_pessoais = lembrete_model.buscar(
        usuario_id=usuario_id,
        tipo_perfil='pessoal',
        concluido=0
    )
    
    lembretes_empresariais = lembrete_model.buscar(
        usuario_id=usuario_id,
        tipo_perfil='empresarial',
        concluido=0
    )
    
    return render_template(
        'lembretes.html',
        app_name=Config.APP_NAME,
        usuario=usuario,
        lembretes_pessoais=lembretes_pessoais,
        lembretes_empresariais=lembretes_empresariais
    )

@web_bp.route('/lembretes/adicionar', methods=['POST'])
@login_required
def adicionar_lembrete():
    """Adicionar um novo lembrete"""
    from config import Config
    
    usuario_id = session.get('usuario_id')
    
    if request.method == 'POST':
        # Obtém os dados do formulário
        titulo = request.form.get('titulo')
        data = request.form.get('data')
        valor = request.form.get('valor', '')
        descricao = request.form.get('descricao', '')
        notificacao = request.form.get('notificacao', 0)
        recorrente = request.form.get('recorrente', '') == 'on'
        periodicidade = request.form.get('periodicidade') if recorrente else None
        tipo_perfil = request.form.get('tipo_perfil', 'pessoal')
        
        # Validações básicas
        if not titulo or not data:
            flash('Por favor, preencha os campos obrigatórios.', 'error')
            return redirect(url_for('web.lembretes'))
        
        # Converte o valor para float se fornecido
        if valor:
            try:
                valor = float(valor.replace(',', '.'))
            except ValueError:
                flash('Valor inválido.', 'error')
                return redirect(url_for('web.lembretes'))
        else:
            valor = None
        
        # Cria o lembrete
        lembrete_model = Lembrete(Config.DATABASE)
        lembrete_model.criar(
            usuario_id=usuario_id,
            titulo=titulo,
            data=data,
            notificacao=notificacao,
            descricao=descricao,
            valor=valor,
            recorrente=1 if recorrente else 0,
            periodicidade=periodicidade,
            tipo_perfil=tipo_perfil
        )
        
        flash('Lembrete adicionado com sucesso!', 'success')
        
    return redirect(url_for('web.lembretes'))

@web_bp.route('/lembretes/concluir/<int:lembrete_id>', methods=['POST'])
@login_required
def concluir_lembrete(lembrete_id):
    """Marcar um lembrete como concluído"""
    from config import Config
    
    usuario_id = session.get('usuario_id')
    
    # Verifica se o lembrete pertence ao usuário
    lembrete_model = Lembrete(Config.DATABASE)
    lembrete = lembrete_model.buscar_por_id(lembrete_id)
    
    if not lembrete or lembrete.get('usuario_id') != usuario_id:
        flash('Lembrete não encontrado ou acesso negado.', 'error')
        return redirect(url_for('web.lembretes'))
    
    # Marca como concluído
    lembrete_model.marcar_como_concluido(lembrete_id)
    
    # Se for recorrente, cria a próxima ocorrência
    if lembrete.get('recorrente'):
        lembrete_model.criar_recorrencia(lembrete_id)
    
    flash('Lembrete marcado como concluído!', 'success')
    
    return redirect(url_for('web.lembretes'))

@web_bp.route('/lembretes/excluir/<int:lembrete_id>', methods=['POST'])
@login_required
def excluir_lembrete(lembrete_id):
    """Excluir um lembrete"""
    from config import Config
    
    usuario_id = session.get('usuario_id')
    
    # Verifica se o lembrete pertence ao usuário
    lembrete_model = Lembrete(Config.DATABASE)
    lembrete = lembrete_model.buscar_por_id(lembrete_id)
    
    if not lembrete or lembrete.get('usuario_id') != usuario_id:
        flash('Lembrete não encontrado ou acesso negado.', 'error')
        return redirect(url_for('web.lembretes'))
    
    # Exclui o lembrete
    lembrete_model.excluir(lembrete_id)
    
    flash('Lembrete excluído com sucesso!', 'success')
    
    return redirect(url_for('web.lembretes'))

@web_bp.route('/sincronizar_agenda', methods=['POST'])
@login_required
def sincronizar_agenda():
    """Sincroniza os lembretes com o Google Calendar"""
    from config import Config
    
    # Mensagem temporária até a implementação completa
    flash('Funcionalidade de sincronização com Google Calendar será implementada em breve.', 'info')
    
    # Redireciona de volta para a página de lembretes
    return redirect(url_for('web.lembretes'))

@web_bp.route('/orcamentos')
@login_required
def orcamentos():
    """Página de gerenciamento de orçamentos"""
    from config import Config
    
    usuario_id = session.get('usuario_id')
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    return render_template(
        'orcamentos.html',
        app_name=Config.APP_NAME,
        usuario=usuario,
        plano=usuario.get('plano', 'gratuito')
    )

@web_bp.route('/orcamentos/adicionar', methods=['POST'])
@login_required
def adicionar_orcamento():
    """Adicionar um novo orçamento"""
    from config import Config
    
    usuario_id = session.get('usuario_id')
    
    # Obtém dados do formulário e cria o orçamento
    # ...
    
    return redirect(url_for('web.orcamentos'))

@web_bp.route('/metas')
@login_required
def metas_financeiras():
    """Página de gestão de metas financeiras"""
    from config import Config
    
    usuario_id = session.get('usuario_id')
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    return render_template(
        'metas_financeiras.html',
        app_name=Config.APP_NAME,
        usuario=usuario,
        plano=usuario.get('plano', 'gratuito')
    )

@web_bp.route('/metas/adicionar', methods=['POST'])
@login_required
def adicionar_meta():
    """Adicionar uma nova meta financeira"""
    # ...
    
    return redirect(url_for('web.metas_financeiras'))

# Rotas para gerenciamento de categorias
@web_bp.route('/categorias')
@login_required
def categorias():
    """Página de categorias personalizadas"""
    from config import Config
    
    usuario_id = session.get('usuario_id')
    
    # Cria instância do modelo de usuário e busca dados do usuário logado
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    # Verifica se o plano permite categorias personalizadas
    plano = usuario.get('plano', 'gratuito')
    if plano == 'gratuito':
        flash('Categorias personalizadas estão disponíveis apenas para os planos Premium, Família e Empresarial.', 'info')
        return redirect(url_for('web.planos'))
    
    # Cria instância do modelo de categorias
    categoria_model = CategoriaPersonalizada(Config.DATABASE)
    
    # Busca as categorias do usuário
    categorias_despesa_pessoais = categoria_model.buscar(
        usuario_id=usuario_id,
        tipo='despesa',
        tipo_perfil='pessoal'
    )
    
    categorias_receita_pessoais = categoria_model.buscar(
        usuario_id=usuario_id,
        tipo='receita',
        tipo_perfil='pessoal'
    )
    
    categorias_despesa_empresariais = categoria_model.buscar(
        usuario_id=usuario_id,
        tipo='despesa',
        tipo_perfil='empresarial'
    )
    
    categorias_receita_empresariais = categoria_model.buscar(
        usuario_id=usuario_id,
        tipo='receita',
        tipo_perfil='empresarial'
    )
    
    return render_template(
        'categorias.html',
        app_name=Config.APP_NAME,
        usuario=usuario,
        categorias_despesa_pessoais=categorias_despesa_pessoais,
        categorias_receita_pessoais=categorias_receita_pessoais,
        categorias_despesa_empresariais=categorias_despesa_empresariais,
        categorias_receita_empresariais=categorias_receita_empresariais
    )

@web_bp.route('/categorias/adicionar', methods=['POST'])
@login_required
@plano_required(['premium', 'familia', 'empresarial'])
def adicionar_categoria():
    """Adicionar uma nova categoria personalizada"""
    from config import Config
    
    usuario_id = session.get('usuario_id')
    
    if request.method == 'POST':
        # Obtém os dados do formulário
        nome = request.form.get('nome')
        tipo = request.form.get('tipo')
        icone = request.form.get('icone')
        cor = request.form.get('cor')
        tipo_perfil = request.form.get('tipo_perfil')
        
        # Validações básicas
        if not nome or not tipo or not tipo_perfil:
            flash('Por favor, preencha todos os campos obrigatórios.', 'error')
            return redirect(url_for('web.categorias'))
        
        # Valores padrão
        if not icone:
            icone = '📦'
        
        if not cor:
            cor = '#28a745'
        
        # Cria a categoria
        categoria_model = CategoriaPersonalizada(Config.DATABASE)
        categoria_model.criar(
            usuario_id=usuario_id,
            nome=nome,
            tipo=tipo,
            icone=icone,
            cor=cor,
            tipo_perfil=tipo_perfil
        )
        
        flash('Categoria adicionada com sucesso!', 'success')
    
    return redirect(url_for('web.categorias'))

@web_bp.route('/categorias/excluir/<int:categoria_id>', methods=['POST'])
@login_required
def excluir_categoria(categoria_id):
    """Excluir uma categoria personalizada"""
    from config import Config
    
    usuario_id = session.get('usuario_id')
    
    # Verifica se a categoria pertence ao usuário
    categoria_model = CategoriaPersonalizada(Config.DATABASE)
    categoria = categoria_model.buscar_por_id(categoria_id)
    
    if not categoria or categoria.get('usuario_id') != usuario_id:
        flash('Categoria não encontrada ou acesso negado.', 'error')
        return redirect(url_for('web.categorias'))
    
    # Exclui a categoria
    sucesso, mensagem = categoria_model.excluir(categoria_id)
    
    if sucesso:
        flash('Categoria excluída com sucesso!', 'success')
    else:
        flash(f'Erro ao excluir categoria: {mensagem}', 'error')
    
    return redirect(url_for('web.categorias'))

@web_bp.route('/categorias/editar/<int:categoria_id>', methods=['POST'])
@login_required
def editar_categoria(categoria_id):
    """Editar uma categoria personalizada"""
    from config import Config
    
    usuario_id = session.get('usuario_id')
    
    # Verifica se a categoria pertence ao usuário
    categoria_model = CategoriaPersonalizada(Config.DATABASE)
    categoria = categoria_model.buscar_por_id(categoria_id)
    
    if not categoria or categoria.get('usuario_id') != usuario_id:
        flash('Categoria não encontrada ou acesso negado.', 'error')
        return redirect(url_for('web.categorias'))
    
    # Obtém os dados do formulário
    nome = request.form.get('nome')
    icone = request.form.get('icone')
    cor = request.form.get('cor')
    
    # Validações básicas
    if not nome:
        flash('Por favor, informe o nome da categoria.', 'error')
        return redirect(url_for('web.categorias'))
    
    # Atualiza a categoria
    categoria_model.atualizar(
        categoria_id=categoria_id,
        nome=nome,
        icone=icone,
        cor=cor
    )
    
    flash('Categoria atualizada com sucesso!', 'success')
    
    return redirect(url_for('web.categorias'))

# Rotas para gerenciamento de membros
@web_bp.route('/membros')
@login_required
@plano_required(['familia', 'empresarial'])
def membros():
    """Página de gerenciamento de membros"""
    from config import Config
    
    usuario_id = session.get('usuario_id')
    
    # Cria instância do modelo de usuário e busca dados do usuário logado
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    # Cria instância do modelo de membros
    membro_model = Membro(Config.DATABASE)
    
    # Busca os membros do usuário
    membros_familia = membro_model.buscar(
        usuario_id=usuario_id,
        tipo_grupo='familia'
    )
    
    membros_empresa = membro_model.buscar(
        usuario_id=usuario_id,
        tipo_grupo='empresa'
    )
    
    return render_template(
        'membros.html',
        app_name=Config.APP_NAME,
        usuario=usuario,
        membros_familia=membros_familia,
        membros_empresa=membros_empresa
    )

@web_bp.route('/membros/adicionar', methods=['POST'])
@login_required
@plano_required(['familia', 'empresarial'])
def adicionar_membro():
    """Adicionar um novo membro"""
    from config import Config
    
    usuario_id = session.get('usuario_id')
    
    if request.method == 'POST':
        # Obtém os dados do formulário
        nome = request.form.get('nome')
        email = request.form.get('email')
        celular = request.form.get('celular')
        permissao = request.form.get('permissao')
        tipo_grupo = request.form.get('tipo_grupo')
        
        # Validações básicas
        if not nome or not email or not tipo_grupo:
            flash('Por favor, preencha todos os campos obrigatórios.', 'error')
            return redirect(url_for('web.membros'))
        
        # Verifica o limite de membros baseado no plano
        usuario_model = Usuario(Config.DATABASE)
        usuario = usuario_model.buscar_por_id(usuario_id)
        plano = usuario.get('plano', 'gratuito')
        
        # Contagem de membros atuais
        membro_model = Membro(Config.DATABASE)
        membros_atuais = membro_model.buscar(usuario_id, tipo_grupo)
        num_membros = len(membros_atuais)
        
        # Limites por plano
        limite_membros = {
            'gratuito': 1,
            'premium': 3,
            'familia': 5,
            'empresarial': 999  # "ilimitado"
        }
        
        # Verifica se já atingiu o limite
        if num_membros >= limite_membros.get(plano, 1):
            flash(f'Você atingiu o limite de {limite_membros.get(plano, 1)} membros para seu plano atual.', 'error')
            return redirect(url_for('web.membros'))
        
        # Verifica se o email já está cadastrado como membro
        membro_existente = membro_model.buscar_por_email(email, tipo_grupo)
        if membro_existente:
            flash('Este email já está cadastrado como membro.', 'error')
            return redirect(url_for('web.membros'))
        
        # Cria o membro
        membro_model.criar(
            usuario_id=usuario_id,
            nome=nome,
            email=email,
            celular=celular,
            permissao=permissao,
            tipo_grupo=tipo_grupo
        )
        
        flash('Membro adicionado com sucesso!', 'success')
        
        # Envia convite (implementação fictícia)
        flash('Um convite foi enviado para o email do membro.', 'info')
    
    return redirect(url_for('web.membros'))

@web_bp.route('/membros/excluir/<int:membro_id>', methods=['POST'])
@login_required
def excluir_membro(membro_id):
    """Excluir um membro"""
    from config import Config
    
    usuario_id = session.get('usuario_id')
    
    # Verifica se o membro pertence ao usuário
    membro_model = Membro(Config.DATABASE)
    membro = membro_model.buscar_por_id(membro_id)
    
    if not membro or membro.get('usuario_id') != usuario_id:
        flash('Membro não encontrado ou acesso negado.', 'error')
        return redirect(url_for('web.membros'))
    
    # Verifica se é o usuário principal (não pode ser excluído)
    if membro.get('usuario_principal'):
        flash('O usuário principal não pode ser excluído.', 'error')
        return redirect(url_for('web.membros'))
    
    # Exclui o membro
    sucesso, mensagem = membro_model.excluir(membro_id)
    
    if sucesso:
        flash('Membro excluído com sucesso!', 'success')
    else:
        flash(f'Erro ao excluir membro: {mensagem}', 'error')
    
    return redirect(url_for('web.membros'))

@web_bp.route('/membros/editar/<int:membro_id>', methods=['POST'])
@login_required
def editar_membro(membro_id):
    """Editar um membro"""
    from config import Config
    
    usuario_id = session.get('usuario_id')
    
    # Verifica se o membro pertence ao usuário
    membro_model = Membro(Config.DATABASE)
    membro = membro_model.buscar_por_id(membro_id)
    
    if not membro or membro.get('usuario_id') != usuario_id:
        flash('Membro não encontrado ou acesso negado.', 'error')
        return redirect(url_for('web.membros'))
    
    # Obtém os dados do formulário
    nome = request.form.get('nome')
    permissao = request.form.get('permissao')
    
    # Validações básicas
    if not nome:
        flash('Por favor, informe o nome do membro.', 'error')
        return redirect(url_for('web.membros'))
    
    # Verifica se é o usuário principal (não pode mudar permissão)
    if membro.get('usuario_principal') and permissao != 'admin':
        flash('A permissão do usuário principal não pode ser alterada.', 'error')
        permissao = 'admin'
    
    # Atualiza o membro
    membro_model.atualizar(
        membro_id=membro_id,
        nome=nome,
        permissao=permissao
    )
    
    flash('Membro atualizado com sucesso!', 'success')
    
    return redirect(url_for('web.membros'))

@web_bp.route('/membros/reenviar_convite/<int:membro_id>', methods=['POST'])
@login_required
def reenviar_convite(membro_id):
    """Reenviar convite para um membro"""
    from config import Config
    
    usuario_id = session.get('usuario_id')
    
    # Verifica se o membro pertence ao usuário
    membro_model = Membro(Config.DATABASE)
    membro = membro_model.buscar_por_id(membro_id)
    
    if not membro or membro.get('usuario_id') != usuario_id:
        flash('Membro não encontrado ou acesso negado.', 'error')
        return redirect(url_for('web.membros'))
    
    # Reenvio de convite (implementação fictícia)
    flash('Convite reenviado com sucesso!', 'success')
    
    return redirect(url_for('web.membros'))

# Rotas para relatórios
@web_bp.route('/relatorios')
@login_required
def relatorios():
    """Página de relatórios financeiros"""
    from config import Config
    
    usuario_id = session.get('usuario_id')
    
    # Cria instância do modelo de usuário e busca dados do usuário logado
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    # Verifica se o plano permite relatórios detalhados
    plano = usuario.get('plano', 'gratuito')
    if plano == 'gratuito':
        flash('Relatórios detalhados estão disponíveis apenas para os planos Premium, Família e Empresarial.', 'info')
        return redirect(url_for('web.planos'))
    
    # Obtém dados para relatórios
    despesa_model = Despesa(Config.DATABASE)
    receita_model = Receita(Config.DATABASE)
    
    # Define o período (últimos 30 dias por padrão)
    hoje = datetime.now()
    data_fim = hoje.strftime("%Y-%m-%d")
    data_inicio = (hoje - timedelta(days=30)).strftime("%Y-%m-%d")
    
    # Obtém totais para perfil pessoal
    total_despesas_pessoal = despesa_model.total_periodo(
        usuario_id=usuario_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        tipo_perfil='pessoal'
    )
    
    total_receitas_pessoal = receita_model.total_periodo(
        usuario_id=usuario_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        tipo_perfil='pessoal'
    )
    
    # Obtém totais para perfil empresarial
    total_despesas_empresarial = despesa_model.total_periodo(
        usuario_id=usuario_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        tipo_perfil='empresarial'
    )
    
    total_receitas_empresarial = receita_model.total_periodo(
        usuario_id=usuario_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        tipo_perfil='empresarial'
    )
    
    # Calcula saldos
    saldo_pessoal = total_receitas_pessoal - total_despesas_pessoal
    saldo_empresarial = total_receitas_empresarial - total_despesas_empresarial
    
    return render_template(
        'relatorios.html',
        app_name=Config.APP_NAME,
        usuario=usuario,
        plano=plano,
        data_inicio=data_inicio,
        data_fim=data_fim,
        total_despesas_pessoal=total_despesas_pessoal,
        total_receitas_pessoal=total_receitas_pessoal,
        saldo_pessoal=saldo_pessoal,
        total_despesas_empresarial=total_despesas_empresarial,
        total_receitas_empresarial=total_receitas_empresarial,
        saldo_empresarial=saldo_empresarial
    )

# Rota para processamento de OCR
@web_bp.route('/processar-imagem', methods=['POST'])
@login_required
def processar_imagem():
    """Processa uma imagem para extrair informações de despesa"""
    # Verifica se foi enviada uma imagem
    if 'imagem' not in request.files:
        return jsonify({"error": "Nenhuma imagem enviada"}), 400
    
    imagem = request.files['imagem']
    
    # Verifica se o arquivo é válido
    if imagem.filename == '':
        return jsonify({"error": "Nenhuma imagem selecionada"}), 400
    
    # Verifica a extensão do arquivo
    extensoes_permitidas = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    if not '.' in imagem.filename or \
       imagem.filename.rsplit('.', 1)[1].lower() not in extensoes_permitidas:
        return jsonify({"error": "Formato de arquivo não permitido"}), 400
    
    try:
        # Gera um nome único para o arquivo
        filename = secure_filename(imagem.filename)
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        
        # Caminho completo para o arquivo
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        # Salva o arquivo
        imagem.save(filepath)
        
        # URL relativa para acessar a imagem
        url_imagem = f"/static/uploads/{filename}"
        
        # Aqui seria implementado o OCR para extrair informações da imagem
        # Para este exemplo, retornaremos informações simuladas
        dados_ocr = {
            "valor": round(150 + 50 * (datetime.now().microsecond / 1000000), 2),
            "data": datetime.now().strftime("%Y-%m-%d"),
            "estabelecimento": "Estabelecimento",
            "categoria": "alimentação"
        }
        
        return jsonify({
            "success": True,
            "url_imagem": url_imagem,
            "dados_ocr": dados_ocr
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# Rota para processamento de áudio
@web_bp.route('/processar-audio', methods=['POST'])
@login_required
def processar_audio():
    """Processa um áudio para extrair informações de despesa"""
    # … validações iniciais …

    try:
        filename = secure_filename(audio.filename)
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        audio.save(filepath)
        url_audio = f"/static/uploads/{filename}"

        # Simula transcrição
        texto_transcrito = "Compra no mercado de 78 reais e 90 centavos"

        # Extrai informações usando seu TextProcessor
        processor = TextProcessor()
        dados = processor.extrair_informacoes_despesa(texto_transcrito)

        return jsonify({
            "success": True,
            "url_audio": url_audio,
            "texto_transcrito": texto_transcrito,
            "dados": dados
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@web_bp.route('/configuracoes')
@login_required
def configuracoes():
    """Página de configurações do usuário"""
    from config import Config
    
    usuario_id = session.get('usuario_id')
    
    # Cria instância do modelo de usuário e busca dados do usuário logado
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    # Obtém as configurações do usuário (numa implementação real, haveria uma tabela separada)
    # Aqui usamos valores simulados
    configuracoes = {
        'notificacoes_whatsapp': True,
        'notificacoes_email': True,
        'relatorio_semanal': True,
        'alerta_limite_gasto': True,
        'tema': 'auto',
        'moeda': 'BRL',
        'formato_data': 'DD/MM/YYYY',
        'dia_fechamento': 1
    }
    
    return render_template(
        'configuracoes.html',
        app_name=Config.APP_NAME,
        usuario=usuario,
        configuracoes=configuracoes
    )

# Nova rota para Dívidas
@web_bp.route('/dividas')
@login_required
def dividas():
    """Página de gerenciamento de dívidas"""
    from config import Config
    
    usuario_id = session.get('usuario_id')
    
    # Cria instância do modelo de usuário e busca dados do usuário logado
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    # Cria instância do modelo de dívida
    divida_model = Divida(Config.DATABASE)
    
    # Por padrão, busca dívidas do tipo pessoal
    dividas = divida_model.buscar(usuario_id, tipo_perfil='pessoal')
    
    return render_template(
        'dividas.html',
        app_name=Config.APP_NAME,
        usuario=usuario,
        dividas=dividas,
        plano=usuario.get('plano', 'gratuito')
    )

@web_bp.route('/dividas/adicionar', methods=['POST'])
@login_required
def adicionar_divida():
    """Adicionar uma nova dívida"""
    from config import Config
    
    try:
        usuario_id = session.get('usuario_id')
        
        # Extrai dados do formulário
        nome = request.form.get('nome')
        valor_total = float(request.form.get('valor_total', 0))
        valor_pago = float(request.form.get('valor_pago', 0))
        data_inicio = request.form.get('data_inicio')
        data_fim = request.form.get('data_fim')
        taxa_juros = float(request.form.get('taxa_juros', 0)) if request.form.get('taxa_juros') else None
        parcelas_total = int(request.form.get('parcelas_total', 1)) if request.form.get('parcelas_total') else None
        parcelas_pagas = int(request.form.get('parcelas_pagas', 0))
        credor = request.form.get('credor')
        tipo_perfil = request.form.get('tipo_perfil', 'pessoal')
        tipo = request.form.get('tipo', 'outros')
        
        # Validações básicas
        if not nome:
            flash('Nome da dívida é obrigatório', 'danger')
            return redirect(url_for('web.dividas'))
        
        if valor_total <= 0:
            flash('Valor total deve ser maior que zero', 'danger')
            return redirect(url_for('web.dividas'))
        
        if not data_inicio:
            flash('Data de início é obrigatória', 'danger')
            return redirect(url_for('web.dividas'))
        
        # Cria o modelo de dívida
        divida_model = Divida(Config.DATABASE)
        
        # Cria a dívida
        divida_id = divida_model.criar(
            usuario_id=usuario_id,
            nome=nome,
            valor_total=valor_total,
            data_inicio=data_inicio,
            data_fim=data_fim,
            taxa_juros=taxa_juros,
            parcelas_total=parcelas_total,
            credor=credor,
            tipo_perfil=tipo_perfil,
            tipo=tipo
        )
        
        # Atualiza os dados adicionais (valor_pago, parcelas_pagas)
        if valor_pago > 0 or parcelas_pagas > 0:
            divida_model.atualizar(
                divida_id,
                valor_pago=valor_pago,
                parcelas_pagas=parcelas_pagas
            )
        
        flash('Dívida adicionada com sucesso!', 'success')
        
    except Exception as e:
        print(f"Erro ao adicionar dívida: {str(e)}")
        flash('Erro ao adicionar dívida. Por favor, tente novamente.', 'danger')
    
    return redirect(url_for('web.dividas'))

@web_bp.route('/dividas/editar/<int:divida_id>', methods=['POST'])
@login_required
def editar_divida(divida_id):
    """Editar uma dívida"""
    from config import Config
    
    try:
        usuario_id = session.get('usuario_id')
        
        # Extrai dados do formulário
        nome = request.form.get('nome')
        valor_total = float(request.form.get('valor_total', 0))
        valor_pago = float(request.form.get('valor_pago', 0))
        data_inicio = request.form.get('data_inicio')
        data_fim = request.form.get('data_fim')
        taxa_juros = float(request.form.get('taxa_juros', 0)) if request.form.get('taxa_juros') else None
        parcelas_total = int(request.form.get('parcelas_total', 1)) if request.form.get('parcelas_total') else None
        parcelas_pagas = int(request.form.get('parcelas_pagas', 0))
        credor = request.form.get('credor')
        tipo = request.form.get('tipo', 'outros')
        
        # Validações básicas
        if not nome:
            flash('Nome da dívida é obrigatório', 'danger')
            return redirect(url_for('web.dividas'))
        
        if valor_total <= 0:
            flash('Valor total deve ser maior que zero', 'danger')
            return redirect(url_for('web.dividas'))
        
        # Cria o modelo de dívida
        divida_model = Divida(Config.DATABASE)
        
        # Verifica se a dívida existe e pertence ao usuário
        divida = divida_model.buscar_por_id(divida_id)
        
        if not divida:
            flash('Dívida não encontrada', 'danger')
            return redirect(url_for('web.dividas'))
        
        if divida['usuario_id'] != usuario_id:
            flash('Você não tem permissão para editar esta dívida', 'danger')
            return redirect(url_for('web.dividas'))
        
        # Prepara status baseado no valor pago
        status = 'quitada' if valor_pago >= valor_total else 'em_dia'
        
        # Atualiza a dívida
        divida_model.atualizar(
            divida_id,
            nome=nome,
            valor_total=valor_total,
            valor_pago=valor_pago,
            data_inicio=data_inicio,
            data_fim=data_fim,
            taxa_juros=taxa_juros,
            parcelas_total=parcelas_total,
            parcelas_pagas=parcelas_pagas,
            credor=credor,
            tipo=tipo,
            status=status
        )
        
        flash('Dívida atualizada com sucesso!', 'success')
        
    except Exception as e:
        print(f"Erro ao editar dívida: {str(e)}")
        flash('Erro ao atualizar dívida. Por favor, tente novamente.', 'danger')
    
    return redirect(url_for('web.dividas'))

@web_bp.route('/dividas/excluir/<int:divida_id>', methods=['POST'])
@login_required
def excluir_divida(divida_id):
    """Excluir uma dívida"""
    from config import Config
    
    try:
        usuario_id = session.get('usuario_id')
        
        # Cria o modelo de dívida
        divida_model = Divida(Config.DATABASE)
        
        # Verifica se a dívida existe e pertence ao usuário
        divida = divida_model.buscar_por_id(divida_id)
        
        if not divida:
            flash('Dívida não encontrada', 'danger')
            return redirect(url_for('web.dividas'))
        
        if divida['usuario_id'] != usuario_id:
            flash('Você não tem permissão para excluir esta dívida', 'danger')
            return redirect(url_for('web.dividas'))
        
        # Exclui a dívida
        excluida = divida_model.excluir(divida_id)
        
        if excluida:
            flash('Dívida excluída com sucesso!', 'success')
        else:
            flash('Erro ao excluir dívida', 'danger')
        
    except Exception as e:
        print(f"Erro ao excluir dívida: {str(e)}")
        flash('Erro ao excluir dívida. Por favor, tente novamente.', 'danger')
    
    return redirect(url_for('web.dividas'))

@web_bp.route('/dividas/registrar_pagamento/<int:divida_id>', methods=['POST'])
@login_required
def registrar_pagamento_divida(divida_id):
    """Registrar um pagamento de parcela de dívida"""
    from config import Config
    
    try:
        usuario_id = session.get('usuario_id')
        
        # Extrai dados do formulário
        valor = float(request.form.get('valor', 0))
        data = request.form.get('data')
        tipo = request.form.get('tipo', 'parcela')
        observacao = request.form.get('observacao')
        
        # Validações básicas
        if valor <= 0:
            flash('Valor do pagamento deve ser maior que zero', 'danger')
            return redirect(url_for('web.dividas'))
        
        # Cria o modelo de dívida
        divida_model = Divida(Config.DATABASE)
        
        # Verifica se a dívida existe e pertence ao usuário
        divida = divida_model.buscar_por_id(divida_id)
        
        if not divida:
            flash('Dívida não encontrada', 'danger')
            return redirect(url_for('web.dividas'))
        
        if divida['usuario_id'] != usuario_id:
            flash('Você não tem permissão para registrar pagamentos nesta dívida', 'danger')
            return redirect(url_for('web.dividas'))
        
        # Registra o pagamento
        pagamento_id = divida_model.registrar_pagamento(
            divida_id=divida_id,
            valor=valor,
            data=data,
            observacao=observacao,
            tipo=tipo
        )
        
        flash('Pagamento registrado com sucesso!', 'success')
        
    except Exception as e:
        print(f"Erro ao registrar pagamento: {str(e)}")
        flash('Erro ao registrar pagamento. Por favor, tente novamente.', 'danger')
    
    return redirect(url_for('web.dividas'))

@web_bp.route('/api/usuario/perfil', methods=['GET'])
@login_required
def obter_perfil_usuario():
    """Obtém informações básicas do perfil do usuário"""
    from config import Config
    
    try:
        usuario_id = session.get('usuario_id')
        
        usuario_model = Usuario(Config.DATABASE)
        usuario = usuario_model.buscar_por_id(usuario_id)
        
        if not usuario:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        # Retorna informações básicas do perfil
        resposta = {
            'id': usuario.get('id'),
            'nome': usuario.get('nome'),
            'email': usuario.get('email'),
            'plano': usuario.get('plano', 'gratuito'),
            'renda_mensal': float(usuario.get('renda_mensal', 0)) if usuario.get('renda_mensal') else 0
        }
        
        return jsonify(resposta), 200
        
    except Exception as e:
        print(f"Erro ao obter perfil do usuário: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

# Rota para Financiamentos
@web_bp.route('/financiamentos')
@login_required
def financiamentos():
    """Página de gerenciamento de financiamentos"""
    from config import Config
    
    usuario_id = session.get('usuario_id')
    
    # Cria instância do modelo de usuário e busca dados do usuário logado
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    # Em uma implementação real, buscaria os financiamentos do banco de dados
    # Aqui usamos dados simulados
    financiamentos = [
        {
            'id': 1,
            'nome': 'Financiamento Imóvel',
            'valor_total': 300000.00,
            'valor_pago': 50000.00,
            'data_inicio': '2024-01-01',
            'data_fim': '2045-01-01',
            'taxa_juros': 0.8,
            'parcelas_total': 240,
            'parcelas_pagas': 16,
            'status': 'em_dia',
            'instituicao': 'Caixa Econômica',
            'tipo_perfil': 'pessoal'
        },
        {
            'id': 2,
            'nome': 'Financiamento Veículo',
            'valor_total': 45000.00,
            'valor_pago': 15000.00,
            'data_inicio': '2024-06-01',
            'data_fim': '2027-06-01',
            'taxa_juros': 1.2,
            'parcelas_total': 36,
            'parcelas_pagas': 11,
            'status': 'em_dia',
            'instituicao': 'Banco ABC',
            'tipo_perfil': 'pessoal'
        },
        {
            'id': 3,
            'nome': 'Financiamento Maquinário Industrial',
            'valor_total': 120000.00,
            'valor_pago': 30000.00,
            'data_inicio': '2024-03-01',
            'data_fim': '2028-03-01',
            'taxa_juros': 1.1,
            'parcelas_total': 48,
            'parcelas_pagas': 14,
            'status': 'em_dia',
            'instituicao': 'BNDES',
            'tipo_perfil': 'empresarial'
        }
    ]
    
    return render_template(
        'financiamentos.html',
        app_name=Config.APP_NAME,
        usuario=usuario,
        financiamentos=financiamentos,
        plano=usuario.get('plano', 'gratuito')
    )

@web_bp.route('/financiamentos/adicionar', methods=['POST'])
@login_required
def adicionar_financiamento():
    """Adicionar um novo financiamento"""
    # Em uma implementação real, salvaria no banco de dados
    flash('Financiamento adicionado com sucesso!', 'success')
    return redirect(url_for('web.financiamentos'))

@web_bp.route('/financiamentos/editar/<int:financiamento_id>', methods=['POST'])
@login_required
def editar_financiamento(financiamento_id):
    """Editar um financiamento"""
    # Em uma implementação real, atualizaria no banco de dados
    flash('Financiamento atualizado com sucesso!', 'success')
    return redirect(url_for('web.financiamentos'))

@web_bp.route('/financiamentos/excluir/<int:financiamento_id>', methods=['POST'])
@login_required
def excluir_financiamento(financiamento_id):
    """Excluir um financiamento"""
    # Em uma implementação real, excluiria do banco de dados
    flash('Financiamento excluído com sucesso!', 'success')
    return redirect(url_for('web.financiamentos'))

@web_bp.route('/financiamentos/registrar_pagamento/<int:financiamento_id>', methods=['POST'])
@login_required
def registrar_pagamento_financiamento(financiamento_id):
    """Registrar um pagamento de parcela de financiamento"""
    # Em uma implementação real, registraria o pagamento no banco de dados
    flash('Pagamento registrado com sucesso!', 'success')
    return redirect(url_for('web.financiamentos'))

# Rotas para edição e exclusão de transações
@web_bp.route('/transacoes/editar_despesa/<int:despesa_id>', methods=['POST'])
@login_required
def editar_despesa(despesa_id):
    """Editar uma despesa"""
    from config import Config
    
    usuario_id = session.get('usuario_id')
    
    # Verifica se a despesa pertence ao usuário
    despesa_model = Despesa(Config.DATABASE)
    despesa = despesa_model.buscar_por_id(despesa_id)
    
    if not despesa or despesa.get('usuario_id') != usuario_id:
        flash('Despesa não encontrada ou acesso negado.', 'error')
        return redirect(url_for('web.dashboard'))
    
    # Obtém os dados do formulário
    dados = {}
    for campo in ['valor', 'categoria', 'descricao', 'data', 'forma_pagamento', 'tipo_perfil']:
        if campo in request.form:
            dados[campo] = request.form.get(campo)
    
    # Converte o valor para float
    if 'valor' in dados:
        try:
            dados['valor'] = float(dados['valor'].replace(',', '.'))
        except ValueError:
            flash('Valor inválido.', 'error')
            return redirect(url_for('web.dashboard'))
    
    # Atualiza a despesa
    despesa_model.atualizar(despesa_id, **dados)
    
    flash('Despesa atualizada com sucesso!', 'success')
    
    # Redireciona para a página anterior
    return redirect(request.referrer or url_for('web.dashboard'))

@web_bp.route('/transacoes/excluir_despesa/<int:despesa_id>', methods=['POST'])
@login_required
def excluir_despesa(despesa_id):
    """Excluir uma despesa"""
    from config import Config
    
    usuario_id = session.get('usuario_id')
    
    # Verifica se a despesa pertence ao usuário
    despesa_model = Despesa(Config.DATABASE)
    despesa = despesa_model.buscar_por_id(despesa_id)
    
    if not despesa or despesa.get('usuario_id') != usuario_id:
        flash('Despesa não encontrada ou acesso negado.', 'error')
        return redirect(url_for('web.dashboard'))
    
    # Exclui a despesa
    despesa_model.excluir(despesa_id)
    
    flash('Despesa excluída com sucesso!', 'success')
    
    # Redireciona para a página anterior
    return redirect(request.referrer or url_for('web.dashboard'))

@web_bp.route('/transacoes/editar_receita/<int:receita_id>', methods=['POST'])
@login_required
def editar_receita(receita_id):
    """Editar uma receita"""
    from config import Config
    
    usuario_id = session.get('usuario_id')
    
    # Verifica se a receita pertence ao usuário
    receita_model = Receita(Config.DATABASE)
    receita = receita_model.buscar_por_id(receita_id)
    
    if not receita or receita.get('usuario_id') != usuario_id:
        flash('Receita não encontrada ou acesso negado.', 'error')
        return redirect(url_for('web.dashboard'))
    
    # Obtém os dados do formulário
    dados = {}
    for campo in ['valor', 'categoria', 'descricao', 'data', 'recorrente', 'periodicidade', 'tipo_perfil']:
        if campo in request.form:
            dados[campo] = request.form.get(campo)
    
    # Converte o valor para float
    if 'valor' in dados:
        try:
            dados['valor'] = float(dados['valor'].replace(',', '.'))
        except ValueError:
            flash('Valor inválido.', 'error')
            return redirect(url_for('web.dashboard'))
    
    # Converte campos booleanos
    if 'recorrente' in dados:
        dados['recorrente'] = 1 if dados['recorrente'] == 'on' else 0
    
    # Atualiza a receita
    receita_model.atualizar(receita_id, **dados)
    
    flash('Receita atualizada com sucesso!', 'success')
    
    # Redireciona para a página anterior
    return redirect(request.referrer or url_for('web.dashboard'))

@web_bp.route('/transacoes/excluir_receita/<int:receita_id>', methods=['POST'])
@login_required
def excluir_receita(receita_id):
    """Excluir uma receita"""
    from config import Config
    
    usuario_id = session.get('usuario_id')
    
    # Verifica se a receita pertence ao usuário
    receita_model = Receita(Config.DATABASE)
    receita = receita_model.buscar_por_id(receita_id)
    
    if not receita or receita.get('usuario_id') != usuario_id:
        flash('Receita não encontrada ou acesso negado.', 'error')
        return redirect(url_for('web.dashboard'))
    
    # Exclui a receita
    receita_model.excluir(receita_id)
    
    flash('Receita excluída com sucesso!', 'success')
    
    # Redireciona para a página anterior
    return redirect(request.referrer or url_for('web.dashboard'))

# Rota para API de WhatsApp
@web_bp.route('/api/whatsapp/atualizar', methods=['POST'])
@login_required
def api_whatsapp_atualizar():
    """API para processar comandos de atualização via WhatsApp"""
    # Recebe os dados do webhook
    dados = request.json
    
    if not dados or 'comando' not in dados or 'usuario_id' not in dados:
        return jsonify({"error": "Dados incompletos"}), 400
    
    try:
        comando = dados['comando']
        usuario_id = int(dados['usuario_id'])
        
        # Verifica se o usuário da sessão tem permissão para este usuário_id
        if session.get('usuario_id') != usuario_id:
            return jsonify({"error": "Não autorizado"}), 403
        
        # Processa comandos
        if comando.startswith('mudar_categoria:'):
            # Formato: mudar_categoria:id_despesa:nova_categoria
            partes = comando.split(':')
            if len(partes) != 3:
                return jsonify({"error": "Formato inválido"}), 400
            
            despesa_id = int(partes[1])
            nova_categoria = partes[2]
            
            # Atualiza a categoria
            despesa_model = Despesa(Config.DATABASE)
            despesa_model.atualizar(despesa_id, categoria=nova_categoria)
            
            return jsonify({"success": True, "message": "Categoria atualizada com sucesso"})
            
        elif comando.startswith('excluir_despesa:'):
            # Formato: excluir_despesa:id_despesa
            partes = comando.split(':')
            if len(partes) != 2:
                return jsonify({"error": "Formato inválido"}), 400
            
            despesa_id = int(partes[1])
            
            # Exclui a despesa
            despesa_model = Despesa(Config.DATABASE)
            despesa_model.excluir(despesa_id)
            
            return jsonify({"success": True, "message": "Despesa excluída com sucesso"})
            
        elif comando.startswith('excluir_lembrete:'):
            # Formato: excluir_lembrete:id_lembrete
            partes = comando.split(':')
            if len(partes) != 2:
                return jsonify({"error": "Formato inválido"}), 400
            
            lembrete_id = int(partes[1])
            
            # Exclui o lembrete
            lembrete_model = Lembrete(Config.DATABASE)
            lembrete_model.excluir(lembrete_id)
            
            return jsonify({"success": True, "message": "Lembrete excluído com sucesso"})
        
        else:
            return jsonify({"error": "Comando não reconhecido"}), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@web_bp.route('/notificacoes')
def notificacoes():
    # Se o usuário não estiver logado, redireciona para a página inicial
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return render_template('notificacoes.html')

# API de Notificações

# Rota para obter todas as notificações do usuário
@web_bp.route('/api/notifications')
def get_notifications():
    if 'usuario_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = session['usuario_id']
    filter_type = request.args.get('filter', 'all')
    is_read = None
    if filter_type == 'unread':
        is_read = False
        filter_type = None
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Buscar notificações usando a classe Notificacao
    notifications = Notificacao.get_for_user(
        user_id=user_id,
        filter_type=filter_type,
        is_read=is_read,
        page=page,
        per_page=per_page
    )
    
    # Contar o total de notificações para paginação
    total = Notificacao.count_for_user(
        user_id=user_id,
        filter_type=filter_type,
        is_read=is_read
    )
    
    # Contar notificações não lidas
    unread_count = Notificacao.count_for_user(
        user_id=user_id,
        is_read=False
    )
    
    return jsonify({
        'notifications': [n.to_dict() for n in notifications],
        'pagination': {
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        },
        'unread_count': unread_count
    })

# Rota para marcar uma notificação como lida
@web_bp.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
def mark_as_read(notification_id):
    if 'usuario_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = session['usuario_id']
    
    # Buscar a notificação e verificar se pertence ao usuário
    notification = Notificacao.get_by_id(notification_id, user_id)
    
    if not notification:
        return jsonify({'error': 'Notification not found'}), 404
    
    # Marcar como lida
    if notification.mark_as_read():
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to mark notification as read'}), 500

# Rota para marcar todas as notificações como lidas
@web_bp.route('/api/notifications/mark-all-read', methods=['POST'])
def mark_all_as_read():
    if 'usuario_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = session['usuario_id']
    filter_type = request.json.get('filter', None) if request.json else None
    
    # Marcar todas como lidas
    if Notificacao.mark_all_as_read(user_id, filter_type):
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to mark notifications as read'}), 500

# Rota para excluir uma notificação
@web_bp.route('/api/notifications/<int:notification_id>', methods=['DELETE'])
def delete_notification(notification_id):
    if 'usuario_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = session['usuario_id']
    
    # Buscar a notificação e verificar se pertence ao usuário
    notification = Notificacao.get_by_id(notification_id, user_id)
    
    if not notification:
        return jsonify({'error': 'Notification not found'}), 404
    
    # Excluir a notificação
    if notification.delete():
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to delete notification'}), 500

# Rota para criar uma nova notificação (uso interno ou para testes)
@web_bp.route('/api/notifications', methods=['POST'])
def create_notification():
    if 'usuario_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = session['usuario_id']
    data = request.json
    
    required_fields = ['type', 'title', 'description']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    # Criar nova notificação
    notification = Notificacao(
        user_id=user_id,
        type=data['type'],
        title=data['title'],
        description=data['description'],
        icon=data.get('icon'),
        icon_color=data.get('icon_color'),
        icon_bg=data.get('icon_bg'),
        action_url=data.get('action_url'),
        action_text=data.get('action_text'),
        metadata=data.get('metadata', {})
    )
    
    if notification.save():
        return jsonify(notification.to_dict())
    else:
        return jsonify({'error': 'Failed to create notification'}), 500

# Rota para obter a contagem de notificações não lidas
@web_bp.route('/api/notifications/unread-count')
def get_unread_count():
    if 'usuario_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = session['usuario_id']
    
    # Contar notificações não lidas
    count = Notificacao.count_for_user(
        user_id=user_id,
        is_read=False
    )
    
    return jsonify({'unread_count': count})

# Rota para executar ação em uma notificação
@web_bp.route('/api/notifications/<int:notification_id>/action', methods=['POST'])
def execute_notification_action(notification_id):
    if 'usuario_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = session['usuario_id']
    action_data = request.json or {}
    
    # Buscar a notificação
    notification = Notificacao.get_by_id(notification_id, user_id)
    
    if not notification:
        return jsonify({'error': 'Notification not found'}), 404
    
    # Marcar como lida independentemente da ação
    notification.mark_as_read()
    
    # Resposta básica
    response = {
        'success': True,
        'message': f"Ação '{notification.action_text}' executada com sucesso",
        'notification': notification.to_dict()
    }
    
    # Processamento específico por tipo
    if notification.type == 'lembrete' and notification.metadata.get('transaction_id') and 'mark_as_paid' in action_data:
        # Aqui você implementaria a lógica para marcar a transação como paga
        # transaction = Transaction.get_by_id(notification.metadata.get('transaction_id'))
        # if transaction:
        #     transaction.mark_as_paid()
        #     response['message'] = 'Pagamento registrado com sucesso'
        pass
    
    return jsonify(response)