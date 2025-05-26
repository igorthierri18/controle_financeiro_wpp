# rotas/planos.py
"""
MÓDULO DE PLANOS E ASSINATURAS
==============================
Gerencia planos de assinatura e pagamentos:

ROTAS WEB:
- GET /planos/ - Página de planos disponíveis
- GET/POST /planos/assinar/<plano> - Processo de assinatura
- POST /planos/cancelar - Cancelar assinatura
- GET /planos/historico - Histórico de pagamentos

ROTAS API:
- GET /planos/api - Informações dos planos (JSON)
- POST /planos/api/assinar - Processar assinatura (JSON)
- POST /planos/api/cancelar - Cancelar assinatura (JSON)
- GET /planos/api/status - Status da assinatura atual

FUNCIONALIDADES:
- Comparação de planos
- Processamento de pagamentos
- Upgrade/downgrade de planos
- Histórico de faturas
- Integração com gateways de pagamento
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash, session, jsonify
from database.models import Usuario
from functools import wraps
from datetime import datetime, timedelta
from config import Config
import sqlite3

# Blueprint principal do módulo
planos_bp = Blueprint('planos', __name__, url_prefix='/planos')

# Middleware para verificar login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# ==================== ROTAS WEB ====================

@planos_bp.route('/')
def index():
    """Página de planos de assinatura"""
    # Se o usuário estiver logado, obtém o plano atual
    plano_atual = None
    usuario = None
    
    if 'usuario_id' in session:
        usuario_model = Usuario(Config.DATABASE)
        usuario = usuario_model.buscar_por_id(session['usuario_id'])
        if usuario:
            plano_atual = usuario.get('plano', 'gratuito')
    
    # Definição dos planos
    planos = get_planos_disponiveis()
    
    return render_template(
        'planos.html',  # Corrigido: usar template correto
        app_name=Config.APP_NAME,
        planos=planos,
        plano_atual=plano_atual,
        usuario=usuario
    )

@planos_bp.route('/assinar/<plano>', methods=['GET', 'POST'])
@login_required
def assinar(plano):
    """Página de assinatura de plano"""
    # Verifica se o plano é válido
    planos_validos = ['gratuito', 'premium', 'familia', 'empresarial']
    if plano not in planos_validos:
        flash('Plano inválido.', 'error')
        return redirect(url_for('planos.index'))
    
    # Obtém dados do usuário
    usuario_id = session.get('usuario_id')
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    # Se o usuário já está no plano selecionado
    if usuario and usuario.get('plano') == plano:
        flash(f'Você já está no plano {plano.capitalize()}.', 'info')
        return redirect(url_for('planos.index'))
    
    # Informações do plano
    planos_info = get_planos_disponiveis()
    plano_info = planos_info.get(plano)
    
    if not plano_info:
        flash('Plano não encontrado.', 'error')
        return redirect(url_for('planos.index'))
    
    if request.method == 'POST':
        # Processa a assinatura
        resultado = processar_assinatura(usuario_id, plano, request.form)
        
        if resultado['sucesso']:
            flash(resultado['mensagem'], 'success')
            return redirect(url_for('web.dashboard'))  # Corrigido: usar rota correta
        else:
            flash(resultado['mensagem'], 'error')
    
    # GET - Renderiza página de assinatura
    return render_template(
        'assinatura.html',  # Template específico para assinatura
        app_name=Config.APP_NAME,
        usuario=usuario,
        plano=plano,
        plano_info=plano_info
    )

@planos_bp.route('/cancelar', methods=['POST'])
@login_required
def cancelar():
    """Cancelar assinatura"""
    usuario_id = session.get('usuario_id')
    
    try:
        # Cancela a assinatura
        resultado = cancelar_assinatura(usuario_id)
        
        if resultado['sucesso']:
            flash(resultado['mensagem'], 'success')
        else:
            flash(resultado['mensagem'], 'error')
            
    except Exception as e:
        flash(f'Erro ao cancelar assinatura: {str(e)}', 'error')
    
    return redirect(url_for('planos.index'))

@planos_bp.route('/historico')
@login_required
def historico():
    """Histórico de pagamentos e faturas"""
    usuario_id = session.get('usuario_id')
    
    # Busca dados do usuário
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    # Busca histórico de pagamentos
    historico_pagamentos = get_historico_pagamentos(usuario_id)
    
    return render_template(
        'planos_historico.html',  # Template específico para histórico
        app_name=Config.APP_NAME,
        usuario=usuario,
        historico=historico_pagamentos
    )

@planos_bp.route('/comparacao')
def comparacao():
    """Página de comparação detalhada de planos"""
    planos = get_planos_disponiveis()
    recursos = get_recursos_detalhados()
    
    return render_template(
        'planos_comparacao.html',  # Template específico para comparação
        app_name=Config.APP_NAME,
        planos=planos,
        recursos=recursos
    )

# ==================== ROTAS API ====================

@planos_bp.route('/api')
def api_listar():
    """API para obter informações dos planos"""
    planos = get_planos_disponiveis()
    return jsonify(planos)

@planos_bp.route('/api/assinar', methods=['POST'])
@login_required
def api_assinar():
    """API para processar assinatura"""
    usuario_id = session.get('usuario_id')
    dados = request.json
    
    if not dados or 'plano' not in dados:
        return jsonify({"error": "Plano não especificado"}), 400
    
    plano = dados['plano']
    
    # Verifica se o plano é válido
    planos_validos = ['gratuito', 'premium', 'familia', 'empresarial']
    if plano not in planos_validos:
        return jsonify({"error": "Plano inválido"}), 400
    
    try:
        # Processa a assinatura
        resultado = processar_assinatura(usuario_id, plano, dados)
        
        if resultado['sucesso']:
            return jsonify({
                "success": True,
                "message": resultado['mensagem'],
                "plano": plano
            }), 200
        else:
            return jsonify({"error": resultado['mensagem']}), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@planos_bp.route('/api/cancelar', methods=['POST'])
@login_required
def api_cancelar():
    """API para cancelar assinatura"""
    usuario_id = session.get('usuario_id')
    
    try:
        resultado = cancelar_assinatura(usuario_id)
        
        if resultado['sucesso']:
            return jsonify({
                "success": True,
                "message": resultado['mensagem']
            }), 200
        else:
            return jsonify({"error": resultado['mensagem']}), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@planos_bp.route('/api/status')
@login_required
def api_status():
    """API para obter status da assinatura"""
    usuario_id = session.get('usuario_id')
    
    # Busca dados do usuário
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    if not usuario:
        return jsonify({"error": "Usuário não encontrado"}), 404
    
    plano_atual = usuario.get('plano', 'gratuito')
    planos_info = get_planos_disponiveis()
    
    status = {
        'plano_atual': plano_atual,
        'info_plano': planos_info.get(plano_atual, {}),
        'data_assinatura': usuario.get('data_assinatura'),
        'data_vencimento': usuario.get('data_vencimento'),
        'status_pagamento': usuario.get('status_pagamento', 'ativo'),
        'pode_upgrade': plano_atual != 'empresarial',
        'pode_cancelar': plano_atual != 'gratuito'
    }
    
    return jsonify(status)

@planos_bp.route('/api/upgrade/<novo_plano>', methods=['POST'])
@login_required
def api_upgrade(novo_plano):
    """API para fazer upgrade de plano"""
    usuario_id = session.get('usuario_id')
    
    # Verifica se o novo plano é válido
    planos_validos = ['premium', 'familia', 'empresarial']
    if novo_plano not in planos_validos:
        return jsonify({"error": "Plano inválido para upgrade"}), 400
    
    try:
        # Busca usuário atual
        usuario_model = Usuario(Config.DATABASE)
        usuario = usuario_model.buscar_por_id(usuario_id)
        plano_atual = usuario.get('plano', 'gratuito')
        
        # Verifica se é realmente um upgrade
        hierarquia_planos = ['gratuito', 'premium', 'familia', 'empresarial']
        
        if hierarquia_planos.index(novo_plano) <= hierarquia_planos.index(plano_atual):
            return jsonify({"error": "Este não é um upgrade válido"}), 400
        
        # Processa o upgrade
        resultado = processar_upgrade(usuario_id, plano_atual, novo_plano)
        
        if resultado['sucesso']:
            return jsonify({
                "success": True,
                "message": resultado['mensagem'],
                "plano_anterior": plano_atual,
                "plano_novo": novo_plano
            }), 200
        else:
            return jsonify({"error": resultado['mensagem']}), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== WEBHOOKS ====================

def processar_webhook_planos(mensagem, usuario_id):
    """Processa comandos de planos via webhook"""
    mensagem_lower = mensagem.lower()
    
    if mensagem_lower in ["planos", "mudar plano", "info planos", "ver planos"]:
        return get_info_planos_webhook()
    
    elif mensagem_lower.startswith("assinar "):
        plano = mensagem_lower.replace("assinar ", "").strip()
        return processar_assinatura_webhook(usuario_id, plano)
    
    return None

def get_info_planos_webhook():
    """Retorna informações sobre os planos via webhook"""
    planos = get_planos_disponiveis()
    
    return (
        f"💳 *Planos {Config.APP_NAME}*\n\n"
        f"*{planos['gratuito']['nome']}* - Grátis\n"
        f"- {planos['gratuito']['limite_transacoes']} transações/mês\n"
        f"- Dashboard básico\n"
        f"- {planos['gratuito']['usuarios']} usuário\n\n"
        
        f"*{planos['premium']['nome']}* - R$ {planos['premium']['preco']:.2f}/mês\n"
        f"- Transações ilimitadas\n"
        f"- Dashboard completo\n"
        f"- {planos['premium']['usuarios']} usuários\n"
        f"- Relatórios detalhados\n\n"
        
        f"*{planos['familia']['nome']}* - R$ {planos['familia']['preco']:.2f}/mês\n"
        f"- Todos os recursos Premium\n"
        f"- {planos['familia']['usuarios']} usuários\n"
        f"- Perfil empresarial\n"
        f"- Grupos familiares\n\n"
        
        f"*{planos['empresarial']['nome']}* - R$ {planos['empresarial']['preco']:.2f}/mês\n"
        f"- Todos os recursos Família\n"
        f"- Usuários ilimitados\n"
        f"- API para integrações\n"
        f"- Suporte prioritário\n\n"
        
        f"Para assinar, acesse:\n{Config.WEBHOOK_BASE_URL}/planos"
    )

def processar_assinatura_webhook(usuario_id, plano):
    """Processa assinatura via webhook"""
    planos_validos = ['premium', 'familia', 'empresarial']
    
    if plano not in planos_validos:
        return f"Plano '{plano}' não encontrado. Planos disponíveis: {', '.join(planos_validos)}"
    
    # Retorna link para assinatura (não processa pagamento via webhook)
    return (
        f"Para assinar o plano {plano.capitalize()}, acesse:\n"
        f"{Config.WEBHOOK_BASE_URL}/planos/assinar/{plano}\n\n"
        f"Lá você poderá escolher a forma de pagamento e finalizar sua assinatura com segurança."
    )

# ==================== FUNÇÕES AUXILIARES ====================

def get_planos_disponiveis():
    """Retorna informações dos planos disponíveis"""
    return {
        'gratuito': {
            'nome': 'Gratuito',
            'preco': 0,
            'preco_anual': 0,
            'limite_transacoes': 3000,
            'dashboard': 'básico',
            'categorias': 'limitadas (8)',
            'usuarios': 1,
            'exportacao_dados': False,
            'relatorios_detalhados': False,
            'suporte': 'comunidade',
            'recursos': [
                'Dashboard básico',
                'Até 3.000 transações/mês',
                '8 categorias pré-definidas',
                '1 usuário',
                'Suporte da comunidade'
            ]
        },
        'premium': {
            'nome': 'Premium',
            'preco': 29.90,
            'preco_anual': 299.00,  # 2 meses grátis
            'transacoes': 'ilimitadas',
            'dashboard': 'completo',
            'categorias': 'personalizadas',
            'usuarios': 3,
            'exportacao_dados': 'CSV',
            'relatorios_detalhados': True,
            'suporte': 'email',
            'recursos': [
                'Transações ilimitadas',
                'Dashboard completo',
                'Categorias personalizadas',
                'Até 3 usuários',
                'Exportação CSV',
                'Relatórios detalhados',
                'Suporte por email'
            ]
        },
        'familia': {
            'nome': 'Família',
            'preco': 32.90,
            'preco_anual': 329.00,
            'transacoes': 'ilimitadas',
            'dashboard': 'completo',
            'categorias': 'personalizadas',
            'usuarios': 5,
            'exportacao_dados': 'CSV/Excel',
            'perfil_empresarial': True,
            'grupos': 'familiares ilimitados',
            'integracao_google': True,
            'suporte': 'prioritário',
            'recursos': [
                'Todos os recursos Premium',
                'Até 5 usuários',
                'Perfil empresarial',
                'Grupos familiares',
                'Integração Google Calendar',
                'Exportação Excel',
                'Suporte prioritário'
            ]
        },
        'empresarial': {
            'nome': 'Empresarial',
            'preco': 39.90,
            'preco_anual': 399.00,
            'transacoes': 'ilimitadas',
            'dashboard': 'completo',
            'categorias': 'personalizadas',
            'usuarios': 'ilimitados',
            'exportacao_dados': 'todos os formatos',
            'perfil_empresarial': True,
            'grupos': 'ilimitados',
            'api_integracao': True,
            'suporte': 'prioritário + telefone',
            'recursos': [
                'Todos os recursos Família',
                'Usuários ilimitados',
                'API para integrações',
                'Relatórios avançados',
                'Análise preditiva',
                'Suporte por telefone',
                'Gerente de conta dedicado'
            ]
        }
    }

def get_recursos_detalhados():
    """Retorna recursos detalhados para comparação"""
    return {
        'Transações por mês': {
            'gratuito': '3.000',
            'premium': 'Ilimitadas',
            'familia': 'Ilimitadas',
            'empresarial': 'Ilimitadas'
        },
        'Número de usuários': {
            'gratuito': '1',
            'premium': '3',
            'familia': '5',
            'empresarial': 'Ilimitados'
        },
        'Categorias personalizadas': {
            'gratuito': '❌',
            'premium': '✅',
            'familia': '✅',
            'empresarial': '✅'
        },
        'Dashboard avançado': {
            'gratuito': '❌',
            'premium': '✅',
            'familia': '✅',
            'empresarial': '✅'
        },
        'Relatórios detalhados': {
            'gratuito': '❌',
            'premium': '✅',
            'familia': '✅',
            'empresarial': '✅'
        },
        'Exportação de dados': {
            'gratuito': '❌',
            'premium': 'CSV',
            'familia': 'CSV/Excel',
            'empresarial': 'Todos formatos'
        },
        'Perfil empresarial': {
            'gratuito': '❌',
            'premium': '❌',
            'familia': '✅',
            'empresarial': '✅'
        },
        'API para integrações': {
            'gratuito': '❌',
            'premium': '❌',
            'familia': '❌',
            'empresarial': '✅'
        },
        'Suporte': {
            'gratuito': 'Comunidade',
            'premium': 'Email',
            'familia': 'Prioritário',
            'empresarial': 'Telefone + Dedicado'
        }
    }

def processar_assinatura(usuario_id, plano, dados_pagamento):
    """Processa uma nova assinatura"""
    try:
        usuario_model = Usuario(Config.DATABASE)
        usuario = usuario_model.buscar_por_id(usuario_id)
        
        if not usuario:
            return {'sucesso': False, 'mensagem': 'Usuário não encontrado'}
        
        planos_info = get_planos_disponiveis()
        plano_info = planos_info.get(plano)
        
        if not plano_info:
            return {'sucesso': False, 'mensagem': 'Plano inválido'}
        
        # Se for plano gratuito, apenas atualiza
        if plano == 'gratuito':
            usuario_model.atualizar(usuario_id, plano=plano)
            return {'sucesso': True, 'mensagem': 'Plano atualizado para Gratuito'}
        
        # Para planos pagos, processa pagamento
        metodo_pagamento = dados_pagamento.get('payment_method', 'credit_card')
        periodo = dados_pagamento.get('period', 'monthly')
        
        # Calcula valor
        if periodo == 'yearly':
            valor = plano_info['preco_anual']
            desconto = True
        else:
            valor = plano_info['preco']
            desconto = False
        
        # Simula processamento de pagamento
        pagamento_aprovado = simular_pagamento(usuario_id, valor, metodo_pagamento)
        
        if not pagamento_aprovado['sucesso']:
            return {'sucesso': False, 'mensagem': pagamento_aprovado['mensagem']}
        
        # Atualiza dados do usuário
        data_inicio = datetime.now()
        if periodo == 'yearly':
            data_vencimento = data_inicio + timedelta(days=365)
        else:
            data_vencimento = data_inicio + timedelta(days=30)
        
        usuario_model.atualizar(
            usuario_id,
            plano=plano,
            data_assinatura=data_inicio.strftime("%Y-%m-%d"),
            data_vencimento=data_vencimento.strftime("%Y-%m-%d")
        )
        
        # Registra pagamento no histórico
        registrar_pagamento(usuario_id, plano, valor, periodo, pagamento_aprovado['transaction_id'])
        
        mensagem = f'Assinatura {plano.capitalize()} ativada com sucesso!'
        if desconto:
            mensagem += f' Você economizou R$ {(plano_info["preco"] * 12) - valor:.2f} com o plano anual!'
        
        return {'sucesso': True, 'mensagem': mensagem}
        
    except Exception as e:
        return {'sucesso': False, 'mensagem': f'Erro ao processar assinatura: {str(e)}'}

def cancelar_assinatura(usuario_id):
    """Cancela a assinatura do usuário"""
    try:
        usuario_model = Usuario(Config.DATABASE)
        usuario = usuario_model.buscar_por_id(usuario_id)
        
        if not usuario:
            return {'sucesso': False, 'mensagem': 'Usuário não encontrado'}
        
        plano_atual = usuario.get('plano', 'gratuito')
        
        if plano_atual == 'gratuito':
            return {'sucesso': False, 'mensagem': 'Você já está no plano gratuito'}
        
        # Atualiza para plano gratuito
        usuario_model.atualizar(usuario_id, plano='gratuito')
        
        # Registra cancelamento
        registrar_cancelamento(usuario_id, plano_atual)
        
        return {
            'sucesso': True, 
            'mensagem': 'Assinatura cancelada. Seu plano foi alterado para Gratuito.'
        }
        
    except Exception as e:
        return {'sucesso': False, 'mensagem': f'Erro ao cancelar: {str(e)}'}

def processar_upgrade(usuario_id, plano_atual, novo_plano):
    """Processa upgrade de plano"""
    try:
        planos_info = get_planos_disponiveis()
        plano_info = planos_info.get(novo_plano)
        
        # Calcula diferença proporcional
        valor_diferenca = plano_info['preco'] - planos_info[plano_atual]['preco']
        
        # Simula cobrança da diferença
        pagamento_aprovado = simular_pagamento(usuario_id, valor_diferenca, 'credit_card')
        
        if not pagamento_aprovado['sucesso']:
            return {'sucesso': False, 'mensagem': pagamento_aprovado['mensagem']}
        
        # Atualiza plano
        usuario_model = Usuario(Config.DATABASE)
        usuario_model.atualizar(usuario_id, plano=novo_plano)
        
        # Registra upgrade
        registrar_upgrade(usuario_id, plano_atual, novo_plano, valor_diferenca)
        
        return {
            'sucesso': True,
            'mensagem': f'Upgrade para {novo_plano.capitalize()} realizado com sucesso!'
        }
        
    except Exception as e:
        return {'sucesso': False, 'mensagem': f'Erro no upgrade: {str(e)}'}

def simular_pagamento(usuario_id, valor, metodo):
    """Simula processamento de pagamento"""
    import random
    
    if valor <= 0:
        return {'sucesso': False, 'mensagem': 'Valor inválido'}
    
    if metodo not in ['credit_card', 'debit_card', 'pix', 'bank_slip']:
        return {'sucesso': False, 'mensagem': 'Método de pagamento inválido'}
    
    # 95% de aprovação (simulação)
    if random.random() < 0.95:
        transaction_id = f'txn_{datetime.now().strftime("%Y%m%d%H%M%S")}_{usuario_id}'
        return {
            'sucesso': True,
            'mensagem': 'Pagamento aprovado',
            'transaction_id': transaction_id
        }
    else:
        return {'sucesso': False, 'mensagem': 'Pagamento recusado pelo banco'}

def registrar_pagamento(usuario_id, plano, valor, periodo, transaction_id):
    """Registra pagamento no histórico"""
    try:
        conn = sqlite3.connect(Config.DATABASE)
        cursor = conn.cursor()
        
        # Cria tabela se não existir
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pagamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                plano TEXT,
                valor REAL,
                periodo TEXT,
                transaction_id TEXT,
                status TEXT DEFAULT 'aprovado',
                data_pagamento DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
            )
        ''')
        
        # Insere pagamento
        cursor.execute('''
            INSERT INTO pagamentos (usuario_id, plano, valor, periodo, transaction_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (usuario_id, plano, valor, periodo, transaction_id))
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Erro ao registrar pagamento: {e}")
        return False

def registrar_cancelamento(usuario_id, plano_cancelado):
    """Registra cancelamento no histórico"""
    try:
        conn = sqlite3.connect(Config.DATABASE)
        cursor = conn.cursor()
        
        # Cria tabela se não existir
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cancelamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                plano_cancelado TEXT,
                motivo TEXT,
                data_cancelamento DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
            )
        ''')
        
        # Insere cancelamento
        cursor.execute('''
            INSERT INTO cancelamentos (usuario_id, plano_cancelado, motivo)
            VALUES (?, ?, ?)
        ''', (usuario_id, plano_cancelado, 'Cancelamento via sistema'))
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Erro ao registrar cancelamento: {e}")
        return False

def registrar_upgrade(usuario_id, plano_anterior, plano_novo, valor_diferenca):
    """Registra upgrade no histórico"""
    try:
        conn = sqlite3.connect(Config.DATABASE)
        cursor = conn.cursor()
        
        # Cria tabela se não existir
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS upgrades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                plano_anterior TEXT,
                plano_novo TEXT,
                valor_diferenca REAL,
                data_upgrade DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
            )
        ''')
        
        # Insere upgrade
        cursor.execute('''
            INSERT INTO upgrades (usuario_id, plano_anterior, plano_novo, valor_diferenca)
            VALUES (?, ?, ?, ?)
        ''', (usuario_id, plano_anterior, plano_novo, valor_diferenca))
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Erro ao registrar upgrade: {e}")
        return False

def get_historico_pagamentos(usuario_id):
    """Busca histórico de pagamentos do usuário"""
    try:
        conn = sqlite3.connect(Config.DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Busca pagamentos
        cursor.execute('''
            SELECT * FROM pagamentos 
            WHERE usuario_id = ? 
            ORDER BY data_pagamento DESC 
            LIMIT 20
        ''', (usuario_id,))
        
        pagamentos = [dict(row) for row in cursor.fetchall()]
        
        # Busca cancelamentos
        cursor.execute('''
            SELECT * FROM cancelamentos 
            WHERE usuario_id = ? 
            ORDER BY data_cancelamento DESC 
            LIMIT 10
        ''', (usuario_id,))
        
        cancelamentos = [dict(row) for row in cursor.fetchall()]
        
        # Busca upgrades
        cursor.execute('''
            SELECT * FROM upgrades 
            WHERE usuario_id = ? 
            ORDER BY data_upgrade DESC 
            LIMIT 10
        ''', (usuario_id,))
        
        upgrades = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'pagamentos': pagamentos,
            'cancelamentos': cancelamentos,
            'upgrades': upgrades
        }
        
    except Exception as e:
        print(f"Erro ao buscar histórico: {e}")
        return {
            'pagamentos': [],
            'cancelamentos': [],
            'upgrades': []
        }