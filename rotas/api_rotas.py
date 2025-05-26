from flask import Blueprint, request, jsonify, session
from datetime import datetime, timedelta
from database.models import Usuario, Despesa, Receita, Divida, Orcamento, PagamentoFixo, Membro, CategoriaPersonalizada, Lembrete, TextProcessor, MetaFinanceira
from config import Config
import pandas as pd
import json
import io
import os
import tempfile
from werkzeug.utils import secure_filename
import sqlite3
from functools import wraps
import traceback

# Criação do blueprint
api_bp = Blueprint('api', __name__)

# Middleware para verificar API
def api_login_required(f):
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return jsonify({"error": "Não autorizado"}), 401
        return f(*args, **kwargs)
    return decorated_function

# Rota para obter despesas
@api_bp.route('/despesas')
@api_login_required
def get_despesas():
    """API para obter despesas do usuário"""
    usuario_id = session.get('usuario_id')
    
    # Parâmetros de filtro
    periodo = request.args.get('periodo', 'mes')
    categoria = request.args.get('categoria')
    
    # Define o período
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
    
    # Se não for período personalizado, data_fim é hoje
    if periodo != 'personalizado':
        data_fim = hoje.strftime("%Y-%m-%d")
    
    # Busca as despesas
    despesa_model = Despesa(Config.DATABASE)
    despesas = despesa_model.buscar(
        usuario_id, 
        data_inicio=data_inicio, 
        data_fim=data_fim,
        categoria=categoria
    )
    
    return jsonify(despesas)

# Rota para adicionar uma despesa
@api_bp.route('/despesas', methods=['POST'])
@api_login_required
def add_despesa():
    """API para adicionar uma despesa com suporte a arquivos"""
    usuario_id = session.get('usuario_id')
    
    # Verifica se a requisição contém um arquivo
    if request.files and 'foto' in request.files and request.files['foto'].filename:
        # Processamento de formulário com arquivo
        try:
            # Salva o arquivo
            file = request.files['foto']
            if not allowed_file(file.filename, ALLOWED_EXTENSIONS):
                return jsonify({"error": "Formato de arquivo não permitido"}), 400
            
            # Cria um nome de arquivo seguro
            filename = secure_filename(file.filename)
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            
            # Caminho completo para salvar o arquivo
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            
            # Salva o arquivo
            file.save(filepath)
            
            # URL relativa para acessar a imagem
            url = f"/static/uploads/{filename}"
            
            # Obtém os dados do formulário
            valor = float(request.form.get('valor'))
            categoria = request.form.get('categoria')
            descricao = request.form.get('descricao')
            data = request.form.get('data')
            forma_pagamento = request.form.get('forma_pagamento')
            parcelado = int(request.form.get('parcelado', 0))
            num_parcelas = int(request.form.get('num_parcelas', 1)) if parcelado else 1
            tipo_perfil = request.form.get('tipo_perfil', 'pessoal')
            
            # Cria a despesa
            despesa_model = Despesa(Config.DATABASE)
            despesa_id = despesa_model.criar(
                usuario_id=usuario_id,
                valor=valor,
                categoria=categoria,
                descricao=descricao,
                data=data,
                forma_pagamento=forma_pagamento,
                parcelado=parcelado,
                num_parcelas=num_parcelas,
                tipo_perfil=tipo_perfil,
                foto_url=url
            )
            
            return jsonify({"success": True, "id": despesa_id, "foto_url": url}), 201
        
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    else:
        # Processamento normal de JSON
        dados = request.json
        
        # Validações básicas
        if not dados or 'valor' not in dados or 'descricao' not in dados or 'categoria' not in dados or 'data' not in dados:
            return jsonify({"error": "Dados incompletos"}), 400
        
        try:
            # Prepara os dados
            valor = float(dados['valor'])
            categoria = dados['categoria']
            descricao = dados['descricao']
            data = dados['data']
            forma_pagamento = dados.get('forma_pagamento')
            parcelado = int(dados.get('parcelado', 0))
            num_parcelas = int(dados.get('num_parcelas', 1)) if parcelado else 1
            tipo_perfil = dados.get('tipo_perfil', 'pessoal')
            
            # Cria a despesa
            despesa_model = Despesa(Config.DATABASE)
            despesa_id = despesa_model.criar(
                usuario_id=usuario_id,
                valor=valor,
                categoria=categoria,
                descricao=descricao,
                data=data,
                forma_pagamento=forma_pagamento,
                parcelado=parcelado,
                num_parcelas=num_parcelas,
                tipo_perfil=tipo_perfil
            )
            
            return jsonify({"success": True, "id": despesa_id}), 201
            
        except Exception as e:
            return jsonify({"error": str(e)}), 400

@api_bp.route('/test')
def test_api():
    """Rota de teste para verificar se a API está funcionando"""
    return jsonify({"status": "API funcionando", "timestamp": datetime.now().isoformat()})

# 2. Adicione esta rota para verificar dados do usuário:
@api_bp.route('/debug/usuario')
@api_login_required
def debug_usuario():
    """Debug: Verifica dados do usuário"""
    usuario_id = session.get('usuario_id')
    
    try:
        # Testa todas as models
        usuario_model = Usuario(Config.DATABASE)
        usuario = usuario_model.buscar_por_id(usuario_id)
        
        lembrete_model = Lembrete(Config.DATABASE)
        lembretes = lembrete_model.buscar(usuario_id=usuario_id, concluido=0)
        
        despesa_model = Despesa(Config.DATABASE)
        despesas = despesa_model.buscar(usuario_id=usuario_id, limit=5)
        
        return jsonify({
            "usuario_id": usuario_id,
            "usuario": usuario,
            "lembretes_count": len(lembretes),
            "lembretes": lembretes[:3] if lembretes else [],
            "despesas_count": len(despesas),
            "despesas": despesas[:3] if despesas else [],
            "status": "OK"
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "usuario_id": usuario_id,
            "status": "ERROR"
        }), 500
    
@api_bp.route('/debug/tabelas')
@api_login_required  
def debug_tabelas():
    """Debug: Verifica se as tabelas existem no banco"""
    try:
        conn = sqlite3.connect(Config.DATABASE)
        cursor = conn.cursor()
        
        # Lista todas as tabelas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tabelas = cursor.fetchall()
        
        # Verifica estrutura de cada tabela importante
        estruturas = {}
        tabelas_importantes = ['usuarios', 'despesas', 'receitas', 'lembretes', 'orcamentos', 'metas_financeiras', 'dividas']
        
        for tabela in tabelas_importantes:
            try:
                cursor.execute(f"PRAGMA table_info({tabela})")
                estruturas[tabela] = cursor.fetchall()
            except:
                estruturas[tabela] = "TABELA NÃO EXISTE"
        
        conn.close()
        
        return jsonify({
            "tabelas_existentes": [t[0] for t in tabelas],
            "estruturas": estruturas,
            "status": "OK"
        })
        
    except Exception as e:
        return jsonify({"error": str(e), "status": "ERROR"}), 500
    
# Rota para obter receitas
@api_bp.route('/receitas')
@api_login_required
def get_receitas():
    """API para obter receitas do usuário"""
    usuario_id = session.get('usuario_id')
    
    # Parâmetros de filtro
    periodo = request.args.get('periodo', 'mes')
    categoria = request.args.get('categoria')
    
    # Define o período
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
    
    # Se não for período personalizado, data_fim é hoje
    if periodo != 'personalizado':
        data_fim = hoje.strftime("%Y-%m-%d")
    
    # Busca as receitas
    receita_model = Receita(Config.DATABASE)
    receitas = receita_model.buscar(
        usuario_id, 
        data_inicio=data_inicio, 
        data_fim=data_fim,
        categoria=categoria
    )
    
    return jsonify(receitas)

# Rota para adicionar uma receita
@api_bp.route('/receitas', methods=['POST'])
@api_login_required
def add_receita():
    """API para adicionar uma receita com suporte a arquivos"""
    usuario_id = session.get('usuario_id')
    
    # Verifica se a requisição contém um arquivo
    if request.files and 'foto' in request.files and request.files['foto'].filename:
        # Processamento de formulário com arquivo
        try:
            # Salva o arquivo
            file = request.files['foto']
            if not allowed_file(file.filename, ALLOWED_EXTENSIONS):
                return jsonify({"error": "Formato de arquivo não permitido"}), 400
            
            # Cria um nome de arquivo seguro
            filename = secure_filename(file.filename)
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            
            # Caminho completo para salvar o arquivo
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            
            # Salva o arquivo
            file.save(filepath)
            
            # URL relativa para acessar a imagem
            url = f"/static/uploads/{filename}"
            
            # Obtém os dados do formulário
            valor = float(request.form.get('valor'))
            categoria = request.form.get('categoria')
            descricao = request.form.get('descricao')
            data = request.form.get('data')
            recorrente = int(request.form.get('recorrente', 0))
            periodicidade = request.form.get('periodicidade') if recorrente else None
            tipo_perfil = request.form.get('tipo_perfil', 'pessoal')
            
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
                tipo_perfil=tipo_perfil,
                foto_url=url
            )
            
            return jsonify({"success": True, "id": receita_id, "foto_url": url}), 201
        
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    else:
        # Processamento normal de JSON
        dados = request.json
        
        # Validações básicas
        if not dados or 'valor' not in dados or 'descricao' not in dados or 'categoria' not in dados or 'data' not in dados:
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

# Diretório para salvar as imagens
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_AUDIO = {'mp3', 'wav', 'ogg', 'm4a'}

# Certifica-se de que o diretório existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

# Rota para processar upload de imagem
@api_bp.route('/upload/imagem', methods=['POST'])
@api_login_required
def upload_imagem():
    """API para fazer upload de imagens"""
    if 'file' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "Nenhum arquivo selecionado"}), 400
    
    if file and allowed_file(file.filename, ALLOWED_EXTENSIONS):
        # Cria um nome de arquivo seguro
        filename = secure_filename(file.filename)
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        
        # Caminho completo para salvar o arquivo
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        # Salva o arquivo
        file.save(filepath)
        
        # URL relativa para acessar a imagem
        url = f"/static/uploads/{filename}"
        
        # Se for uma imagem de comprovante, tenta fazer OCR
        ocr_resultado = None
        if request.form.get('tipo') == 'comprovante':
            # Aqui você usaria uma biblioteca de OCR (por exemplo, pytesseract)
            # Para este exemplo, simulamos alguns resultados
            ocr_resultado = {
                "detectado": True,
                "valor": round(random.uniform(10, 500), 2),
                "data": datetime.now().strftime("%Y-%m-%d"),
                "estabelecimento": "Estabelecimento",
                "categoria_sugerida": "alimentação"
            }
        
        return jsonify({
            "success": True, 
            "url": url, 
            "filename": filename,
            "ocr_resultado": ocr_resultado
        }), 201
    
    return jsonify({"error": "Formato de arquivo não permitido"}), 400

# Rota para processar upload de áudio
@api_bp.route('/upload/audio', methods=['POST'])
@api_login_required
def upload_audio():
    """API para fazer upload de arquivos de áudio"""
    if 'file' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "Nenhum arquivo selecionado"}), 400
    
    if file and allowed_file(file.filename, ALLOWED_AUDIO):
        # Cria um nome de arquivo seguro
        filename = secure_filename(file.filename)
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        
        # Caminho completo para salvar o arquivo
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        # Salva o arquivo
        file.save(filepath)
        
        # URL relativa para acessar o áudio
        url = f"/static/uploads/{filename}"
        
        # Aqui você faria a transcrição do áudio para texto
        # Para este exemplo, simulamos o resultado
        resultado_texto = "Compra no supermercado 157 reais"
        
        # Processa o texto para extrair informações da despesa
        from database.models import TextProcessor
        processador = TextProcessor()
        dados_despesa = processador.extrair_informacoes_despesa(resultado_texto)
        
        return jsonify({
            "success": True, 
            "url": url, 
            "filename": filename,
            "texto": resultado_texto,
            "dados_extraidos": dados_despesa
        }), 201
    
    return jsonify({"error": "Formato de arquivo não permitido"}), 400

# Rota para obter gráfico por categoria
@api_bp.route('/grafico/por_categoria')
@api_login_required
def get_grafico_por_categoria():
    """API para obter dados do gráfico de despesas por categoria"""
    usuario_id = session.get('usuario_id')
    
    # Parâmetros de filtro
    periodo = request.args.get('periodo', 'mes')
    
    # Define o período
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
    
    # Se não for período personalizado, data_fim é hoje
    if periodo != 'personalizado':
        data_fim = hoje.strftime("%Y-%m-%d")
    
    # Busca as despesas por categoria
    despesa_model = Despesa(Config.DATABASE)
    categorias = despesa_model.total_por_categoria(
        usuario_id, 
        data_inicio=data_inicio, 
        data_fim=data_fim
    )
    
    if not categorias:
        # Dados de exemplo para quando não há despesas
        dados_exemplo = [
            {"categoria": "alimentação", "total": 540.25},
            {"categoria": "transporte", "total": 320.40},
            {"categoria": "moradia", "total": 150.00},
            {"categoria": "lazer", "total": 180.50},
            {"categoria": "saúde", "total": 59.50}
        ]
        categorias = dados_exemplo
    
    # Converte para DataFrame para facilitar o processamento
    df = pd.DataFrame(categorias)
    
    # Define cores para as categorias
    cores = {
        'alimentação': '#FFA726',
        'transporte': '#42A5F5',
        'moradia': '#66BB6A',
        'saúde': '#EC407A',
        'educação': '#AB47BC',
        'lazer': '#26C6DA',
        'vestuário': '#8D6E63',
        'outros': '#78909C'
    }
    
    # Cores para as categorias presentes no dataset
    cores_categorias = [cores.get(cat, '#78909C') for cat in df['categoria']]
    
    # Calcula o total
    total = df['total'].sum()
    
    # Cria o gráfico
    dados_grafico = [{
        'values': df['total'].tolist(),
        'labels': df['categoria'].tolist(),
        'type': 'pie',
        'hole': 0.6,
        'textinfo': 'label+percent',
        'textposition': 'outside',
        'marker': {
            'colors': cores_categorias
        }
    }]
    
    layout_grafico = {
        'margin': {'l': 10, 'r': 10, 't': 10, 'b': 10},
        'showlegend': False,
        'height': 300,
        'annotations': [{
            'font': {'size': 14},
            'showarrow': False,
            'text': f'R$ {total:.2f}',
            'x': 0.5,
            'y': 0.5
        }]
    }
    
    return jsonify({'data': dados_grafico, 'layout': layout_grafico})

# Rota para obter gráfico por tempo
@api_bp.route('/grafico/por_tempo')
@api_login_required
def get_grafico_por_tempo():
    """API para obter dados do gráfico de despesas por tempo"""
    usuario_id = session.get('usuario_id')
    
    # Parâmetros de filtro
    periodo = request.args.get('periodo', 'mes')
    
    # Define o período
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
    
    # Se não for período personalizado, data_fim é hoje
    if periodo != 'personalizado':
        data_fim = hoje.strftime("%Y-%m-%d")
    
    # Busca as despesas por dia
    despesa_model = Despesa(Config.DATABASE)
    despesas_por_dia = despesa_model.total_por_dia(
        usuario_id, 
        data_inicio=data_inicio, 
        data_fim=data_fim
    )
    
    if not despesas_por_dia:
        # Dados de exemplo para quando não há despesas
        datas_exemplo = [(hoje - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(5)]
        valores_exemplo = [120.35, 85.50, 200.80, 150.20, 79.96]
        despesas_por_dia = [{"data": d, "total": v} for d, v in zip(datas_exemplo, valores_exemplo)]
    
    # Converte para DataFrame para facilitar o processamento
    df = pd.DataFrame(despesas_por_dia)
    
    # Cria o gráfico
    dados_grafico = [{
        'x': df['data'].tolist(),
        'y': df['total'].tolist(),
        'type': 'scatter',
        'mode': 'lines+markers',
        'line': {'color': '#28a745', 'width': 3},
        'marker': {'color': '#28a745', 'size': 8}
    }]
    
    layout_grafico = {
        'margin': {'l': 40, 'r': 10, 't': 10, 'b': 40},
        'showlegend': False,
        'height': 300,
        'xaxis': {
            'title': 'Data',
            'tickformat': '%d/%m'
        },
        'yaxis': {
            'title': 'Valor (R$)'
        }
    }
    
    return jsonify({'data': dados_grafico, 'layout': layout_grafico})

# Rota para exportar despesas em CSV
@api_bp.route('/exportar/despesas')
@api_login_required
def exportar_despesas():
    """API para exportar despesas em CSV"""
    from flask import send_file
    
    usuario_id = session.get('usuario_id')
    
    # Parâmetros de filtro
    periodo = request.args.get('periodo')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    # Define o período se não fornecido explicitamente
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
    
    # Busca as despesas
    despesa_model = Despesa(Config.DATABASE)
    despesas = despesa_model.buscar(
        usuario_id, 
        data_inicio=data_inicio, 
        data_fim=data_fim
    )
    
    if not despesas:
        return jsonify({"error": "Não há despesas para exportar"}), 404
    
    # Converte para DataFrame
    df = pd.DataFrame(despesas)
    
    # Reformata colunas para melhor legibilidade
    df['data'] = pd.to_datetime(df['data']).dt.strftime('%d/%m/%Y')
    df['data_criacao'] = pd.to_datetime(df['data_criacao']).dt.strftime('%d/%m/%Y %H:%M:%S')
    
    # Traduz nomes das colunas
    colunas = {
        'id': 'ID',
        'usuario_id': 'ID do Usuário',
        'valor': 'Valor',
        'categoria': 'Categoria',
        'descricao': 'Descrição',
        'data': 'Data',
        'forma_pagamento': 'Forma de Pagamento',
        'parcelado': 'Parcelado',
        'num_parcelas': 'Número de Parcelas',
        'data_criacao': 'Data de Criação',
        'mensagem_original': 'Mensagem Original'
    }
    df = df.rename(columns=colunas)
    
    # Cria o CSV em memória
    csv_data = df.to_csv(index=False)
    
    # Envia o arquivo
    return send_file(
        io.BytesIO(csv_data.encode()),
        mimetype='text/csv',
        download_name='despesas.csv',
        as_attachment=True
    )

# Rota para exportar receitas em CSV
@api_bp.route('/exportar/receitas')
@api_login_required
def exportar_receitas():
    """API para exportar receitas em CSV"""
    from flask import send_file
    
    usuario_id = session.get('usuario_id')
    
    # Parâmetros de filtro
    periodo = request.args.get('periodo')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    # Define o período se não fornecido explicitamente
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
    
    # Busca as receitas
    receita_model = Receita(Config.DATABASE)
    receitas = receita_model.buscar(
        usuario_id, 
        data_inicio=data_inicio, 
        data_fim=data_fim
    )
    
    if not receitas:
        return jsonify({"error": "Não há receitas para exportar"}), 404
    
    # Converte para DataFrame
    df = pd.DataFrame(receitas)
    
    # Reformata colunas para melhor legibilidade
    df['data'] = pd.to_datetime(df['data']).dt.strftime('%d/%m/%Y')
    df['data_criacao'] = pd.to_datetime(df['data_criacao']).dt.strftime('%d/%m/%Y %H:%M:%S')
    
    # Traduz nomes das colunas
    colunas = {
        'id': 'ID',
        'usuario_id': 'ID do Usuário',
        'valor': 'Valor',
        'categoria': 'Categoria',
        'descricao': 'Descrição',
        'data': 'Data',
        'recorrente': 'Recorrente',
        'periodicidade': 'Periodicidade',
        'data_criacao': 'Data de Criação'
    }
    df = df.rename(columns=colunas)
    
    # Cria o CSV em memória
    csv_data = df.to_csv(index=False)
    
    # Envia o arquivo
    return send_file(
        io.BytesIO(csv_data.encode()),
        mimetype='text/csv',
        download_name='receitas.csv',
        as_attachment=True
    )

# Rota para gerar imagem do gráfico
@api_bp.route('/grafico/imagem')
@api_login_required
def get_grafico_imagem():
    """Gera uma imagem do gráfico para envio pelo WhatsApp"""
    from flask import send_file
    import plotly.graph_objects as go
    import plotly.io as pio
    
    usuario_id = session.get('usuario_id')
    
    # Parâmetros
    tipo = request.args.get('tipo', 'categoria')  # categoria ou tempo
    periodo = request.args.get('periodo', 'mes')
    
    # Define o período
    hoje = datetime.now()
    
    if periodo == 'dia':
        data_inicio = hoje.strftime("%Y-%m-%d")
        periodo_texto = "hoje"
    elif periodo == 'semana':
        data_inicio = (hoje - timedelta(days=7)).strftime("%Y-%m-%d")
        periodo_texto = "na última semana"
    elif periodo == 'mes':
        data_inicio = f"{hoje.year}-{hoje.month:02d}-01"
        periodo_texto = "neste mês"
    elif periodo == 'ano':
        data_inicio = f"{hoje.year}-01-01"
        periodo_texto = "neste ano"
    else:
        data_inicio = None
        periodo_texto = "em todos os tempos"
    
    data_fim = hoje.strftime("%Y-%m-%d")
    
    # Cria o gráfico de acordo com o tipo
    despesa_model = Despesa(Config.DATABASE)
    
    if tipo == 'categoria':
        # Busca despesas por categoria
        categorias = despesa_model.total_por_categoria(
            usuario_id, 
            data_inicio=data_inicio, 
            data_fim=data_fim
        )
        
        if not categorias:
            # Dados de exemplo para quando não há despesas
            dados_exemplo = [
                {"categoria": "alimentação", "total": 540.25},
                {"categoria": "transporte", "total": 320.40},
                {"categoria": "moradia", "total": 150.00},
                {"categoria": "lazer", "total": 180.50},
                {"categoria": "saúde", "total": 59.50}
            ]
            categorias = dados_exemplo
        
        # Converte para DataFrame
        df = pd.DataFrame(categorias)
        
        # Define cores para as categorias
        cores = {
            'alimentação': '#FFA726',
            'transporte': '#42A5F5',
            'moradia': '#66BB6A',
            'saúde': '#EC407A',
            'educação': '#AB47BC',
            'lazer': '#26C6DA',
            'vestuário': '#8D6E63',
            'outros': '#78909C'
        }
        
        # Cores para as categorias presentes no dataset
        cores_categorias = [cores.get(cat, '#78909C') for cat in df['categoria']]
        
        # Calcula o total
        total = df['total'].sum()
        
        # Cria a figura
        fig = go.Figure(data=[go.Pie(
            labels=df['categoria'],
            values=df['total'],
            hole=0.6,
            textinfo='percent',
            marker_colors=cores_categorias
        )])
        
        fig.update_layout(
            title_text=f"Despesas por categoria {periodo_texto}<br>Total: R$ {total:.2f}",
            font=dict(size=14),
            width=800,
            height=600,
            showlegend=True
        )
        
    else:  # tipo == 'tempo'
        # Busca despesas por dia
        despesas_por_dia = despesa_model.total_por_dia(
            usuario_id, 
            data_inicio=data_inicio, 
            data_fim=data_fim
        )
        
        if not despesas_por_dia:
            # Dados de exemplo
            datas_exemplo = [(hoje - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(5)]
            valores_exemplo = [120.35, 85.50, 200.80, 150.20, 79.96]
            despesas_por_dia = [{"data": d, "total": v} for d, v in zip(datas_exemplo, valores_exemplo)]
        
        # Converte para DataFrame
        df = pd.DataFrame(despesas_por_dia)
        
        # Formata as datas
        df['data_formatada'] = pd.to_datetime(df['data']).dt.strftime('%d/%m')
        
        # Cria a figura
        fig = go.Figure(data=[go.Scatter(
            x=df['data_formatada'],
            y=df['total'],
            mode='lines+markers',
            line=dict(color='#28a745', width=3),
            marker=dict(color='#28a745', size=8)
        )])
        
        fig.update_layout(
            title_text=f"Despesas ao longo do tempo {periodo_texto}",
            font=dict(size=14),
            width=800,
            height=600,
            xaxis=dict(title='Data'),
            yaxis=dict(title='Valor (R$)')
        )
    
    # Gera a imagem
    img_bytes = io.BytesIO()
    
    try:
        pio.write_image(fig, img_bytes, format='png')
        img_bytes.seek(0)
        
        # Envia a imagem
        return send_file(
            img_bytes, 
            mimetype='image/png',
            download_name=f'grafico_{tipo}_{periodo}.png',
            as_attachment=False
        )
    except Exception as e:
        # Caso ocorra erro ao gerar imagem, retorna JSON com mensagem
        return jsonify({
            "error": "Não foi possível gerar a imagem", 
            "details": str(e),
            "message": "É necessário instalar o pacote kaleido para gerar imagens: pip install kaleido"
        }), 500

# Rota para obter resumo
@api_bp.route('/resumo')
@api_login_required
def get_resumo():
    """API para obter resumo financeiro"""
    usuario_id = session.get('usuario_id')
    
    # Parâmetros
    periodo = request.args.get('periodo', 'mes')
    
    # Define o período
    hoje = datetime.now()
    
    if periodo == 'dia':
        data_inicio = hoje.strftime("%Y-%m-%d")
        periodo_texto = "hoje"
    elif periodo == 'semana':
        data_inicio = (hoje - timedelta(days=7)).strftime("%Y-%m-%d")
        periodo_texto = "na última semana"
    elif periodo == 'mes':
        data_inicio = f"{hoje.year}-{hoje.month:02d}-01"
        periodo_texto = "neste mês"
    elif periodo == 'ano':
        data_inicio = f"{hoje.year}-01-01"
        periodo_texto = "neste ano"
    else:
        data_inicio = None
        periodo_texto = "em todos os tempos"
    
    data_fim = hoje.strftime("%Y-%m-%d")
    
    # Busca os totais
    despesa_model = Despesa(Config.DATABASE)
    receita_model = Receita(Config.DATABASE)
    
    total_despesas = despesa_model.total_periodo(
        usuario_id, 
        data_inicio=data_inicio, 
        data_fim=data_fim
    )
    
    total_receitas = receita_model.total_periodo(
        usuario_id, 
        data_inicio=data_inicio, 
        data_fim=data_fim
    )
    
    # Calcula o saldo e percentual de economia
    saldo = total_receitas - total_despesas
    
    economia_percentual = 0
    if total_receitas > 0:
        economia_percentual = (saldo / total_receitas) * 100
    
    # Busca as despesas por categoria
    categorias = despesa_model.total_por_categoria(
        usuario_id, 
        data_inicio=data_inicio, 
        data_fim=data_fim
    )
    
    # Busca as últimas despesas
    ultimas_despesas = despesa_model.buscar(
        usuario_id, 
        data_inicio=data_inicio, 
        data_fim=data_fim,
        limit=5
    )
    
    # Cria o objeto de resposta
    resumo = {
        'periodo': periodo_texto,
        'total_despesas': round(total_despesas, 2),
        'total_receitas': round(total_receitas, 2),
        'saldo': round(saldo, 2),
        'economia_percentual': round(economia_percentual, 1),
        'despesas_por_categoria': categorias,
        'ultimas_despesas': ultimas_despesas
    }
    
    return jsonify(resumo)

# Rota para obter dados do usuário
@api_bp.route('/usuario')
@api_login_required
def get_usuario():
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

# Rota para atualizar dados do usuário
@api_bp.route('/usuario', methods=['PUT'])
@api_login_required
def update_usuario():
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
        
        # Atualiza o usuário
        usuario_model = Usuario(Config.DATABASE)
        usuario_model.atualizar(
            usuario_id=usuario_id,
            nome=nome,
            email=email,
            senha=senha
        )
        
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Rota para deletar transação (despesa ou receita)
@api_bp.route('/despesas/<int:despesa_id>', methods=['DELETE'])
@api_login_required
def delete_despesa(despesa_id):
    """API para deletar uma despesa"""
    usuario_id = session.get('usuario_id')
    
    # Busca a despesa para verificar se pertence ao usuário
    despesa_model = Despesa(Config.DATABASE)
    despesa = despesa_model.buscar_por_id(despesa_id)
    
    if not despesa:
        return jsonify({"error": "Despesa não encontrada"}), 404
    
    # Verifica se a despesa pertence ao usuário logado
    if despesa['usuario_id'] != usuario_id:
        return jsonify({"error": "Não autorizado"}), 403
    
    # Exclui a despesa
    sucesso = despesa_model.excluir(despesa_id)
    
    if sucesso:
        return jsonify({"success": True}), 200
    else:
        return jsonify({"error": "Não foi possível excluir a despesa"}), 500

# Rota para deletar uma receita
@api_bp.route('/receitas/<int:receita_id>', methods=['DELETE'])
@api_login_required
def delete_receita(receita_id):
    """API para deletar uma receita"""
    usuario_id = session.get('usuario_id')
    
    # Busca a receita para verificar se pertence ao usuário
    receita_model = Receita(Config.DATABASE)
    receita = receita_model.buscar_por_id(receita_id)
    
    if not receita:
        return jsonify({"error": "Receita não encontrada"}), 404
    
    # Verifica se a receita pertence ao usuário logado
    if receita['usuario_id'] != usuario_id:
        return jsonify({"error": "Não autorizado"}), 403
    
    # Exclui a receita
    sucesso = receita_model.excluir(receita_id)
    
    if sucesso:
        return jsonify({"success": True}), 200
    else:
        return jsonify({"error": "Não foi possível excluir a receita"}), 500
    
    # Adicione ao arquivo api_rotas.py

# Importação da classe Lembrete
from database.models import Lembrete

# Rota para obter lembretes
@api_bp.route('/lembretes')
@api_login_required
def get_lembretes():
    """API para obter lembretes do usuário"""
    try:
        usuario_id = session.get('usuario_id')
        
        # Parâmetros de filtro
        tipo_perfil = request.args.get('tipo_perfil')
        concluido = request.args.get('concluido')
        
        if concluido is not None:
            concluido = int(concluido)
        
        # Busca os lembretes
        lembrete_model = Lembrete(Config.DATABASE)
        lembretes = lembrete_model.buscar(
            usuario_id=usuario_id,
            tipo_perfil=tipo_perfil,
            concluido=concluido
        )
        
        # Ordena por data se houver lembretes
        if lembretes:
            lembretes = sorted(lembretes, key=lambda x: x.get('data', '9999-12-31'))
        
        return jsonify(lembretes)
        
    except Exception as e:
        print(f"Erro em get_lembretes: {str(e)}")
        return jsonify({"error": str(e), "lembretes": []}), 500

# Rota para adicionar um lembrete
@api_bp.route('/lembretes', methods=['POST'])
@api_login_required
def add_lembrete():
    """API para adicionar um lembrete"""
    usuario_id = session.get('usuario_id')
    dados = request.json
    
    # Validações básicas
    if not dados or 'titulo' not in dados or 'data' not in dados:
        return jsonify({"error": "Dados incompletos"}), 400
    
    try:
        # Prepara os dados
        titulo = dados['titulo']
        data = dados['data']
        notificacao = int(dados.get('notificacao', 0))
        descricao = dados.get('descricao')
        valor = float(dados['valor']) if 'valor' in dados and dados['valor'] else None
        recorrente = int(dados.get('recorrente', 0))
        periodicidade = dados.get('periodicidade') if recorrente else None
        tipo_perfil = dados.get('tipo_perfil_lembrete', 'pessoal')
        
        # Cria o lembrete
        lembrete_model = Lembrete(Config.DATABASE)
        lembrete_id = lembrete_model.criar(
            usuario_id=usuario_id,
            titulo=titulo,
            data=data,
            notificacao=notificacao,
            descricao=descricao,
            valor=valor,
            recorrente=recorrente,
            periodicidade=periodicidade,
            tipo_perfil=tipo_perfil
        )
        
        return jsonify({"success": True, "id": lembrete_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Rota para atualizar um lembrete
@api_bp.route('/lembretes/<int:lembrete_id>', methods=['PUT'])
@api_login_required
def update_lembrete(lembrete_id):
    """API para atualizar um lembrete"""
    usuario_id = session.get('usuario_id')
    dados = request.json
    
    # Busca o lembrete para verificar se pertence ao usuário
    lembrete_model = Lembrete(Config.DATABASE)
    lembrete = lembrete_model.buscar_por_id(lembrete_id)
    
    if not lembrete:
        return jsonify({"error": "Lembrete não encontrado"}), 404
    
    # Verifica se o lembrete pertence ao usuário logado
    if lembrete['usuario_id'] != usuario_id:
        return jsonify({"error": "Não autorizado"}), 403
    
    try:
        # Atualiza os dados que foram enviados
        campos_update = {}
        
        if 'titulo' in dados:
            campos_update['titulo'] = dados['titulo']
        
        if 'data' in dados:
            campos_update['data'] = dados['data']
        
        if 'notificacao' in dados:
            campos_update['notificacao'] = int(dados['notificacao'])
        
        if 'descricao' in dados:
            campos_update['descricao'] = dados['descricao']
        
        if 'valor' in dados:
            campos_update['valor'] = float(dados['valor']) if dados['valor'] else None
        
        if 'recorrente' in dados:
            campos_update['recorrente'] = int(dados['recorrente'])
        
        if 'periodicidade' in dados:
            campos_update['periodicidade'] = dados['periodicidade']
        
        if 'tipo_perfil' in dados:
            campos_update['tipo_perfil'] = dados['tipo_perfil']
        
        if 'concluido' in dados:
            campos_update['concluido'] = int(dados['concluido'])
        
        # Atualiza o lembrete
        lembrete_model.atualizar(lembrete_id, **campos_update)
        
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Rota para excluir um lembrete
@api_bp.route('/lembretes/<int:lembrete_id>', methods=['DELETE'])
@api_login_required
def delete_lembrete(lembrete_id):
    """API para excluir um lembrete"""
    usuario_id = session.get('usuario_id')
    
    # Busca o lembrete para verificar se pertence ao usuário
    lembrete_model = Lembrete(Config.DATABASE)
    lembrete = lembrete_model.buscar_por_id(lembrete_id)
    
    if not lembrete:
        return jsonify({"error": "Lembrete não encontrado"}), 404
    
    # Verifica se o lembrete pertence ao usuário logado
    if lembrete['usuario_id'] != usuario_id:
        return jsonify({"error": "Não autorizado"}), 403
    
    # Exclui o lembrete
    sucesso = lembrete_model.excluir(lembrete_id)
    
    if sucesso:
        return jsonify({"success": True}), 200
    else:
        return jsonify({"error": "Não foi possível excluir o lembrete"}), 500

# Rota para marcar um lembrete como concluído
@api_bp.route('/lembretes/<int:lembrete_id>/concluir', methods=['PUT'])
@api_login_required
def concluir_lembrete(lembrete_id):
    """API para marcar um lembrete como concluído"""
    usuario_id = session.get('usuario_id')
    
    # Busca o lembrete para verificar se pertence ao usuário
    lembrete_model = Lembrete(Config.DATABASE)
    lembrete = lembrete_model.buscar_por_id(lembrete_id)
    
    if not lembrete:
        return jsonify({"error": "Lembrete não encontrado"}), 404
    
    # Verifica se o lembrete pertence ao usuário logado
    if lembrete['usuario_id'] != usuario_id:
        return jsonify({"error": "Não autorizado"}), 403
    
    # Marca o lembrete como concluído
    sucesso = lembrete_model.marcar_como_concluido(lembrete_id)
    
    if sucesso:
        # Se o lembrete for recorrente, cria uma nova ocorrência
        if lembrete['recorrente']:
            lembrete_model.criar_recorrencia(lembrete_id)
        
        return jsonify({"success": True}), 200
    else:
        return jsonify({"error": "Não foi possível marcar o lembrete como concluído"}), 500
    
    # Adicione ao arquivo api_rotas.py

# Importação da classe CategoriaPersonalizada
from database.models import CategoriaPersonalizada

# Rota para obter categorias
@api_bp.route('/categorias')
@api_login_required
def get_categorias():
    """API para obter categorias personalizadas do usuário"""
    usuario_id = session.get('usuario_id')
    
    # Parâmetros de filtro
    tipo = request.args.get('tipo')
    tipo_perfil = request.args.get('tipo_perfil')
    
    # Busca as categorias
    categoria_model = CategoriaPersonalizada(Config.DATABASE)
    categorias = categoria_model.buscar(
        usuario_id=usuario_id,
        tipo=tipo,
        tipo_perfil=tipo_perfil
    )
    
    return jsonify(categorias)

# Rota para adicionar uma categoria
@api_bp.route('/categorias', methods=['POST'])
@api_login_required
def add_categoria():
    """API para adicionar uma categoria personalizada"""
    usuario_id = session.get('usuario_id')
    dados = request.json
    
    # Validações básicas
    if not dados or 'nome' not in dados or 'tipo_categoria' not in dados:
        return jsonify({"error": "Dados incompletos"}), 400
    
    try:
        # Prepara os dados
        nome = dados['nome']
        tipo = dados['tipo_categoria']
        icone = dados.get('icone', '📦')
        cor = dados.get('cor', '#28a745')
        tipo_perfil = dados.get('tipo_perfil_categoria', 'pessoal')
        
        # Cria a categoria
        categoria_model = CategoriaPersonalizada(Config.DATABASE)
        categoria_id = categoria_model.criar(
            usuario_id=usuario_id,
            nome=nome,
            tipo=tipo,
            icone=icone,
            cor=cor,
            tipo_perfil=tipo_perfil
        )
        
        return jsonify({"success": True, "id": categoria_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Rota para atualizar uma categoria
@api_bp.route('/categorias/<int:categoria_id>', methods=['PUT'])
@api_login_required
def update_categoria(categoria_id):
    """API para atualizar uma categoria personalizada"""
    usuario_id = session.get('usuario_id')
    dados = request.json
    
    # Busca a categoria para verificar se pertence ao usuário
    categoria_model = CategoriaPersonalizada(Config.DATABASE)
    categoria = categoria_model.buscar_por_id(categoria_id)
    
    if not categoria:
        return jsonify({"error": "Categoria não encontrada"}), 404
    
    # Verifica se a categoria pertence ao usuário logado
    if categoria['usuario_id'] != usuario_id:
        return jsonify({"error": "Não autorizado"}), 403
    
    try:
        # Atualiza os dados que foram enviados
        campos_update = {}
        
        if 'nome' in dados:
            campos_update['nome'] = dados['nome']
        
        if 'icone' in dados:
            campos_update['icone'] = dados['icone']
        
        if 'cor' in dados:
            campos_update['cor'] = dados['cor']
        
        if 'tipo' in dados:
            campos_update['tipo'] = dados['tipo']
        
        if 'tipo_perfil' in dados:
            campos_update['tipo_perfil'] = dados['tipo_perfil']
        
        # Atualiza a categoria
        categoria_model.atualizar(categoria_id, **campos_update)
        
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Rota para excluir uma categoria
@api_bp.route('/categorias/<int:categoria_id>', methods=['DELETE'])
@api_login_required
def delete_categoria(categoria_id):
    """API para excluir uma categoria personalizada"""
    usuario_id = session.get('usuario_id')
    
    # Busca a categoria para verificar se pertence ao usuário
    categoria_model = CategoriaPersonalizada(Config.DATABASE)
    categoria = categoria_model.buscar_por_id(categoria_id)
    
    if not categoria:
        return jsonify({"error": "Categoria não encontrada"}), 404
    
    # Verifica se a categoria pertence ao usuário logado
    if categoria['usuario_id'] != usuario_id:
        return jsonify({"error": "Não autorizado"}), 403
    
    # Exclui a categoria
    sucesso, mensagem = categoria_model.excluir(categoria_id)
    
    if sucesso:
        return jsonify({"success": True}), 200
    else:
        return jsonify({"error": mensagem}), 400
    
    # Adicione ao arquivo api_rotas.py

# Importação da classe Membro
from database.models import Membro

# Rota para obter membros
@api_bp.route('/membros')
@api_login_required
def get_membros():
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

# Rota para adicionar um membro
@api_bp.route('/membros', methods=['POST'])
@api_login_required
def add_membro():
    """API para adicionar um membro"""
    usuario_id = session.get('usuario_id')
    dados = request.json
    
    # Validações básicas
    if not dados or 'nome' not in dados or 'email' not in dados or 'tipo_grupo' not in dados:
        return jsonify({"error": "Dados incompletos"}), 400
    
    try:
        # Prepara os dados
        nome = dados['nome']
        email = dados['email']
        tipo_grupo = dados['tipo_grupo']
        permissao = dados.get('permissao', 'visualizador')
        celular = dados.get('celular')
        
        # Verifica se o email já está cadastrado
        membro_model = Membro(Config.DATABASE)
        membro_existente = membro_model.buscar_por_email(email, tipo_grupo)
        
        if membro_existente:
            return jsonify({"error": f"Este email já está cadastrado como membro do grupo {tipo_grupo}."}), 400
        
        # Cria o membro
        membro_id = membro_model.criar(
            usuario_id=usuario_id,
            nome=nome,
            email=email,
            tipo_grupo=tipo_grupo,
            permissao=permissao,
            celular=celular
        )
        
        # Envia convite se tiver email ou celular
        if email or celular:
            membro_model.enviar_convite(membro_id)
        
        return jsonify({"success": True, "id": membro_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Rota para atualizar um membro
@api_bp.route('/membros/<int:membro_id>', methods=['PUT'])
@api_login_required
def update_membro(membro_id):
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
        return jsonify({"error": "Não é possível alterar a permissão do usuário principal."}), 400
    
    try:
        # Atualiza os dados que foram enviados
        campos_update = {}
        
        if 'nome' in dados:
            campos_update['nome'] = dados['nome']
        
        if 'email' in dados:
            campos_update['email'] = dados['email']
        
        if 'celular' in dados:
            campos_update['celular'] = dados['celular']
        
        if 'permissao' in dados:
            campos_update['permissao'] = dados['permissao']
        
        if 'convite_aceito' in dados:
            campos_update['convite_aceito'] = int(dados['convite_aceito'])
        
        # Atualiza o membro
        membro_model.atualizar(membro_id, **campos_update)
        
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Rota para excluir um membro
@api_bp.route('/membros/<int:membro_id>', methods=['DELETE'])
@api_login_required
def delete_membro(membro_id):
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
        return jsonify({"error": "Não é possível excluir o usuário principal."}), 400
    
    # Exclui o membro
    sucesso, mensagem = membro_model.excluir(membro_id)
    
    if sucesso:
        return jsonify({"success": True}), 200
    else:
        return jsonify({"error": mensagem}), 400

# Rota para reenviar convite
@api_bp.route('/membros/<int:membro_id>/reenviar_convite', methods=['POST'])
@api_login_required
def reenviar_convite(membro_id):
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
        return jsonify({"error": "O convite já foi aceito."}), 400
    
    # Envia o convite
    sucesso, mensagem = membro_model.enviar_convite(membro_id)
    
    if sucesso:
        return jsonify({"success": True, "message": mensagem}), 200
    else:
        return jsonify({"error": mensagem}), 400
    
    # Adicione ao arquivo api_rotas.py

# Rota para obter top despesas
@api_bp.route('/despesas/top')
@api_login_required
def get_top_despesas():
    """API para obter top despesas do usuário"""
    usuario_id = session.get('usuario_id')
    
    # Parâmetros de filtro
    periodo = request.args.get('periodo', 'mes')
    tipo_perfil = request.args.get('tipo_perfil')
    limit = int(request.args.get('limit', 5))
    
    # Define o período
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
    
    # Se não for período personalizado, data_fim é hoje
    if periodo != 'personalizado':
        data_fim = hoje.strftime("%Y-%m-%d")
    
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Busca as top despesas
    query = """
    SELECT descricao, valor, categoria, data
    FROM despesas 
    WHERE usuario_id = ?
    """
    params = [usuario_id]
    
    if data_inicio:
        query += " AND data >= ?"
        params.append(data_inicio)
    
    if data_fim:
        query += " AND data <= ?"
        params.append(data_fim)
    
    # Filtro por tipo de perfil
    if tipo_perfil:
        query += " AND (tipo_perfil = ? OR tipo_perfil IS NULL)"
        params.append(tipo_perfil)
    
    query += " ORDER BY valor DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    despesas = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify(despesas)

# Rota para obter gráfico de evolução de saldo
@api_bp.route('/grafico/evolucao_saldo')
@api_login_required
def get_grafico_evolucao_saldo():
    """API para obter dados do gráfico de evolução de saldo"""
    usuario_id = session.get('usuario_id')
    
    # Parâmetros de filtro
    periodo = request.args.get('periodo', 'mes')
    tipo_perfil = request.args.get('tipo_perfil')
    
    # Define o período
    hoje = datetime.now()
    
    if periodo == 'dia':
        dias = 1
        data_inicio = hoje.strftime("%Y-%m-%d")
    elif periodo == 'semana':
        dias = 7
        data_inicio = (hoje - timedelta(days=7)).strftime("%Y-%m-%d")
    elif periodo == 'mes':
        dias = 30
        data_inicio = f"{hoje.year}-{hoje.month:02d}-01"
    elif periodo == 'ano':
        dias = 365
        data_inicio = f"{hoje.year}-01-01"
    else:
        dias = 30
        data_inicio = f"{hoje.year}-{hoje.month:02d}-01"
    
    data_fim = hoje.strftime("%Y-%m-%d")
    
    # Busca as despesas diárias
    despesa_model = Despesa(Config.DATABASE)
    despesas_diarias = despesa_model.total_por_dia(
        usuario_id, 
        data_inicio=data_inicio, 
        data_fim=data_fim,
        tipo_perfil=tipo_perfil
    )
    
    # Busca as receitas diárias
    receita_model = Receita(Config.DATABASE)
    receitas_diarias = receita_model.total_por_dia(
        usuario_id, 
        data_inicio=data_inicio, 
        data_fim=data_fim,
        tipo_perfil=tipo_perfil
    )
    
    # Converte para dicionários para facilitar o acesso
    despesas_dict = {item['data']: item['total'] for item in despesas_diarias}
    receitas_dict = {item['data']: item['total'] for item in receitas_diarias}
    
    # Gera o intervalo de datas
    datas = []
    data_atual = datetime.strptime(data_inicio, "%Y-%m-%d")
    while data_atual <= datetime.strptime(data_fim, "%Y-%m-%d"):
        datas.append(data_atual.strftime("%Y-%m-%d"))
        data_atual += timedelta(days=1)
    
    # Calcula o saldo acumulado
    saldo_acumulado = 0
    dados_grafico = []
    
    for data in datas:
        despesa_dia = despesas_dict.get(data, 0)
        receita_dia = receitas_dict.get(data, 0)
        saldo_dia = receita_dia - despesa_dia
        saldo_acumulado += saldo_dia
        
        dados_grafico.append({
            'data': data,
            'saldo': saldo_acumulado
        })
    
    # Formata para o Plotly
    x = [item['data'] for item in dados_grafico]
    y = [item['saldo'] for item in dados_grafico]
    
    # Cria o gráfico
    dados_plotly = [{
        'x': x,
        'y': y,
        'type': 'scatter',
        'mode': 'lines+markers',
        'line': {'color': '#28a745', 'width': 3},
        'marker': {'color': '#28a745', 'size': 8}
    }]
    
    layout_plotly = {
        'margin': {'l': 40, 'r': 10, 't': 10, 'b': 40},
        'showlegend': False,
        'height': 300,
        'xaxis': {
            'title': 'Data',
            'tickformat': '%d/%m'
        },
        'yaxis': {
            'title': 'Saldo (R$)'
        }
    }
    
    return jsonify({'data': dados_plotly, 'layout': layout_plotly})

# Rota para obter gráfico de evolução de lucro
@api_bp.route('/grafico/evolucao_lucro')
@api_login_required
def get_grafico_evolucao_lucro():
    """API para obter dados do gráfico de evolução de lucro empresarial"""
    usuario_id = session.get('usuario_id')
    
    # Parâmetros de filtro
    periodo = request.args.get('periodo', 'mes')
    
    # Define o período
    hoje = datetime.now()
    
    if periodo == 'dia':
        dias = 1
        data_inicio = hoje.strftime("%Y-%m-%d")
    elif periodo == 'semana':
        dias = 7
        data_inicio = (hoje - timedelta(days=7)).strftime("%Y-%m-%d")
    elif periodo == 'mes':
        dias = 30
        data_inicio = f"{hoje.year}-{hoje.month:02d}-01"
    elif periodo == 'ano':
        dias = 365
        data_inicio = f"{hoje.year}-01-01"
    else:
        dias = 30
        data_inicio = f"{hoje.year}-{hoje.month:02d}-01"
    
    data_fim = hoje.strftime("%Y-%m-%d")
    
    # Busca as despesas diárias para o perfil empresarial
    despesa_model = Despesa(Config.DATABASE)
    despesas_diarias = despesa_model.total_por_dia(
        usuario_id, 
        data_inicio=data_inicio, 
        data_fim=data_fim,
        tipo_perfil='empresarial'
    )
    
    # Busca as receitas diárias para o perfil empresarial
    receita_model = Receita(Config.DATABASE)
    receitas_diarias = receita_model.total_por_dia(
        usuario_id, 
        data_inicio=data_inicio, 
        data_fim=data_fim,
        tipo_perfil='empresarial'
    )
    
    # Converte para dicionários para facilitar o acesso
    despesas_dict = {item['data']: item['total'] for item in despesas_diarias}
    receitas_dict = {item['data']: item['total'] for item in receitas_diarias}
    
    # Gera o intervalo de datas
    datas = []
    data_atual = datetime.strptime(data_inicio, "%Y-%m-%d")
    while data_atual <= datetime.strptime(data_fim, "%Y-%m-%d"):
        datas.append(data_atual.strftime("%Y-%m-%d"))
        data_atual += timedelta(days=1)
    
    # Calcula o lucro diário e acumulado
    lucro_acumulado = 0
    dados_grafico = []
    
    for data in datas:
        despesa_dia = despesas_dict.get(data, 0)
        receita_dia = receitas_dict.get(data, 0)
        lucro_dia = receita_dia - despesa_dia
        lucro_acumulado += lucro_dia
        
        dados_grafico.append({
            'data': data,
            'lucro_dia': lucro_dia,
            'lucro_acumulado': lucro_acumulado
        })
    
    # Formata para o Plotly
    x = [item['data'] for item in dados_grafico]
    y_lucro_dia = [item['lucro_dia'] for item in dados_grafico]
    y_lucro_acumulado = [item['lucro_acumulado'] for item in dados_grafico]
    
    # Cria o gráfico
    dados_plotly = [
        {
            'x': x,
            'y': y_lucro_dia,
            'type': 'bar',
            'name': 'Lucro diário',
            'marker': {'color': '#34c759'}
        },
        {
            'x': x,
            'y': y_lucro_acumulado,
            'type': 'scatter',
            'mode': 'lines',
            'name': 'Lucro acumulado',
            'line': {'color': '#4a6cf7', 'width': 3}
        }
    ]
    
    layout_plotly = {
        'margin': {'l': 40, 'r': 10, 't': 10, 'b': 40},
        'showlegend': True,
        'height': 300,
        'xaxis': {
            'title': 'Data',
            'tickformat': '%d/%m'
        },
        'yaxis': {
            'title': 'Valor (R$)'
        },
        'legend': {
            'orientation': 'h',
            'y': 1.1
        }
    }
    
    return jsonify({'data': dados_plotly, 'layout': layout_plotly})

# Rota para obter gráfico de previsão
@api_bp.route('/grafico/previsao')
@api_login_required
def get_grafico_previsao():
    """API para obter dados do gráfico de previsão (disponível apenas para planos premium+)"""
    # Verificar se o usuário tem plano premium ou superior
    usuario_id = session.get('usuario_id')
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    plano = usuario.get('plano', 'gratuito') if usuario else 'gratuito'
    planos_validos = ['premium', 'familia', 'empresarial']
    
    if plano not in planos_validos:
        return jsonify({
            "error": "Recurso disponível apenas para planos premium ou superior",
            "plano_atual": plano
        }), 403
    
    # Parâmetros de filtro
    periodo = request.args.get('periodo', 'mes')
    tipo_perfil = request.args.get('tipo_perfil', 'pessoal')
    meses_previsao = int(request.args.get('meses', 3))
    
    # Define o período para análise de histórico
    hoje = datetime.now()
    
    # Para previsão, usamos 3x o período solicitado como histórico
    if periodo == 'mes':
        # Analisa os últimos 3 meses para prever os próximos 3
        meses_historico = 3
        data_inicio = (hoje - timedelta(days=meses_historico*30)).strftime("%Y-%m-%d")
    elif periodo == 'ano':
        # Analisa os últimos 12 meses para prever os próximos 3
        data_inicio = (hoje - timedelta(days=365)).strftime("%Y-%m-%d")
    else:
        # Para outros períodos, usa 90 dias
        data_inicio = (hoje - timedelta(days=90)).strftime("%Y-%m-%d")
    
    data_fim = hoje.strftime("%Y-%m-%d")
    
    # Busca o histórico de despesas mensais
    conn = sqlite3.connect(Config.DATABASE)
    cursor = conn.cursor()
    
    query = """
    SELECT strftime('%Y-%m', data) AS mes, SUM(valor) as total
    FROM despesas
    WHERE usuario_id = ? AND data >= ? AND data <= ?
    """
    params = [usuario_id, data_inicio, data_fim]
    
    if tipo_perfil:
        query += " AND (tipo_perfil = ? OR tipo_perfil IS NULL)"
        params.append(tipo_perfil)
    
    query += " GROUP BY mes ORDER BY mes"
    
    cursor.execute(query, params)
    despesas_mensais = cursor.fetchall()
    
    # Busca o histórico de receitas mensais
    query = """
    SELECT strftime('%Y-%m', data) AS mes, SUM(valor) as total
    FROM receitas
    WHERE usuario_id = ? AND data >= ? AND data <= ?
    """
    params = [usuario_id, data_inicio, data_fim]
    
    if tipo_perfil:
        query += " AND (tipo_perfil = ? OR tipo_perfil IS NULL)"
        params.append(tipo_perfil)
    
    query += " GROUP BY mes ORDER BY mes"
    
    cursor.execute(query, params)
    receitas_mensais = cursor.fetchall()
    
    conn.close()
    
    # Prepara os dados para análise
    meses = []
    despesas = []
    receitas = []
    
    # Meses do histórico
    mes_atual = datetime.strptime(data_inicio, "%Y-%m-%d").replace(day=1)
    ultimo_mes = datetime.strptime(data_fim, "%Y-%m-%d").replace(day=1)
    
    while mes_atual <= ultimo_mes:
        mes_str = mes_atual.strftime("%Y-%m")
        meses.append(mes_str)
        
        # Busca despesa para este mês
        despesa_valor = 0
        for mes, total in despesas_mensais:
            if mes == mes_str:
                despesa_valor = total
                break
        despesas.append(despesa_valor)
        
        # Busca receita para este mês
        receita_valor = 0
        for mes, total in receitas_mensais:
            if mes == mes_str:
                receita_valor = total
                break
        receitas.append(receita_valor)
        
        # Avança para o próximo mês
        if mes_atual.month == 12:
            mes_atual = mes_atual.replace(year=mes_atual.year+1, month=1)
        else:
            mes_atual = mes_atual.replace(month=mes_atual.month+1)
    
    # Calcula médias para previsão
    if len(despesas) > 0:
        media_despesas = sum(despesas) / len(despesas)
        # Aplica tendência (exemplo: aumento médio de 5% ao mês)
        if len(despesas) > 1:
            # Calcula tendência com regressão linear básica
            soma_x = sum(range(len(despesas)))
            soma_y = sum(despesas)
            soma_xy = sum(i * despesas[i] for i in range(len(despesas)))
            soma_x2 = sum(i**2 for i in range(len(despesas)))
            n = len(despesas)
            
            if soma_x2 * n - soma_x**2 != 0:  # Evita divisão por zero
                b = (soma_xy * n - soma_x * soma_y) / (soma_x2 * n - soma_x**2)
            else:
                b = 0
        else:
            b = 0
    else:
        media_despesas = 0
        b = 0
    
    if len(receitas) > 0:
        media_receitas = sum(receitas) / len(receitas)
        # Semelhante para receitas
        if len(receitas) > 1:
            soma_x = sum(range(len(receitas)))
            soma_y = sum(receitas)
            soma_xy = sum(i * receitas[i] for i in range(len(receitas)))
            soma_x2 = sum(i**2 for i in range(len(receitas)))
            n = len(receitas)
            
            if soma_x2 * n - soma_x**2 != 0:
                b_receitas = (soma_xy * n - soma_x * soma_y) / (soma_x2 * n - soma_x**2)
            else:
                b_receitas = 0
        else:
            b_receitas = 0
    else:
        media_receitas = 0
        b_receitas = 0
    
    # Gera previsão para meses futuros
    meses_previsao_list = []
    despesas_previsao = []
    receitas_previsao = []
    saldo_previsao = []
    
    for i in range(1, meses_previsao + 1):
        if ultimo_mes.month + i > 12:
            ano = ultimo_mes.year + (ultimo_mes.month + i - 1) // 12
            mes = (ultimo_mes.month + i - 1) % 12 + 1
        else:
            ano = ultimo_mes.year
            mes = ultimo_mes.month + i
        
        mes_prev = datetime(ano, mes, 1)
        mes_prev_str = mes_prev.strftime("%Y-%m")
        meses_previsao_list.append(mes_prev_str)
        
        despesa_prevista = media_despesas + b * (len(despesas) + i - 1)
        receita_prevista = media_receitas + b_receitas * (len(receitas) + i - 1)
        
        # Garante valores positivos
        despesa_prevista = max(0, despesa_prevista)
        receita_prevista = max(0, receita_prevista)
        
        despesas_previsao.append(despesa_prevista)
        receitas_previsao.append(receita_prevista)
        saldo_previsao.append(receita_prevista - despesa_prevista)
    
    # Formata meses para exibição
    meses_exibicao = [datetime.strptime(m, "%Y-%m").strftime("%b/%Y") for m in meses]
    meses_previsao_exibicao = [datetime.strptime(m, "%Y-%m").strftime("%b/%Y") for m in meses_previsao_list]
    
    # Dados do gráfico
    dados_historico = {
        'x': meses_exibicao,
        'despesas': despesas,
        'receitas': receitas,
        'saldo': [r - d for r, d in zip(receitas, despesas)]
    }
    
    dados_previsao = {
        'x': meses_previsao_exibicao,
        'despesas': despesas_previsao,
        'receitas': receitas_previsao,
        'saldo': saldo_previsao
    }
    
    # Cria o gráfico com Plotly
    dados_plotly = [
        # Histórico
        {
            'x': dados_historico['x'],
            'y': dados_historico['despesas'],
            'type': 'scatter',
            'mode': 'lines+markers',
            'name': 'Despesas (histórico)',
            'line': {'color': '#e74c3c', 'width': 3},
            'marker': {'color': '#e74c3c', 'size': 8}
        },
        {
            'x': dados_historico['x'],
            'y': dados_historico['receitas'],
            'type': 'scatter',
            'mode': 'lines+markers',
            'name': 'Receitas (histórico)',
            'line': {'color': '#28a745', 'width': 3},
            'marker': {'color': '#28a745', 'size': 8}
        },
        {
            'x': dados_historico['x'],
            'y': dados_historico['saldo'],
            'type': 'scatter',
            'mode': 'lines+markers',
            'name': 'Saldo (histórico)',
            'line': {'color': '#4a6cf7', 'width': 3},
            'marker': {'color': '#4a6cf7', 'size': 8}
        },
        # Previsão
        {
            'x': dados_previsao['x'],
            'y': dados_previsao['despesas'],
            'type': 'scatter',
            'mode': 'lines+markers',
            'name': 'Despesas (previsão)',
            'line': {'color': '#e74c3c', 'width': 2, 'dash': 'dash'},
            'marker': {'color': '#e74c3c', 'size': 8}
        },
        {
            'x': dados_previsao['x'],
            'y': dados_previsao['receitas'],
            'type': 'scatter',
            'mode': 'lines+markers',
            'name': 'Receitas (previsão)',
            'line': {'color': '#28a745', 'width': 2, 'dash': 'dash'},
            'marker': {'color': '#28a745', 'size': 8}
        },
        {
            'x': dados_previsao['x'],
            'y': dados_previsao['saldo'],
            'type': 'scatter',
            'mode': 'lines+markers',
            'name': 'Saldo (previsão)',
            'line': {'color': '#4a6cf7', 'width': 2, 'dash': 'dash'},
            'marker': {'color': '#4a6cf7', 'size': 8}
        }
    ]
    
    layout_plotly = {
        'margin': {'l': 40, 'r': 10, 't': 30, 'b': 40},
        'title': 'Previsão Financeira',
        'showlegend': True,
        'height': 400,
        'xaxis': {
            'title': 'Mês/Ano'
        },
        'yaxis': {
            'title': 'Valor (R$)'
        },
        'legend': {
            'orientation': 'h',
            'y': 1.1
        },
        'shapes': [
            # Linha vertical separando histórico de previsão
            {
                'type': 'line',
                'x0': meses_exibicao[-1],
                'y0': 0,
                'x1': meses_exibicao[-1],
                'y1': 1,
                'yref': 'paper',
                'line': {
                    'color': 'rgba(0, 0, 0, 0.5)',
                    'width': 1,
                    'dash': 'dot'
                }
            }
        ],
        'annotations': [
            {
                'x': meses_previsao_exibicao[0],
                'y': 1,
                'xref': 'x',
                'yref': 'paper',
                'text': 'Previsão',
                'showarrow': True,
                'arrowhead': 2,
                'ax': 0,
                'ay': -30
            }
        ]
    }
    
    return jsonify({'data': dados_plotly, 'layout': layout_plotly})

# Rota para obter distribuição de gastos ao longo do tempo
@api_bp.route('/grafico/distribuicao_tempo')
@api_login_required
def get_grafico_distribuicao_tempo():
    """API para obter dados do gráfico de distribuição de gastos ao longo do tempo"""
    usuario_id = session.get('usuario_id')
    
    # Parâmetros de filtro
    periodo = request.args.get('periodo', 'mes')
    tipo_perfil = request.args.get('tipo_perfil')
    
    # Define o período
    hoje = datetime.now()
    
    if periodo == 'dia':
        # Para um dia, analisamos as horas
        data_inicio = hoje.strftime("%Y-%m-%d")
        data_fim = hoje.strftime("%Y-%m-%d")
        tipo_agrupamento = 'hora'
    elif periodo == 'semana':
        # Para uma semana, analisamos os dias da semana
        data_inicio = (hoje - timedelta(days=7)).strftime("%Y-%m-%d")
        data_fim = hoje.strftime("%Y-%m-%d")
        tipo_agrupamento = 'dia_semana'
    elif periodo == 'mes':
        # Para um mês, analisamos dias do mês
        data_inicio = f"{hoje.year}-{hoje.month:02d}-01"
        data_fim = hoje.strftime("%Y-%m-%d")
        tipo_agrupamento = 'dia'
    elif periodo == 'ano':
        # Para um ano, analisamos meses
        data_inicio = f"{hoje.year}-01-01"
        data_fim = hoje.strftime("%Y-%m-%d")
        tipo_agrupamento = 'mes'
    else:
        data_inicio = None
        data_fim = None
        tipo_agrupamento = 'mes'
    
    # Consulta SQL para obter dados agrupados por tempo
    conn = sqlite3.connect(Config.DATABASE)
    cursor = conn.cursor()
    
    if tipo_agrupamento == 'hora':
        # Agrupa por hora do dia
        query = """
        SELECT strftime('%H', data_criacao) as periodo, SUM(valor) as total
        FROM despesas
        WHERE usuario_id = ? AND DATE(data_criacao) = ?
        """
        params = [usuario_id, data_inicio]
        
        if tipo_perfil:
            query += " AND (tipo_perfil = ? OR tipo_perfil IS NULL)"
            params.append(tipo_perfil)
        
        query += " GROUP BY periodo ORDER BY periodo"
        
    elif tipo_agrupamento == 'dia_semana':
        # Agrupa por dia da semana (0=Domingo, 1=Segunda, ...)
        query = """
        SELECT strftime('%w', data) as periodo, SUM(valor) as total
        FROM despesas
        WHERE usuario_id = ? AND data BETWEEN ? AND ?
        """
        params = [usuario_id, data_inicio, data_fim]
        
        if tipo_perfil:
            query += " AND (tipo_perfil = ? OR tipo_perfil IS NULL)"
            params.append(tipo_perfil)
        
        query += " GROUP BY periodo ORDER BY periodo"
        
    elif tipo_agrupamento == 'dia':
        # Agrupa por dia do mês
        query = """
        SELECT strftime('%d', data) as periodo, SUM(valor) as total
        FROM despesas
        WHERE usuario_id = ? AND data BETWEEN ? AND ?
        """
        params = [usuario_id, data_inicio, data_fim]
        
        if tipo_perfil:
            query += " AND (tipo_perfil = ? OR tipo_perfil IS NULL)"
            params.append(tipo_perfil)
        
        query += " GROUP BY periodo ORDER BY periodo"
        
    else:  # tipo_agrupamento == 'mes'
        # Agrupa por mês
        query = """
        SELECT strftime('%m', data) as periodo, SUM(valor) as total
        FROM despesas
        WHERE usuario_id = ? AND data BETWEEN ? AND ?
        """
        params = [usuario_id, data_inicio, data_fim]
        
        if tipo_perfil:
            query += " AND (tipo_perfil = ? OR tipo_perfil IS NULL)"
            params.append(tipo_perfil)
        
        query += " GROUP BY periodo ORDER BY periodo"
    
    cursor.execute(query, params)
    resultados = cursor.fetchall()
    
    conn.close()
    
    # Prepara os dados para o gráfico
    nomes_periodos = []
    valores = []
    
    if tipo_agrupamento == 'hora':
        # Para completar todas as 24 horas
        horas = {f"{h:02d}": 0 for h in range(24)}
        for periodo, total in resultados:
            horas[periodo] = total
        
        # Adiciona os dados no gráfico
        for hora, valor in horas.items():
            nomes_periodos.append(f"{hora}h")
            valores.append(valor)
        
        titulo = "Distribuição de gastos por hora do dia"
        
    elif tipo_agrupamento == 'dia_semana':
        # Nomes dos dias da semana
        dias_semana = {
            "0": "Domingo",
            "1": "Segunda",
            "2": "Terça",
            "3": "Quarta",
            "4": "Quinta",
            "5": "Sexta",
            "6": "Sábado"
        }
        
        # Para completar todos os 7 dias da semana
        dias = {str(d): 0 for d in range(7)}
        for periodo, total in resultados:
            dias[periodo] = total
        
        # Adiciona os dados no gráfico
        for dia, valor in dias.items():
            nomes_periodos.append(dias_semana[dia])
            valores.append(valor)
        
        titulo = "Distribuição de gastos por dia da semana"
        
    elif tipo_agrupamento == 'dia':
        # Para completar todos os dias do mês
        ultimo_dia = datetime.strptime(data_fim, "%Y-%m-%d").day
        dias = {f"{d:02d}": 0 for d in range(1, ultimo_dia + 1)}
        
        for periodo, total in resultados:
            dias[periodo] = total
        
        # Adiciona os dados no gráfico
        for dia, valor in dias.items():
            nomes_periodos.append(f"Dia {dia}")
            valores.append(valor)
        
        titulo = "Distribuição de gastos por dia do mês"
        
    else:  # tipo_agrupamento == 'mes'
        # Nomes dos meses
        meses = {
            "01": "Jan", "02": "Fev", "03": "Mar", "04": "Abr", "05": "Mai", "06": "Jun",
            "07": "Jul", "08": "Ago", "09": "Set", "10": "Out", "11": "Nov", "12": "Dez"
        }
        
        # Determina quais meses incluir com base nas datas
        mes_inicio = int(data_inicio.split('-')[1])
        mes_fim = int(data_fim.split('-')[1])
        
        if hoje.year == int(data_inicio.split('-')[0]):
            meses_periodo = {f"{m:02d}": 0 for m in range(mes_inicio, mes_fim + 1)}
        else:
            # Se o ano inicial for diferente, inclui todos os meses
            meses_periodo = {f"{m:02d}": 0 for m in range(1, 13)}
        
        for periodo, total in resultados:
            meses_periodo[periodo] = total
        
        # Adiciona os dados no gráfico
        for mes, valor in meses_periodo.items():
            nomes_periodos.append(meses[mes])
            valores.append(valor)
        
        titulo = "Distribuição de gastos por mês"
    
    # Cria o gráfico com Plotly
    dados_plotly = [
        {
            'x': nomes_periodos,
            'y': valores,
            'type': 'bar',
            'marker': {
                'color': '#28a745'
            }
        }
    ]
    
    layout_plotly = {
        'margin': {'l': 40, 'r': 10, 't': 40, 'b': 40},
        'title': titulo,
        'showlegend': False,
        'height': 400,
        'xaxis': {
            'title': 'Período'
        },
        'yaxis': {
            'title': 'Valor (R$)'
        }
    }
    
    return jsonify({'data': dados_plotly, 'layout': layout_plotly})

# Rota para obter gráfico de fluxo de caixa (empresarial)
@api_bp.route('/grafico/fluxo_caixa')
@api_login_required
def get_grafico_fluxo_caixa():
    """API para obter dados do gráfico de fluxo de caixa empresarial"""
    usuario_id = session.get('usuario_id')
    
    # Verificar se o usuário tem plano familia ou empresarial
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    plano = usuario.get('plano', 'gratuito') if usuario else 'gratuito'
    planos_validos = ['familia', 'empresarial']
    
    if plano not in planos_validos:
        return jsonify({
            "error": "Recurso disponível apenas para planos Família ou Empresarial",
            "plano_atual": plano
        }), 403
    
    # Parâmetros de filtro
    periodo = request.args.get('periodo', 'mes')
    
    # Define o período
    hoje = datetime.now()
    
    if periodo == 'semana':
        data_inicio = (hoje - timedelta(days=7)).strftime("%Y-%m-%d")
        data_fim = hoje.strftime("%Y-%m-%d")
        tipo_agrupamento = 'dia'
    elif periodo == 'mes':
        data_inicio = f"{hoje.year}-{hoje.month:02d}-01"
        data_fim = hoje.strftime("%Y-%m-%d")
        tipo_agrupamento = 'dia'
    elif periodo == 'ano':
        data_inicio = f"{hoje.year}-01-01"
        data_fim = hoje.strftime("%Y-%m-%d")
        tipo_agrupamento = 'mes'
    else:
        data_inicio = f"{hoje.year}-01-01"
        data_fim = hoje.strftime("%Y-%m-%d")
        tipo_agrupamento = 'mes'
    
    # Consulta SQL para obter receitas no período
    conn = sqlite3.connect(Config.DATABASE)
    cursor = conn.cursor()
    
    if tipo_agrupamento == 'dia':
        query_receitas = """
        SELECT data, SUM(valor) as total
        FROM receitas
        WHERE usuario_id = ? AND tipo_perfil = 'empresarial' AND data BETWEEN ? AND ?
        GROUP BY data
        ORDER BY data
        """
        
        query_despesas = """
        SELECT data, SUM(valor) as total
        FROM despesas
        WHERE usuario_id = ? AND tipo_perfil = 'empresarial' AND data BETWEEN ? AND ?
        GROUP BY data
        ORDER BY data
        """
    else:  # tipo_agrupamento == 'mes'
        query_receitas = """
        SELECT strftime('%Y-%m', data) as mes, SUM(valor) as total
        FROM receitas
        WHERE usuario_id = ? AND tipo_perfil = 'empresarial' AND data BETWEEN ? AND ?
        GROUP BY mes
        ORDER BY mes
        """
        
        query_despesas = """
        SELECT strftime('%Y-%m', data) as mes, SUM(valor) as total
        FROM despesas
        WHERE usuario_id = ? AND tipo_perfil = 'empresarial' AND data BETWEEN ? AND ?
        GROUP BY mes
        ORDER BY mes
        """
    
    cursor.execute(query_receitas, [usuario_id, data_inicio, data_fim])
    receitas_dados = cursor.fetchall()
    
    cursor.execute(query_despesas, [usuario_id, data_inicio, data_fim])
    despesas_dados = cursor.fetchall()
    
    conn.close()
    
    # Prepara dados do gráfico
    if tipo_agrupamento == 'dia':
        # Cria dicionários para facilitar acesso
        receitas_dict = {r[0]: r[1] for r in receitas_dados}
        despesas_dict = {d[0]: d[1] for d in despesas_dados}
        
        # Gera lista de todas as datas no período
        datas = []
        data_atual = datetime.strptime(data_inicio, "%Y-%m-%d")
        data_final = datetime.strptime(data_fim, "%Y-%m-%d")
        
        while data_atual <= data_final:
            datas.append(data_atual.strftime("%Y-%m-%d"))
            data_atual += timedelta(days=1)
        
        # Prepara os dados formatados
        x = [datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m") for d in datas]
        y_receitas = [receitas_dict.get(d, 0) for d in datas]
        y_despesas = [despesas_dict.get(d, 0) for d in datas]
        y_saldo = [r - d for r, d in zip(y_receitas, y_despesas)]
    else:  # tipo_agrupamento == 'mes'
        # Cria dicionários para facilitar acesso
        receitas_dict = {r[0]: r[1] for r in receitas_dados}
        despesas_dict = {d[0]: d[1] for d in despesas_dados}
        
        # Gera lista de todos os meses no período
        meses = []
        data_atual = datetime.strptime(data_inicio, "%Y-%m-%d").replace(day=1)
        data_final = datetime.strptime(data_fim, "%Y-%m-%d").replace(day=1)
        
        while data_atual <= data_final:
            meses.append(data_atual.strftime("%Y-%m"))
            if data_atual.month == 12:
                data_atual = data_atual.replace(year=data_atual.year+1, month=1)
            else:
                data_atual = data_atual.replace(month=data_atual.month+1)
        
        # Prepara os dados formatados
        x = [datetime.strptime(m, "%Y-%m").strftime("%b/%Y") for m in meses]
        y_receitas = [receitas_dict.get(m, 0) for m in meses]
        y_despesas = [despesas_dict.get(m, 0) for m in meses]
        y_saldo = [r - d for r, d in zip(y_receitas, y_despesas)]
    
    # Cria o gráfico com Plotly
    dados_plotly = [
        {
            'x': x,
            'y': y_receitas,
            'type': 'bar',
            'name': 'Receitas',
            'marker': {'color': '#28a745'}
        },
        {
            'x': x,
            'y': y_despesas,
            'type': 'bar',
            'name': 'Despesas',
            'marker': {'color': '#e74c3c'}
        },
        {
            'x': x,
            'y': y_saldo,
            'type': 'scatter',
            'mode': 'lines+markers',
            'name': 'Saldo',
            'line': {'color': '#4a6cf7', 'width': 3},
            'marker': {'color': '#4a6cf7', 'size': 8}
        }
    ]
    
    layout_plotly = {
        'barmode': 'group',
        'margin': {'l': 40, 'r': 10, 't': 40, 'b': 40},
        'title': 'Fluxo de Caixa Empresarial',
        'showlegend': True,
        'height': 400,
        'xaxis': {
            'title': 'Período'
        },
        'yaxis': {
            'title': 'Valor (R$)'
        }
    }
    
    return jsonify({'data': dados_plotly, 'layout': layout_plotly})

# Rota para obter comparativo de gastos
@api_bp.route('/grafico/comparativo')
@api_login_required
def get_grafico_comparativo():
    """API para obter dados do gráfico comparativo entre períodos"""
    usuario_id = session.get('usuario_id')
    
    # Parâmetros de filtro
    periodo1 = request.args.get('periodo1', 'mes_atual')
    periodo2 = request.args.get('periodo2', 'mes_anterior')
    tipo_perfil = request.args.get('tipo_perfil')
    
    # Define os períodos
    hoje = datetime.now()
    
    # Período 1
    if periodo1 == 'mes_atual':
        data_inicio1 = f"{hoje.year}-{hoje.month:02d}-01"
        data_fim1 = hoje.strftime("%Y-%m-%d")
        titulo_periodo1 = "Mês Atual"
    elif periodo1 == 'mes_anterior':
        # Calcula o mês anterior
        if hoje.month == 1:
            mes_anterior = 12
            ano_anterior = hoje.year - 1
        else:
            mes_anterior = hoje.month - 1
            ano_anterior = hoje.year
        
        data_inicio1 = f"{ano_anterior}-{mes_anterior:02d}-01"
        
        # Último dia do mês anterior
        ultimo_dia = (datetime(hoje.year, hoje.month, 1) - timedelta(days=1)).day
        data_fim1 = f"{ano_anterior}-{mes_anterior:02d}-{ultimo_dia:02d}"
        
        titulo_periodo1 = "Mês Anterior"
    elif periodo1 == 'ano_atual':
        data_inicio1 = f"{hoje.year}-01-01"
        data_fim1 = hoje.strftime("%Y-%m-%d")
        titulo_periodo1 = "Ano Atual"
    elif periodo1 == 'ano_anterior':
        data_inicio1 = f"{hoje.year-1}-01-01"
        data_fim1 = f"{hoje.year-1}-12-31"
        titulo_periodo1 = "Ano Anterior"
    
    # Período 2
    if periodo2 == 'mes_atual':
        data_inicio2 = f"{hoje.year}-{hoje.month:02d}-01"
        data_fim2 = hoje.strftime("%Y-%m-%d")
        titulo_periodo2 = "Mês Atual"
    elif periodo2 == 'mes_anterior':
        # Calcula o mês anterior
        if hoje.month == 1:
            mes_anterior = 12
            ano_anterior = hoje.year - 1
        else:
            mes_anterior = hoje.month - 1
            ano_anterior = hoje.year
        
        data_inicio2 = f"{ano_anterior}-{mes_anterior:02d}-01"
        
        # Último dia do mês anterior
        ultimo_dia = (datetime(hoje.year, hoje.month, 1) - timedelta(days=1)).day
        data_fim2 = f"{ano_anterior}-{mes_anterior:02d}-{ultimo_dia:02d}"
        
        titulo_periodo2 = "Mês Anterior"
    elif periodo2 == 'ano_atual':
        data_inicio2 = f"{hoje.year}-01-01"
        data_fim2 = hoje.strftime("%Y-%m-%d")
        titulo_periodo2 = "Ano Atual"
    elif periodo2 == 'ano_anterior':
        data_inicio2 = f"{hoje.year-1}-01-01"
        data_fim2 = f"{hoje.year-1}-12-31"
        titulo_periodo2 = "Ano Anterior"
    
    # Busca as despesas por categoria para o período 1
    despesa_model = Despesa(Config.DATABASE)
    categorias1 = despesa_model.total_por_categoria(
        usuario_id, 
        data_inicio=data_inicio1, 
        data_fim=data_fim1,
        tipo_perfil=tipo_perfil
    )
    
    # Busca as despesas por categoria para o período 2
    categorias2 = despesa_model.total_por_categoria(
        usuario_id, 
        data_inicio=data_inicio2, 
        data_fim=data_fim2,
        tipo_perfil=tipo_perfil
    )
    
    # Converte para dicionários para facilitar o acesso
    categorias_dict1 = {item['categoria']: item['total'] for item in categorias1}
    categorias_dict2 = {item['categoria']: item['total'] for item in categorias2}
    
    # Obtém todas as categorias únicas
    todas_categorias = sorted(set(list(categorias_dict1.keys()) + list(categorias_dict2.keys())))
    
    # Prepara os dados para o gráfico
    categorias_nomes = []
    valores1 = []
    valores2 = []
    
    for categoria in todas_categorias:
        categorias_nomes.append(categoria.capitalize())
        valores1.append(categorias_dict1.get(categoria, 0))
        valores2.append(categorias_dict2.get(categoria, 0))
    
    # Cria o gráfico com Plotly
    dados_plotly = [
        {
            'x': categorias_nomes,
            'y': valores1,
            'type': 'bar',
            'name': titulo_periodo1
        },
        {
            'x': categorias_nomes,
            'y': valores2,
            'type': 'bar',
            'name': titulo_periodo2
        }
    ]
    
    layout_plotly = {
        'barmode': 'group',
        'margin': {'l': 40, 'r': 10, 't': 40, 'b': 40},
        'title': f'Comparativo de Despesas: {titulo_periodo1} vs {titulo_periodo2}',
        'showlegend': True,
        'height': 400,
        'xaxis': {
            'title': 'Categorias'
        },
        'yaxis': {
            'title': 'Valor (R$)'
        }
    }
    
    return jsonify({'data': dados_plotly, 'layout': layout_plotly})

def api_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return jsonify({"error": "Não autorizado"}), 401
        return f(*args, **kwargs)
    return decorated_function

# Rota para buscar dívidas
@api_bp.route('/dividas', methods=['GET'])
@api_login_required
def listar_dividas():
    """Lista todas as dívidas do usuário"""
    try:
        usuario_id = session.get('usuario_id')
        tipo_perfil = request.args.get('tipo_perfil', 'pessoal')
        status = request.args.get('status')
        tipo = request.args.get('tipo')
        
        divida_model = Divida(Config.DATABASE)
        dividas = divida_model.buscar(usuario_id, tipo_perfil=tipo_perfil, status=status, tipo=tipo)
        
        return jsonify(dividas), 200
        
    except Exception as e:
        print(f"Erro ao listar dívidas: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': 'Erro interno do servidor'}), 500

@api_bp.route('/dividas', methods=['POST'])
@api_login_required
def criar_divida():
    """Cria uma nova dívida"""
    try:
        usuario_id = session.get('usuario_id')
        dados = request.get_json()
        
        # Validações básicas
        if not dados.get('nome'):
            return jsonify({'error': 'Nome da dívida é obrigatório'}), 400
        
        if not dados.get('valor_total') or float(dados.get('valor_total', 0)) <= 0:
            return jsonify({'error': 'Valor total deve ser maior que zero'}), 400
        
        if not dados.get('data_inicio'):
            return jsonify({'error': 'Data de início é obrigatória'}), 400
        
        # Dados da dívida
        divida_data = {
            'usuario_id': usuario_id,
            'nome': dados.get('nome'),
            'valor_total': float(dados.get('valor_total', 0)),
            'valor_pago': float(dados.get('valor_pago', 0)),
            'data_inicio': dados.get('data_inicio'),
            'data_fim': dados.get('data_fim'),
            'taxa_juros': float(dados.get('taxa_juros', 0)) if dados.get('taxa_juros') else None,
            'parcelas_total': int(dados.get('parcelas_total', 1)) if dados.get('parcelas_total') else None,
            'parcelas_pagas': int(dados.get('parcelas_pagas', 0)),
            'credor': dados.get('credor'),
            'tipo_perfil': dados.get('tipo_perfil', 'pessoal'),
            'tipo': dados.get('tipo', 'outros')
        }
        
        divida_model = Divida(Config.DATABASE)
        
        # Cria a dívida com todos os dados
        divida_id = divida_model.criar(
            usuario_id=divida_data['usuario_id'],
            nome=divida_data['nome'],
            valor_total=divida_data['valor_total'],
            data_inicio=divida_data['data_inicio'],
            data_fim=divida_data['data_fim'],
            taxa_juros=divida_data['taxa_juros'],
            parcelas_total=divida_data['parcelas_total'],
            credor=divida_data['credor'],
            tipo_perfil=divida_data['tipo_perfil'],
            tipo=divida_data['tipo']
        )
        
        # Atualiza com os dados adicionais se necessário (valor_pago, parcelas_pagas)
        if divida_data['valor_pago'] > 0 or divida_data['parcelas_pagas'] > 0:
            divida_model.atualizar(
                divida_id,
                valor_pago=divida_data['valor_pago'],
                parcelas_pagas=divida_data['parcelas_pagas']
            )
        
        return jsonify({'id': divida_id, 'message': 'Dívida criada com sucesso'}), 201
        
    except Exception as e:
        print(f"Erro ao criar dívida: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e) or 'Erro interno do servidor'}), 500

@api_bp.route('/dividas/<int:divida_id>', methods=['GET'])
@api_login_required
def obter_divida(divida_id):
    """Obtém uma dívida específica"""
    try:
        usuario_id = session.get('usuario_id')
        
        divida_model = Divida(Config.DATABASE)
        divida = divida_model.buscar_por_id(divida_id)
        
        if not divida:
            return jsonify({'error': 'Dívida não encontrada'}), 404
        
        # Verifica se a dívida pertence ao usuário logado
        if divida['usuario_id'] != usuario_id:
            return jsonify({'error': 'Acesso negado'}), 403
        
        return jsonify(divida), 200
        
    except Exception as e:
        print(f"Erro ao obter dívida: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': 'Erro interno do servidor'}), 500

@api_bp.route('/dividas/<int:divida_id>', methods=['PUT'])
@api_login_required
def atualizar_divida(divida_id):
    """Atualiza uma dívida"""
    try:
        usuario_id = session.get('usuario_id')
        dados = request.get_json()
        
        divida_model = Divida(Config.DATABASE)
        divida = divida_model.buscar_por_id(divida_id)
        
        if not divida:
            return jsonify({'error': 'Dívida não encontrada'}), 404
        
        # Verifica se a dívida pertence ao usuário logado
        if divida['usuario_id'] != usuario_id:
            return jsonify({'error': 'Acesso negado'}), 403
        
        # Prepara os dados para atualização
        dados_atualizacao = {}
        
        # Lista de campos que podem ser atualizados
        campos_permitidos = [
            'nome', 'valor_total', 'valor_pago', 'data_inicio', 'data_fim',
            'taxa_juros', 'parcelas_total', 'parcelas_pagas', 'credor', 'tipo', 'status'
        ]
        
        for campo in campos_permitidos:
            if campo in dados:
                if campo in ['valor_total', 'valor_pago', 'taxa_juros']:
                    dados_atualizacao[campo] = float(dados[campo])
                elif campo in ['parcelas_total', 'parcelas_pagas']:
                    dados_atualizacao[campo] = int(dados[campo])
                else:
                    dados_atualizacao[campo] = dados[campo]
        
        # Atualiza status automaticamente se a dívida foi quitada
        if 'valor_pago' in dados_atualizacao and 'valor_total' in dados:
            valor_total = float(dados['valor_total'])
            if dados_atualizacao['valor_pago'] >= valor_total:
                dados_atualizacao['status'] = 'quitada'
            else:
                dados_atualizacao['status'] = 'em_dia'
        elif 'valor_pago' in dados_atualizacao:
            valor_total = divida['valor_total']
            if dados_atualizacao['valor_pago'] >= valor_total:
                dados_atualizacao['status'] = 'quitada'
            else:
                dados_atualizacao['status'] = 'em_dia'
        
        # Realiza a atualização
        divida_model.atualizar(divida_id, **dados_atualizacao)
        
        # Retorna a dívida atualizada
        divida_atualizada = divida_model.buscar_por_id(divida_id)
        return jsonify(divida_atualizada), 200
        
    except Exception as e:
        print(f"Erro ao atualizar dívida: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e) or 'Erro interno do servidor'}), 500

@api_bp.route('/dividas/<int:divida_id>', methods=['DELETE'])
@api_login_required
def excluir_divida(divida_id):
    """Exclui uma dívida"""
    try:
        usuario_id = session.get('usuario_id')
        
        divida_model = Divida(Config.DATABASE)
        divida = divida_model.buscar_por_id(divida_id)
        
        if not divida:
            return jsonify({'error': 'Dívida não encontrada'}), 404
        
        # Verifica se a dívida pertence ao usuário logado
        if divida['usuario_id'] != usuario_id:
            return jsonify({'error': 'Acesso negado'}), 403
        
        # Exclui a dívida
        excluida = divida_model.excluir(divida_id)
        
        if excluida:
            return jsonify({'message': 'Dívida excluída com sucesso'}), 200
        else:
            return jsonify({'error': 'Erro ao excluir dívida'}), 500
        
    except Exception as e:
        print(f"Erro ao excluir dívida: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e) or 'Erro interno do servidor'}), 500

@api_bp.route('/dividas/pagamento', methods=['POST'])
@api_login_required
def registrar_pagamento():
    """Registra um pagamento para uma dívida"""
    try:
        usuario_id = session.get('usuario_id')
        dados = request.get_json()
        
        divida_id = dados.get('divida_id')
        valor = float(dados.get('valor', 0))
        data = dados.get('data')
        observacao = dados.get('observacao')
        tipo_pagamento = dados.get('tipo', 'parcela')
        
        if not divida_id:
            return jsonify({'error': 'ID da dívida é obrigatório'}), 400
        
        if valor <= 0:
            return jsonify({'error': 'Valor deve ser maior que zero'}), 400
        
        divida_model = Divida(Config.DATABASE)
        divida = divida_model.buscar_por_id(divida_id)
        
        if not divida:
            return jsonify({'error': 'Dívida não encontrada'}), 404
        
        # Verifica se a dívida pertence ao usuário logado
        if divida['usuario_id'] != usuario_id:
            return jsonify({'error': 'Acesso negado'}), 403
        
        # Registra o pagamento
        pagamento_id = divida_model.registrar_pagamento(
            divida_id=divida_id,
            valor=valor,
            data=data,
            observacao=observacao,
            tipo=tipo_pagamento
        )
        
        # Obtém a dívida atualizada após o pagamento
        divida_atualizada = divida_model.buscar_por_id(divida_id)
        
        return jsonify({
            'id': pagamento_id,
            'message': 'Pagamento registrado com sucesso',
            'divida': divida_atualizada
        }), 201
        
    except Exception as e:
        print(f"Erro ao registrar pagamento: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e) or 'Erro interno do servidor'}), 500

@api_bp.route('/usuario/renda', methods=['GET'])
@api_login_required
def obter_renda_usuario():
    """Obtém a renda mensal do usuário para cálculo de comprometimento"""
    try:
        usuario_id = session.get('usuario_id')
        
        usuario_model = Usuario(Config.DATABASE)
        usuario = usuario_model.buscar_por_id(usuario_id)
        
        if not usuario:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        # Tenta obter a renda_mensal do usuário
        renda = usuario.get('renda_mensal', 0)
        
        return jsonify({
            'success': True,
            'renda': float(renda) if renda else 0
        }), 200
        
    except Exception as e:
        print(f"Erro ao obter renda do usuário: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e) or 'Erro interno do servidor'}), 500

