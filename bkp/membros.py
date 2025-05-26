# rotas/membros.py
"""
MÓDULO DE MEMBROS
=================
Gerencia membros de família e equipe empresarial:

ROTAS WEB:
- GET /membros/ - Lista membros do usuário
- POST /membros/adicionar - Adicionar novo membro
- POST /membros/editar/<id> - Editar membro
- POST /membros/excluir/<id> - Excluir membro
- POST /membros/reenviar_convite/<id> - Reenviar convite

ROTAS API:
- GET /membros/api - Listar membros (JSON)
- POST /membros/api - Criar membro (JSON)
- PUT /membros/api/<id> - Atualizar membro (JSON)
- DELETE /membros/api/<id> - Excluir membro (JSON)
- POST /membros/api/<id>/reenviar_convite - Reenviar convite

FUNCIONALIDADES:
- Gestão de membros familiares e empresariais
- Sistema de convites por email/WhatsApp
- Controle de permissões (admin, editor, visualizador)
- Limite de membros por plano
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash, session, jsonify
from database.models import Usuario, Membro
from functools import wraps
from config import Config

# Blueprint principal do módulo
membros_bp = Blueprint('membros', __name__, url_prefix='/membros')

# Middleware para verificar login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Middleware para verificar plano
def plano_required(planos_permitidos):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'usuario_id' not in session:
                return redirect(url_for('login', next=request.url))
            
            usuario_model = Usuario(Config.DATABASE)
            usuario = usuario_model.buscar_por_id(session['usuario_id'])
            
            if usuario and usuario.get('plano') in planos_permitidos:
                return f(*args, **kwargs)
            else:
                flash(f'Esta funcionalidade está disponível apenas para os planos: {", ".join(planos_permitidos)}', 'error')
                return redirect(url_for('planos.index'))
                
        return decorated_function
    return decorator

# ==================== ROTAS WEB ====================

@membros_bp.route('/')
@login_required
@plano_required(['familia', 'empresarial'])
def index():
    """Página principal de gerenciamento de membros"""
    usuario_id = session.get('usuario_id')
    
    # Busca dados do usuário
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    # Busca membros
    membro_model = Membro(Config.DATABASE)
    
    membros_familia = membro_model.buscar(
        usuario_id=usuario_id,
        tipo_grupo='familia'
    )
    
    membros_empresa = membro_model.buscar(
        usuario_id=usuario_id,
        tipo_grupo='empresa'
    )
    
    # Limites por plano
    plano = usuario.get('plano', 'gratuito')
    limite_membros = {
        'gratuito': 1,
        'premium': 3,
        'familia': 5,
        'empresarial': 999  # "ilimitado"
    }
    
    limite_atual = limite_membros.get(plano, 1)
    membros_usados_familia = len(membros_familia)
    membros_usados_empresa = len(membros_empresa)
    
    return render_template(
        'membros/index.html',
        app_name=Config.APP_NAME,
        usuario=usuario,
        membros_familia=membros_familia,
        membros_empresa=membros_empresa,
        limite_membros=limite_atual,
        membros_usados_familia=membros_usados_familia,
        membros_usados_empresa=membros_usados_empresa,
        plano=plano
    )

@membros_bp.route('/adicionar', methods=['POST'])
@login_required
@plano_required(['familia', 'empresarial'])
def adicionar():
    """Adicionar novo membro"""
    usuario_id = session.get('usuario_id')
    
    # Dados do formulário
    nome = request.form.get('nome')
    email = request.form.get('email')
    celular = request.form.get('celular')
    permissao = request.form.get('permissao')
    tipo_grupo = request.form.get('tipo_grupo')
    
    # Validações básicas
    if not nome or not email or not tipo_grupo:
        flash('Por favor, preencha todos os campos obrigatórios.', 'error')
        return redirect(url_for('membros.index'))
    
    # Verifica limite de membros baseado no plano
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
        'empresarial': 999
    }
    
    # Verifica se já atingiu o limite
    if num_membros >= limite_membros.get(plano, 1):
        flash(f'Você atingiu o limite de {limite_membros.get(plano, 1)} membros para seu plano atual.', 'error')
        return redirect(url_for('membros.index'))
    
    # Verifica se o email já está cadastrado como membro
    membro_existente = membro_model.buscar_por_email(email, tipo_grupo)
    if membro_existente:
        flash('Este email já está cadastrado como membro.', 'error')
        return redirect(url_for('membros.index'))
    
    try:
        # Cria o membro
        membro_id = membro_model.criar(
            usuario_id=usuario_id,
            nome=nome,
            email=email,
            celular=celular,
            permissao=permissao,
            tipo_grupo=tipo_grupo
        )
        
        # Envia convite
        sucesso_convite, mensagem_convite = membro_model.enviar_convite(membro_id)
        
        flash('Membro adicionado com sucesso!', 'success')
        
        if sucesso_convite:
            flash(mensagem_convite, 'info')
        else:
            flash(f'Erro ao enviar convite: {mensagem_convite}', 'warning')
            
    except Exception as e:
        flash(f'Erro ao adicionar membro: {str(e)}', 'error')
    
    return redirect(url_for('membros.index'))

@membros_bp.route('/editar/<int:membro_id>', methods=['POST'])
@login_required
def editar(membro_id):
    """Editar membro"""
    usuario_id = session.get('usuario_id')
    
    # Verifica se o membro pertence ao usuário
    membro_model = Membro(Config.DATABASE)
    membro = membro_model.buscar_por_id(membro_id)
    
    if not membro or membro.get('usuario_id') != usuario_id:
        flash('Membro não encontrado ou acesso negado.', 'error')
        return redirect(url_for('membros.index'))
    
    # Dados do formulário
    nome = request.form.get('nome')
    permissao = request.form.get('permissao')
    celular = request.form.get('celular')
    
    # Validações básicas
    if not nome:
        flash('Por favor, informe o nome do membro.', 'error')
        return redirect(url_for('membros.index'))
    
    # Verifica se é o usuário principal (não pode mudar permissão)
    if membro.get('usuario_principal') and permissao != 'admin':
        flash('A permissão do usuário principal não pode ser alterada.', 'error')
        permissao = 'admin'
    
    try:
        # Atualiza o membro
        membro_model.atualizar(
            membro_id=membro_id,
            nome=nome,
            permissao=permissao,
            celular=celular
        )
        
        flash('Membro atualizado com sucesso!', 'success')
        
    except Exception as e:
        flash(f'Erro ao atualizar membro: {str(e)}', 'error')
    
    return redirect(url_for('membros.index'))

@membros_bp.route('/excluir/<int:membro_id>', methods=['POST'])
@login_required
def excluir(membro_id):
    """Excluir membro"""
    usuario_id = session.get('usuario_id')
    
    # Verifica se o membro pertence ao usuário
    membro_model = Membro(Config.DATABASE)
    membro = membro_model.buscar_por_id(membro_id)
    
    if not membro or membro.get('usuario_id') != usuario_id:
        flash('Membro não encontrado ou acesso negado.', 'error')
        return redirect(url_for('membros.index'))
    
    # Verifica se é o usuário principal (não pode ser excluído)
    if membro.get('usuario_principal'):
        flash('O usuário principal não pode ser excluído.', 'error')
        return redirect(url_for('membros.index'))
    
    try:
        # Exclui o membro
        sucesso, mensagem = membro_model.excluir(membro_id)
        
        if sucesso:
            flash('Membro excluído com sucesso!', 'success')
        else:
            flash(f'Erro ao excluir membro: {mensagem}', 'error')
            
    except Exception as e:
        flash(f'Erro ao excluir membro: {str(e)}', 'error')
    
    return redirect(url_for('membros.index'))

@membros_bp.route('/reenviar_convite/<int:membro_id>', methods=['POST'])
@login_required
def reenviar_convite(membro_id):
    """Reenviar convite para um membro"""
    usuario_id = session.get('usuario_id')
    
    # Verifica se o membro pertence ao usuário
    membro_model = Membro(Config.DATABASE)
    membro = membro_model.buscar_por_id(membro_id)
    
    if not membro or membro.get('usuario_id') != usuario_id:
        flash('Membro não encontrado ou acesso negado.', 'error')
        return redirect(url_for('membros.index'))
    
    # Verifica se o convite já foi aceito
    if membro.get('convite_aceito') == 1:
        flash('O convite já foi aceito.', 'info')
        return redirect(url_for('membros.index'))
    
    try:
        # Reenvia o convite
        sucesso, mensagem = membro_model.enviar_convite(membro_id)
        
        if sucesso:
            flash(f'Convite reenviado com sucesso! {mensagem}', 'success')
        else:
            flash(f'Erro ao reenviar convite: {mensagem}', 'error')
            
    except Exception as e:
        flash(f'Erro ao reenviar convite: {str(e)}', 'error')
    
    return redirect(url_for('membros.index'))

# ==================== ROTAS API ====================

@membros_bp.route('/api')
@login_required
def api_listar():
    """API para obter membros do usuário"""
    usuario_id = session.get('usuario_id')
    
    # Parâmetros de filtro
    tipo_grupo = request.args.get('tipo_grupo')
    
    # Busca os membros
    membro_model = Membro(Config.DATABASE)
    membros = membro_model.buscar(
        usuario_id=usuario_id,
        tipo_grupo=tipo_grupo
    )
    
    return jsonify(membros)

@membros_bp.route('/api', methods=['POST'])
@login_required
@plano_required(['familia', 'empresarial'])
def api_criar():
    """API para adicionar um membro"""
    usuario_id = session.get('usuario_id')
    dados = request.json
    
    # Validações básicas
    if not dados or 'nome' not in dados or 'email' not in dados or 'tipo_grupo' not in dados:
        return jsonify({"error": "Dados incompletos"}), 400
    
    try:
        # Verifica limite de membros
        usuario_model = Usuario(Config.DATABASE)
        usuario = usuario_model.buscar_por_id(usuario_id)
        plano = usuario.get('plano', 'gratuito')
        
        membro_model = Membro(Config.DATABASE)
        membros_atuais = membro_model.buscar(usuario_id, dados['tipo_grupo'])
        num_membros = len(membros_atuais)
        
        limite_membros = {
            'gratuito': 1,
            'premium': 3,
            'familia': 5,
            'empresarial': 999
        }
        
        if num_membros >= limite_membros.get(plano, 1):
            return jsonify({"error": f"Limite de {limite_membros.get(plano, 1)} membros atingido"}), 400
        
        # Verifica se email já existe
        membro_existente = membro_model.buscar_por_email(dados['email'], dados['tipo_grupo'])
        if membro_existente:
            return jsonify({"error": "Este email já está cadastrado como membro"}), 400
        
        # Prepara os dados
        nome = dados['nome']
        email = dados['email']
        celular = dados.get('celular')
        permissao = dados.get('permissao', 'visualizador')
        tipo_grupo = dados['tipo_grupo']
        
        # Cria o membro
        membro_id = membro_model.criar(
            usuario_id=usuario_id,
            nome=nome,
            email=email,
            celular=celular,
            permissao=permissao,
            tipo_grupo=tipo_grupo
        )
        
        # Envia convite
        sucesso_convite, mensagem_convite = membro_model.enviar_convite(membro_id)
        
        return jsonify({
            "success": True, 
            "id": membro_id,
            "convite_enviado": sucesso_convite,
            "mensagem_convite": mensagem_convite
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@membros_bp.route('/api/<int:membro_id>', methods=['PUT'])
@login_required
def api_atualizar(membro_id):
    """API para atualizar um membro"""
    usuario_id = session.get('usuario_id')
    dados = request.json
    
    # Busca o membro para verificar se pertence ao usuário
    membro_model = Membro(Config.DATABASE)
    membro = membro_model.buscar_por_id(membro_id)
    
    if not membro:
        return jsonify({"error": "Membro não encontrado"}), 404
    
    # Verifica se o membro pertence ao usuário logado
    if membro['usuario_id'] != usuario_id:
        return jsonify({"error": "Não autorizado"}), 403
    
    # Verifica se é o usuário principal tentando mudar a permissão
    if membro.get('usuario_principal') == 1 and 'permissao' in dados:
        return jsonify({"error": "Não é possível alterar a permissão do usuário principal"}), 400
    
    try:
        # Atualiza os dados que foram enviados
        campos_update = {}
        
        for campo in ['nome', 'email', 'celular', 'permissao', 'convite_aceito']:
            if campo in dados:
                if campo == 'convite_aceito':
                    campos_update[campo] = int(dados[campo])
                else:
                    campos_update[campo] = dados[campo]
        
        # Atualiza o membro
        membro_model.atualizar(membro_id, **campos_update)
        
        return jsonify({"success": True}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@membros_bp.route('/api/<int:membro_id>', methods=['DELETE'])
@login_required
def api_excluir(membro_id):
    """API para excluir um membro"""
    usuario_id = session.get('usuario_id')
    
    # Busca o membro para verificar se pertence ao usuário
    membro_model = Membro(Config.DATABASE)
    membro = membro_model.buscar_por_id(membro_id)
    
    if not membro:
        return jsonify({"error": "Membro não encontrado"}), 404
    
    # Verifica se o membro pertence ao usuário logado
    if membro['usuario_id'] != usuario_id:
        return jsonify({"error": "Não autorizado"}), 403
    
    # Verifica se é o usuário principal
    if membro.get('usuario_principal') == 1:
        return jsonify({"error": "Não é possível excluir o usuário principal"}), 400
    
    # Exclui o membro
    sucesso, mensagem = membro_model.excluir(membro_id)
    
    if sucesso:
        return jsonify({"success": True}), 200
    else:
        return jsonify({"error": mensagem}), 400

@membros_bp.route('/api/<int:membro_id>/reenviar_convite', methods=['POST'])
@login_required
def api_reenviar_convite(membro_id):
    """API para reenviar convite para um membro"""
    usuario_id = session.get('usuario_id')
    
    # Busca o membro para verificar se pertence ao usuário
    membro_model = Membro(Config.DATABASE)
    membro = membro_model.buscar_por_id(membro_id)
    
    if not membro:
        return jsonify({"error": "Membro não encontrado"}), 404
    
    # Verifica se o membro pertence ao usuário logado
    if membro['usuario_id'] != usuario_id:
        return jsonify({"error": "Não autorizado"}), 403
    
    # Verifica se o convite já foi aceito
    if membro.get('convite_aceito') == 1:
        return jsonify({"error": "O convite já foi aceito"}), 400
    
    # Envia o convite
    sucesso, mensagem = membro_model.enviar_convite(membro_id)
    
    if sucesso:
        return jsonify({"success": True, "message": mensagem}), 200
    else:
        return jsonify({"error": mensagem}), 400

@membros_bp.route('/api/estatisticas')
@login_required
def api_estatisticas():
    """API para obter estatísticas de membros"""
    usuario_id = session.get('usuario_id')
    
    # Busca todos os membros
    membro_model = Membro(Config.DATABASE)
    membros_familia = membro_model.buscar(usuario_id=usuario_id, tipo_grupo='familia')
    membros_empresa = membro_model.buscar(usuario_id=usuario_id, tipo_grupo='empresa')
    
    # Estatísticas básicas
    stats = {
        'total_membros': len(membros_familia) + len(membros_empresa),
        'membros_familia': len(membros_familia),
        'membros_empresa': len(membros_empresa),
        'convites_pendentes': 0,
        'membros_ativos': 0,
        'por_permissao': {
            'admin': 0,
            'editor': 0,
            'visualizador': 0
        }
    }
    
    # Conta estatísticas detalhadas
    todos_membros = membros_familia + membros_empresa
    
    for membro in todos_membros:
        # Convites pendentes
        if membro.get('convite_aceito') == 0:
            stats['convites_pendentes'] += 1
        else:
            stats['membros_ativos'] += 1
        
        # Por permissão
        permissao = membro.get('permissao', 'visualizador')
        if permissao in stats['por_permissao']:
            stats['por_permissao'][permissao] += 1
    
    # Limites do plano
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    plano = usuario.get('plano', 'gratuito')
    
    limite_membros = {
        'gratuito': 1,
        'premium': 3,
        'familia': 5,
        'empresarial': 999
    }
    
    stats['limite_plano'] = limite_membros.get(plano, 1)
    stats['plano_atual'] = plano
    stats['pode_adicionar'] = stats['total_membros'] < stats['limite_plano']
    
    return jsonify(stats)

# ==================== FUNCIONALIDADES AUXILIARES ====================

def verificar_permissao_membro(usuario_id, membro_id, acao_requerida):
    """Verifica se um membro tem permissão para realizar uma ação"""
    membro_model = Membro(Config.DATABASE)
    membro = membro_model.buscar_por_id(membro_id)
    
    if not membro or membro['usuario_id'] != usuario_id:
        return False
    
    permissao = membro.get('permissao', 'visualizador')
    
    # Mapeamento de permissões
    permissoes = {
        'visualizador': ['visualizar'],
        'editor': ['visualizar', 'editar', 'criar'],
        'admin': ['visualizar', 'editar', 'criar', 'excluir', 'gerenciar_membros']
    }
    
    return acao_requerida in permissoes.get(permissao, [])

def get_membros_ativos(usuario_id, tipo_grupo=None):
    """Retorna apenas membros com convites aceitos"""
    membro_model = Membro(Config.DATABASE)
    todos_membros = membro_model.buscar(usuario_id=usuario_id, tipo_grupo=tipo_grupo)
    
    return [m for m in todos_membros if m.get('convite_aceito') == 1]

def criar_membro_principal(usuario_id, tipo_grupo='familia'):
    """Cria o membro principal (dono da conta) automaticamente"""
    try:
        # Busca dados do usuário
        usuario_model = Usuario(Config.DATABASE)
        usuario = usuario_model.buscar_por_id(usuario_id)
        
        if not usuario:
            return False
        
        # Cria membro principal
        membro_model = Membro(Config.DATABASE)
        membro_id = membro_model.criar(
            usuario_id=usuario_id,
            nome=usuario['nome'],
            email=usuario['email'],
            permissao='admin',
            tipo_grupo=tipo_grupo,
            usuario_principal=True,
            convite_aceito=True
        )
        
        return membro_id
        
    except Exception as e:
        print(f"Erro ao criar membro principal: {e}")
        return False