from flask import Blueprint, request, jsonify, session
from datetime import datetime, timedelta
from database.models import Usuario, Despesa, Receita
from config import Config
import pandas as pd
import json
import io

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
    """API para adicionar uma despesa"""
    usuario_id = session.get('usuario_id')
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
            num_parcelas=num_parcelas
        )
        
        return jsonify({"success": True, "id": despesa_id}), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400

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
    """API para adicionar uma receita"""
    usuario_id = session.get('usuario_id')
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
        
        # Cria a receita
        receita_model = Receita(Config.DATABASE)
        receita_id = receita_model.criar(
            usuario_id=usuario_id,
            valor=valor,
            categoria=categoria,
            descricao=descricao,
            data=data,
            recorrente=recorrente,
            periodicidade=periodicidade
        )
        
        return jsonify({"success": True, "id": receita_id}), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400

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