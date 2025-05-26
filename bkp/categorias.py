from flask import Blueprint, render_template, redirect, url_for, request, flash, session, jsonify
from database.models import Usuario, CategoriaPersonalizada, Despesa, Receita
from functools import wraps
from config import Config
import sqlite3

categorias_bp = Blueprint('categorias', __name__, url_prefix='/categorias')

# Middleware para verificar login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Middleware para verificar plano
def plano_required(planos_permitidos):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'usuario_id' not in session:
                return redirect(url_for('auth.login', next=request.url))
            
            usuario_model = Usuario(Config.DATABASE)
            usuario = usuario_model.buscar_por_id(session['usuario_id'])
            
            if usuario and usuario.get('plano') in planos_permitidos:
                return f(*args, **kwargs)
            else:
                flash(f'Esta funcionalidade está disponível apenas para os planos: {", ".join(planos_permitidos)}', 'error')
                return redirect(url_for('web.planos'))
                
        return decorated_function
    return decorator

# ==================== ROTAS WEB ====================

@categorias_bp.route('/')
@login_required
@plano_required(['premium', 'familia', 'empresarial'])
def index():
    """Página principal de categorias personalizadas"""
    usuario_id = session.get('usuario_id')
    
    # Busca dados do usuário
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    if not usuario:
        flash('Usuário não encontrado.', 'error')
        return redirect(url_for('auth.logout'))
    
    # Busca categorias existentes
    categoria_model = CategoriaPersonalizada(Config.DATABASE)
    
    # Categorias de despesa
    categorias_despesa_pessoais = categoria_model.buscar(
        usuario_id=usuario_id,
        tipo='despesa',
        tipo_perfil='pessoal'
    )
    
    categorias_despesa_empresariais = categoria_model.buscar(
        usuario_id=usuario_id,
        tipo='despesa',
        tipo_perfil='empresarial'
    )
    
    # Categorias de receita
    categorias_receita_pessoais = categoria_model.buscar(
        usuario_id=usuario_id,
        tipo='receita',
        tipo_perfil='pessoal'
    )
    
    categorias_receita_empresariais = categoria_model.buscar(
        usuario_id=usuario_id,
        tipo='receita',
        tipo_perfil='empresarial'
    )
    
    # Adiciona estatísticas de uso para cada categoria
    for categorias_lista in [categorias_despesa_pessoais, categorias_despesa_empresariais, 
                            categorias_receita_pessoais, categorias_receita_empresariais]:
        for categoria in categorias_lista:
            try:
                uso_stats = verificar_uso_categoria(categoria['id'], categoria['tipo'])
                categoria['total_uso'] = uso_stats['total_transacoes']
                categoria['pode_excluir'] = not uso_stats['em_uso']
                categoria['ultimo_uso'] = uso_stats.get('ultimo_uso')
            except:
                categoria['total_uso'] = 0
                categoria['pode_excluir'] = True
                categoria['ultimo_uso'] = None
    
    # Ícones e cores disponíveis
    icones_disponiveis = get_icones_disponiveis()
    cores_disponiveis = get_cores_disponiveis()
    
    # Estatísticas gerais
    estatisticas = {
        'total_categorias': len(categorias_despesa_pessoais) + len(categorias_despesa_empresariais) + 
                           len(categorias_receita_pessoais) + len(categorias_receita_empresariais),
        'categorias_despesa': len(categorias_despesa_pessoais) + len(categorias_despesa_empresariais),
        'categorias_receita': len(categorias_receita_pessoais) + len(categorias_receita_empresariais),
        'limite_plano': get_limite_categorias_por_plano(usuario.get('plano', 'gratuito'))
    }
    
    return render_template(
        'categorias.html',
        app_name=Config.APP_NAME,
        usuario=usuario,
        categorias_despesa_pessoais=categorias_despesa_pessoais,
        categorias_despesa_empresariais=categorias_despesa_empresariais,
        categorias_receita_pessoais=categorias_receita_pessoais,
        categorias_receita_empresariais=categorias_receita_empresariais,
        icones_disponiveis=icones_disponiveis,
        cores_disponiveis=cores_disponiveis,
        estatisticas=estatisticas
    )

@categorias_bp.route('/adicionar', methods=['POST'])
@login_required
@plano_required(['premium', 'familia', 'empresarial'])
def adicionar():
    """Adicionar nova categoria personalizada"""
    usuario_id = session.get('usuario_id')
    
    # Dados do formulário
    nome = request.form.get('nome', '').strip()
    tipo = request.form.get('tipo')
    icone = request.form.get('icone')
    cor = request.form.get('cor')
    tipo_perfil = request.form.get('tipo_perfil')
    
    # Validações básicas
    if not nome or not tipo or not tipo_perfil:
        flash('Por favor, preencha todos os campos obrigatórios.', 'error')
        return redirect(url_for('categorias.index'))
    
    # Validação de tamanho do nome
    if len(nome) < 2:
        flash('O nome da categoria deve ter pelo menos 2 caracteres.', 'error')
        return redirect(url_for('categorias.index'))
    
    if len(nome) > 50:
        flash('O nome da categoria deve ter no máximo 50 caracteres.', 'error')
        return redirect(url_for('categorias.index'))
    
    # Verifica limite de categorias por plano
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    plano = usuario.get('plano', 'gratuito')
    
    categoria_model = CategoriaPersonalizada(Config.DATABASE)
    total_categorias = len(categoria_model.buscar(usuario_id=usuario_id))
    limite = get_limite_categorias_por_plano(plano)
    
    if total_categorias >= limite:
        flash(f'Você atingiu o limite de {limite} categorias para seu plano atual.', 'error')
        return redirect(url_for('categorias.index'))
    
    # Verifica se já existe categoria com mesmo nome
    categorias_existentes = categoria_model.buscar(
        usuario_id=usuario_id,
        tipo=tipo,
        tipo_perfil=tipo_perfil
    )
    
    for cat in categorias_existentes:
        if cat['nome'].lower() == nome.lower():
            flash('Já existe uma categoria com este nome para este tipo e perfil.', 'error')
            return redirect(url_for('categorias.index'))
    
    # Valores padrão
    if not icone:
        icone = get_icone_padrao_por_tipo(tipo)
    
    if not cor:
        cor = get_cor_padrao_por_tipo(tipo)
    
    try:
        # Cria a categoria
        categoria_id = categoria_model.criar(
            usuario_id=usuario_id,
            nome=nome,
            tipo=tipo,
            icone=icone,
            cor=cor,
            tipo_perfil=tipo_perfil
        )
        
        flash(f'Categoria "{nome}" adicionada com sucesso!', 'success')
        
        # Log da ação
        registrar_log_categoria(usuario_id, 'criar', categoria_id, nome)
        
    except Exception as e:
        print(f'Erro ao criar categoria: {e}')
        flash(f'Erro ao criar categoria: {str(e)}', 'error')
    
    return redirect(url_for('categorias.index'))

@categorias_bp.route('/editar/<int:categoria_id>', methods=['POST'])
@login_required
def editar(categoria_id):
    """Editar categoria personalizada"""
    usuario_id = session.get('usuario_id')
    
    # Verifica se a categoria pertence ao usuário
    categoria_model = CategoriaPersonalizada(Config.DATABASE)
    categoria = categoria_model.buscar_por_id(categoria_id)
    
    if not categoria or categoria.get('usuario_id') != usuario_id:
        flash('Categoria não encontrada ou acesso negado.', 'error')
        return redirect(url_for('categorias.index'))
    
    # Dados do formulário
    nome = request.form.get('nome', '').strip()
    icone = request.form.get('icone')
    cor = request.form.get('cor')
    
    # Validações básicas
    if not nome:
        flash('Por favor, informe o nome da categoria.', 'error')
        return redirect(url_for('categorias.index'))
    
    # Validação de tamanho do nome
    if len(nome) < 2:
        flash('O nome da categoria deve ter pelo menos 2 caracteres.', 'error')
        return redirect(url_for('categorias.index'))
    
    if len(nome) > 50:
        flash('O nome da categoria deve ter no máximo 50 caracteres.', 'error')
        return redirect(url_for('categorias.index'))
    
    # Verifica se já existe categoria com mesmo nome (exceto a atual)
    categorias_existentes = categoria_model.buscar(
        usuario_id=usuario_id,
        tipo=categoria['tipo'],
        tipo_perfil=categoria['tipo_perfil']
    )
    
    for cat in categorias_existentes:
        if cat['id'] != categoria_id and cat['nome'].lower() == nome.lower():
            flash('Já existe uma categoria com este nome para este tipo e perfil.', 'error')
            return redirect(url_for('categorias.index'))
    
    try:
        # Atualiza a categoria
        categoria_model.atualizar(
            categoria_id=categoria_id,
            nome=nome,
            icone=icone,
            cor=cor
        )
        
        flash(f'Categoria "{nome}" atualizada com sucesso!', 'success')
        
        # Log da ação
        registrar_log_categoria(usuario_id, 'editar', categoria_id, nome)
        
    except Exception as e:
        print(f'Erro ao atualizar categoria: {e}')
        flash(f'Erro ao atualizar categoria: {str(e)}', 'error')
    
    return redirect(url_for('categorias.index'))

@categorias_bp.route('/excluir/<int:categoria_id>', methods=['POST'])
@login_required
def excluir(categoria_id):
    """Excluir categoria personalizada"""
    usuario_id = session.get('usuario_id')
    
    # Verifica se a categoria pertence ao usuário
    categoria_model = CategoriaPersonalizada(Config.DATABASE)
    categoria = categoria_model.buscar_por_id(categoria_id)
    
    if not categoria or categoria.get('usuario_id') != usuario_id:
        flash('Categoria não encontrada ou acesso negado.', 'error')
        return redirect(url_for('categorias.index'))
    
    # Verifica se a categoria está sendo usada
    uso_stats = verificar_uso_categoria(categoria_id, categoria['tipo'])
    
    if uso_stats['em_uso']:
        flash(f'Não é possível excluir esta categoria pois existem {uso_stats["total_transacoes"]} transações associadas a ela.', 'error')
        return redirect(url_for('categorias.index'))
    
    try:
        # Exclui a categoria
        sucesso, mensagem = categoria_model.excluir(categoria_id)
        
        if sucesso:
            flash(f'Categoria "{categoria["nome"]}" excluída com sucesso!', 'success')
            # Log da ação
            registrar_log_categoria(usuario_id, 'excluir', categoria_id, categoria['nome'])
        else:
            flash(f'Erro ao excluir categoria: {mensagem}', 'error')
            
    except Exception as e:
        print(f'Erro ao excluir categoria: {e}')
        flash(f'Erro ao excluir categoria: {str(e)}', 'error')
    
    return redirect(url_for('categorias.index'))

@categorias_bp.route('/duplicar/<int:categoria_id>', methods=['POST'])
@login_required
@plano_required(['premium', 'familia', 'empresarial'])
def duplicar(categoria_id):
    """Duplicar categoria personalizada"""
    usuario_id = session.get('usuario_id')
    
    # Verifica se a categoria pertence ao usuário
    categoria_model = CategoriaPersonalizada(Config.DATABASE)
    categoria = categoria_model.buscar_por_id(categoria_id)
    
    if not categoria or categoria.get('usuario_id') != usuario_id:
        flash('Categoria não encontrada ou acesso negado.', 'error')
        return redirect(url_for('categorias.index'))
    
    # Verifica limite de categorias
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    plano = usuario.get('plano', 'gratuito')
    
    total_categorias = len(categoria_model.buscar(usuario_id=usuario_id))
    limite = get_limite_categorias_por_plano(plano)
    
    if total_categorias >= limite:
        flash(f'Você atingiu o limite de {limite} categorias para seu plano atual.', 'error')
        return redirect(url_for('categorias.index'))
    
    try:
        # Cria nova categoria baseada na existente
        novo_nome = f"{categoria['nome']} (Cópia)"
        contador = 1
        
        # Verifica se já existe categoria com este nome
        while True:
            categorias_existentes = categoria_model.buscar(
                usuario_id=usuario_id,
                tipo=categoria['tipo'],
                tipo_perfil=categoria['tipo_perfil']
            )
            
            nome_existe = any(cat['nome'].lower() == novo_nome.lower() for cat in categorias_existentes)
            
            if not nome_existe:
                break
            
            contador += 1
            novo_nome = f"{categoria['nome']} (Cópia {contador})"
        
        # Cria a categoria duplicada
        nova_categoria_id = categoria_model.criar(
            usuario_id=usuario_id,
            nome=novo_nome,
            tipo=categoria['tipo'],
            icone=categoria['icone'],
            cor=categoria['cor'],
            tipo_perfil=categoria['tipo_perfil']
        )
        
        flash(f'Categoria duplicada como "{novo_nome}"!', 'success')
        
        # Log da ação
        registrar_log_categoria(usuario_id, 'duplicar', nova_categoria_id, novo_nome)
        
    except Exception as e:
        print(f'Erro ao duplicar categoria: {e}')
        flash('Erro ao duplicar categoria.', 'error')
    
    return redirect(url_for('categorias.index'))

# ==================== ROTAS API ====================

@categorias_bp.route('/api')
@login_required
def api_listar():
    """API para obter categorias personalizadas"""
    usuario_id = session.get('usuario_id')
    
    # Parâmetros de filtro
    tipo = request.args.get('tipo')
    tipo_perfil = request.args.get('tipo_perfil')
    incluir_uso = request.args.get('incluir_uso', 'false').lower() == 'true'
    
    try:
        # Busca as categorias
        categoria_model = CategoriaPersonalizada(Config.DATABASE)
        categorias = categoria_model.buscar(
            usuario_id=usuario_id,
            tipo=tipo,
            tipo_perfil=tipo_perfil
        )
        
        # Adiciona informações de uso se solicitado
        if incluir_uso:
            for categoria in categorias:
                uso_stats = verificar_uso_categoria(categoria['id'], categoria['tipo'])
                categoria['uso'] = uso_stats
        
        return jsonify({
            'success': True,
            'categorias': categorias,
            'total': len(categorias)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@categorias_bp.route('/api', methods=['POST'])
@login_required
@plano_required(['premium', 'familia', 'empresarial'])
def api_criar():
    """API para adicionar categoria personalizada"""
    usuario_id = session.get('usuario_id')
    dados = request.json
    
    # Validações básicas
    if not dados or 'nome' not in dados or 'tipo' not in dados:
        return jsonify({"error": "Dados incompletos"}), 400
    
    nome = dados['nome'].strip()
    tipo = dados['tipo']
    
    if not nome or len(nome) < 2:
        return jsonify({"error": "Nome deve ter pelo menos 2 caracteres"}), 400
    
    if len(nome) > 50:
        return jsonify({"error": "Nome deve ter no máximo 50 caracteres"}), 400
    
    try:
        # Verifica limite de categorias
        usuario_model = Usuario(Config.DATABASE)
        usuario = usuario_model.buscar_por_id(usuario_id)
        plano = usuario.get('plano', 'gratuito')
        
        categoria_model = CategoriaPersonalizada(Config.DATABASE)
        total_categorias = len(categoria_model.buscar(usuario_id=usuario_id))
        limite = get_limite_categorias_por_plano(plano)
        
        if total_categorias >= limite:
            return jsonify({"error": f"Limite de {limite} categorias atingido"}), 400
        
        # Prepara os dados
        icone = dados.get('icone') or get_icone_padrao_por_tipo(tipo)
        cor = dados.get('cor') or get_cor_padrao_por_tipo(tipo)
        tipo_perfil = dados.get('tipo_perfil', 'pessoal')
        
        # Verifica duplicatas
        categorias_existentes = categoria_model.buscar(
            usuario_id=usuario_id,
            tipo=tipo,
            tipo_perfil=tipo_perfil
        )
        
        if any(cat['nome'].lower() == nome.lower() for cat in categorias_existentes):
            return jsonify({"error": "Já existe uma categoria com este nome"}), 400
        
        # Cria a categoria
        categoria_id = categoria_model.criar(
            usuario_id=usuario_id,
            nome=nome,
            tipo=tipo,
            icone=icone,
            cor=cor,
            tipo_perfil=tipo_perfil
        )
        
        # Log da ação
        registrar_log_categoria(usuario_id, 'criar_api', categoria_id, nome)
        
        return jsonify({
            "success": True, 
            "id": categoria_id,
            "message": f"Categoria '{nome}' criada com sucesso"
        }), 201
        
    except Exception as e:
        print(f'Erro API criar categoria: {e}')
        return jsonify({"error": str(e)}), 500

@categorias_bp.route('/api/<int:categoria_id>', methods=['PUT'])
@login_required
def api_atualizar(categoria_id):
    """API para atualizar categoria personalizada"""
    usuario_id = session.get('usuario_id')
    dados = request.json
    
    # Busca a categoria para verificar se pertence ao usuário
    categoria_model = CategoriaPersonalizada(Config.DATABASE)
    categoria = categoria_model.buscar_por_id(categoria_id)
    
    if not categoria:
        return jsonify({"error": "Categoria não encontrada"}), 404
    
    if categoria['usuario_id'] != usuario_id:
        return jsonify({"error": "Não autorizado"}), 403
    
    try:
        # Atualiza os dados que foram enviados
        campos_update = {}
        
        if 'nome' in dados:
            nome = dados['nome'].strip()
            if not nome or len(nome) < 2:
                return jsonify({"error": "Nome deve ter pelo menos 2 caracteres"}), 400
            if len(nome) > 50:
                return jsonify({"error": "Nome deve ter no máximo 50 caracteres"}), 400
            campos_update['nome'] = nome
        
        for campo in ['icone', 'cor']:
            if campo in dados:
                campos_update[campo] = dados[campo]
        
        # Atualiza a categoria
        categoria_model.atualizar(categoria_id, **campos_update)
        
        # Log da ação
        nome_para_log = campos_update.get('nome', categoria['nome'])
        registrar_log_categoria(usuario_id, 'editar_api', categoria_id, nome_para_log)
        
        return jsonify({
            "success": True,
            "message": "Categoria atualizada com sucesso"
        }), 200
        
    except Exception as e:
        print(f'Erro API atualizar categoria: {e}')
        return jsonify({"error": str(e)}), 500

@categorias_bp.route('/api/<int:categoria_id>', methods=['DELETE'])
@login_required
def api_excluir(categoria_id):
    """API para excluir categoria personalizada"""
    usuario_id = session.get('usuario_id')
    
    # Busca a categoria para verificar se pertence ao usuário
    categoria_model = CategoriaPersonalizada(Config.DATABASE)
    categoria = categoria_model.buscar_por_id(categoria_id)
    
    if not categoria:
        return jsonify({"error": "Categoria não encontrada"}), 404
    
    if categoria['usuario_id'] != usuario_id:
        return jsonify({"error": "Não autorizado"}), 403
    
    # Verifica se está sendo usada
    uso_stats = verificar_uso_categoria(categoria_id, categoria['tipo'])
    
    if uso_stats['em_uso']:
        return jsonify({
            "error": f"Categoria está sendo usada em {uso_stats['total_transacoes']} transações"
        }), 400
    
    try:
        # Exclui a categoria
        sucesso, mensagem = categoria_model.excluir(categoria_id)
        
        if sucesso:
            # Log da ação
            registrar_log_categoria(usuario_id, 'excluir_api', categoria_id, categoria['nome'])
            
            return jsonify({
                "success": True,
                "message": "Categoria excluída com sucesso"
            }), 200
        else:
            return jsonify({"error": mensagem}), 400
            
    except Exception as e:
        print(f'Erro API excluir categoria: {e}')
        return jsonify({"error": str(e)}), 500

@categorias_bp.route('/api/sugestoes')
@login_required
def api_sugestoes():
    """API para obter sugestões de categorias"""
    tipo = request.args.get('tipo', 'despesa')
    tipo_perfil = request.args.get('tipo_perfil', 'pessoal')
    
    sugestoes = get_sugestoes_categorias(tipo, tipo_perfil)
    
    return jsonify({
        'success': True,
        'sugestoes': sugestoes,
        'tipo': tipo,
        'tipo_perfil': tipo_perfil
    })

@categorias_bp.route('/api/uso/<int:categoria_id>')
@login_required
def api_verificar_uso(categoria_id):
    """API para verificar se categoria está sendo usada"""
    usuario_id = session.get('usuario_id')
    
    # Verifica se a categoria pertence ao usuário
    categoria_model = CategoriaPersonalizada(Config.DATABASE)
    categoria = categoria_model.buscar_por_id(categoria_id)
    
    if not categoria or categoria['usuario_id'] != usuario_id:
        return jsonify({"error": "Categoria não encontrada"}), 404
    
    try:
        # Verifica uso da categoria
        uso_stats = verificar_uso_categoria(categoria_id, categoria['tipo'])
        
        return jsonify({
            "success": True,
            "uso": uso_stats
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@categorias_bp.route('/api/estatisticas')
@login_required
def api_estatisticas():
    """API para obter estatísticas das categorias"""
    usuario_id = session.get('usuario_id')
    
    try:
        categoria_model = CategoriaPersonalizada(Config.DATABASE)
        
        # Busca todas as categorias do usuário
        todas_categorias = categoria_model.buscar(usuario_id=usuario_id)
        
        # Separa por tipo
        despesas = [c for c in todas_categorias if c['tipo'] == 'despesa']
        receitas = [c for c in todas_categorias if c['tipo'] == 'receita']
        
        # Separa por perfil
        pessoais = [c for c in todas_categorias if c['tipo_perfil'] == 'pessoal']
        empresariais = [c for c in todas_categorias if c['tipo_perfil'] == 'empresarial']
        
        # Busca dados do usuário para limite do plano
        usuario_model = Usuario(Config.DATABASE)
        usuario = usuario_model.buscar_por_id(usuario_id)
        plano = usuario.get('plano', 'gratuito')
        limite = get_limite_categorias_por_plano(plano)
        
        estatisticas = {
            'total_categorias': len(todas_categorias),
            'categorias_despesa': len(despesas),
            'categorias_receita': len(receitas),
            'categorias_pessoais': len(pessoais),
            'categorias_empresariais': len(empresariais),
            'limite_plano': limite,
            'percentual_usado': (len(todas_categorias) / limite * 100) if limite > 0 else 0,
            'plano_atual': plano
        }
        
        return jsonify({
            'success': True,
            'estatisticas': estatisticas
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== FUNÇÕES AUXILIARES ====================

def get_icones_disponiveis():
    """Retorna lista de ícones disponíveis"""
    return [
        # Alimentação
        '🍽️', '🍔', '🍕', '🍜', '🍱', '🥗', '☕', '🛒', '🥤', '🍰',
        # Transporte
        '🚗', '🚕', '🚌', '🚇', '✈️', '⛽', '🚲', '🛴', '🏍️', '🚁',
        # Moradia
        '🏠', '🏡', '🏢', '🔌', '💡', '🚿', '🔧', '🪑', '🛏️', '📺',
        # Saúde
        '💊', '🏥', '⚕️', '💉', '🩺', '🦷', '👓', '🧘', '💪', '🏃',
        # Educação
        '📚', '🎓', '✏️', '📝', '💻', '🖥️', '📊', '🧑‍🏫', '🎯', '📋',
        # Lazer
        '🎬', '🎵', '🎮', '🎨', '📸', '🎪', '🎭', '🎸', '🏆', '🎲',
        # Vestuário
        '👕', '👖', '👗', '👞', '👜', '⌚', '👓', '💍', '🧥', '👔',
        # Negócios
        '💼', '📈', '💰', '🏦', '💳', '📱', '🖨️', '📞', '✉️', '📦',
        # Outros
        '🎁', '❤️', '🌟', '🔥', '⚡', '🌈', '🎯', '🔮', '🎊', '✨'
    ]

def get_cores_disponiveis():
    """Retorna lista de cores disponíveis"""
    return [
        # Cores primárias
        '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', 
        '#DDA0DD', '#F39C12', '#95A5A6', '#E74C3C', '#3498DB',
        # Cores secundárias
        '#2ECC71', '#F1C40F', '#E67E22', '#9B59B6', '#1ABC9C',
        '#34495E', '#16A085', '#27AE60', '#2980B9', '#8E44AD',
        # Tons pastéis
        '#FFB6C1', '#98FB98', '#87CEEB', '#DDA0DD', '#F0E68C',
        '#FFA07A', '#20B2AA', '#87CEFA', '#778899', '#B0C4DE'
    ]

def get_icone_padrao_por_tipo(tipo):
    """Retorna ícone padrão baseado no tipo"""
    icones_padrao = {
        'despesa': '💸',
        'receita': '💰'
    }
    return icones_padrao.get(tipo, '📦')

def get_cor_padrao_por_tipo(tipo):
    """Retorna cor padrão baseada no tipo"""
    cores_padrao = {
        'despesa': '#E74C3C',
        'receita': '#27AE60'
    }
    return cores_padrao.get(tipo, '#95A5A6')

def get_limite_categorias_por_plano(plano):
    """Retorna limite de categorias por plano"""
    limites = {
        'gratuito': 8,
        'premium': 50,
        'familia': 100,
        'empresarial': 200
    }
    return limites.get(plano, 8)

def get_sugestoes_categorias(tipo, tipo_perfil):
    """Retorna sugestões de categorias"""
    if tipo == 'despesa':
        if tipo_perfil == 'empresarial':
            return [
                {'nome': 'Material de Escritório', 'icone': '📋', 'cor': '#3498DB'},
                {'nome': 'Marketing Digital', 'icone': '📢', 'cor': '#E74C3C'},
                {'nome': 'Equipamentos TI', 'icone': '💻', 'cor': '#2ECC71'},
                {'nome': 'Consultoria', 'icone': '👨‍💼', 'cor': '#9B59B6'},
                {'nome': 'Software/Licenças', 'icone': '💿', 'cor': '#F39C12'},
                {'nome': 'Viagens Corporativas', 'icone': '✈️', 'cor': '#1ABC9C'},
                {'nome': 'Treinamentos', 'icone': '🎓', 'cor': '#E67E22'},
                {'nome': 'Taxas Bancárias', 'icone': '🏦', 'cor': '#95A5A6'},
                {'nome': 'Manutenção', 'icone': '🔧', 'cor': '#34495E'},
                {'nome': 'Segurança', 'icone': '🛡️', 'cor': '#8E44AD'}
            ]
        else:
            return [
                {'nome': 'Supermercado', 'icone': '🛒', 'cor': '#FF6B6B'},
                {'nome': 'Farmácia', 'icone': '💊', 'cor': '#4ECDC4'},
                {'nome': 'Combustível', 'icone': '⛽', 'cor': '#45B7D1'},
                {'nome': 'Academia', 'icone': '💪', 'cor': '#96CEB4'},
                {'nome': 'Streaming', 'icone': '📺', 'cor': '#FFEAA7'},
                {'nome': 'Pet Shop', 'icone': '🐕', 'cor': '#DDA0DD'},
                {'nome': 'Barbeiro/Salão', 'icone': '✂️', 'cor': '#F39C12'},
                {'nome': 'Telefone/Internet', 'icone': '📱', 'cor': '#95A5A6'},
                {'nome': 'Delivery', 'icone': '🛵', 'cor': '#E74C3C'},
                {'nome': 'Estacionamento', 'icone': '🅿️', 'cor': '#3498DB'}
            ]
    else:  # receita
        if tipo_perfil == 'empresarial':
            return [
                {'nome': 'Vendas Produtos', 'icone': '🛍️', 'cor': '#27AE60'},
                {'nome': 'Prestação Serviços', 'icone': '🔧', 'cor': '#3498DB'},
                {'nome': 'Comissões', 'icone': '💼', 'cor': '#9B59B6'},
                {'nome': 'Juros/Rendimentos', 'icone': '📈', 'cor': '#F39C12'},
                {'nome': 'Aluguel Equipamentos', 'icone': '🏭', 'cor': '#1ABC9C'},
                {'nome': 'Royalties', 'icone': '👑', 'cor': '#E67E22'},
                {'nome': 'Licenciamento', 'icone': '📜', 'cor': '#8E44AD'},
                {'nome': 'Parcerias', 'icone': '🤝', 'cor': '#2ECC71'}
            ]
        else:
            return [
                {'nome': 'Trabalho Extra', 'icone': '⏰', 'cor': '#27AE60'},
                {'nome': 'Freelance', 'icone': '💻', 'cor': '#3498DB'},
                {'nome': 'Vendas Online', 'icone': '🛒', 'cor': '#9B59B6'},
                {'nome': 'Dividendos', 'icone': '📊', 'cor': '#F39C12'},
                {'nome': 'Aluguel', 'icone': '🏠', 'cor': '#1ABC9C'},
                {'nome': '13º Salário', 'icone': '🎁', 'cor': '#E74C3C'},
                {'nome': 'Restituição IR', 'icone': '📋', 'cor': '#2ECC71'},
                {'nome': 'Prêmios', 'icone': '🏆', 'cor': '#F1C40F'},
                {'nome': 'Pensão', 'icone': '👥', 'cor': '#95A5A6'},
                {'nome': 'Mesada', 'icone': '💰', 'cor': '#FFEAA7'}
            ]

def verificar_uso_categoria(categoria_id, tipo_categoria):
    """Verifica se uma categoria está sendo usada"""
    try:
        conn = sqlite3.connect(Config.DATABASE)
        cursor = conn.cursor()
        
        # Busca a categoria para obter o nome
        cursor.execute("SELECT nome FROM categorias_personalizadas WHERE id = ?", (categoria_id,))
        categoria_result = cursor.fetchone()
        nome_categoria = categoria_result[0] if categoria_result else ""
        
        total_transacoes = 0
        ultimo_uso = None
        detalhes = {'despesas': 0, 'receitas': 0}
        
        if tipo_categoria == 'despesa':
            # Verifica uso em despesas
            cursor.execute("""
                SELECT COUNT(*), MAX(data) FROM despesas 
                WHERE categoria = ?
            """, (nome_categoria,))
            result = cursor.fetchone()
            detalhes['despesas'] = result[0] or 0
            if result[1]:
                ultimo_uso = result[1]
        else:
            # Verifica uso em receitas
            cursor.execute("""
                SELECT COUNT(*), MAX(data) FROM receitas 
                WHERE categoria = ?
            """, (nome_categoria,))
            result = cursor.fetchone()
            detalhes['receitas'] = result[0] or 0
            if result[1]:
                ultimo_uso = result[1]
        
        total_transacoes = detalhes['despesas'] + detalhes['receitas']
        
        conn.close()
        
        return {
            'em_uso': total_transacoes > 0,
            'total_transacoes': total_transacoes,
            'ultimo_uso': ultimo_uso,
            'detalhes': detalhes
        }
        
    except Exception as e:
        print(f'Erro ao verificar uso da categoria: {e}')
        return {
            'em_uso': False,
            'total_transacoes': 0,
            'ultimo_uso': None,
            'detalhes': {'despesas': 0, 'receitas': 0}
        }

def registrar_log_categoria(usuario_id, acao, categoria_id, nome_categoria):
    """Registra log de ações nas categorias"""
    try:
        # Em uma aplicação real, registraria em uma tabela de logs
        print(f"[LOG] Usuário {usuario_id} - {acao} categoria {categoria_id}: {nome_categoria}")
    except Exception as e:
        print(f"Erro ao registrar log: {e}")

def criar_categorias_iniciais(usuario_id):
    """Cria categorias iniciais para um novo usuário"""
    categoria_model = CategoriaPersonalizada(Config.DATABASE)
    categorias_criadas = 0
    
    categorias_padrao = {
        'despesa': [
            {'nome': 'Alimentação', 'icone': '🍽️', 'cor': '#FF6B6B'},
            {'nome': 'Transporte', 'icone': '🚗', 'cor': '#4ECDC4'},
            {'nome': 'Moradia', 'icone': '🏠', 'cor': '#45B7D1'},
            {'nome': 'Saúde', 'icone': '💊', 'cor': '#96CEB4'},
            {'nome': 'Educação', 'icone': '📚', 'cor': '#FFEAA7'},
            {'nome': 'Lazer', 'icone': '🎬', 'cor': '#DDA0DD'},
            {'nome': 'Vestuário', 'icone': '👕', 'cor': '#F39C12'},
            {'nome': 'Outros', 'icone': '📦', 'cor': '#95A5A6'}
        ],
        'receita': [
            {'nome': 'Salário', 'icone': '💼', 'cor': '#27AE60'},
            {'nome': 'Freelance', 'icone': '💻', 'cor': '#3498DB'},
            {'nome': 'Investimentos', 'icone': '📈', 'cor': '#9B59B6'},
            {'nome': 'Outros Ganhos', 'icone': '💰', 'cor': '#1ABC9C'}
        ]
    }
    
    try:
        for tipo, categorias in categorias_padrao.items():
            for categoria in categorias:
                categoria_model.criar(
                    usuario_id=usuario_id,
                    nome=categoria['nome'],
                    tipo=tipo,
                    icone=categoria['icone'],
                    cor=categoria['cor'],
                    tipo_perfil='pessoal'
                )
                categorias_criadas += 1
        
        return categorias_criadas
        
    except Exception as e:
        print(f"Erro ao criar categorias iniciais: {e}")
        return 0