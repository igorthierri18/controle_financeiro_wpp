from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from database.models import Usuario
from config import Config
import sqlite3
from datetime import datetime
import re

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
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
            
            # Redireciona para o dashboard ou página solicitada
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('dashboard.index'))
        else:
            flash('Email ou senha incorretos.', 'error')
    
    # Se já estiver logado, redireciona para o dashboard
    if 'usuario_id' in session:
        return redirect(url_for('dashboard.index'))
    
    return render_template('login.html', app_name=Config.APP_NAME)

@auth_bp.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    """Página de cadastro"""
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
                nome=nome, email=email, celular=celular,
                origem=origem, cupom=cupom
            )
        
        # Validação de email
        if not validar_email(email):
            flash('Por favor, informe um email válido.', 'error')
            return render_template('cadastro.html', 
                app_name=Config.APP_NAME,
                nome=nome, email=email, celular=celular,
                origem=origem, cupom=cupom
            )
        
        # Validação de senha
        if len(senha) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.', 'error')
            return render_template('cadastro.html', 
                app_name=Config.APP_NAME,
                nome=nome, email=email, celular=celular,
                origem=origem, cupom=cupom
            )
        
        if senha != confirma_senha:
            flash('As senhas não coincidem.', 'error')
            return render_template('cadastro.html', 
                app_name=Config.APP_NAME,
                nome=nome, email=email, celular=celular,
                origem=origem, cupom=cupom
            )
        
        # Verifica se o email já existe
        usuario_model = Usuario(Config.DATABASE)
        if usuario_model.buscar_por_email(email):
            flash('Este email já está cadastrado.', 'error')
            return render_template('cadastro.html', 
                app_name=Config.APP_NAME,
                nome=nome, celular=celular,
                origem=origem, cupom=cupom
            )
        
        # Formata o celular
        celular = formatar_celular(celular)
        
        # Validação de celular
        if not validar_celular(celular):
            flash('Por favor, informe um número de celular válido.', 'error')
            return render_template('cadastro.html', 
                app_name=Config.APP_NAME,
                nome=nome, email=email,
                origem=origem, cupom=cupom
            )
        
        # Verifica se o celular já existe
        if usuario_model.buscar_por_celular(celular):
            flash('Este número de celular já está cadastrado.', 'error')
            return render_template('cadastro.html', 
                app_name=Config.APP_NAME,
                nome=nome, email=email,
                origem=origem, cupom=cupom
            )
        
        # Cria o usuário
        # Em um sistema real, a senha seria hasheada com bcrypt
        usuario_id = usuario_model.criar(celular, nome, email, senha)
        
        if usuario_id:
            # Configurações iniciais do usuário
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
                
                # Cria categorias padrão
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
                
                # Atualiza a origem na tabela usuarios
                cursor.execute(
                    "UPDATE usuarios SET origem = ? WHERE id = ?",
                    (origem, usuario_id)
                )
                
                conn.commit()
                conn.close()
                
                # Aplica cupom se fornecido
                if cupom:
                    try:
                        aplicar_cupom_resultado = aplicar_cupom(cupom, usuario_id)
                        if aplicar_cupom_resultado.get('sucesso'):
                            flash(aplicar_cupom_resultado.get('mensagem', 'Cupom aplicado com sucesso!'), 'success')
                        else:
                            flash(aplicar_cupom_resultado.get('mensagem', 'Cupom inválido ou expirado.'), 'warning')
                    except Exception as e:
                        print(f"Erro ao aplicar cupom: {e}")
                        # Não bloqueia o cadastro se houver erro no cupom
                
                # Cria a sessão
                session['usuario_id'] = usuario_id
                flash('Conta criada com sucesso! Bem-vindo ao Despezap!', 'success')
                return redirect(url_for('dashboard.index'))
                
            except Exception as e:
                print(f"Erro ao configurar conta: {e}")
                flash(f'Erro ao configurar sua conta: {str(e)}', 'error')
                # Mesmo com erro nas configurações extras, o usuário foi criado
                session['usuario_id'] = usuario_id
                return redirect(url_for('dashboard.index'))
        else:
            flash('Erro ao criar usuário. Tente novamente.', 'error')
    
    # Se já estiver logado, redireciona para o dashboard
    if 'usuario_id' in session:
        return redirect(url_for('dashboard.index'))
    
    return render_template('cadastro.html', app_name=Config.APP_NAME)

@auth_bp.route('/logout')
def logout():
    """Logout do usuário"""
    session.pop('usuario_id', None)
    flash('Você foi desconectado com sucesso.', 'info')
    return redirect(url_for('index'))

@auth_bp.route('/recuperar_senha', methods=['GET', 'POST'])
def recuperar_senha():
    """Página de recuperação de senha"""
    if request.method == 'POST':
        email = request.form.get('email')
        
        if not email:
            flash('Por favor, informe seu email.', 'error')
            return render_template('recuperar_senha.html', app_name=Config.APP_NAME)
        
        if not validar_email(email):
            flash('Por favor, informe um email válido.', 'error')
            return render_template('recuperar_senha.html', app_name=Config.APP_NAME)
        
        # Verifica se o email existe
        usuario_model = Usuario(Config.DATABASE)
        usuario = usuario_model.buscar_por_email(email)
        
        # Por segurança, sempre mostra a mesma mensagem
        flash('Se este email estiver cadastrado, enviaremos instruções para recuperar sua senha.', 'success')
        
        # Se o usuário existe, aqui implementaria o envio de email real
        if usuario:
            try:
                # Gera token de recuperação
                token = gerar_token_recuperacao(usuario['id'])
                
                # Em um sistema real, enviaria email com link de recuperação
                # enviar_email_recuperacao(usuario['email'], token)
                
                print(f"Token de recuperação para {email}: {token}")  # Log para desenvolvimento
                
            except Exception as e:
                print(f"Erro ao processar recuperação de senha: {e}")
        
        return render_template('recuperar_senha.html', app_name=Config.APP_NAME)
    
    return render_template('recuperar_senha.html', app_name=Config.APP_NAME)

@auth_bp.route('/resetar_senha/<token>', methods=['GET', 'POST'])
def resetar_senha(token):
    """Página para resetar senha com token"""
    if request.method == 'POST':
        nova_senha = request.form.get('nova_senha')
        confirma_senha = request.form.get('confirma_senha')
        
        if not nova_senha or not confirma_senha:
            flash('Por favor, preencha todos os campos.', 'error')
            return render_template('resetar_senha.html', app_name=Config.APP_NAME, token=token)
        
        if len(nova_senha) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.', 'error')
            return render_template('resetar_senha.html', app_name=Config.APP_NAME, token=token)
        
        if nova_senha != confirma_senha:
            flash('As senhas não coincidem.', 'error')
            return render_template('resetar_senha.html', app_name=Config.APP_NAME, token=token)
        
        # Valida o token
        usuario_id = validar_token_recuperacao(token)
        
        if not usuario_id:
            flash('Token inválido ou expirado.', 'error')
            return redirect(url_for('auth.recuperar_senha'))
        
        # Atualiza a senha
        try:
            usuario_model = Usuario(Config.DATABASE)
            usuario_model.atualizar(usuario_id, senha=nova_senha)
            
            # Invalida o token usado
            invalidar_token_recuperacao(token)
            
            flash('Senha alterada com sucesso! Você pode fazer login agora.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            print(f"Erro ao resetar senha: {e}")
            flash('Erro ao alterar senha. Tente novamente.', 'error')
    
    # Verifica se o token é válido
    if not validar_token_recuperacao(token):
        flash('Token inválido ou expirado.', 'error')
        return redirect(url_for('auth.recuperar_senha'))
    
    return render_template('resetar_senha.html', app_name=Config.APP_NAME, token=token)

@auth_bp.route('/verificar_email/<token>')
def verificar_email(token):
    """Verificação de email para novos usuários"""
    # Implementaria a verificação de email se necessário
    flash('Email verificado com sucesso!', 'success')
    return redirect(url_for('login'))

# Funções auxiliares

def validar_email(email):
    """Valida formato do email"""
    padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(padrao, email) is not None

def validar_celular(celular):
    """Valida formato do celular brasileiro"""
    # Remove caracteres não numéricos
    celular_limpo = re.sub(r'[^0-9]', '', celular)
    
    # Verifica se tem entre 10 e 15 dígitos (considerando código do país)
    if len(celular_limpo) < 10 or len(celular_limpo) > 15:
        return False
    
    # Verifica se começa com código do Brasil (55) para números internacionais
    if len(celular_limpo) >= 12 and not celular_limpo.startswith('55'):
        return False
    
    return True

def formatar_celular(celular):
    """Formata o número de celular"""
    # Remove caracteres não numéricos
    celular_limpo = ''.join(filter(str.isdigit, celular))
    
    # Adiciona código do país se necessário
    if len(celular_limpo) == 10 or len(celular_limpo) == 11:
        # Número brasileiro sem código do país
        celular_limpo = '55' + celular_limpo
    elif len(celular_limpo) >= 12 and not celular_limpo.startswith('55'):
        # Número internacional que não é brasileiro
        pass  # Mantém como está
    
    return celular_limpo

def gerar_token_recuperacao(usuario_id):
    """Gera token para recuperação de senha"""
    import secrets
    import hashlib
    
    # Gera token aleatório
    token = secrets.token_urlsafe(32)
    
    # Calcula data de expiração (2 horas)
    data_expiracao = (datetime.now() + datetime.timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
    data_criacao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        conn = sqlite3.connect(Config.DATABASE)
        cursor = conn.cursor()
        
        # Invalida tokens anteriores do usuário
        cursor.execute(
            "UPDATE tokens_recuperacao SET utilizado = 1 WHERE usuario_id = ? AND utilizado = 0",
            (usuario_id,)
        )
        
        # Insere novo token
        cursor.execute(
            """INSERT INTO tokens_recuperacao 
               (usuario_id, token, data_criacao, data_expiracao, utilizado) 
               VALUES (?, ?, ?, ?, 0)""",
            (usuario_id, token, data_criacao, data_expiracao)
        )
        
        conn.commit()
        conn.close()
        
        return token
        
    except Exception as e:
        print(f"Erro ao gerar token de recuperação: {e}")
        return None

def validar_token_recuperacao(token):
    """Valida token de recuperação de senha"""
    try:
        conn = sqlite3.connect(Config.DATABASE)
        cursor = conn.cursor()
        
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute(
            """SELECT usuario_id FROM tokens_recuperacao 
               WHERE token = ? AND utilizado = 0 AND data_expiracao > ?""",
            (token, agora)
        )
        
        resultado = cursor.fetchone()
        conn.close()
        
        return resultado[0] if resultado else None
        
    except Exception as e:
        print(f"Erro ao validar token: {e}")
        return None

def invalidar_token_recuperacao(token):
    """Invalida token após uso"""
    try:
        conn = sqlite3.connect(Config.DATABASE)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE tokens_recuperacao SET utilizado = 1 WHERE token = ?",
            (token,)
        )
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Erro ao invalidar token: {e}")
        return False

def aplicar_cupom(codigo_cupom, usuario_id):
    """Aplica cupom de desconto/trial"""
    try:
        conn = sqlite3.connect(Config.DATABASE)
        cursor = conn.cursor()
        
        # Busca o cupom
        hoje = datetime.now().strftime("%Y-%m-%d")
        cursor.execute(
            """SELECT * FROM cupons 
               WHERE codigo = ? AND ativo = 1 
               AND (data_fim IS NULL OR data_fim >= ?) 
               AND data_inicio <= ?""",
            (codigo_cupom, hoje, hoje)
        )
        
        cupom = cursor.fetchone()
        
        if not cupom:
            return {'sucesso': False, 'mensagem': 'Cupom inválido ou expirado.'}
        
        # Verifica limite de usos
        if cupom[5] is not None and cupom[6] >= cupom[5]:  # limite_usos e usos_atuais
            return {'sucesso': False, 'mensagem': 'Cupom esgotado.'}
        
        # Verifica se o usuário já usou este cupom
        cursor.execute(
            "SELECT id FROM cupom_usos WHERE cupom_id = ? AND usuario_id = ?",
            (cupom[0], usuario_id)
        )
        
        if cursor.fetchone():
            return {'sucesso': False, 'mensagem': 'Você já utilizou este cupom.'}
        
        # Registra o uso do cupom
        data_uso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO cupom_usos (cupom_id, usuario_id, data_uso) VALUES (?, ?, ?)",
            (cupom[0], usuario_id, data_uso)
        )
        
        # Incrementa contador de usos
        cursor.execute(
            "UPDATE cupons SET usos_atuais = usos_atuais + 1 WHERE id = ?",
            (cupom[0],)
        )
        
        # Aplica o benefício do cupom
        tipo_cupom = cupom[2]  # tipo
        valor_cupom = cupom[3]  # valor
        
        if tipo_cupom == 'trial':
            # Aplica trial gratuito
            from datetime import timedelta
            
            dias_trial = int(valor_cupom)
            data_inicio = datetime.now().strftime("%Y-%m-%d")
            data_fim = (datetime.now() + timedelta(days=dias_trial)).strftime("%Y-%m-%d")
            
            # Cria assinatura trial
            cursor.execute(
                """INSERT INTO assinaturas 
                   (usuario_id, plano, data_inicio, data_fim, valor, status, forma_pagamento) 
                   VALUES (?, 'premium', ?, ?, 0, 'trial', 'cupom')""",
                (usuario_id, data_inicio, data_fim)
            )
            
            # Atualiza plano do usuário
            cursor.execute(
                "UPDATE usuarios SET plano = 'premium' WHERE id = ?",
                (usuario_id,)
            )
            
            mensagem = f'Trial Premium de {dias_trial} dias ativado com sucesso!'
            
        elif tipo_cupom == 'desconto_percentual':
            # Cupom de desconto percentual (será aplicado no checkout)
            mensagem = f'Cupom de {valor_cupom}% de desconto aplicado!'
            
        elif tipo_cupom == 'desconto_fixo':
            # Cupom de desconto fixo (será aplicado no checkout)
            mensagem = f'Cupom de R$ {valor_cupom:.2f} de desconto aplicado!'
            
        else:
            mensagem = 'Cupom aplicado com sucesso!'
        
        conn.commit()
        conn.close()
        
        return {'sucesso': True, 'mensagem': mensagem}
        
    except Exception as e:
        print(f"Erro ao aplicar cupom: {e}")
        return {'sucesso': False, 'mensagem': 'Erro ao aplicar cupom.'}

# Middleware de verificação de login (usado em outros blueprints)
def login_required(f):
    """Decorator para verificar se o usuário está logado"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator para verificar se o usuário é admin"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login', next=request.url))
        
        # Verifica se é admin
        usuario_model = Usuario(Config.DATABASE)
        if not usuario_model.eh_admin(session['usuario_id']):
            flash('Acesso negado. Você precisa ser administrador.', 'error')
            return redirect(url_for('dashboard.index'))
        
        return f(*args, **kwargs)
    return decorated_function

def plano_required(planos_permitidos):
    """Decorator para verificar se o usuário tem um plano específico"""
    def decorator(f):
        from functools import wraps
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'usuario_id' not in session:
                return redirect(url_for('login', next=request.url))
            
            # Verifica o plano do usuário
            usuario_model = Usuario(Config.DATABASE)
            usuario = usuario_model.buscar_por_id(session['usuario_id'])
            
            if usuario and usuario.get('plano') in planos_permitidos:
                return f(*args, **kwargs)
            else:
                flash(f'Esta funcionalidade está disponível apenas para os planos: {", ".join(planos_permitidos)}', 'error')
                return redirect(url_for('planos'))
                
        return decorated_function
    return decorator