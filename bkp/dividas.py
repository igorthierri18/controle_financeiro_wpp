# rotas/dividas.py
"""
MÓDULO DE DÍVIDAS
=================
Gerencia todas as funcionalidades relacionadas a dívidas e financiamentos:

ROTAS WEB:
- GET /dividas/ - Lista dívidas com filtros
- GET/POST /dividas/adicionar - Formulário para nova dívida
- GET/POST /dividas/editar/<id> - Formulário para editar dívida
- POST /dividas/excluir/<id> - Excluir dívida
- POST /dividas/pagamento/<id> - Registrar pagamento

ROTAS API:
- GET /dividas/api - Listar dívidas (JSON)
- POST /dividas/api - Criar dívida (JSON)
- PUT /dividas/api/<id> - Atualizar dívida (JSON)
- DELETE /dividas/api/<id> - Excluir dívida (JSON)
- POST /dividas/api/pagamento - Registrar pagamento (JSON)
- GET /dividas/api/resumo - Resumo de dívidas

WEBHOOKS:
- processar_webhook_divida() - Comandos via WhatsApp
- "minhas dívidas" - Lista dívidas pendentes
- "pagar cartão 500" - Registrar pagamento
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash, session, jsonify
from database.models import Usuario, Divida
from functools import wraps
from datetime import datetime, timedelta
import traceback
from config import Config

# Blueprint principal do módulo
dividas_bp = Blueprint('dividas', __name__, url_prefix='/dividas')

# Middleware para verificar login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# ==================== ROTAS WEB ====================

@dividas_bp.route('/')
@login_required
def index():
    """Página principal de dívidas"""
    usuario_id = session.get('usuario_id')
    
    # Busca dados do usuário
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    # Filtros da URL
    status = request.args.get('status')
    tipo = request.args.get('tipo')
    tipo_perfil = request.args.get('tipo_perfil', 'pessoal')
    
    # Busca dívidas
    divida_model = Divida(Config.DATABASE)
    dividas = divida_model.buscar(
        usuario_id=usuario_id,
        tipo_perfil=tipo_perfil,
        status=status,
        tipo=tipo
    )
    
    # Calcula resumo
    total_dividas = sum(d['valor_total'] for d in dividas)
    total_pago = sum(d['valor_pago'] for d in dividas)
    total_restante = total_dividas - total_pago
    
    # Dívidas por status
    dividas_ativas = [d for d in dividas if d['status'] != 'quitada']
    dividas_quitadas = [d for d in dividas if d['status'] == 'quitada']
    
    return render_template(
        'dividas/index.html',
        app_name=Config.APP_NAME,
        usuario=usuario,
        dividas=dividas,
        dividas_ativas=dividas_ativas,
        dividas_quitadas=dividas_quitadas,
        total_dividas=total_dividas,
        total_pago=total_pago,
        total_restante=total_restante,
        status_filtro=status,
        tipo_filtro=tipo,
        tipo_perfil=tipo_perfil
    )

@dividas_bp.route('/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar():
    """Adicionar nova dívida"""
    if request.method == 'POST':
        try:
            usuario_id = session.get('usuario_id')
            
            # Dados do formulário
            nome = request.form.get('nome')
            valor_total = float(request.form.get('valor_total', 0))
            valor_pago = float(request.form.get('valor_pago', 0))
            data_inicio = request.form.get('data_inicio')
            data_fim = request.form.get('data_fim')
            taxa_juros = float(request.form.get('taxa_juros', 0)) if request.form.get('taxa_juros') else None
            parcelas_total = int(request.form.get('parcelas_total', 1)) if request.form.get('parcelas_total') else None
            parcelas_pagas = int(request.form.get('parcelas_pagas', 0))
            credor = request.form.get('credor')
            tipo_perfil = request.form.get('tipo_perfil', 'pessoal')
            tipo = request.form.get('tipo', 'outros')
            
            # Validações básicas
            if not nome:
                flash('Nome da dívida é obrigatório', 'error')
                return redirect(url_for('dividas.adicionar'))
            
            if valor_total <= 0:
                flash('Valor total deve ser maior que zero', 'error')
                return redirect(url_for('dividas.adicionar'))
            
            if not data_inicio:
                flash('Data de início é obrigatória', 'error')
                return redirect(url_for('dividas.adicionar'))
            
            # Cria a dívida
            divida_model = Divida(Config.DATABASE)
            divida_id = divida_model.criar(
                usuario_id=usuario_id,
                nome=nome,
                valor_total=valor_total,
                data_inicio=data_inicio,
                data_fim=data_fim,
                taxa_juros=taxa_juros,
                parcelas_total=parcelas_total,
                credor=credor,
                tipo_perfil=tipo_perfil,
                tipo=tipo
            )
            
            # Atualiza valores pagos se fornecidos
            if valor_pago > 0 or parcelas_pagas > 0:
                divida_model.atualizar(
                    divida_id,
                    valor_pago=valor_pago,
                    parcelas_pagas=parcelas_pagas
                )
            
            flash('Dívida adicionada com sucesso!', 'success')
            return redirect(url_for('dividas.index'))
            
        except Exception as e:
            print(f"Erro ao adicionar dívida: {str(e)}")
            flash('Erro ao adicionar dívida. Tente novamente.', 'error')
    
    # GET - Exibe formulário
    usuario_id = session.get('usuario_id')
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    return render_template(
        'dividas/adicionar.html',
        app_name=Config.APP_NAME,
        usuario=usuario
    )

@dividas_bp.route('/editar/<int:divida_id>', methods=['GET', 'POST'])
@login_required
def editar(divida_id):
    """Editar dívida"""
    usuario_id = session.get('usuario_id')
    
    # Verifica se a dívida pertence ao usuário
    divida_model = Divida(Config.DATABASE)
    divida = divida_model.buscar_por_id(divida_id)
    
    if not divida or divida.get('usuario_id') != usuario_id:
        flash('Dívida não encontrada ou acesso negado.', 'error')
        return redirect(url_for('dividas.index'))
    
    if request.method == 'POST':
        try:
            # Dados do formulário
            nome = request.form.get('nome')
            valor_total = float(request.form.get('valor_total', 0))
            valor_pago = float(request.form.get('valor_pago', 0))
            data_inicio = request.form.get('data_inicio')
            data_fim = request.form.get('data_fim')
            taxa_juros = float(request.form.get('taxa_juros', 0)) if request.form.get('taxa_juros') else None
            parcelas_total = int(request.form.get('parcelas_total', 1)) if request.form.get('parcelas_total') else None
            parcelas_pagas = int(request.form.get('parcelas_pagas', 0))
            credor = request.form.get('credor')
            tipo = request.form.get('tipo', 'outros')
            
            # Validações básicas
            if not nome:
                flash('Nome da dívida é obrigatório', 'error')
                return redirect(url_for('dividas.editar', divida_id=divida_id))
            
            if valor_total <= 0:
                flash('Valor total deve ser maior que zero', 'error')
                return redirect(url_for('dividas.editar', divida_id=divida_id))
            
            # Status baseado no valor pago
            status = 'quitada' if valor_pago >= valor_total else 'em_dia'
            
            # Atualiza a dívida
            divida_model.atualizar(
                divida_id,
                nome=nome,
                valor_total=valor_total,
                valor_pago=valor_pago,
                data_inicio=data_inicio,
                data_fim=data_fim,
                taxa_juros=taxa_juros,
                parcelas_total=parcelas_total,
                parcelas_pagas=parcelas_pagas,
                credor=credor,
                tipo=tipo,
                status=status
            )
            
            flash('Dívida atualizada com sucesso!', 'success')
            return redirect(url_for('dividas.index'))
            
        except Exception as e:
            print(f"Erro ao editar dívida: {str(e)}")
            flash('Erro ao atualizar dívida. Tente novamente.', 'error')
    
    # GET - Exibe formulário de edição
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    return render_template(
        'dividas/editar.html',
        app_name=Config.APP_NAME,
        usuario=usuario,
        divida=divida
    )

@dividas_bp.route('/excluir/<int:divida_id>', methods=['POST'])
@login_required
def excluir(divida_id):
    """Excluir dívida"""
    try:
        usuario_id = session.get('usuario_id')
        
        # Verifica se a dívida pertence ao usuário
        divida_model = Divida(Config.DATABASE)
        divida = divida_model.buscar_por_id(divida_id)
        
        if not divida or divida.get('usuario_id') != usuario_id:
            flash('Dívida não encontrada ou acesso negado.', 'error')
            return redirect(url_for('dividas.index'))
        
        # Exclui a dívida
        excluida = divida_model.excluir(divida_id)
        
        if excluida:
            flash('Dívida excluída com sucesso!', 'success')
        else:
            flash('Erro ao excluir dívida', 'error')
            
    except Exception as e:
        print(f"Erro ao excluir dívida: {str(e)}")
        flash('Erro ao excluir dívida. Tente novamente.', 'error')
    
    return redirect(url_for('dividas.index'))

@dividas_bp.route('/pagamento/<int:divida_id>', methods=['POST'])
@login_required
def registrar_pagamento(divida_id):
    """Registrar pagamento de dívida"""
    try:
        usuario_id = session.get('usuario_id')
        
        # Dados do formulário
        valor = float(request.form.get('valor', 0))
        data = request.form.get('data')
        tipo = request.form.get('tipo', 'parcela')
        observacao = request.form.get('observacao')
        
        # Validações básicas
        if valor <= 0:
            flash('Valor do pagamento deve ser maior que zero', 'error')
            return redirect(url_for('dividas.index'))
        
        # Verifica se a dívida pertence ao usuário
        divida_model = Divida(Config.DATABASE)
        divida = divida_model.buscar_por_id(divida_id)
        
        if not divida or divida.get('usuario_id') != usuario_id:
            flash('Dívida não encontrada ou acesso negado.', 'error')
            return redirect(url_for('dividas.index'))
        
        # Registra o pagamento
        pagamento_id = divida_model.registrar_pagamento(
            divida_id=divida_id,
            valor=valor,
            data=data,
            observacao=observacao,
            tipo=tipo
        )
        
        flash('Pagamento registrado com sucesso!', 'success')
        
    except Exception as e:
        print(f"Erro ao registrar pagamento: {str(e)}")
        flash('Erro ao registrar pagamento. Tente novamente.', 'error')
    
    return redirect(url_for('dividas.index'))

# ==================== ROTAS API ====================

@dividas_bp.route('/api')
@login_required
def api_listar():
    """API para listar dívidas"""
    try:
        usuario_id = session.get('usuario_id')
        tipo_perfil = request.args.get('tipo_perfil', 'pessoal')
        status = request.args.get('status')
        tipo = request.args.get('tipo')
        
        # Busca dívidas
        divida_model = Divida(Config.DATABASE)
        dividas = divida_model.buscar(
            usuario_id=usuario_id,
            tipo_perfil=tipo_perfil,
            status=status,
            tipo=tipo
        )
        
        return jsonify(dividas), 200
        
    except Exception as e:
        print(f"Erro ao listar dívidas: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@dividas_bp.route('/api', methods=['POST'])
@login_required
def api_criar():
    """API para criar dívida"""
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
        
        # Cria a dívida
        divida_model = Divida(Config.DATABASE)
        divida_id = divida_model.criar(
            usuario_id=usuario_id,
            nome=dados.get('nome'),
            valor_total=float(dados.get('valor_total', 0)),
            data_inicio=dados.get('data_inicio'),
            data_fim=dados.get('data_fim'),
            taxa_juros=float(dados.get('taxa_juros', 0)) if dados.get('taxa_juros') else None,
            parcelas_total=int(dados.get('parcelas_total', 1)) if dados.get('parcelas_total') else None,
            credor=dados.get('credor'),
            tipo_perfil=dados.get('tipo_perfil', 'pessoal'),
            tipo=dados.get('tipo', 'outros')
        )
        
        # Atualiza valores pagos se fornecidos
        valor_pago = float(dados.get('valor_pago', 0))
        parcelas_pagas = int(dados.get('parcelas_pagas', 0))
        
        if valor_pago > 0 or parcelas_pagas > 0:
            divida_model.atualizar(
                divida_id,
                valor_pago=valor_pago,
                parcelas_pagas=parcelas_pagas
            )
        
        return jsonify({'id': divida_id, 'message': 'Dívida criada com sucesso'}), 201
        
    except Exception as e:
        print(f"Erro ao criar dívida: {str(e)}")
        return jsonify({'error': str(e) or 'Erro interno do servidor'}), 500

@dividas_bp.route('/api/<int:divida_id>', methods=['PUT'])
@login_required
def api_atualizar(divida_id):
    """API para atualizar dívida"""
    try:
        usuario_id = session.get('usuario_id')
        dados = request.get_json()
        
        # Verifica se a dívida pertence ao usuário
        divida_model = Divida(Config.DATABASE)
        divida = divida_model.buscar_por_id(divida_id)
        
        if not divida:
            return jsonify({'error': 'Dívida não encontrada'}), 404
        
        if divida['usuario_id'] != usuario_id:
            return jsonify({'error': 'Acesso negado'}), 403
        
        # Prepara dados para atualização
        dados_atualizacao = {}
        
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
        
        # Atualiza status automaticamente se quitada
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
        
        # Atualiza a dívida
        divida_model.atualizar(divida_id, **dados_atualizacao)
        
        # Retorna dívida atualizada
        divida_atualizada = divida_model.buscar_por_id(divida_id)
        return jsonify(divida_atualizada), 200
        
    except Exception as e:
        print(f"Erro ao atualizar dívida: {str(e)}")
        return jsonify({'error': str(e) or 'Erro interno do servidor'}), 500

@dividas_bp.route('/api/<int:divida_id>', methods=['DELETE'])
@login_required
def api_excluir(divida_id):
    """API para excluir dívida"""
    try:
        usuario_id = session.get('usuario_id')
        
        # Verifica se a dívida pertence ao usuário
        divida_model = Divida(Config.DATABASE)
        divida = divida_model.buscar_por_id(divida_id)
        
        if not divida:
            return jsonify({'error': 'Dívida não encontrada'}), 404
        
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
        return jsonify({'error': str(e) or 'Erro interno do servidor'}), 500

@dividas_bp.route('/api/pagamento', methods=['POST'])
@login_required
def api_registrar_pagamento():
    """API para registrar pagamento"""
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
        
        # Verifica se a dívida pertence ao usuário
        divida_model = Divida(Config.DATABASE)
        divida = divida_model.buscar_por_id(divida_id)
        
        if not divida:
            return jsonify({'error': 'Dívida não encontrada'}), 404
        
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
        
        # Obtém dívida atualizada
        divida_atualizada = divida_model.buscar_por_id(divida_id)
        
        return jsonify({
            'id': pagamento_id,
            'message': 'Pagamento registrado com sucesso',
            'divida': divida_atualizada
        }), 201
        
    except Exception as e:
        print(f"Erro ao registrar pagamento: {str(e)}")
        return jsonify({'error': str(e) or 'Erro interno do servidor'}), 500

@dividas_bp.route('/api/resumo')
@login_required
def api_resumo():
    """API para obter resumo de dívidas"""
    try:
        usuario_id = session.get('usuario_id')
        tipo_perfil = request.args.get('tipo_perfil', 'pessoal')
        
        # Busca todas as dívidas
        divida_model = Divida(Config.DATABASE)
        dividas = divida_model.buscar(
            usuario_id=usuario_id,
            tipo_perfil=tipo_perfil
        )
        
        # Calcula resumo
        total_dividas = sum(d['valor_total'] for d in dividas)
        total_pago = sum(d['valor_pago'] for d in dividas)
        total_restante = total_dividas - total_pago
        
        # Agrupa por status
        resumo_status = {}
        for divida in dividas:
            status = divida['status']
            if status not in resumo_status:
                resumo_status[status] = {'count': 0, 'valor_total': 0, 'valor_restante': 0}
            
            resumo_status[status]['count'] += 1
            resumo_status[status]['valor_total'] += divida['valor_total']
            resumo_status[status]['valor_restante'] += (divida['valor_total'] - divida['valor_pago'])
        
        # Próximos vencimentos
        hoje = datetime.now()
        proximos_vencimentos = []
        
        for divida in dividas:
            if divida['status'] != 'quitada' and divida.get('data_fim'):
                try:
                    data_fim = datetime.strptime(divida['data_fim'], '%Y-%m-%d')
                    dias_restantes = (data_fim - hoje).days
                    
                    if dias_restantes <= 30:  # Próximos 30 dias
                        proximos_vencimentos.append({
                            'id': divida['id'],
                            'nome': divida['nome'],
                            'data_fim': divida['data_fim'],
                            'dias_restantes': dias_restantes,
                            'valor_restante': divida['valor_total'] - divida['valor_pago']
                        })
                except:
                    pass
        
        # Ordena por data de vencimento
        proximos_vencimentos.sort(key=lambda x: x['dias_restantes'])
        
        resumo = {
            'total_dividas': total_dividas,
            'total_pago': total_pago,
            'total_restante': total_restante,
            'quantidade_dividas': len(dividas),
            'resumo_por_status': resumo_status,
            'proximos_vencimentos': proximos_vencimentos[:5]  # Top 5
        }
        
        return jsonify(resumo), 200
        
    except Exception as e:
        print(f"Erro ao gerar resumo: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

# ==================== WEBHOOKS ====================

def processar_webhook_divida(mensagem, usuario_id):
    """Processa comandos de dívida via webhook"""
    mensagem_lower = mensagem.lower()
    
    # Comandos de listagem
    if mensagem_lower in ['dívidas', 'dividas', 'minhas dívidas', 'minhas dividas']:
        return get_lista_dividas(usuario_id)
    elif mensagem_lower in ['dívidas pendentes', 'dividas pendentes']:
        return get_lista_dividas(usuario_id, status='em_dia')
    elif mensagem_lower in ['dívidas quitadas', 'dividas quitadas']:
        return get_lista_dividas(usuario_id, status='quitada')
    
    # Comando para registrar pagamento
    elif mensagem_lower.startswith('pagar '):
        return processar_pagamento_divida(mensagem[6:], usuario_id)
    
    return None

def get_lista_dividas(usuario_id, status=None):
    """Retorna lista de dívidas"""
    divida_model = Divida(Config.DATABASE)
    dividas = divida_model.buscar(
        usuario_id=usuario_id,
        status=status
    )
    
    if not dividas:
        if status == 'quitada':
            return "📊 Você não tem dívidas quitadas registradas."
        elif status == 'em_dia':
            return "🎉 Parabéns! Você não tem dívidas pendentes."
        else:
            return "📊 Você não tem dívidas registradas."
    
    # Monta resposta
    if status == 'quitada':
        resposta = "✅ *Suas dívidas quitadas:*\n\n"
    elif status == 'em_dia':
        resposta = "⚠️ *Suas dívidas pendentes:*\n\n"
    else:
        resposta = "💳 *Suas dívidas:*\n\n"
    
    total_dividas = 0
    total_pago = 0
    
    for i, divida in enumerate(dividas[:5], 1):  # Máximo 5 dívidas
        valor_total = divida['valor_total']
        valor_pago = divida['valor_pago']
        valor_restante = valor_total - valor_pago
        
        total_dividas += valor_total
        total_pago += valor_pago
        
        status_emoji = "✅" if divida['status'] == 'quitada' else "⏳"
        
        resposta += f"{i}. {status_emoji} {divida['nome']}\n"
        resposta += f"   💰 Total: R$ {valor_total:.2f}\n"
        resposta += f"   💳 Pago: R$ {valor_pago:.2f}\n"
        
        if valor_restante > 0:
            resposta += f"   ⚠️ Restante: R$ {valor_restante:.2f}\n"
        
        if divida.get('credor'):
            resposta += f"   🏢 Credor: {divida['credor']}\n"
        
        if divida.get('data_fim'):
            try:
                data_fim = datetime.strptime(divida['data_fim'], '%Y-%m-%d')
                data_formatada = data_fim.strftime('%d/%m/%Y')
                dias_restantes = (data_fim - datetime.now()).days
                
                if dias_restantes > 0:
                    resposta += f"   📅 Vence em: {data_formatada} ({dias_restantes} dias)\n"
                elif dias_restantes == 0:
                    resposta += f"   🚨 Vence hoje: {data_formatada}\n"
                else:
                    resposta += f"   ⚠️ Venceu em: {data_formatada}\n"
            except:
                pass
        
        resposta += "\n"
    
    if len(dividas) > 5:
        resposta += f"... e mais {len(dividas) - 5} dívidas.\n\n"
    
    # Resumo total
    total_restante = total_dividas - total_pago
    resposta += f"💰 *Resumo Total:*\n"
    resposta += f"Total em dívidas: R$ {total_dividas:.2f}\n"
    resposta += f"Total pago: R$ {total_pago:.2f}\n"
    resposta += f"Total restante: R$ {total_restante:.2f}\n\n"
    
    resposta += f"Para registrar um pagamento, envie:\n\"pagar [nome da dívida] [valor]\"\n\n"
    resposta += f"Acesse {Config.WEBHOOK_BASE_URL}/dividas para gerenciar suas dívidas"
    
    return resposta

def processar_pagamento_divida(texto, usuario_id):
    """Processa registro de pagamento via texto"""
    try:
        # Extrai valor do texto
        import re
        valor_match = re.search(r'(\d+(?:[,.]\d{2})?)', texto)
        
        if not valor_match:
            return "❌ Não consegui identificar o valor do pagamento.\n\nExemplo: \"pagar cartão 500\""
        
        valor = float(valor_match.group(1).replace(',', '.'))
        
        # Remove o valor do texto para identificar a dívida
        nome_divida = texto.replace(valor_match.group(1), '').strip()
        
        # Busca dívida similar
        divida_model = Divida(Config.DATABASE)
        dividas = divida_model.buscar(usuario_id=usuario_id, status='em_dia')
        
        divida_encontrada = None
        for divida in dividas:
            if nome_divida.lower() in divida['nome'].lower():
                divida_encontrada = divida
                break
        
        if not divida_encontrada:
            return f"❌ Não encontrei nenhuma dívida com '{nome_divida}'.\n\nEnvie 'dívidas' para ver suas dívidas pendentes."
        
        # Registra o pagamento
        pagamento_id = divida_model.registrar_pagamento(
            divida_id=divida_encontrada['id'],
            valor=valor,
            data=datetime.now().strftime("%Y-%m-%d"),
            observacao="Pagamento via WhatsApp",
            tipo='parcela'
        )
        
        # Busca dívida atualizada
        divida_atualizada = divida_model.buscar_por_id(divida_encontrada['id'])
        valor_restante = divida_atualizada['valor_total'] - divida_atualizada['valor_pago']
        
        resposta = f"✅ Pagamento registrado!\n\n"
        resposta += f"💳 Dívida: {divida_encontrada['nome']}\n"
        resposta += f"💰 Valor pago: R$ {valor:.2f}\n"
        resposta += f"📊 Valor restante: R$ {valor_restante:.2f}\n"
        
        if valor_restante <= 0:
            resposta += f"\n🎉 Parabéns! Dívida quitada!"
        
        return resposta
        
    except Exception as e:
        return f"❌ Erro ao registrar pagamento: {str(e)}"