from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify, flash
from database.models import Usuario, Lembrete, Orcamento, MetaFinanceira, Divida, Despesa, Receita
from functools import wraps
from config import Config
from datetime import datetime, timedelta
import sqlite3

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@dashboard_bp.route('/')
@login_required
def index():
    """Dashboard principal"""
    usuario_id = session.get('usuario_id')
    
    # Busca dados do usuário
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    if not usuario:
        flash('Usuário não encontrado.', 'error')
        return redirect(url_for('auth.logout'))
    
    # Busca lembretes próximos (não concluídos)
    lembrete_model = Lembrete(Config.DATABASE)
    lembretes = lembrete_model.buscar(
        usuario_id=usuario_id,
        concluido=0
    )
    # Ordena por data e pega os 3 mais próximos
    lembretes = sorted(lembretes, key=lambda x: x['data'])[:3]
    
    # Busca orçamentos ativos
    orcamento_model = Orcamento(Config.DATABASE)
    orcamentos = orcamento_model.buscar(
        usuario_id=usuario_id,
        tipo_perfil='pessoal'
    )
    
    # Adiciona gasto atual para cada orçamento
    for orcamento in orcamentos:
        try:
            orcamento['gasto_atual'] = orcamento_model.calcular_gasto_atual(orcamento['id'])
            # Calcula percentual usado
            if orcamento['valor_limite'] > 0:
                orcamento['percentual_usado'] = (orcamento['gasto_atual'] / orcamento['valor_limite']) * 100
            else:
                orcamento['percentual_usado'] = 0
        except:
            orcamento['gasto_atual'] = 0
            orcamento['percentual_usado'] = 0
    
    # Busca metas financeiras ativas
    meta_model = MetaFinanceira(Config.DATABASE)
    metas = meta_model.buscar(
        usuario_id=usuario_id,
        tipo_perfil='pessoal',
        concluida=0  # Apenas metas não concluídas
    )
    
    # Calcula percentual de progresso para cada meta
    for meta in metas:
        if meta['valor_alvo'] > 0:
            meta['percentual_progresso'] = min(100, (meta['valor_atual'] / meta['valor_alvo']) * 100)
        else:
            meta['percentual_progresso'] = 0
    
    # Busca dívidas ativas
    divida_model = Divida(Config.DATABASE)
    dividas = divida_model.buscar(
        usuario_id=usuario_id,
        tipo_perfil='pessoal'
    )
    
    # Calcula informações adicionais para cada dívida
    for divida in dividas:
        # Percentual pago
        if divida['valor_total'] > 0:
            divida['percentual_pago'] = (divida['valor_pago'] / divida['valor_total']) * 100
        else:
            divida['percentual_pago'] = 0
        
        # Valor restante
        divida['valor_restante'] = divida['valor_total'] - divida['valor_pago']
        
        # Status visual baseado no percentual pago
        if divida['percentual_pago'] >= 100:
            divida['status_visual'] = 'success'
        elif divida['percentual_pago'] >= 50:
            divida['status_visual'] = 'warning'
        else:
            divida['status_visual'] = 'danger'
    
    # Dados financeiros resumidos para o mês atual
    hoje = datetime.now()
    inicio_mes = f"{hoje.year}-{hoje.month:02d}-01"
    fim_mes = hoje.strftime("%Y-%m-%d")
    
    # Total de despesas do mês
    despesa_model = Despesa(Config.DATABASE)
    total_despesas_mes = despesa_model.total_periodo(
        usuario_id=usuario_id,
        data_inicio=inicio_mes,
        data_fim=fim_mes,
        tipo_perfil='pessoal'
    )
    
    # Total de receitas do mês
    receita_model = Receita(Config.DATABASE)
    total_receitas_mes = receita_model.total_periodo(
        usuario_id=usuario_id,
        data_inicio=inicio_mes,
        data_fim=fim_mes,
        tipo_perfil='pessoal'
    )
    
    # Saldo do mês
    saldo_mes = total_receitas_mes - total_despesas_mes
    
    # Últimas transações (5 mais recentes)
    ultimas_despesas = despesa_model.buscar(
        usuario_id=usuario_id,
        limit=3,
        tipo_perfil='pessoal'
    )
    
    ultimas_receitas = receita_model.buscar(
        usuario_id=usuario_id,
        limit=2,
        tipo_perfil='pessoal'
    )
    
    # Determina funcionalidades por plano
    plano = usuario.get('plano', 'gratuito')
    pode_acesso_empresarial = plano in ['familia', 'empresarial']
    
    # Estatísticas rápidas
    estatisticas = {
        'total_despesas_mes': total_despesas_mes,
        'total_receitas_mes': total_receitas_mes,
        'saldo_mes': saldo_mes,
        'num_lembretes_ativos': len([l for l in lembretes if l['concluido'] == 0]),
        'num_orcamentos': len(orcamentos),
        'num_metas': len(metas),
        'num_dividas': len([d for d in dividas if d['status'] != 'quitada']),
        'economia_percentual': (saldo_mes / total_receitas_mes * 100) if total_receitas_mes > 0 else 0
    }
    
    return render_template(
        'dashboard.html',
        app_name=Config.APP_NAME,
        usuario=usuario,
        lembretes=lembretes,
        orcamentos=orcamentos,
        metas=metas,
        dividas=dividas,
        plano=plano,
        pode_acesso_empresarial=pode_acesso_empresarial,
        estatisticas=estatisticas,
        ultimas_despesas=ultimas_despesas,
        ultimas_receitas=ultimas_receitas
    )

@dashboard_bp.route('/api/resumo')
@login_required
def api_resumo():
    """API para obter dados de resumo do dashboard"""
    usuario_id = session.get('usuario_id')
    periodo = request.args.get('periodo', 'mes')  # dia, semana, mes, ano
    
    # Define período
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
    else:
        data_inicio = f"{hoje.year}-{hoje.month:02d}-01"
        data_fim = hoje.strftime("%Y-%m-%d")
    
    try:
        despesa_model = Despesa(Config.DATABASE)
        receita_model = Receita(Config.DATABASE)
        
        # Totais do período
        total_despesas = despesa_model.total_periodo(
            usuario_id=usuario_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            tipo_perfil='pessoal'
        )
        
        total_receitas = receita_model.total_periodo(
            usuario_id=usuario_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            tipo_perfil='pessoal'
        )
        
        # Despesas por categoria
        despesas_categoria = despesa_model.total_por_categoria(
            usuario_id=usuario_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            tipo_perfil='pessoal'
        )
        
        # Transações recentes
        despesas_recentes = despesa_model.buscar(
            usuario_id=usuario_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            limit=5
        )
        
        saldo = total_receitas - total_despesas
        
        return jsonify({
            'success': True,
            'periodo': periodo,
            'total_despesas': round(total_despesas, 2),
            'total_receitas': round(total_receitas, 2),
            'saldo': round(saldo, 2),
            'despesas_categoria': despesas_categoria,
            'despesas_recentes': despesas_recentes[:5],
            'economia_percentual': round((saldo / total_receitas * 100) if total_receitas > 0 else 0, 1)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dashboard_bp.route('/api/graficos/despesas_categoria')
@login_required
def api_grafico_despesas_categoria():
    """API para dados do gráfico de despesas por categoria"""
    usuario_id = session.get('usuario_id')
    periodo = request.args.get('periodo', 'mes')
    
    hoje = datetime.now()
    
    if periodo == 'mes':
        data_inicio = f"{hoje.year}-{hoje.month:02d}-01"
    elif periodo == 'ano':
        data_inicio = f"{hoje.year}-01-01"
    else:
        data_inicio = f"{hoje.year}-{hoje.month:02d}-01"
    
    data_fim = hoje.strftime("%Y-%m-%d")
    
    try:
        despesa_model = Despesa(Config.DATABASE)
        categorias = despesa_model.total_por_categoria(
            usuario_id=usuario_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            tipo_perfil='pessoal'
        )
        
        # Formata para o gráfico
        labels = [cat['categoria'].capitalize() for cat in categorias]
        values = [cat['total'] for cat in categorias]
        
        return jsonify({
            'success': True,
            'labels': labels,
            'values': values,
            'total': sum(values)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dashboard_bp.route('/api/graficos/evolucao_saldo')
@login_required
def api_grafico_evolucao_saldo():
    """API para dados do gráfico de evolução do saldo"""
    usuario_id = session.get('usuario_id')
    periodo = request.args.get('periodo', 'mes')
    
    hoje = datetime.now()
    
    if periodo == 'mes':
        dias = 30
        data_inicio = (hoje - timedelta(days=dias)).strftime("%Y-%m-%d")
    elif periodo == 'semana':
        dias = 7
        data_inicio = (hoje - timedelta(days=dias)).strftime("%Y-%m-%d")
    else:
        dias = 30
        data_inicio = (hoje - timedelta(days=dias)).strftime("%Y-%m-%d")
    
    data_fim = hoje.strftime("%Y-%m-%d")
    
    try:
        despesa_model = Despesa(Config.DATABASE)
        receita_model = Receita(Config.DATABASE)
        
        # Busca transações por dia
        despesas_dia = despesa_model.total_por_dia(
            usuario_id=usuario_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            tipo_perfil='pessoal'
        )
        
        receitas_dia = receita_model.total_por_dia(
            usuario_id=usuario_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            tipo_perfil='pessoal'
        )
        
        # Converte para dicionários
        despesas_dict = {d['data']: d['total'] for d in despesas_dia}
        receitas_dict = {r['data']: r['total'] for r in receitas_dia}
        
        # Gera série temporal
        datas = []
        saldos = []
        saldo_acumulado = 0
        
        data_atual = datetime.strptime(data_inicio, "%Y-%m-%d")
        data_final = datetime.strptime(data_fim, "%Y-%m-%d")
        
        while data_atual <= data_final:
            data_str = data_atual.strftime("%Y-%m-%d")
            despesa_dia = despesas_dict.get(data_str, 0)
            receita_dia = receitas_dict.get(data_str, 0)
            
            saldo_dia = receita_dia - despesa_dia
            saldo_acumulado += saldo_dia
            
            datas.append(data_atual.strftime("%d/%m"))
            saldos.append(round(saldo_acumulado, 2))
            
            data_atual += timedelta(days=1)
        
        return jsonify({
            'success': True,
            'labels': datas,
            'values': saldos
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dashboard_bp.route('/api/notificacoes')
@login_required
def api_notificacoes():
    """API para obter notificações do usuário"""
    usuario_id = session.get('usuario_id')
    
    try:
        notificacoes = []
        
        # Lembretes vencendo
        lembrete_model = Lembrete(Config.DATABASE)
        lembretes_proximos = lembrete_model.buscar(
            usuario_id=usuario_id,
            concluido=0
        )
        
        hoje = datetime.now()
        for lembrete in lembretes_proximos:
            data_lembrete = datetime.strptime(lembrete['data'], "%Y-%m-%d")
            dias_restantes = (data_lembrete - hoje).days
            
            if dias_restantes <= 3:  # Lembretes nos próximos 3 dias
                if dias_restantes == 0:
                    mensagem = f"Lembrete para hoje: {lembrete['titulo']}"
                    tipo = "warning"
                elif dias_restantes == 1:
                    mensagem = f"Lembrete para amanhã: {lembrete['titulo']}"
                    tipo = "info"
                else:
                    mensagem = f"Lembrete em {dias_restantes} dias: {lembrete['titulo']}"
                    tipo = "info"
                
                notificacoes.append({
                    'id': f"lembrete_{lembrete['id']}",
                    'tipo': tipo,
                    'titulo': 'Lembrete',
                    'mensagem': mensagem,
                    'data': lembrete['data']
                })
        
        # Orçamentos estourados
        orcamento_model = Orcamento(Config.DATABASE)
        orcamentos = orcamento_model.buscar(
            usuario_id=usuario_id,
            tipo_perfil='pessoal'
        )
        
        for orcamento in orcamentos:
            try:
                gasto_atual = orcamento_model.calcular_gasto_atual(orcamento['id'])
                percentual = (gasto_atual / orcamento['valor_limite']) * 100 if orcamento['valor_limite'] > 0 else 0
                
                if percentual >= 100:
                    notificacoes.append({
                        'id': f"orcamento_{orcamento['id']}",
                        'tipo': 'danger',
                        'titulo': 'Orçamento Estourado',
                        'mensagem': f"Orçamento de {orcamento['categoria']} foi ultrapassado ({percentual:.1f}%)",
                        'data': datetime.now().strftime("%Y-%m-%d")
                    })
                elif percentual >= 80:
                    notificacoes.append({
                        'id': f"orcamento_{orcamento['id']}",
                        'tipo': 'warning',
                        'titulo': 'Orçamento Alto',
                        'mensagem': f"Orçamento de {orcamento['categoria']} está em {percentual:.1f}%",
                        'data': datetime.now().strftime("%Y-%m-%d")
                    })
            except:
                continue
        
        # Ordena por urgência/data
        notificacoes.sort(key=lambda x: (
            0 if x['tipo'] == 'danger' else 1 if x['tipo'] == 'warning' else 2,
            x['data']
        ))
        
        return jsonify({
            'success': True,
            'notificacoes': notificacoes[:10],  # Máximo 10 notificações
            'total': len(notificacoes)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dashboard_bp.route('/api/widgets/status')
@login_required
def api_widgets_status():
    """API para obter status dos widgets do dashboard"""
    usuario_id = session.get('usuario_id')
    
    try:
        hoje = datetime.now()
        inicio_mes = f"{hoje.year}-{hoje.month:02d}-01"
        fim_mes = hoje.strftime("%Y-%m-%d")
        
        # Contadores básicos
        lembrete_model = Lembrete(Config.DATABASE)
        lembretes_pendentes = len(lembrete_model.buscar(usuario_id=usuario_id, concluido=0))
        
        meta_model = MetaFinanceira(Config.DATABASE)
        metas_ativas = len(meta_model.buscar(usuario_id=usuario_id, concluida=0))
        
        divida_model = Divida(Config.DATABASE)
        dividas_ativas = len(divida_model.buscar(usuario_id=usuario_id))
        dividas_ativas = len([d for d in divida_model.buscar(usuario_id=usuario_id) if d['status'] != 'quitada'])
        
        # Resumo financeiro
        despesa_model = Despesa(Config.DATABASE)
        receita_model = Receita(Config.DATABASE)
        
        total_despesas = despesa_model.total_periodo(usuario_id, inicio_mes, fim_mes, 'pessoal')
        total_receitas = receita_model.total_periodo(usuario_id, inicio_mes, fim_mes, 'pessoal')
        
        return jsonify({
            'success': True,
            'widgets': {
                'lembretes_pendentes': lembretes_pendentes,
                'metas_ativas': metas_ativas,
                'dividas_ativas': dividas_ativas,
                'total_despesas_mes': round(total_despesas, 2),
                'total_receitas_mes': round(total_receitas, 2),
                'saldo_mes': round(total_receitas - total_despesas, 2)
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500