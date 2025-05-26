# rotas/relatorios.py
"""
MÓDULO DE RELATÓRIOS
====================
Gerencia relatórios financeiros avançados e gráficos:

ROTAS WEB:
- GET /relatorios/ - Dashboard de relatórios
- GET /relatorios/detalhado - Relatório detalhado
- GET /relatorios/comparativo - Comparação entre períodos

ROTAS API:
- GET /relatorios/api/resumo - Resumo financeiro (JSON)
- GET /relatorios/api/grafico/<tipo> - Dados para gráficos
- GET /relatorios/api/evolucao - Evolução temporal
- GET /relatorios/api/previsao - Análise preditiva (Premium+)

FUNCIONALIDADES:
- Gráficos interativos (Plotly)
- Análise comparativa
- Previsões financeiras
- Exportação de relatórios
- Dashboards personalizados
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash, session, jsonify, send_file
from database.models import Usuario, Despesa, Receita
from functools import wraps
from datetime import datetime, timedelta
import pandas as pd
import io
import json
from config import Config

# Blueprint principal do módulo
relatorios_bp = Blueprint('relatorios', __name__, url_prefix='/relatorios')

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

@relatorios_bp.route('/')
@login_required
@plano_required(['premium', 'familia', 'empresarial'])
def index():
    """Dashboard principal de relatórios"""
    usuario_id = session.get('usuario_id')
    
    # Busca dados do usuário
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    # Parâmetros da URL
    periodo = request.args.get('periodo', 'mes')
    tipo_perfil = request.args.get('tipo_perfil', 'pessoal')
    
    # Define período
    hoje = datetime.now()
    if periodo == 'dia':
        data_inicio = hoje.strftime("%Y-%m-%d")
        periodo_texto = "hoje"
    elif periodo == 'semana':
        data_inicio = (hoje - timedelta(days=7)).strftime("%Y-%m-%d")
        periodo_texto = "últimos 7 dias"
    elif periodo == 'mes':
        data_inicio = f"{hoje.year}-{hoje.month:02d}-01"
        periodo_texto = "este mês"
    elif periodo == 'ano':
        data_inicio = f"{hoje.year}-01-01"
        periodo_texto = "este ano"
    else:
        data_inicio = f"{hoje.year}-{hoje.month:02d}-01"
        periodo_texto = "este mês"
    
    data_fim = hoje.strftime("%Y-%m-%d")
    
    # Calcula resumo financeiro
    resumo = calcular_resumo_financeiro(usuario_id, data_inicio, data_fim, tipo_perfil)
    
    # Determina recursos disponíveis por plano
    plano = usuario.get('plano', 'gratuito')
    recursos_disponiveis = get_recursos_por_plano(plano)
    
    return render_template(
        'relatorios.html',
        app_name=Config.APP_NAME,
        usuario=usuario,
        resumo=resumo,
        periodo=periodo,
        periodo_texto=periodo_texto,
        tipo_perfil=tipo_perfil,
        recursos=recursos_disponiveis,
        plano=plano
    )

@relatorios_bp.route('/detalhado')
@login_required
@plano_required(['premium', 'familia', 'empresarial'])
def detalhado():
    """Relatório detalhado avançado"""
    usuario_id = session.get('usuario_id')
    
    # Busca dados do usuário
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    # Parâmetros
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    tipo_perfil = request.args.get('tipo_perfil', 'pessoal')
    
    # Define período padrão se não fornecido
    if not data_inicio or not data_fim:
        hoje = datetime.now()
        data_inicio = f"{hoje.year}-{hoje.month:02d}-01"
        data_fim = hoje.strftime("%Y-%m-%d")
    
    # Gera relatório detalhado
    relatorio = gerar_relatorio_detalhado(usuario_id, data_inicio, data_fim, tipo_perfil)
    
    return render_template(
        'relatorios.html',
        app_name=Config.APP_NAME,
        usuario=usuario,
        relatorio=relatorio,
        data_inicio=data_inicio,
        data_fim=data_fim,
        tipo_perfil=tipo_perfil
    )

@relatorios_bp.route('/comparativo')
@login_required
@plano_required(['premium', 'familia', 'empresarial'])
def comparativo():
    """Relatório comparativo entre períodos"""
    usuario_id = session.get('usuario_id')
    
    # Busca dados do usuário
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    # Parâmetros
    periodo1 = request.args.get('periodo1', 'mes_atual')
    periodo2 = request.args.get('periodo2', 'mes_anterior')
    tipo_perfil = request.args.get('tipo_perfil', 'pessoal')
    
    # Gera comparação
    comparacao = gerar_relatorio_comparativo(usuario_id, periodo1, periodo2, tipo_perfil)
    
    return render_template(
        'relatorios.html',
        app_name=Config.APP_NAME,
        usuario=usuario,
        comparacao=comparacao,
        periodo1=periodo1,
        periodo2=periodo2,
        tipo_perfil=tipo_perfil
    )

@relatorios_bp.route('/previsao')
@login_required
@plano_required(['familia', 'empresarial'])
def previsao():
    """Análise preditiva e previsões"""
    usuario_id = session.get('usuario_id')
    
    # Busca dados do usuário
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    # Parâmetros
    meses_historico = int(request.args.get('meses_historico', 6))
    meses_previsao = int(request.args.get('meses_previsao', 3))
    tipo_perfil = request.args.get('tipo_perfil', 'pessoal')
    
    # Gera previsão
    previsao = gerar_previsao_financeira(usuario_id, meses_historico, meses_previsao, tipo_perfil)
    
    return render_template(
        'relatorios.html',
        app_name=Config.APP_NAME,
        usuario=usuario,
        previsao=previsao,
        meses_historico=meses_historico,
        meses_previsao=meses_previsao,
        tipo_perfil=tipo_perfil
    )

# ==================== ROTAS API ====================

@relatorios_bp.route('/api/resumo')
@login_required
def api_resumo():
    """API para resumo financeiro"""
    usuario_id = session.get('usuario_id')
    
    # Parâmetros
    periodo = request.args.get('periodo', 'mes')
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
    
    # Calcula resumo
    resumo = calcular_resumo_financeiro(usuario_id, data_inicio, data_fim, tipo_perfil)
    
    return jsonify(resumo)

@relatorios_bp.route('/api/grafico/<tipo>')
@login_required
def api_grafico(tipo):
    """API para dados de gráficos"""
    usuario_id = session.get('usuario_id')
    
    # Parâmetros
    periodo = request.args.get('periodo', 'mes')
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
    
    # Gera dados do gráfico baseado no tipo
    if tipo == 'pizza_categorias':
        dados = gerar_grafico_pizza_categorias(usuario_id, data_inicio, data_fim, tipo_perfil)
    elif tipo == 'linha_tempo':
        dados = gerar_grafico_linha_tempo(usuario_id, data_inicio, data_fim, tipo_perfil)
    elif tipo == 'barras_comparativo':
        dados = gerar_grafico_barras_comparativo(usuario_id, data_inicio, data_fim, tipo_perfil)
    elif tipo == 'evolucao_saldo':
        dados = gerar_grafico_evolucao_saldo(usuario_id, data_inicio, data_fim, tipo_perfil)
    else:
        return jsonify({"error": "Tipo de gráfico não suportado"}), 400
    
    return jsonify(dados)

@relatorios_bp.route('/api/evolucao')
@login_required
def api_evolucao():
    """API para evolução temporal"""
    usuario_id = session.get('usuario_id')
    
    # Parâmetros
    meses = int(request.args.get('meses', 12))
    tipo_perfil = request.args.get('tipo_perfil', 'pessoal')
    
    # Gera dados de evolução
    evolucao = gerar_dados_evolucao(usuario_id, meses, tipo_perfil)
    
    return jsonify(evolucao)

@relatorios_bp.route('/api/previsao')
@login_required
@plano_required(['familia', 'empresarial'])
def api_previsao():
    """API para análise preditiva"""
    usuario_id = session.get('usuario_id')
    
    # Parâmetros
    meses_historico = int(request.args.get('meses_historico', 6))
    meses_previsao = int(request.args.get('meses_previsao', 3))
    tipo_perfil = request.args.get('tipo_perfil', 'pessoal')
    
    # Gera previsão
    previsao = gerar_previsao_financeira(usuario_id, meses_historico, meses_previsao, tipo_perfil)
    
    return jsonify(previsao)

@relatorios_bp.route('/api/exportar/<formato>')
@login_required
def api_exportar(formato):
    """API para exportar relatórios"""
    usuario_id = session.get('usuario_id')
    
    # Parâmetros
    periodo = request.args.get('periodo', 'mes')
    tipo_perfil = request.args.get('tipo_perfil', 'pessoal')
    tipo_relatorio = request.args.get('tipo', 'completo')
    
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
    
    try:
        if formato.lower() == 'csv':
            return exportar_csv(usuario_id, data_inicio, data_fim, tipo_perfil, tipo_relatorio)
        elif formato.lower() == 'excel':
            return exportar_excel(usuario_id, data_inicio, data_fim, tipo_perfil, tipo_relatorio)
        elif formato.lower() == 'pdf':
            return exportar_pdf(usuario_id, data_inicio, data_fim, tipo_perfil, tipo_relatorio)
        else:
            return jsonify({"error": "Formato não suportado"}), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== FUNÇÕES DE CÁLCULO ====================

def calcular_resumo_financeiro(usuario_id, data_inicio, data_fim, tipo_perfil):
    """Calcula resumo financeiro completo"""
    despesa_model = Despesa(Config.DATABASE)
    receita_model = Receita(Config.DATABASE)
    
    # Totais do período
    total_despesas = despesa_model.total_periodo(usuario_id, data_inicio, data_fim, tipo_perfil)
    total_receitas = receita_model.total_periodo(usuario_id, data_inicio, data_fim, tipo_perfil)
    
    # Saldo e economia
    saldo = total_receitas - total_despesas
    economia_percentual = (saldo / total_receitas * 100) if total_receitas > 0 else 0
    
    # Despesas por categoria
    despesas_por_categoria = despesa_model.total_por_categoria(usuario_id, data_inicio, data_fim, tipo_perfil)
    receitas_por_categoria = receita_model.total_por_categoria(usuario_id, data_inicio, data_fim, tipo_perfil)
    
    # Transações recentes
    ultimas_despesas = despesa_model.buscar(usuario_id, data_inicio, data_fim, tipo_perfil=tipo_perfil, limit=5)
    ultimas_receitas = receita_model.buscar(usuario_id, data_inicio, data_fim, tipo_perfil=tipo_perfil, limit=5)
    
    # Métricas avançadas
    ticket_medio_despesa = total_despesas / len(ultimas_despesas) if ultimas_despesas else 0
    ticket_medio_receita = total_receitas / len(ultimas_receitas) if ultimas_receitas else 0
    
    # Comparação com período anterior
    if data_inicio:
        periodo_anterior = calcular_periodo_anterior(data_inicio, data_fim)
        despesas_anterior = despesa_model.total_periodo(usuario_id, periodo_anterior['inicio'], periodo_anterior['fim'], tipo_perfil)
        receitas_anterior = receita_model.total_periodo(usuario_id, periodo_anterior['inicio'], periodo_anterior['fim'], tipo_perfil)
        
        variacao_despesas = ((total_despesas - despesas_anterior) / despesas_anterior * 100) if despesas_anterior > 0 else 0
        variacao_receitas = ((total_receitas - receitas_anterior) / receitas_anterior * 100) if receitas_anterior > 0 else 0
    else:
        variacao_despesas = 0
        variacao_receitas = 0
    
    return {
        'periodo': {
            'inicio': data_inicio,
            'fim': data_fim
        },
        'totais': {
            'despesas': round(total_despesas, 2),
            'receitas': round(total_receitas, 2),
            'saldo': round(saldo, 2),
            'economia_percentual': round(economia_percentual, 1)
        },
        'por_categoria': {
            'despesas': despesas_por_categoria,
            'receitas': receitas_por_categoria
        },
        'recentes': {
            'despesas': ultimas_despesas,
            'receitas': ultimas_receitas
        },
        'metricas': {
            'ticket_medio_despesa': round(ticket_medio_despesa, 2),
            'ticket_medio_receita': round(ticket_medio_receita, 2),
            'total_transacoes': len(ultimas_despesas) + len(ultimas_receitas)
        },
        'comparacao': {
            'variacao_despesas': round(variacao_despesas, 1),
            'variacao_receitas': round(variacao_receitas, 1)
        }
    }

def gerar_relatorio_detalhado(usuario_id, data_inicio, data_fim, tipo_perfil):
    """Gera relatório detalhado completo"""
    despesa_model = Despesa(Config.DATABASE)
    receita_model = Receita(Config.DATABASE)
    
    # Resumo básico
    resumo = calcular_resumo_financeiro(usuario_id, data_inicio, data_fim, tipo_perfil)
    
    # Análise temporal (dia a dia)
    despesas_diarias = despesa_model.total_por_dia(usuario_id, data_inicio, data_fim, tipo_perfil)
    receitas_diarias = receita_model.total_por_dia(usuario_id, data_inicio, data_fim, tipo_perfil)
    
    # Top despesas e receitas
    top_despesas = despesa_model.buscar(usuario_id, data_inicio, data_fim, tipo_perfil=tipo_perfil, order_by="valor DESC", limit=10)
    top_receitas = receita_model.buscar(usuario_id, data_inicio, data_fim, tipo_perfil=tipo_perfil, order_by="valor DESC", limit=10)
    
    # Análise de padrões
    padroes = analisar_padroes_gastos(usuario_id, data_inicio, data_fim, tipo_perfil)
    
    return {
        'resumo': resumo,
        'temporal': {
            'despesas_diarias': despesas_diarias,
            'receitas_diarias': receitas_diarias
        },
        'rankings': {
            'top_despesas': top_despesas,
            'top_receitas': top_receitas
        },
        'padroes': padroes
    }

def gerar_relatorio_comparativo(usuario_id, periodo1, periodo2, tipo_perfil):
    """Gera relatório comparativo entre dois períodos"""
    # Define períodos
    datas1 = definir_periodo(periodo1)
    datas2 = definir_periodo(periodo2)
    
    # Calcula resumos para cada período
    resumo1 = calcular_resumo_financeiro(usuario_id, datas1['inicio'], datas1['fim'], tipo_perfil)
    resumo2 = calcular_resumo_financeiro(usuario_id, datas2['inicio'], datas2['fim'], tipo_perfil)
    
    # Calcula variações
    variacao_despesas = calcular_variacao(resumo1['totais']['despesas'], resumo2['totais']['despesas'])
    variacao_receitas = calcular_variacao(resumo1['totais']['receitas'], resumo2['totais']['receitas'])
    variacao_saldo = calcular_variacao(resumo1['totais']['saldo'], resumo2['totais']['saldo'])
    
    # Comparação por categoria
    comparacao_categorias = comparar_categorias(resumo1['por_categoria'], resumo2['por_categoria'])
    
    return {
        'periodo1': {
            'nome': periodo1,
            'datas': datas1,
            'resumo': resumo1
        },
        'periodo2': {
            'nome': periodo2,
            'datas': datas2,
            'resumo': resumo2
        },
        'variacoes': {
            'despesas': variacao_despesas,
            'receitas': variacao_receitas,
            'saldo': variacao_saldo
        },
        'categorias': comparacao_categorias
    }

def gerar_previsao_financeira(usuario_id, meses_historico, meses_previsao, tipo_perfil):
    """Gera previsão financeira usando análise de tendências"""
    # Busca dados históricos
    hoje = datetime.now()
    data_inicio = (hoje - timedelta(days=meses_historico*30)).strftime("%Y-%m-%d")
    data_fim = hoje.strftime("%Y-%m-%d")
    
    despesa_model = Despesa(Config.DATABASE)
    receita_model = Receita(Config.DATABASE)
    
    # Dados mensais históricos
    despesas_mensais = despesa_model.total_por_mes(usuario_id, data_inicio, data_fim, tipo_perfil)
    receitas_mensais = receita_model.total_por_mes(usuario_id, data_inicio, data_fim, tipo_perfil)
    
    # Análise de tendência usando regressão linear simples
    previsao_despesas = calcular_tendencia_linear(despesas_mensais, meses_previsao)
    previsao_receitas = calcular_tendencia_linear(receitas_mensais, meses_previsao)
    
    # Cenários (otimista, realista, pessimista)
    cenarios = gerar_cenarios_previsao(previsao_despesas, previsao_receitas)
    
    # Recomendações baseadas na análise
    recomendacoes = gerar_recomendacoes_financeiras(despesas_mensais, receitas_mensais, previsao_despesas, previsao_receitas)
    
    return {
        'historico': {
            'despesas_mensais': despesas_mensais,
            'receitas_mensais': receitas_mensais,
            'periodo_analise': f"{meses_historico} meses"
        },
        'previsao': {
            'despesas': previsao_despesas,
            'receitas': previsao_receitas,
            'periodo_previsao': f"{meses_previsao} meses"
        },
        'cenarios': cenarios,
        'recomendacoes': recomendacoes
    }

# ==================== FUNÇÕES DE GRÁFICOS ====================

def gerar_grafico_pizza_categorias(usuario_id, data_inicio, data_fim, tipo_perfil):
    """Gera dados para gráfico de pizza por categorias"""
    despesa_model = Despesa(Config.DATABASE)
    categorias = despesa_model.total_por_categoria(usuario_id, data_inicio, data_fim, tipo_perfil)
    
    if not categorias:
        return {"data": [], "layout": {}}
    
    # Cores para categorias
    cores = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#F39C12', '#95A5A6']
    
    dados = {
        "data": [{
            "values": [cat['total'] for cat in categorias],
            "labels": [cat['categoria'].capitalize() for cat in categorias],
            "type": "pie",
            "hole": 0.4,
            "textinfo": "label+percent",
            "textposition": "outside",
            "marker": {"colors": cores[:len(categorias)]}
        }],
        "layout": {
            "title": "Despesas por Categoria",
            "showlegend": False,
            "height": 400
        }
    }
    
    return dados

def gerar_grafico_linha_tempo(usuario_id, data_inicio, data_fim, tipo_perfil):
    """Gera dados para gráfico de linha temporal"""
    despesa_model = Despesa(Config.DATABASE)
    receita_model = Receita(Config.DATABASE)
    
    despesas_diarias = despesa_model.total_por_dia(usuario_id, data_inicio, data_fim, tipo_perfil)
    receitas_diarias = receita_model.total_por_dia(usuario_id, data_inicio, data_fim, tipo_perfil)
    
    # Converte para dictionários para facilitar acesso
    despesas_dict = {item['data']: item['total'] for item in despesas_diarias}
    receitas_dict = {item['data']: item['total'] for item in receitas_diarias}
    
    # Gera range de datas
    inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
    fim = datetime.strptime(data_fim, "%Y-%m-%d")
    
    datas = []
    valores_despesas = []
    valores_receitas = []
    
    data_atual = inicio
    while data_atual <= fim:
        data_str = data_atual.strftime("%Y-%m-%d")
        datas.append(data_str)
        valores_despesas.append(despesas_dict.get(data_str, 0))
        valores_receitas.append(receitas_dict.get(data_str, 0))
        data_atual += timedelta(days=1)
    
    dados = {
        "data": [
            {
                "x": datas,
                "y": valores_despesas,
                "type": "scatter",
                "mode": "lines+markers",
                "name": "Despesas",
                "line": {"color": "#e74c3c"}
            },
            {
                "x": datas,
                "y": valores_receitas,
                "type": "scatter",
                "mode": "lines+markers",
                "name": "Receitas",
                "line": {"color": "#27ae60"}
            }
        ],
        "layout": {
            "title": "Evolução Temporal",
            "xaxis": {"title": "Data"},
            "yaxis": {"title": "Valor (R$)"},
            "height": 400
        }
    }
    
    return dados

def gerar_grafico_evolucao_saldo(usuario_id, data_inicio, data_fim, tipo_perfil):
    """Gera dados para gráfico de evolução do saldo"""
    despesa_model = Despesa(Config.DATABASE)
    receita_model = Receita(Config.DATABASE)
    
    despesas_diarias = despesa_model.total_por_dia(usuario_id, data_inicio, data_fim, tipo_perfil)
    receitas_diarias = receita_model.total_por_dia(usuario_id, data_inicio, data_fim, tipo_perfil)
    
    # Calcula saldo acumulado
    saldo_acumulado = 0
    datas = []
    saldos = []
    
    # Converte para dicionários
    despesas_dict = {item['data']: item['total'] for item in despesas_diarias}
    receitas_dict = {item['data']: item['total'] for item in receitas_diarias}
    
    # Gera range de datas
    inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
    fim = datetime.strptime(data_fim, "%Y-%m-%d")
    
    data_atual = inicio
    while data_atual <= fim:
        data_str = data_atual.strftime("%Y-%m-%d")
        
        receita_dia = receitas_dict.get(data_str, 0)
        despesa_dia = despesas_dict.get(data_str, 0)
        saldo_dia = receita_dia - despesa_dia
        saldo_acumulado += saldo_dia
        
        datas.append(data_str)
        saldos.append(saldo_acumulado)
        data_atual += timedelta(days=1)
    
    dados = {
        "data": [{
            "x": datas,
            "y": saldos,
            "type": "scatter",
            "mode": "lines+markers",
            "name": "Saldo Acumulado",
            "line": {"color": "#3498db", "width": 3},
            "fill": "tonexty"
        }],
        "layout": {
            "title": "Evolução do Saldo",
            "xaxis": {"title": "Data"},
            "yaxis": {"title": "Saldo (R$)"},
            "height": 400
        }
    }
    
    return dados

# ==================== FUNÇÕES AUXILIARES ====================

def get_recursos_por_plano(plano):
    """Retorna recursos disponíveis por plano"""
    recursos = {
        'gratuito': {
            'graficos_basicos': True,
            'exportacao_csv': False,
            'exportacao_excel': False,
            'exportacao_pdf': False,
            'previsoes': False,
            'analise_avancada': False
        },
        'premium': {
            'graficos_basicos': True,
            'graficos_avancados': True,
            'exportacao_csv': True,
            'exportacao_excel': False,
            'exportacao_pdf': False,
            'previsoes': False,
            'analise_avancada': True
        },
        'familia': {
            'graficos_basicos': True,
            'graficos_avancados': True,
            'exportacao_csv': True,
            'exportacao_excel': True,
            'exportacao_pdf': True,
            'previsoes': True,
            'analise_avancada': True,
            'comparativos': True
        },
        'empresarial': {
            'graficos_basicos': True,
            'graficos_avancados': True,
            'exportacao_csv': True,
            'exportacao_excel': True,
            'exportacao_pdf': True,
            'previsoes': True,
            'analise_avancada': True,
            'comparativos': True,
            'dashboards_personalizados': True,
            'api_relatorios': True
        }
    }
    
    return recursos.get(plano, recursos['gratuito'])

def calcular_periodo_anterior(data_inicio, data_fim):
    """Calcula período anterior equivalente"""
    inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
    fim = datetime.strptime(data_fim, "%Y-%m-%d")
    
    diferenca = fim - inicio
    
    inicio_anterior = inicio - diferenca - timedelta(days=1)
    fim_anterior = inicio - timedelta(days=1)
    
    return {
        'inicio': inicio_anterior.strftime("%Y-%m-%d"),
        'fim': fim_anterior.strftime("%Y-%m-%d")
    }

def calcular_variacao(valor_atual, valor_anterior):
    """Calcula variação percentual"""
    if valor_anterior == 0:
        return 0 if valor_atual == 0 else 100
    
    return round(((valor_atual - valor_anterior) / valor_anterior) * 100, 1)

def definir_periodo(periodo_nome):
    """Define datas baseado no nome do período"""
    hoje = datetime.now()
    
    if periodo_nome == 'mes_atual':
        return {
            'inicio': f"{hoje.year}-{hoje.month:02d}-01",
            'fim': hoje.strftime("%Y-%m-%d")
        }
    elif periodo_nome == 'mes_anterior':
        if hoje.month == 1:
            mes_anterior = 12
            ano_anterior = hoje.year - 1
        else:
            mes_anterior = hoje.month - 1
            ano_anterior = hoje.year
        
        # Último dia do mês anterior
        ultimo_dia = (datetime(hoje.year, hoje.month, 1) - timedelta(days=1)).day
        
        return {
            'inicio': f"{ano_anterior}-{mes_anterior:02d}-01",
            'fim': f"{ano_anterior}-{mes_anterior:02d}-{ultimo_dia:02d}"
        }
    elif periodo_nome == 'ano_atual':
        return {
            'inicio': f"{hoje.year}-01-01",
            'fim': hoje.strftime("%Y-%m-%d")
        }
    elif periodo_nome == 'ano_anterior':
        return {
            'inicio': f"{hoje.year-1}-01-01",
            'fim': f"{hoje.year-1}-12-31"
        }
    
    # Padrão: mês atual
    return {
        'inicio': f"{hoje.year}-{hoje.month:02d}-01",
        'fim': hoje.strftime("%Y-%m-%d")
    }

def exportar_csv(usuario_id, data_inicio, data_fim, tipo_perfil, tipo_relatorio):
    """Exporta relatório em CSV"""
    if tipo_relatorio == 'despesas':
        despesa_model = Despesa(Config.DATABASE)
        dados = despesa_model.buscar(usuario_id, data_inicio, data_fim, tipo_perfil=tipo_perfil)
    elif tipo_relatorio == 'receitas':
        receita_model = Receita(Config.DATABASE)
        dados = receita_model.buscar(usuario_id, data_inicio, data_fim, tipo_perfil=tipo_perfil)
    else:
        # Relatório completo
        resumo = calcular_resumo_financeiro(usuario_id, data_inicio, data_fim, tipo_perfil)
        dados = []
        
        # Adiciona despesas
        despesa_model = Despesa(Config.DATABASE)
        despesas = despesa_model.buscar(usuario_id, data_inicio, data_fim, tipo_perfil=tipo_perfil)
        for d in despesas:
            d['tipo'] = 'Despesa'
            dados.append(d)
        
        # Adiciona receitas
        receita_model = Receita(Config.DATABASE)
        receitas = receita_model.buscar(usuario_id, data_inicio, data_fim, tipo_perfil=tipo_perfil)
        for r in receitas:
            r['tipo'] = 'Receita'
            dados.append(r)
    
    if not dados:
        return jsonify({"error": "Não há dados para exportar"}), 404
    
    # Converte para DataFrame
    df = pd.DataFrame(dados)
    
    # Cria CSV
    csv_data = df.to_csv(index=False)
    
    return send_file(
        io.BytesIO(csv_data.encode()),
        mimetype='text/csv',
        download_name=f'relatorio_{tipo_relatorio}_{data_inicio}_{data_fim}.csv',
        as_attachment=True
    )

def exportar_excel(usuario_id, data_inicio, data_fim, tipo_perfil, tipo_relatorio):
    """Exporta relatório em Excel"""
    # Busca dados
    despesa_model = Despesa(Config.DATABASE)
    receita_model = Receita(Config.DATABASE)
    
    despesas = despesa_model.buscar(usuario_id, data_inicio, data_fim, tipo_perfil=tipo_perfil)
    receitas = receita_model.buscar(usuario_id, data_inicio, data_fim, tipo_perfil=tipo_perfil)
    
    # Cria Excel com múltiplas abas
    excel_buffer = io.BytesIO()
    
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        # Aba Resumo
        resumo = calcular_resumo_financeiro(usuario_id, data_inicio, data_fim, tipo_perfil)
        resumo_df = pd.DataFrame([resumo['totais']])
        resumo_df.to_excel(writer, sheet_name='Resumo', index=False)
        
        # Aba Despesas
        if despesas:
            despesas_df = pd.DataFrame(despesas)
            despesas_df.to_excel(writer, sheet_name='Despesas', index=False)
        
        # Aba Receitas
        if receitas:
            receitas_df = pd.DataFrame(receitas)
            receitas_df.to_excel(writer, sheet_name='Receitas', index=False)
    
    excel_buffer.seek(0)
    
    return send_file(
        excel_buffer,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        download_name=f'relatorio_{tipo_relatorio}_{data_inicio}_{data_fim}.xlsx',
        as_attachment=True
    )

def exportar_pdf(usuario_id, data_inicio, data_fim, tipo_perfil, tipo_relatorio):
    """Exporta relatório em PDF"""
    # Esta função requeria uma biblioteca de PDF como ReportLab
    # Por simplicidade, retornamos um erro indicando que não está implementado
    return jsonify({"error": "Exportação PDF não implementada ainda"}), 501

def gerar_grafico_barras_comparativo(usuario_id, data_inicio, data_fim, tipo_perfil):
    """Gera dados para gráfico de barras comparativo"""
    despesa_model = Despesa(Config.DATABASE)
    receita_model = Receita(Config.DATABASE)
    
    # Dados do período atual
    despesas_categorias = despesa_model.total_por_categoria(usuario_id, data_inicio, data_fim, tipo_perfil)
    receitas_categorias = receita_model.total_por_categoria(usuario_id, data_inicio, data_fim, tipo_perfil)
    
    # Organiza dados para gráfico
    categorias = list(set([d['categoria'] for d in despesas_categorias] + [r['categoria'] for r in receitas_categorias]))
    
    despesas_dict = {item['categoria']: item['total'] for item in despesas_categorias}
    receitas_dict = {item['categoria']: item['total'] for item in receitas_categorias}
    
    dados = {
        "data": [
            {
                "x": categorias,
                "y": [despesas_dict.get(cat, 0) for cat in categorias],
                "name": "Despesas",
                "type": "bar",
                "marker": {"color": "#e74c3c"}
            },
            {
                "x": categorias,
                "y": [receitas_dict.get(cat, 0) for cat in categorias],
                "name": "Receitas",
                "type": "bar",
                "marker": {"color": "#27ae60"}
            }
        ],
        "layout": {
            "title": "Comparativo por Categoria",
            "xaxis": {"title": "Categorias"},
            "yaxis": {"title": "Valor (R$)"},
            "barmode": "group",
            "height": 400
        }
    }
    
    return dados

def gerar_dados_evolucao(usuario_id, meses, tipo_perfil):
    """Gera dados de evolução temporal para API"""
    hoje = datetime.now()
    data_inicio = (hoje - timedelta(days=meses*30)).strftime("%Y-%m-%d")
    data_fim = hoje.strftime("%Y-%m-%d")
    
    despesa_model = Despesa(Config.DATABASE)
    receita_model = Receita(Config.DATABASE)
    
    # Dados mensais
    despesas_mensais = despesa_model.total_por_mes(usuario_id, data_inicio, data_fim, tipo_perfil)
    receitas_mensais = receita_model.total_por_mes(usuario_id, data_inicio, data_fim, tipo_perfil)
    
    return {
        'despesas_mensais': despesas_mensais,
        'receitas_mensais': receitas_mensais,
        'periodo': f"{meses} meses"
    }

def analisar_padroes_gastos(usuario_id, data_inicio, data_fim, tipo_perfil):
    """Analisa padrões de gastos"""
    despesa_model = Despesa(Config.DATABASE)
    
    # Padrões por dia da semana
    gastos_por_dia_semana = despesa_model.total_por_dia_semana(usuario_id, data_inicio, data_fim, tipo_perfil)
    
    # Horários de maior gasto
    gastos_por_hora = despesa_model.total_por_hora(usuario_id, data_inicio, data_fim, tipo_perfil)
    
    # Categoria mais frequente
    categoria_mais_frequente = despesa_model.categoria_mais_frequente(usuario_id, data_inicio, data_fim, tipo_perfil)
    
    return {
        'dia_semana': gastos_por_dia_semana,
        'horarios': gastos_por_hora,
        'categoria_frequente': categoria_mais_frequente
    }

def comparar_categorias(categorias1, categorias2):
    """Compara categorias entre dois períodos"""
    # Organiza dados
    despesas1 = {item['categoria']: item['total'] for item in categorias1.get('despesas', [])}
    despesas2 = {item['categoria']: item['total'] for item in categorias2.get('despesas', [])}
    
    receitas1 = {item['categoria']: item['total'] for item in categorias1.get('receitas', [])}
    receitas2 = {item['categoria']: item['total'] for item in categorias2.get('receitas', [])}
    
    # Todas as categorias
    todas_categorias = set(list(despesas1.keys()) + list(despesas2.keys()) + 
                          list(receitas1.keys()) + list(receitas2.keys()))
    
    comparacao = []
    for categoria in todas_categorias:
        desp1 = despesas1.get(categoria, 0)
        desp2 = despesas2.get(categoria, 0)
        rec1 = receitas1.get(categoria, 0)
        rec2 = receitas2.get(categoria, 0)
        
        comparacao.append({
            'categoria': categoria,
            'despesas': {
                'periodo1': desp1,
                'periodo2': desp2,
                'variacao': calcular_variacao(desp1, desp2)
            },
            'receitas': {
                'periodo1': rec1,
                'periodo2': rec2,
                'variacao': calcular_variacao(rec1, rec2)
            }
        })
    
    return comparacao

def calcular_tendencia_linear(dados_historicos, meses_previsao):
    """Calcula tendência linear simples para previsão"""
    if not dados_historicos or len(dados_historicos) < 2:
        return []
    
    # Simplificado: usa média dos últimos meses como base
    valores = [item['total'] for item in dados_historicos]
    media = sum(valores) / len(valores)
    
    # Calcula tendência (crescimento médio)
    if len(valores) >= 2:
        tendencia = (valores[-1] - valores[0]) / len(valores)
    else:
        tendencia = 0
    
    # Gera previsões
    previsoes = []
    for i in range(meses_previsao):
        valor_previsto = media + (tendencia * i)
        previsoes.append({
            'mes': i + 1,
            'valor_previsto': max(0, valor_previsto)  # Não permite valores negativos
        })
    
    return previsoes

def gerar_cenarios_previsao(previsao_despesas, previsao_receitas):
    """Gera cenários otimista, realista e pessimista"""
    cenarios = {
        'otimista': {
            'descricao': 'Redução de 10% nas despesas e aumento de 5% nas receitas',
            'despesas': [{'mes': p['mes'], 'valor': p['valor_previsto'] * 0.9} for p in previsao_despesas],
            'receitas': [{'mes': p['mes'], 'valor': p['valor_previsto'] * 1.05} for p in previsao_receitas]
        },
        'realista': {
            'descricao': 'Manutenção das tendências atuais',
            'despesas': previsao_despesas,
            'receitas': previsao_receitas
        },
        'pessimista': {
            'descricao': 'Aumento de 10% nas despesas e redução de 5% nas receitas',
            'despesas': [{'mes': p['mes'], 'valor': p['valor_previsto'] * 1.1} for p in previsao_despesas],
            'receitas': [{'mes': p['mes'], 'valor': p['valor_previsto'] * 0.95} for p in previsao_receitas]
        }
    }
    
    return cenarios

def gerar_recomendacoes_financeiras(despesas_historicas, receitas_historicas, previsao_despesas, previsao_receitas):
    """Gera recomendações baseadas na análise"""
    recomendacoes = []
    
    # Análise básica
    if despesas_historicas and receitas_historicas:
        total_despesas = sum([item['total'] for item in despesas_historicas])
        total_receitas = sum([item['total'] for item in receitas_historicas])
        
        if total_despesas > total_receitas * 0.8:
            recomendacoes.append({
                'tipo': 'alerta',
                'titulo': 'Gastos Elevados',
                'descricao': 'Suas despesas representam mais de 80% das receitas. Considere reduzir gastos desnecessários.'
            })
        
        if total_despesas < total_receitas * 0.5:
            recomendacoes.append({
                'tipo': 'positivo',
                'titulo': 'Boa Economia',
                'descricao': 'Parabéns! Você está economizando mais de 50% das suas receitas.'
            })
    
    # Adiciona recomendações padrão
    recomendacoes.extend([
        {
            'tipo': 'dica',
            'titulo': 'Revise Gastos Mensalmente',
            'descricao': 'Faça uma revisão mensal dos seus gastos para identificar oportunidades de economia.'
        },
        {
            'tipo': 'meta',
            'titulo': 'Defina Metas Financeiras',
            'descricao': 'Estabeleça metas claras de economia e investimento para o próximo período.'
        }
    ])
    
    return recomendacoes