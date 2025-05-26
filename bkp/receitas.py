# rotas/receitas.py
"""
MÓDULO DE RECEITAS
==================
Gerencia todas as funcionalidades relacionadas a receitas/ganhos:

ROTAS WEB:
- GET /receitas/ - Lista receitas com filtros
- GET/POST /receitas/adicionar - Formulário para nova receita
- GET/POST /receitas/editar/<id> - Formulário para editar receita
- POST /receitas/excluir/<id> - Excluir receita

ROTAS API:
- GET /receitas/api - Listar receitas (JSON)
- POST /receitas/api - Criar receita (JSON)
- PUT /receitas/api/<id> - Atualizar receita (JSON)
- DELETE /receitas/api/<id> - Excluir receita (JSON)
- GET /receitas/api/categorias - Receitas por categoria
- GET /receitas/api/exportar - Exportar CSV

WEBHOOKS:
- processar_webhook_receita() - Comandos via WhatsApp
- "receita salário 3000" - Registrar nova receita
- "ganhos do mês" - Relatório de receitas
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash, session, jsonify, send_file
from database.models import Usuario, Receita, TextProcessor
from functools import wraps
from datetime import datetime, timedelta
import pandas as pd
import io
from config import Config

# Blueprint principal do módulo
receitas_bp = Blueprint('receitas', __name__, url_prefix='/receitas')

# Middleware para verificar login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# ==================== ROTAS WEB ====================

@receitas_bp.route('/')
@login_required
def index():
    """Página principal de receitas"""
    usuario_id = session.get('usuario_id')
    
    # Busca dados do usuário
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    # Filtros da URL
    periodo = request.args.get('periodo', 'mes')
    categoria = request.args.get('categoria')
    tipo_perfil = request.args.get('tipo_perfil', 'pessoal')
    
    # Define período
    hoje = datetime.now()
    if periodo == 'dia':
        data_inicio = hoje.strftime("%Y-%m-%d")
    elif periodo == 'semana':
        data_inicio = (hoje - timedelta(days=7)).strftime("%Y-%m-%d")
    elif periodo == 'mes':
        data_inicio = f"{hoje.year}-{hoje.month:02d}-01"
    elif periodo == 'ano':
        data_inicio = f"{hoje.year}-01-01"
    else:
        data_inicio = None
    
    data_fim = hoje.strftime("%Y-%m-%d")
    
    # Busca receitas
    receita_model = Receita(Config.DATABASE)
    receitas = receita_model.buscar(
        usuario_id=usuario_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        categoria=categoria,
        tipo_perfil=tipo_perfil
    )
    
    # Calcula totais
    total = receita_model.total_periodo(
        usuario_id=usuario_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        tipo_perfil=tipo_perfil
    )
    
    # Receitas por categoria
    categorias = receita_model.total_por_categoria(
        usuario_id=usuario_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        tipo_perfil=tipo_perfil
    )
    
    return render_template(
        'receitas.html',  # Template correto
        app_name=Config.APP_NAME,
        usuario=usuario,
        receitas=receitas,
        total=total,
        categorias=categorias,
        periodo=periodo,
        categoria_filtro=categoria,
        tipo_perfil=tipo_perfil
    )

@receitas_bp.route('/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar():
    """Adicionar nova receita"""
    if request.method == 'POST':
        usuario_id = session.get('usuario_id')
        
        # Dados do formulário
        valor = float(request.form.get('valor', 0))
        categoria = request.form.get('categoria')
        descricao = request.form.get('descricao')
        data = request.form.get('data')
        recorrente = int(request.form.get('recorrente', 0))
        periodicidade = request.form.get('periodicidade') if recorrente else None
        tipo_perfil = request.form.get('tipo_perfil', 'pessoal')
        
        # Validações
        if not valor or not categoria or not descricao or not data:
            flash('Por favor, preencha todos os campos obrigatórios.', 'error')
            return redirect(url_for('receitas.adicionar'))
        
        # Cria a receita
        receita_model = Receita(Config.DATABASE)
        receita_id = receita_model.criar(
            usuario_id=usuario_id,
            valor=valor,
            categoria=categoria,
            descricao=descricao,
            data=data,
            recorrente=recorrente,
            periodicidade=periodicidade,
            tipo_perfil=tipo_perfil
        )
        
        flash('Receita adicionada com sucesso!', 'success')
        return redirect(url_for('receitas.index'))
    
    # GET - Exibe formulário
    usuario_id = session.get('usuario_id')
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    return render_template(
        'receitas_adicionar.html',  # Template específico
        app_name=Config.APP_NAME,
        usuario=usuario
    )

@receitas_bp.route('/editar/<int:receita_id>', methods=['GET', 'POST'])
@login_required
def editar(receita_id):
    """Editar receita"""
    usuario_id = session.get('usuario_id')
    
    # Verifica se a receita pertence ao usuário
    receita_model = Receita(Config.DATABASE)
    receita = receita_model.buscar_por_id(receita_id)
    
    if not receita or receita.get('usuario_id') != usuario_id:
        flash('Receita não encontrada ou acesso negado.', 'error')
        return redirect(url_for('receitas.index'))
    
    if request.method == 'POST':
        # Dados do formulário
        dados = {}
        for campo in ['valor', 'categoria', 'descricao', 'data', 'recorrente', 'periodicidade', 'tipo_perfil']:
            if campo in request.form:
                dados[campo] = request.form.get(campo)
        
        # Converte campos específicos
        if 'valor' in dados:
            try:
                dados['valor'] = float(dados['valor'])
            except ValueError:
                flash('Valor inválido.', 'error')
                return redirect(url_for('receitas.editar', receita_id=receita_id))
        
        if 'recorrente' in dados:
            dados['recorrente'] = int(dados['recorrente'])
        
        # Atualiza a receita
        receita_model.atualizar(receita_id, **dados)
        flash('Receita atualizada com sucesso!', 'success')
        return redirect(url_for('receitas.index'))
    
    # GET - Exibe formulário de edição
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    return render_template(
        'receitas_editar.html',  # Template específico
        app_name=Config.APP_NAME,
        usuario=usuario,
        receita=receita
    )

@receitas_bp.route('/excluir/<int:receita_id>', methods=['POST'])
@login_required
def excluir(receita_id):
    """Excluir receita"""
    usuario_id = session.get('usuario_id')
    
    # Verifica se a receita pertence ao usuário
    receita_model = Receita(Config.DATABASE)
    receita = receita_model.buscar_por_id(receita_id)
    
    if not receita or receita.get('usuario_id') != usuario_id:
        flash('Receita não encontrada ou acesso negado.', 'error')
        return redirect(url_for('receitas.index'))
    
    # Exclui a receita
    receita_model.excluir(receita_id)
    flash('Receita excluída com sucesso!', 'success')
    
    return redirect(url_for('receitas.index'))

# ==================== ROTAS API ====================

@receitas_bp.route('/api')
@login_required
def api_listar():
    """API para obter receitas"""
    usuario_id = session.get('usuario_id')
    
    # Parâmetros de filtro
    periodo = request.args.get('periodo', 'mes')
    categoria = request.args.get('categoria')
    tipo_perfil = request.args.get('tipo_perfil')
    
    # Define período
    hoje = datetime.now()
    if periodo == 'dia':
        data_inicio = hoje.strftime("%Y-%m-%d")
    elif periodo == 'semana':
        data_inicio = (hoje - timedelta(days=7)).strftime("%Y-%m-%d")
    elif periodo == 'mes':
        data_inicio = f"{hoje.year}-{hoje.month:02d}-01"
    elif periodo == 'ano':
        data_inicio = f"{hoje.year}-01-01"
    elif periodo == 'personalizado':
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
    else:
        data_inicio = None
    
    if periodo != 'personalizado':
        data_fim = hoje.strftime("%Y-%m-%d")
    
    # Busca as receitas
    receita_model = Receita(Config.DATABASE)
    receitas = receita_model.buscar(
        usuario_id=usuario_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        categoria=categoria,
        tipo_perfil=tipo_perfil
    )
    
    return jsonify(receitas)

@receitas_bp.route('/api', methods=['POST'])
@login_required
def api_criar():
    """API para criar receita"""
    usuario_id = session.get('usuario_id')
    dados = request.json
    
    # Validações básicas
    if not dados or 'valor' not in dados or 'categoria' not in dados:
        return jsonify({"error": "Dados incompletos"}), 400
    
    try:
        # Prepara os dados
        valor = float(dados['valor'])
        categoria = dados['categoria']
        descricao = dados['descricao']
        data = dados['data']
        recorrente = int(dados.get('recorrente', 0))
        periodicidade = dados.get('periodicidade') if recorrente else None
        tipo_perfil = dados.get('tipo_perfil', 'pessoal')
        
        # Cria a receita
        receita_model = Receita(Config.DATABASE)
        receita_id = receita_model.criar(
            usuario_id=usuario_id,
            valor=valor,
            categoria=categoria,
            descricao=descricao,
            data=data,
            recorrente=recorrente,
            periodicidade=periodicidade,
            tipo_perfil=tipo_perfil
        )
        
        return jsonify({"success": True, "id": receita_id}), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@receitas_bp.route('/api/<int:receita_id>', methods=['PUT'])
@login_required
def api_atualizar(receita_id):
    """API para atualizar receita"""
    usuario_id = session.get('usuario_id')
    dados = request.json
    
    # Verifica se a receita pertence ao usuário
    receita_model = Receita(Config.DATABASE)
    receita = receita_model.buscar_por_id(receita_id)
    
    if not receita:
        return jsonify({"error": "Receita não encontrada"}), 404
    
    if receita['usuario_id'] != usuario_id:
        return jsonify({"error": "Não autorizado"}), 403
    
    try:
        # Prepara campos para atualização
        campos_update = {}
        
        for campo in ['valor', 'categoria', 'descricao', 'data', 'recorrente', 'periodicidade', 'tipo_perfil']:
            if campo in dados:
                if campo == 'valor':
                    campos_update[campo] = float(dados[campo])
                elif campo == 'recorrente':
                    campos_update[campo] = int(dados[campo])
                else:
                    campos_update[campo] = dados[campo]
        
        # Atualiza a receita
        receita_model.atualizar(receita_id, **campos_update)
        
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@receitas_bp.route('/api/<int:receita_id>', methods=['DELETE'])
@login_required
def api_excluir(receita_id):
    """API para excluir receita"""
    usuario_id = session.get('usuario_id')
    
    # Verifica se a receita pertence ao usuário
    receita_model = Receita(Config.DATABASE)
    receita = receita_model.buscar_por_id(receita_id)
    
    if not receita:
        return jsonify({"error": "Receita não encontrada"}), 404
    
    if receita['usuario_id'] != usuario_id:
        return jsonify({"error": "Não autorizado"}), 403
    
    # Exclui a receita
    sucesso = receita_model.excluir(receita_id)
    
    if sucesso:
        return jsonify({"success": True}), 200
    else:
        return jsonify({"error": "Não foi possível excluir a receita"}), 500

@receitas_bp.route('/api/categorias')
@login_required
def api_por_categoria():
    """API para obter receitas agrupadas por categoria"""
    usuario_id = session.get('usuario_id')
    
    # Parâmetros
    periodo = request.args.get('periodo', 'mes')
    tipo_perfil = request.args.get('tipo_perfil')
    
    # Define período
    hoje = datetime.now()
    if periodo == 'dia':
        data_inicio = hoje.strftime("%Y-%m-%d")
    elif periodo == 'semana':
        data_inicio = (hoje - timedelta(days=7)).strftime("%Y-%m-%d")
    elif periodo == 'mes':
        data_inicio = f"{hoje.year}-{hoje.month:02d}-01"
    elif periodo == 'ano':
        data_inicio = f"{hoje.year}-01-01"
    else:
        data_inicio = None
    
    data_fim = hoje.strftime("%Y-%m-%d")
    
    # Busca receitas por categoria
    receita_model = Receita(Config.DATABASE)
    categorias = receita_model.total_por_categoria(
        usuario_id=usuario_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        tipo_perfil=tipo_perfil
    )
    
    return jsonify(categorias)

@receitas_bp.route('/api/exportar')
@login_required
def api_exportar():
    """API para exportar receitas em CSV"""
    usuario_id = session.get('usuario_id')
    
    # Parâmetros
    periodo = request.args.get('periodo')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    tipo_perfil = request.args.get('tipo_perfil')
    
    # Define período se não fornecido
    hoje = datetime.now()
    if periodo == 'dia':
        data_inicio = hoje.strftime("%Y-%m-%d")
        data_fim = hoje.strftime("%Y-%m-%d")
    elif periodo == 'semana':
        data_inicio = (hoje - timedelta(days=7)).strftime("%Y-%m-%d")
        data_fim = hoje.strftime("%Y-%m-%d")
    elif periodo == 'mes':
        data_inicio = f"{hoje.year}-{hoje.month:02d}-01"
        data_fim = hoje.strftime("%Y-%m-%d")
    elif periodo == 'ano':
        data_inicio = f"{hoje.year}-01-01"
        data_fim = hoje.strftime("%Y-%m-%d")
    
    # Busca receitas
    receita_model = Receita(Config.DATABASE)
    receitas = receita_model.buscar(
        usuario_id=usuario_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        tipo_perfil=tipo_perfil
    )
    
    if not receitas:
        return jsonify({"error": "Não há receitas para exportar"}), 404
    
    # Converte para DataFrame
    df = pd.DataFrame(receitas)
    
    # Formata datas
    if 'data' in df.columns:
        df['data'] = pd.to_datetime(df['data']).dt.strftime('%d/%m/%Y')
    if 'data_criacao' in df.columns:
        df['data_criacao'] = pd.to_datetime(df['data_criacao']).dt.strftime('%d/%m/%Y %H:%M:%S')
    
    # Traduz colunas
    colunas = {
        'id': 'ID',
        'valor': 'Valor',
        'categoria': 'Categoria',
        'descricao': 'Descrição',
        'data': 'Data',
        'recorrente': 'Recorrente',
        'periodicidade': 'Periodicidade',
        'data_criacao': 'Data de Criação'
    }
    df = df.rename(columns={k: v for k, v in colunas.items() if k in df.columns})
    
    # Cria CSV
    csv_data = df.to_csv(index=False)
    
    return send_file(
        io.BytesIO(csv_data.encode()),
        mimetype='text/csv',
        download_name='receitas.csv',
        as_attachment=True
    )

# ==================== WEBHOOKS ====================

def processar_webhook_receita(mensagem, usuario_id):
    """Processa comandos de receita via webhook"""
    mensagem_lower = mensagem.lower()
    
    # Comandos de relatório de receitas
    if mensagem_lower in ['ganhos', 'receitas', 'entradas']:
        return get_relatorio_receitas(usuario_id, 'mes')
    elif mensagem_lower in ['ganhos hoje', 'receitas hoje']:
        return get_relatorio_receitas(usuario_id, 'dia')
    elif mensagem_lower in ['ganhos do mês', 'receitas do mês', 'ganhos mes', 'receitas mes']:
        return get_relatorio_receitas(usuario_id, 'mes')
    elif mensagem_lower in ['ganhos do ano', 'receitas do ano']:
        return get_relatorio_receitas(usuario_id, 'ano')
    
    # Se não for comando específico de receita, verifica se é uma nova receita
    elif any(palavra in mensagem_lower for palavra in ['receita', 'ganho', 'salário', 'salario', 'renda', 'recebimento']):
        return processar_nova_receita(mensagem, usuario_id)
    
    return None

def get_relatorio_receitas(usuario_id, periodo):
    """Gera relatório de receitas"""
    hoje = datetime.now()
    
    if periodo == "dia":
        periodo_texto = "hoje"
        data_inicio = hoje.strftime("%Y-%m-%d")
    elif periodo == "semana":
        periodo_texto = "na última semana"
        data_inicio = (hoje - timedelta(days=7)).strftime("%Y-%m-%d")
    elif periodo == "mes":
        periodo_texto = "neste mês"
        data_inicio = f"{hoje.year}-{hoje.month:02d}-01"
    elif periodo == "ano":
        periodo_texto = "neste ano"
        data_inicio = f"{hoje.year}-01-01"
    else:
        periodo_texto = "em todos os tempos"
        data_inicio = "2000-01-01"
    
    data_fim = hoje.strftime("%Y-%m-%d")
    
    # Busca receitas
    receita_model = Receita(Config.DATABASE)
    receitas = receita_model.buscar(usuario_id, data_inicio, data_fim)
    
    if not receitas:
        return f"💰 Não há receitas registradas {periodo_texto}."
    
    # Calcula totais
    total = receita_model.total_periodo(usuario_id, data_inicio, data_fim)
    categorias = receita_model.total_por_categoria(usuario_id, data_inicio, data_fim)
    
    # Monta relatório
    report = f"💰 *Relatório de receitas {periodo_texto}*\n\n"
    report += f"💵 Total recebido: *R$ {total:.2f}*\n\n"
    report += "🔍 *Por categoria:*\n"
    
    # Emojis por categoria
    emojis_categoria = {
        'salário': '💼',
        'salario': '💼',
        'freelance': '💻',
        'investimentos': '📈',
        'vendas': '🛒',
        'comissões': '💰',
        'comissoes': '💰',
        'outros': '💰'
    }
    
    for categoria in categorias:
        nome = categoria['categoria']
        valor = categoria['total']
        percent = (valor / total) * 100
        emoji = emojis_categoria.get(nome.lower(), '💰')
        report += f"- {emoji} {nome.capitalize()}: R$ {valor:.2f} ({percent:.1f}%)\n"
    
    # Últimas receitas
    report += "\n📝 *Últimas receitas:*\n"
    for i, receita in enumerate(receitas[:3]):
        data = datetime.strptime(receita['data'], "%Y-%m-%d").strftime("%d/%m")
        emoji = emojis_categoria.get(receita['categoria'].lower(), '💰')
        report += f"{i+1}. {data}: R$ {receita['valor']:.2f} - {emoji} {receita['descricao'][:20]}\n"
    
    report += f"\n🔍 Acesse {Config.WEBHOOK_BASE_URL}/receitas para ver mais detalhes!"
    
    return report

def processar_nova_receita(mensagem, usuario_id):
    """Processa mensagem para criar nova receita"""
    # Extrai informações da receita
    processador = TextProcessor()
    dados_receita = processador.extrair_informacoes_despesa(mensagem)  # Reutiliza o método
    
    if not dados_receita or not dados_receita.get("valor"):
        return (
            "Não consegui identificar um valor de receita na sua mensagem. 🤔\n\n"
            "Por favor, inclua o valor recebido, por exemplo:\n"
            "• \"Receita salário R$ 3000\"\n"
            "• \"Ganho freelance 500 reais\"\n"
            "• \"Recebimento 1200,50\"\n\n"
            "Ou envie \"ajuda\" para ver todos os comandos."
        )
    
    try:
        # Determina categoria baseada no contexto
        categoria = determinar_categoria_receita(mensagem.lower())
        
        # Salva a receita
        receita_model = Receita(Config.DATABASE)
        receita_id = receita_model.criar(
            usuario_id=usuario_id,
            valor=dados_receita["valor"],
            categoria=categoria,
            descricao=dados_receita.get("descricao", "Receita via WhatsApp"),
            data=dados_receita.get("data", datetime.now().strftime("%Y-%m-%d")),
            tipo_perfil='pessoal'
        )
        
        # Emoji da categoria
        emojis_categoria = {
            'salário': '💼',
            'salario': '💼',
            'freelance': '💻',
            'investimentos': '📈',
            'vendas': '🛒',
            'comissões': '💰',
            'comissoes': '💰',
            'outros': '💰'
        }
        emoji = emojis_categoria.get(categoria.lower(), '💰')
        
        # Resposta
        resposta = (
            f"✅ Receita registrada!\n\n"
            f"💰 Valor: R$ {dados_receita['valor']:.2f}\n"
            f"🏷️ Categoria: {emoji} {categoria.capitalize()}\n"
            f"📅 Data: {datetime.strptime(dados_receita.get('data', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d').strftime('%d/%m/%Y')}\n"
        )
        
        resposta += f"\nVeja suas receitas em: {Config.WEBHOOK_BASE_URL}/receitas"
        
        return resposta
        
    except Exception as e:
        return f"Erro ao salvar receita: {str(e)}"

def determinar_categoria_receita(mensagem_lower):
    """Determina a categoria da receita baseada no contexto"""
    if any(palavra in mensagem_lower for palavra in ['salário', 'salario', 'ordenado']):
        return 'salário'
    elif any(palavra in mensagem_lower for palavra in ['freelance', 'freela', 'trabalho extra']):
        return 'freelance'
    elif any(palavra in mensagem_lower for palavra in ['investimento', 'dividendo', 'juros', 'rendimento']):
        return 'investimentos'
    elif any(palavra in mensagem_lower for palavra in ['venda', 'vendeu', 'comissão', 'comissao']):
        return 'vendas'
    elif any(palavra in mensagem_lower for palavra in ['presente', 'gift', 'doação', 'doacao']):
        return 'outros'
    else:
        return 'outros'