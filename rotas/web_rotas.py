from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from database.models import Usuario, Despesa, Receita
from functools import wraps
import os
from datetime import datetime, timedelta

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
    
    # Cria instância do modelo de usuário e busca dados do usuário logado
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    return render_template(
        'dashboard.html',
        app_name=Config.APP_NAME,
        usuario=usuario
    )

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
        
        # Validações
        if not nome or not email or not celular or not senha:
            flash('Por favor, preencha todos os campos.', 'error')
            return render_template('cadastro.html', app_name=Config.APP_NAME)
        
        if senha != confirma_senha:
            flash('As senhas não coincidem.', 'error')
            return render_template('cadastro.html', app_name=Config.APP_NAME)
        
        # Verifica se o email já existe
        usuario_model = Usuario(Config.DATABASE)
        if usuario_model.buscar_por_email(email):
            flash('Este email já está cadastrado.', 'error')
            return render_template('cadastro.html', app_name=Config.APP_NAME)
        
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
            return render_template('cadastro.html', app_name=Config.APP_NAME)
        
        # Cria o usuário
        # Em um sistema real, a senha seria armazenada com hash
        usuario_id = usuario_model.criar(celular, nome, email, senha)
        
        if usuario_id:
            # Cria a sessão e redireciona para o dashboard
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
    
    # Validações básicas
    if not nome or not email:
        flash('Por favor, preencha todos os campos obrigatórios.', 'error')
        return redirect(url_for('web.perfil'))
    
    # Verifica se o email já está em uso por outro usuário
    usuario_model = Usuario(Config.DATABASE)
    usuario_email = usuario_model.buscar_por_email(email)
    
    if usuario_email and usuario_email['id'] != usuario_id:
        flash('Este email já está sendo usado por outro usuário.', 'error')
        return redirect(url_for('web.perfil'))
    
    # Atualiza os dados do usuário
    usuario_model.atualizar(usuario_id, nome=nome, email=email)
    
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
    
    return render_template(
        'planos.html',
        app_name=Config.APP_NAME,
        plano_gratuito=Config.PLANO_GRATUITO,
        plano_premium=Config.PLANO_PREMIUM,
        plano_profissional=Config.PLANO_PROFISSIONAL,
        plano_atual=plano_atual
    )

@web_bp.route('/assinatura/<plano>', methods=['GET', 'POST'])
@login_required
def assinatura(plano):
    """Página de pagamento da assinatura"""
    from config import Config
    
    # Verifica se o plano é válido
    planos_validos = ['gratuito', 'premium', 'profissional']
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
            if plano == 'premium':
                valor = 29.90 if period == 'monthly' else 287.04  # Anual com 20% de desconto
            else:  # profissional
                valor = 59.90 if period == 'monthly' else 575.04  # Anual com 20% de desconto
            
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
        preco_premium=Config.PLANO_PREMIUM['preco'],
        preco_profissional=Config.PLANO_PROFISSIONAL['preco']
    )

@web_bp.route('/cancelar_assinatura', methods=['POST'])
@login_required
def cancelar_assinatura():
    """Cancelamento de assinatura"""
    from config import Config
    
    usuario_id = session.get('usuario_id')
    
    # Cancela a assinatura
    usuario_model = Usuario(Config.DATABASE)
    sucesso = usuario_model.cancelar_assinatura(usuario_id)
    
    if sucesso:
        flash('Sua assinatura foi cancelada com sucesso. Seu plano será alterado para Gratuito no próximo ciclo de faturamento.', 'success')
    else:
        flash('Não foi possível cancelar sua assinatura. Talvez você não tenha uma assinatura ativa.', 'error')
    
    return redirect(url_for('web.perfil'))