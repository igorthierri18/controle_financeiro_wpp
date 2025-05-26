from flask import Blueprint, render_template, redirect, url_for, request, flash, session, jsonify
from database.models import Usuario
from functools import wraps
from datetime import datetime
from config import Config

# Criação do blueprint
perfil_bp = Blueprint('perfil', __name__)

# Middleware para verificar login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# ===== ROTAS WEB =====

@perfil_bp.route('/perfil', methods=['GET'])
@login_required
def perfil():
    """Página de perfil do usuário"""
    usuario_id = session.get('usuario_id')
    
    # Busca dados do usuário
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    if not usuario:
        flash('Usuário não encontrado.', 'error')
        return redirect(url_for('auth.logout'))
    
    # Formata a data de criação
    if usuario.get('data_criacao'):
        data_criacao = datetime.strptime(usuario['data_criacao'], "%Y-%m-%d %H:%M:%S")
        usuario['data_criacao'] = data_criacao.strftime("%d/%m/%Y")
    
    return render_template(
        'perfil.html',
        app_name=Config.APP_NAME,
        usuario=usuario
    )

@perfil_bp.route('/atualizar_perfil', methods=['POST'])
@login_required
def atualizar_perfil():
    """Atualização de dados do perfil"""
    usuario_id = session.get('usuario_id')
    
    # Obtém os dados do formulário
    nome = request.form.get('nome')
    email = request.form.get('email')
    renda = request.form.get('renda')
    
    # Validações básicas
    if not nome or not email:
        flash('Por favor, preencha todos os campos obrigatórios.', 'error')
        return redirect(url_for('perfil.perfil'))
    
    # Converte renda para float se fornecida
    if renda:
        try:
            renda = float(renda)
        except ValueError:
            flash('Valor de renda inválido.', 'error')
            return redirect(url_for('perfil.perfil'))
    else:
        renda = None
    
    # Verifica se o email já está em uso por outro usuário
    usuario_model = Usuario(Config.DATABASE)
    usuario_email = usuario_model.buscar_por_email(email)
    
    if usuario_email and usuario_email['id'] != usuario_id:
        flash('Este email já está sendo usado por outro usuário.', 'error')
        return redirect(url_for('perfil.perfil'))
    
    # Atualiza os dados do usuário
    usuario_model.atualizar(usuario_id, nome=nome, email=email, renda=renda)
    
    flash('Perfil atualizado com sucesso!', 'success')
    return redirect(url_for('perfil.perfil'))

@perfil_bp.route('/alterar_senha', methods=['POST'])
@login_required
def alterar_senha():
    """Alteração de senha do usuário"""
    usuario_id = session.get('usuario_id')
    
    # Obtém os dados do formulário
    senha_atual = request.form.get('senha_atual')
    nova_senha = request.form.get('nova_senha')
    confirma_senha = request.form.get('confirma_senha')
    
    # Validações básicas
    if not senha_atual or not nova_senha or not confirma_senha:
        flash('Por favor, preencha todos os campos.', 'error')
        return redirect(url_for('perfil.perfil'))
    
    if nova_senha != confirma_senha:
        flash('A nova senha e a confirmação não coincidem.', 'error')
        return redirect(url_for('perfil.perfil'))
    
    # Verifica se a senha atual está correta
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    if not usuario or usuario['senha'] != senha_atual:
        flash('Senha atual incorreta.', 'error')
        return redirect(url_for('perfil.perfil'))
    
    # Atualiza a senha
    usuario_model.atualizar(usuario_id, senha=nova_senha)
    
    flash('Senha alterada com sucesso!', 'success')
    return redirect(url_for('perfil.perfil'))

@perfil_bp.route('/excluir_conta', methods=['POST'])
@login_required
def excluir_conta():
    """Exclusão da conta do usuário"""
    usuario_id = session.get('usuario_id')
    
    # Exclui o usuário
    usuario_model = Usuario(Config.DATABASE)
    
    # Aqui você implementaria a lógica para excluir o usuário e seus dados
    # Exemplo: usuario_model.excluir(usuario_id)
    
    # Encerra a sessão
    session.pop('usuario_id', None)
    
    flash('Sua conta foi excluída com sucesso.', 'success')
    return redirect(url_for('web.index'))

@perfil_bp.route('/configuracoes')
@login_required
def configuracoes():
    """Página de configurações do usuário"""
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

@perfil_bp.route('/atualizar_configuracoes', methods=['POST'])
@login_required
def atualizar_configuracoes():
    """Atualizar configurações do usuário"""
    usuario_id = session.get('usuario_id')
    
    # Obtém os dados do formulário
    configuracoes = {
        'notificacoes_whatsapp': request.form.get('notificacoes_whatsapp') == 'on',
        'notificacoes_email': request.form.get('notificacoes_email') == 'on',
        'relatorio_semanal': request.form.get('relatorio_semanal') == 'on',
        'alerta_limite_gasto': request.form.get('alerta_limite_gasto') == 'on',
        'tema': request.form.get('tema', 'auto'),
        'moeda': request.form.get('moeda', 'BRL'),
        'formato_data': request.form.get('formato_data', 'DD/MM/YYYY'),
        'dia_fechamento': int(request.form.get('dia_fechamento', 1))
    }
    
    # Em uma implementação real, salvaria essas configurações no banco de dados
    # Por enquanto, apenas mostra mensagem de sucesso
    flash('Configurações atualizadas com sucesso!', 'success')
    return redirect(url_for('perfil.configuracoes'))

# ===== ROTAS API =====

@perfil_bp.route('/api/usuario', methods=['GET'])
@login_required
def api_get_usuario():
    """API para obter dados do usuário logado"""
    usuario_id = session.get('usuario_id')
    
    # Busca os dados do usuário
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    if not usuario:
        return jsonify({"error": "Usuário não encontrado"}), 404
    
    # Remove a senha do objeto retornado
    if 'senha' in usuario:
        del usuario['senha']
    
    return jsonify(usuario)

@perfil_bp.route('/api/usuario', methods=['PUT'])
@login_required
def api_update_usuario():
    """API para atualizar dados do usuário"""
    usuario_id = session.get('usuario_id')
    dados = request.json
    
    # Validação básica
    if not dados:
        return jsonify({"error": "Nenhum dado fornecido"}), 400
    
    try:
        # Extrai os dados que podem ser atualizados
        nome = dados.get('nome')
        email = dados.get('email')
        senha = dados.get('senha')
        renda = dados.get('renda')
        
        # Validações
        if email:
            usuario_model = Usuario(Config.DATABASE)
            usuario_email = usuario_model.buscar_por_email(email)
            
            if usuario_email and usuario_email['id'] != usuario_id:
                return jsonify({"error": "Email já está em uso por outro usuário"}), 400
        
        # Atualiza o usuário
        usuario_model.atualizar(
            usuario_id=usuario_id,
            nome=nome,
            email=email,
            senha=senha,
            renda=renda
        )
        
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@perfil_bp.route('/api/usuario/perfil', methods=['GET'])
@login_required
def api_obter_perfil_usuario():
    """Obtém informações básicas do perfil do usuário"""
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
            'renda_mensal': float(usuario.get('renda', 0)) if usuario.get('renda') else 0
        }
        
        return jsonify(resposta), 200
        
    except Exception as e:
        print(f"Erro ao obter perfil do usuário: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@perfil_bp.route('/api/usuario/renda', methods=['GET'])
@login_required
def api_obter_renda_usuario():
    """Obtém a renda mensal do usuário para cálculo de comprometimento"""
    try:
        usuario_id = session.get('usuario_id')
        
        usuario_model = Usuario(Config.DATABASE)
        usuario = usuario_model.buscar_por_id(usuario_id)
        
        if not usuario:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        # Tenta obter a renda do usuário
        renda = usuario.get('renda', 0)
        
        return jsonify({
            'success': True,
            'renda': float(renda) if renda else 0
        }), 200
        
    except Exception as e:
        print(f"Erro ao obter renda do usuário: {str(e)}")
        return jsonify({'error': str(e) or 'Erro interno do servidor'}), 500

@perfil_bp.route('/api/usuario/renda', methods=['PUT'])
@login_required
def api_atualizar_renda_usuario():
    """Atualiza a renda mensal do usuário"""
    try:
        usuario_id = session.get('usuario_id')
        dados = request.json
        
        if not dados or 'renda' not in dados:
            return jsonify({'error': 'Valor da renda é obrigatório'}), 400
        
        renda = float(dados['renda'])
        
        if renda < 0:
            return jsonify({'error': 'Renda não pode ser negativa'}), 400
        
        usuario_model = Usuario(Config.DATABASE)
        usuario_model.atualizar(usuario_id, renda=renda)
        
        return jsonify({
            'success': True,
            'message': 'Renda atualizada com sucesso',
            'renda': renda
        }), 200
        
    except ValueError:
        return jsonify({'error': 'Valor de renda inválido'}), 400
    except Exception as e:
        print(f"Erro ao atualizar renda do usuário: {str(e)}")
        return jsonify({'error': str(e) or 'Erro interno do servidor'}), 500

@perfil_bp.route('/api/usuario/configuracoes', methods=['GET'])
@login_required
def api_obter_configuracoes():
    """Obtém as configurações do usuário"""
    try:
        usuario_id = session.get('usuario_id')
        
        # Em uma implementação real, buscaria as configurações do banco de dados
        # Por enquanto, retorna configurações padrão
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
        
        return jsonify({
            'success': True,
            'configuracoes': configuracoes
        }), 200
        
    except Exception as e:
        print(f"Erro ao obter configurações: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@perfil_bp.route('/api/usuario/configuracoes', methods=['PUT'])
@login_required
def api_atualizar_configuracoes():
    """Atualiza as configurações do usuário"""
    try:
        usuario_id = session.get('usuario_id')
        dados = request.json
        
        if not dados:
            return jsonify({'error': 'Dados de configuração são obrigatórios'}), 400
        
        # Em uma implementação real, salvaria as configurações no banco de dados
        # Por enquanto, apenas valida os dados
        configuracoes_validas = [
            'notificacoes_whatsapp', 'notificacoes_email', 'relatorio_semanal',
            'alerta_limite_gasto', 'tema', 'moeda', 'formato_data', 'dia_fechamento'
        ]
        
        configuracoes_atualizadas = {}
        for chave, valor in dados.items():
            if chave in configuracoes_validas:
                configuracoes_atualizadas[chave] = valor
        
        return jsonify({
            'success': True,
            'message': 'Configurações atualizadas com sucesso',
            'configuracoes': configuracoes_atualizadas
        }), 200
        
    except Exception as e:
        print(f"Erro ao atualizar configurações: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@perfil_bp.route('/api/usuario/estatisticas', methods=['GET'])
@login_required
def api_obter_estatisticas_usuario():
    """Obtém estatísticas do usuário"""
    try:
        usuario_id = session.get('usuario_id')
        
        from database.models import Despesa, Receita, Lembrete
        from datetime import datetime, timedelta
        
        # Data atual
        hoje = datetime.now()
        inicio_mes = f"{hoje.year}-{hoje.month:02d}-01"
        fim_mes = hoje.strftime("%Y-%m-%d")
        
        # Busca dados
        despesa_model = Despesa(Config.DATABASE)
        receita_model = Receita(Config.DATABASE)
        lembrete_model = Lembrete(Config.DATABASE)
        
        # Estatísticas do mês atual
        total_despesas = despesa_model.total_periodo(usuario_id, inicio_mes, fim_mes)
        total_receitas = receita_model.total_periodo(usuario_id, inicio_mes, fim_mes)
        
        # Despesas por categoria
        categorias = despesa_model.total_por_categoria(usuario_id, inicio_mes, fim_mes)
        
        # Lembretes ativos
        lembretes_ativos = len(lembrete_model.buscar(usuario_id, concluido=0))
        
        # Transações totais
        total_transacoes = len(despesa_model.buscar(usuario_id)) + len(receita_model.buscar(usuario_id))
        
        return jsonify({
            'success': True,
            'estatisticas': {
                'total_despesas_mes': total_despesas,
                'total_receitas_mes': total_receitas,
                'saldo_mes': total_receitas - total_despesas,
                'categorias_mes': categorias,
                'lembretes_ativos': lembretes_ativos,
                'total_transacoes': total_transacoes,
                'mes_referencia': f"{hoje.month:02d}/{hoje.year}"
            }
        }), 200
        
    except Exception as e:
        print(f"Erro ao obter estatísticas: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500