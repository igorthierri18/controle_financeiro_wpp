from flask import Blueprint, render_template, redirect, url_for, request, flash, session, jsonify, send_file
from database.models import Usuario, Despesa, Receita, TextProcessor, CategoriaPersonalizada
from functools import wraps
from datetime import datetime, timedelta
import pandas as pd
import io
from config import Config
import sqlite3
from werkzeug.utils import secure_filename
import os

despesas_bp = Blueprint('despesas', __name__, url_prefix='/despesas')

# Middleware para verificar login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# ==================== ROTAS WEB ====================

@despesas_bp.route('/')
@login_required
def index():
    """Página principal de despesas"""
    usuario_id = session.get('usuario_id')
    
    # Busca dados do usuário
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    if not usuario:
        flash('Usuário não encontrado.', 'error')
        return redirect(url_for('auth.logout'))
    
    # Filtros da URL
    periodo = request.args.get('periodo', 'mes')
    categoria = request.args.get('categoria')
    tipo_perfil = request.args.get('tipo_perfil', 'pessoal')
    data_inicio_custom = request.args.get('data_inicio')
    data_fim_custom = request.args.get('data_fim')
    
    # Define período
    hoje = datetime.now()
    
    if periodo == 'personalizado' and data_inicio_custom and data_fim_custom:
        data_inicio = data_inicio_custom
        data_fim = data_fim_custom
        periodo_texto = f"de {datetime.strptime(data_inicio, '%Y-%m-%d').strftime('%d/%m/%Y')} a {datetime.strptime(data_fim, '%Y-%m-%d').strftime('%d/%m/%Y')}"
    elif periodo == 'dia':
        data_inicio = hoje.strftime("%Y-%m-%d")
        data_fim = hoje.strftime("%Y-%m-%d")
        periodo_texto = "hoje"
    elif periodo == 'semana':
        data_inicio = (hoje - timedelta(days=7)).strftime("%Y-%m-%d")
        data_fim = hoje.strftime("%Y-%m-%d")
        periodo_texto = "nos últimos 7 dias"
    elif periodo == 'mes':
        data_inicio = f"{hoje.year}-{hoje.month:02d}-01"
        data_fim = hoje.strftime("%Y-%m-%d")
        periodo_texto = "neste mês"
    elif periodo == 'ano':
        data_inicio = f"{hoje.year}-01-01"
        data_fim = hoje.strftime("%Y-%m-%d")
        periodo_texto = "neste ano"
    else:
        data_inicio = f"{hoje.year}-{hoje.month:02d}-01"
        data_fim = hoje.strftime("%Y-%m-%d")
        periodo_texto = "neste mês"
    
    # Busca despesas
    despesa_model = Despesa(Config.DATABASE)
    despesas = despesa_model.buscar(
        usuario_id=usuario_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        categoria=categoria
    )
    
    # Filtra por tipo de perfil se especificado
    if tipo_perfil:
        despesas = [d for d in despesas if d.get('tipo_perfil', 'pessoal') == tipo_perfil]
    
    # Calcula totais
    total = sum(d['valor'] for d in despesas)
    
    # Despesas por categoria
    categorias = {}
    for despesa in despesas:
        cat = despesa['categoria']
        if cat not in categorias:
            categorias[cat] = {'categoria': cat, 'total': 0, 'count': 0}
        categorias[cat]['total'] += despesa['valor']
        categorias[cat]['count'] += 1
    
    categorias_lista = sorted(categorias.values(), key=lambda x: x['total'], reverse=True)
    
    # Top 5 despesas
    top_despesas = sorted(despesas, key=lambda x: x['valor'], reverse=True)[:5]
    
    # Estatísticas adicionais
    estatisticas = {
        'total_transacoes': len(despesas),
        'valor_medio': total / len(despesas) if despesas else 0,
        'maior_despesa': max(despesas, key=lambda x: x['valor']) if despesas else None,
        'categoria_mais_gasta': categorias_lista[0] if categorias_lista else None,
        'total_categorias': len(categorias_lista)
    }
    
    # Busca categorias disponíveis para filtros
    categoria_model = CategoriaPersonalizada(Config.DATABASE)
    categorias_usuario = categoria_model.buscar(
        usuario_id=usuario_id,
        tipo='despesa',
        tipo_perfil=tipo_perfil
    )
    
    # Adiciona categorias padrão se não tiver categorias customizadas
    if not categorias_usuario:
        categorias_usuario = get_categorias_padrao_despesa()
    
    return render_template(
        'despesas.html',
        app_name=Config.APP_NAME,
        usuario=usuario,
        despesas=despesas,
        total=total,
        categorias=categorias_lista,
        top_despesas=top_despesas,
        periodo=periodo,
        periodo_texto=periodo_texto,
        categoria_filtro=categoria,
        tipo_perfil=tipo_perfil,
        data_inicio=data_inicio,
        data_fim=data_fim,
        estatisticas=estatisticas,
        categorias_usuario=categorias_usuario
    )

@despesas_bp.route('/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar():
    """Adicionar nova despesa"""
    if request.method == 'POST':
        usuario_id = session.get('usuario_id')
        
        try:
            # Dados do formulário
            valor = float(request.form.get('valor', 0))
            categoria = request.form.get('categoria')
            descricao = request.form.get('descricao', '').strip()
            data = request.form.get('data')
            forma_pagamento = request.form.get('forma_pagamento')
            tipo_perfil = request.form.get('tipo_perfil', 'pessoal')
            parcelado = int(request.form.get('parcelado', 0))
            num_parcelas = int(request.form.get('num_parcelas', 1)) if parcelado else 1
            observacoes = request.form.get('observacoes', '')
            
            # Validações
            if not valor or valor <= 0:
                flash('Por favor, informe um valor válido maior que zero.', 'error')
                return redirect(url_for('despesas.adicionar'))
            
            if not categoria:
                flash('Por favor, selecione uma categoria.', 'error')
                return redirect(url_for('despesas.adicionar'))
            
            if not descricao:
                flash('Por favor, informe uma descrição.', 'error')
                return redirect(url_for('despesas.adicionar'))
            
            if not data:
                data = datetime.now().strftime('%Y-%m-%d')
            
            # Validação de data
            try:
                datetime.strptime(data, '%Y-%m-%d')
            except ValueError:
                flash('Data inválida.', 'error')
                return redirect(url_for('despesas.adicionar'))
            
            # Validação de parcelas
            if parcelado and (num_parcelas < 2 or num_parcelas > 60):
                flash('Número de parcelas deve estar entre 2 e 60.', 'error')
                return redirect(url_for('despesas.adicionar'))
            
            # Cria a despesa
            despesa_model = Despesa(Config.DATABASE)
            
            if parcelado and num_parcelas > 1:
                # Cria despesas parceladas
                valor_parcela = valor / num_parcelas
                data_base = datetime.strptime(data, '%Y-%m-%d')
                
                for i in range(num_parcelas):
                    data_parcela = data_base + timedelta(days=30 * i)  # Parcelas mensais
                    descricao_parcela = f"{descricao} ({i+1}/{num_parcelas})"
                    
                    despesa_model.criar(
                        usuario_id=usuario_id,
                        valor=valor_parcela,
                        categoria=categoria,
                        descricao=descricao_parcela,
                        data=data_parcela.strftime('%Y-%m-%d'),
                        forma_pagamento=forma_pagamento,
                        tipo_perfil=tipo_perfil,
                        parcelado=1,
                        num_parcelas=num_parcelas,
                        mensagem_original=observacoes
                    )
                
                flash(f'Despesa parcelada em {num_parcelas}x criada com sucesso!', 'success')
            else:
                # Cria despesa única
                despesa_model.criar(
                    usuario_id=usuario_id,
                    valor=valor,
                    categoria=categoria,
                    descricao=descricao,
                    data=data,
                    forma_pagamento=forma_pagamento,
                    tipo_perfil=tipo_perfil,
                    parcelado=0,
                    num_parcelas=1,
                    mensagem_original=observacoes
                )
                
                flash('Despesa adicionada com sucesso!', 'success')
            
            return redirect(url_for('despesas.index'))
            
        except ValueError as e:
            flash('Valor inválido. Use apenas números.', 'error')
            return redirect(url_for('despesas.adicionar'))
        except Exception as e:
            print(f'Erro ao adicionar despesa: {e}')
            flash('Erro ao adicionar despesa. Tente novamente.', 'error')
            return redirect(url_for('despesas.adicionar'))
    
    # GET - Exibe formulário
    usuario_id = session.get('usuario_id')
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    # Busca categorias do usuário
    categoria_model = CategoriaPersonalizada(Config.DATABASE)
    categorias_despesa = categoria_model.buscar(
        usuario_id=usuario_id,
        tipo='despesa'
    )
    
    # Se não tiver categorias customizadas, usa as padrão
    if not categorias_despesa:
        categorias_despesa = get_categorias_padrao_despesa()
    
    # Formas de pagamento disponíveis
    formas_pagamento = [
        'Dinheiro', 'Cartão de Crédito', 'Cartão de Débito', 
        'PIX', 'Transferência', 'Boleto', 'Cheque', 'Vale'
    ]
    
    return render_template(
        'despesas/adicionar.html',
        app_name=Config.APP_NAME,
        usuario=usuario,
        categorias_despesa=categorias_despesa,
        formas_pagamento=formas_pagamento,
        data_hoje=datetime.now().strftime('%Y-%m-%d')
    )

@despesas_bp.route('/editar/<int:despesa_id>', methods=['GET', 'POST'])
@login_required
def editar(despesa_id):
    """Editar despesa"""
    usuario_id = session.get('usuario_id')
    
    # Verifica se a despesa pertence ao usuário
    despesa_model = Despesa(Config.DATABASE)
    despesa = despesa_model.buscar_por_id(despesa_id)
    
    if not despesa or despesa.get('usuario_id') != usuario_id:
        flash('Despesa não encontrada ou acesso negado.', 'error')
        return redirect(url_for('despesas.index'))
    
    if request.method == 'POST':
        try:
            # Dados do formulário
            dados = {}
            
            valor = request.form.get('valor')
            if valor:
                dados['valor'] = float(valor)
            
            categoria = request.form.get('categoria')
            if categoria:
                dados['categoria'] = categoria
            
            descricao = request.form.get('descricao')
            if descricao:
                dados['descricao'] = descricao.strip()
            
            data = request.form.get('data')
            if data:
                # Validação de data
                try:
                    datetime.strptime(data, '%Y-%m-%d')
                    dados['data'] = data
                except ValueError:
                    flash('Data inválida.', 'error')
                    return redirect(url_for('despesas.editar', despesa_id=despesa_id))
            
            forma_pagamento = request.form.get('forma_pagamento')
            if forma_pagamento:
                dados['forma_pagamento'] = forma_pagamento
            
            tipo_perfil = request.form.get('tipo_perfil')
            if tipo_perfil:
                dados['tipo_perfil'] = tipo_perfil
            
            # Validações
            if 'valor' in dados and dados['valor'] <= 0:
                flash('O valor deve ser maior que zero.', 'error')
                return redirect(url_for('despesas.editar', despesa_id=despesa_id))
            
            if 'descricao' in dados and not dados['descricao']:
                flash('A descrição não pode estar vazia.', 'error')
                return redirect(url_for('despesas.editar', despesa_id=despesa_id))
            
            # Atualiza a despesa
            if dados:
                despesa_model.atualizar(despesa_id, **dados)
                flash('Despesa atualizada com sucesso!', 'success')
            else:
                flash('Nenhuma alteração foi feita.', 'info')
            
            return redirect(url_for('despesas.index'))
            
        except ValueError:
            flash('Valor inválido. Use apenas números.', 'error')
            return redirect(url_for('despesas.editar', despesa_id=despesa_id))
        except Exception as e:
            print(f'Erro ao editar despesa: {e}')
            flash('Erro ao atualizar despesa.', 'error')
            return redirect(url_for('despesas.editar', despesa_id=despesa_id))
    
    # GET - Exibe formulário de edição
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    # Busca categorias do usuário
    categoria_model = CategoriaPersonalizada(Config.DATABASE)
    categorias_despesa = categoria_model.buscar(
        usuario_id=usuario_id,
        tipo='despesa'
    )
    
    if not categorias_despesa:
        categorias_despesa = get_categorias_padrao_despesa()
    
    formas_pagamento = [
        'Dinheiro', 'Cartão de Crédito', 'Cartão de Débito', 
        'PIX', 'Transferência', 'Boleto', 'Cheque', 'Vale'
    ]
    
    return render_template(
        'despesas/editar.html',
        app_name=Config.APP_NAME,
        usuario=usuario,
        despesa=despesa,
        categorias_despesa=categorias_despesa,
        formas_pagamento=formas_pagamento
    )

@despesas_bp.route('/excluir/<int:despesa_id>', methods=['POST'])
@login_required
def excluir(despesa_id):
    """Excluir despesa"""
    usuario_id = session.get('usuario_id')
    
    # Verifica se a despesa pertence ao usuário
    despesa_model = Despesa(Config.DATABASE)
    despesa = despesa_model.buscar_por_id(despesa_id)
    
    if not despesa or despesa.get('usuario_id') != usuario_id:
        flash('Despesa não encontrada ou acesso negado.', 'error')
        return redirect(url_for('despesas.index'))
    
    try:
        # Exclui a despesa
        sucesso = despesa_model.excluir(despesa_id)
        
        if sucesso:
            flash('Despesa excluída com sucesso!', 'success')
        else:
            flash('Erro ao excluir despesa.', 'error')
            
    except Exception as e:
        print(f'Erro ao excluir despesa: {e}')
        flash('Erro ao excluir despesa.', 'error')
    
    return redirect(url_for('despesas.index'))

@despesas_bp.route('/duplicar/<int:despesa_id>', methods=['POST'])
@login_required
def duplicar(despesa_id):
    """Duplicar despesa"""
    usuario_id = session.get('usuario_id')
    
    # Verifica se a despesa pertence ao usuário
    despesa_model = Despesa(Config.DATABASE)
    despesa = despesa_model.buscar_por_id(despesa_id)
    
    if not despesa or despesa.get('usuario_id') != usuario_id:
        flash('Despesa não encontrada ou acesso negado.', 'error')
        return redirect(url_for('despesas.index'))
    
    try:
        # Duplica a despesa com data de hoje
        nova_despesa_id = despesa_model.criar(
            usuario_id=usuario_id,
            valor=despesa['valor'],
            categoria=despesa['categoria'],
            descricao=f"{despesa['descricao']} (Cópia)",
            data=datetime.now().strftime('%Y-%m-%d'),
            forma_pagamento=despesa.get('forma_pagamento'),
            tipo_perfil=despesa.get('tipo_perfil', 'pessoal'),
            mensagem_original=f"Duplicada de despesa ID {despesa_id}"
        )
        
        flash('Despesa duplicada com sucesso!', 'success')
        
    except Exception as e:
        print(f'Erro ao duplicar despesa: {e}')
        flash('Erro ao duplicar despesa.', 'error')
    
    return redirect(url_for('despesas.index'))

# ==================== ROTAS API ====================

@despesas_bp.route('/api')
@login_required
def api_listar():
    """API para obter despesas"""
    usuario_id = session.get('usuario_id')
    
    try:
        # Parâmetros de filtro
        periodo = request.args.get('periodo', 'mes')
        categoria = request.args.get('categoria')
        tipo_perfil = request.args.get('tipo_perfil')
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        limit = request.args.get('limit', type=int)
        
        # Define período se não for personalizado
        if periodo != 'personalizado':
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
            usuario_id=usuario_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            categoria=categoria,
            limit=limit
        )
        
        # Filtra por tipo de perfil se especificado
        if tipo_perfil:
            despesas = [d for d in despesas if d.get('tipo_perfil', 'pessoal') == tipo_perfil]
        
        return jsonify({
            'success': True,
            'despesas': despesas,
            'total': len(despesas),
            'valor_total': sum(d['valor'] for d in despesas)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@despesas_bp.route('/api', methods=['POST'])
@login_required
def api_criar():
    """API para criar despesa"""
    usuario_id = session.get('usuario_id')
    dados = request.json
    
    # Validações básicas
    if not dados or 'valor' not in dados or 'categoria' not in dados or 'descricao' not in dados:
        return jsonify({"error": "Dados incompletos"}), 400
    
    try:
        # Prepara os dados
        valor = float(dados['valor'])
        categoria = dados['categoria']
        descricao = dados['descricao'].strip()
        data = dados.get('data', datetime.now().strftime('%Y-%m-%d'))
        forma_pagamento = dados.get('forma_pagamento')
        parcelado = int(dados.get('parcelado', 0))
        num_parcelas = int(dados.get('num_parcelas', 1)) if parcelado else 1
        tipo_perfil = dados.get('tipo_perfil', 'pessoal')
        
        # Validações
        if valor <= 0:
            return jsonify({"error": "Valor deve ser maior que zero"}), 400
        
        if not descricao:
            return jsonify({"error": "Descrição é obrigatória"}), 400
        
        # Validação de data
        try:
            datetime.strptime(data, '%Y-%m-%d')
        except ValueError:
            return jsonify({"error": "Formato de data inválido"}), 400
        
        # Cria a despesa
        despesa_model = Despesa(Config.DATABASE)
        
        if parcelado and num_parcelas > 1:
            despesas_ids = []
            valor_parcela = valor / num_parcelas
            data_base = datetime.strptime(data, '%Y-%m-%d')
            
            for i in range(num_parcelas):
                data_parcela = data_base + timedelta(days=30 * i)
                descricao_parcela = f"{descricao} ({i+1}/{num_parcelas})"
                
                despesa_id = despesa_model.criar(
                    usuario_id=usuario_id,
                    valor=valor_parcela,
                    categoria=categoria,
                    descricao=descricao_parcela,
                    data=data_parcela.strftime('%Y-%m-%d'),
                    forma_pagamento=forma_pagamento,
                    parcelado=1,
                    num_parcelas=num_parcelas,
                    tipo_perfil=tipo_perfil
                )
                despesas_ids.append(despesa_id)
            
            return jsonify({
                "success": True, 
                "despesas_ids": despesas_ids,
                "message": f"Despesa parcelada em {num_parcelas}x criada com sucesso"
            }), 201
        else:
            despesa_id = despesa_model.criar(
                usuario_id=usuario_id,
                valor=valor,
                categoria=categoria,
                descricao=descricao,
                data=data,
                forma_pagamento=forma_pagamento,
                parcelado=0,
                num_parcelas=1,
                tipo_perfil=tipo_perfil
            )
            
            return jsonify({
                "success": True, 
                "id": despesa_id,
                "message": "Despesa criada com sucesso"
            }), 201
        
    except ValueError:
        return jsonify({"error": "Valor inválido"}), 400
    except Exception as e:
        print(f'Erro API criar despesa: {e}')
        return jsonify({"error": str(e)}), 500

@despesas_bp.route('/api/<int:despesa_id>', methods=['PUT'])
@login_required
def api_atualizar(despesa_id):
    """API para atualizar despesa"""
    usuario_id = session.get('usuario_id')
    dados = request.json
    
    # Verifica se a despesa pertence ao usuário
    despesa_model = Despesa(Config.DATABASE)
    despesa = despesa_model.buscar_por_id(despesa_id)
    
    if not despesa:
        return jsonify({"error": "Despesa não encontrada"}), 404
    
    if despesa['usuario_id'] != usuario_id:
        return jsonify({"error": "Não autorizado"}), 403
    
    try:
        # Prepara campos para atualização
        campos_update = {}
        
        if 'valor' in dados:
            valor = float(dados['valor'])
            if valor <= 0:
                return jsonify({"error": "Valor deve ser maior que zero"}), 400
            campos_update['valor'] = valor
        
        if 'categoria' in dados:
            campos_update['categoria'] = dados['categoria']
        
        if 'descricao' in dados:
            descricao = dados['descricao'].strip()
            if not descricao:
                return jsonify({"error": "Descrição não pode estar vazia"}), 400
            campos_update['descricao'] = descricao
        
        if 'data' in dados:
            try:
                datetime.strptime(dados['data'], '%Y-%m-%d')
                campos_update['data'] = dados['data']
            except ValueError:
                return jsonify({"error": "Formato de data inválido"}), 400
        
        if 'forma_pagamento' in dados:
            campos_update['forma_pagamento'] = dados['forma_pagamento']
        
        if 'tipo_perfil' in dados:
            campos_update['tipo_perfil'] = dados['tipo_perfil']
        
        # Atualiza a despesa
        if campos_update:
            despesa_model.atualizar(despesa_id, **campos_update)
            return jsonify({
                "success": True,
                "message": "Despesa atualizada com sucesso"
            }), 200
        else:
            return jsonify({
                "success": True,
                "message": "Nenhuma alteração foi feita"
            }), 200
            
    except ValueError:
        return jsonify({"error": "Valor inválido"}), 400
    except Exception as e:
        print(f'Erro API atualizar despesa: {e}')
        return jsonify({"error": str(e)}), 500

@despesas_bp.route('/api/<int:despesa_id>', methods=['DELETE'])
@login_required
def api_excluir(despesa_id):
    """API para excluir despesa"""
    usuario_id = session.get('usuario_id')
    
    # Verifica se a despesa pertence ao usuário
    despesa_model = Despesa(Config.DATABASE)
    despesa = despesa_model.buscar_por_id(despesa_id)
    
    if not despesa:
        return jsonify({"error": "Despesa não encontrada"}), 404
    
    if despesa['usuario_id'] != usuario_id:
        return jsonify({"error": "Não autorizado"}), 403
    
    try:
        # Exclui a despesa
        sucesso = despesa_model.excluir(despesa_id)
        
        if sucesso:
            return jsonify({
                "success": True,
                "message": "Despesa excluída com sucesso"
            }), 200
        else:
            return jsonify({"error": "Erro ao excluir despesa"}), 500
            
    except Exception as e:
        print(f'Erro API excluir despesa: {e}')
        return jsonify({"error": str(e)}), 500

@despesas_bp.route('/api/top')
@login_required
def api_top_despesas():
    """API para obter top despesas"""
    usuario_id = session.get('usuario_id')
    
    try:
        # Parâmetros
        periodo = request.args.get('periodo', 'mes')
        limit = int(request.args.get('limit', 5))
        tipo_perfil = request.args.get('tipo_perfil')
        
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
            data_inicio = None
            data_fim = None
        
        # Busca despesas
        despesa_model = Despesa(Config.DATABASE)
        despesas = despesa_model.buscar(
            usuario_id=usuario_id,
            data_inicio=data_inicio,
            data_fim=data_fim
        )
        
        # Filtra por tipo de perfil
        if tipo_perfil:
            despesas = [d for d in despesas if d.get('tipo_perfil', 'pessoal') == tipo_perfil]
        
        # Ordena por valor e pega o top
        top_despesas = sorted(despesas, key=lambda x: x['valor'], reverse=True)[:limit]
        
        return jsonify({
            'success': True,
            'despesas': top_despesas,
            'total': len(top_despesas)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@despesas_bp.route('/api/categorias')
@login_required
def api_por_categoria():
    """API para obter despesas agrupadas por categoria"""
    usuario_id = session.get('usuario_id')
    
    try:
        # Parâmetros
        periodo = request.args.get('periodo', 'mes')
        tipo_perfil = request.args.get('tipo_perfil')
        
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
            data_inicio = None
            data_fim = None
        
        # Busca despesas por categoria
        despesa_model = Despesa(Config.DATABASE)
        categorias = despesa_model.total_por_categoria(
            usuario_id=usuario_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            tipo_perfil=tipo_perfil
        )
        
        return jsonify({
            'success': True,
            'categorias': categorias,
            'total_categorias': len(categorias)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@despesas_bp.route('/api/estatisticas')
@login_required
def api_estatisticas():
    """API para obter estatísticas de despesas"""
    usuario_id = session.get('usuario_id')
    
    try:
        # Parâmetros
        periodo = request.args.get('periodo', 'mes')
        tipo_perfil = request.args.get('tipo_perfil')
        
        # Define período
        hoje = datetime.now()
        
        if periodo == 'mes':
            data_inicio = f"{hoje.year}-{hoje.month:02d}-01"
            data_fim = hoje.strftime("%Y-%m-%d")
            
            # Mês anterior para comparação
            if hoje.month == 1:
                mes_anterior = 12
                ano_anterior = hoje.year - 1
            else:
                mes_anterior = hoje.month - 1
                ano_anterior = hoje.year
            
            data_inicio_anterior = f"{ano_anterior}-{mes_anterior:02d}-01"
            ultimo_dia_anterior = (datetime(hoje.year, hoje.month, 1) - timedelta(days=1)).day
            data_fim_anterior = f"{ano_anterior}-{mes_anterior:02d}-{ultimo_dia_anterior:02d}"
            
        elif periodo == 'ano':
            data_inicio = f"{hoje.year}-01-01"
            data_fim = hoje.strftime("%Y-%m-%d")
            data_inicio_anterior = f"{hoje.year-1}-01-01"
            data_fim_anterior = f"{hoje.year-1}-12-31"
        else:
            data_inicio = f"{hoje.year}-{hoje.month:02d}-01"
            data_fim = hoje.strftime("%Y-%m-%d")
            data_inicio_anterior = data_inicio
            data_fim_anterior = data_fim
        
        # Busca despesas
        despesa_model = Despesa(Config.DATABASE)
        despesas_atual = despesa_model.buscar(
            usuario_id=usuario_id,
            data_inicio=data_inicio,
            data_fim=data_fim
        )
        
        despesas_anterior = despesa_model.buscar(
            usuario_id=usuario_id,
            data_inicio=data_inicio_anterior,
            data_fim=data_fim_anterior
        )
        
        # Filtra por tipo de perfil
        if tipo_perfil:
            despesas_atual = [d for d in despesas_atual if d.get('tipo_perfil', 'pessoal') == tipo_perfil]
            despesas_anterior = [d for d in despesas_anterior if d.get('tipo_perfil', 'pessoal') == tipo_perfil]
        
        # Calcula estatísticas
        total_atual = sum(d['valor'] for d in despesas_atual)
        total_anterior = sum(d['valor'] for d in despesas_anterior)
        
        variacao_percentual = 0
        if total_anterior > 0:
            variacao_percentual = ((total_atual - total_anterior) / total_anterior) * 100
        
        # Estatísticas detalhadas
        estatisticas = {
            'total_atual': round(total_atual, 2),
            'total_anterior': round(total_anterior, 2),
            'variacao_absoluta': round(total_atual - total_anterior, 2),
            'variacao_percentual': round(variacao_percentual, 1),
            'numero_transacoes_atual': len(despesas_atual),
            'numero_transacoes_anterior': len(despesas_anterior),
            'valor_medio_atual': round(total_atual / len(despesas_atual), 2) if despesas_atual else 0,
            'valor_medio_anterior': round(total_anterior / len(despesas_anterior), 2) if despesas_anterior else 0,
            'maior_despesa_atual': max(despesas_atual, key=lambda x: x['valor']) if despesas_atual else None,
            'periodo': periodo
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

@despesas_bp.route('/api/exportar')
@login_required
def api_exportar():
    """API para exportar despesas em CSV"""
    usuario_id = session.get('usuario_id')
    
    try:
        # Parâmetros
        periodo = request.args.get('periodo')
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        tipo_perfil = request.args.get('tipo_perfil')
        formato = request.args.get('formato', 'csv')  # csv ou xlsx
        
        # Define período se não fornecido
        if not data_inicio or not data_fim:
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
        
        # Busca despesas
        despesa_model = Despesa(Config.DATABASE)
        despesas = despesa_model.buscar(
            usuario_id=usuario_id,
            data_inicio=data_inicio,
            data_fim=data_fim
        )
        
        # Filtra por tipo de perfil
        if tipo_perfil:
            despesas = [d for d in despesas if d.get('tipo_perfil', 'pessoal') == tipo_perfil]
        
        if not despesas:
            return jsonify({"error": "Não há despesas para exportar"}), 404
        
        # Converte para DataFrame
        df = pd.DataFrame(despesas)
        
        # Seleciona e renomeia colunas
        colunas_exportar = {
            'data': 'Data',
            'descricao': 'Descrição',
            'categoria': 'Categoria',
            'valor': 'Valor (R$)',
            'forma_pagamento': 'Forma de Pagamento',
            'tipo_perfil': 'Perfil'
        }
        
        # Filtra apenas colunas que existem
        colunas_existentes = {k: v for k, v in colunas_exportar.items() if k in df.columns}
        df_export = df[list(colunas_existentes.keys())].copy()
        df_export = df_export.rename(columns=colunas_existentes)
        
        # Formata datas
        if 'Data' in df_export.columns:
            df_export['Data'] = pd.to_datetime(df_export['Data']).dt.strftime('%d/%m/%Y')
        
        # Formata valores
        if 'Valor (R$)' in df_export.columns:
            df_export['Valor (R$)'] = df_export['Valor (R$)'].apply(lambda x: f"R$ {x:.2f}")
        
        # Adiciona linha de total
        total_row = {}
        for col in df_export.columns:
            if col == 'Valor (R$)':
                total_row[col] = f"R$ {sum(d['valor'] for d in despesas):.2f}"
            elif col == 'Descrição':
                total_row[col] = 'TOTAL GERAL'
            else:
                total_row[col] = ''
        
        df_export = pd.concat([df_export, pd.DataFrame([total_row])], ignore_index=True)
        
        # Gera arquivo
        if formato.lower() == 'xlsx':
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_export.to_excel(writer, index=False, sheet_name='Despesas')
            
            output.seek(0)
            
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                download_name=f'despesas_{data_inicio}_a_{data_fim}.xlsx',
                as_attachment=True
            )
        else:
            # CSV
            csv_data = df_export.to_csv(index=False, encoding='utf-8-sig')
            
            return send_file(
                io.BytesIO(csv_data.encode('utf-8-sig')),
                mimetype='text/csv',
                download_name=f'despesas_{data_inicio}_a_{data_fim}.csv',
                as_attachment=True
            )
        
    except Exception as e:
        print(f'Erro ao exportar despesas: {e}')
        return jsonify({"error": str(e)}), 500

@despesas_bp.route('/api/processar_texto', methods=['POST'])
@login_required
def api_processar_texto():
    """API para processar texto e extrair informações de despesa"""
    dados = request.json
    
    if not dados or 'texto' not in dados:
        return jsonify({"error": "Texto não fornecido"}), 400
    
    try:
        # Processa o texto
        processador = TextProcessor()
        dados_despesa = processador.extrair_informacoes_despesa(dados['texto'])
        
        if not dados_despesa:
            return jsonify({
                "success": False,
                "message": "Não foi possível extrair informações do texto"
            })
        
        return jsonify({
            "success": True,
            "dados": dados_despesa,
            "message": "Informações extraídas com sucesso"
        })
        
    except Exception as e:
        print(f'Erro ao processar texto: {e}')
        return jsonify({"error": str(e)}), 500

# ==================== WEBHOOKS ====================

def processar_webhook_despesa(mensagem, usuario_id):
    """Processa comandos de despesa via webhook"""
    mensagem_lower = mensagem.lower().strip()
    
    # Comandos de relatório
    if mensagem_lower in ['resumo', 'relatório', 'relatorio', 'report']:
        return get_relatorio_despesas(usuario_id, 'mes')
    elif mensagem_lower == 'hoje':
        return get_relatorio_despesas(usuario_id, 'dia')
    elif mensagem_lower in ['semana', 'semanal']:
        return get_relatorio_despesas(usuario_id, 'semana')
    elif mensagem_lower in ['mês', 'mes', 'mensal']:
        return get_relatorio_despesas(usuario_id, 'mes')
    elif mensagem_lower in ['ano', 'anual']:
        return get_relatorio_despesas(usuario_id, 'ano')
    
    # Correção de categoria
    elif mensagem_lower.startswith("corrigir categoria para "):
        nova_categoria = mensagem_lower.replace("corrigir categoria para ", "").strip()
        return corrigir_ultima_categoria(usuario_id, nova_categoria)
    
    # Comandos de exclusão
    elif mensagem_lower.startswith("excluir última") or mensagem_lower.startswith("deletar última"):
        return excluir_ultima_despesa(usuario_id)
    
    # Se não for comando específico, tenta processar como nova despesa
    else:
        return processar_nova_despesa(mensagem, usuario_id)

def get_relatorio_despesas(usuario_id, periodo):
    """Gera relatório de despesas para webhook"""
    hoje = datetime.now()
    
    if periodo == "dia":
        periodo_texto = "hoje"
        data_inicio = hoje.strftime("%Y-%m-%d")
        data_fim = hoje.strftime("%Y-%m-%d")
    elif periodo == "semana":
        periodo_texto = "na última semana"
        data_inicio = (hoje - timedelta(days=7)).strftime("%Y-%m-%d")
        data_fim = hoje.strftime("%Y-%m-%d")
    elif periodo == "mes":
        periodo_texto = "neste mês"
        data_inicio = f"{hoje.year}-{hoje.month:02d}-01"
        data_fim = hoje.strftime("%Y-%m-%d")
    elif periodo == "ano":
        periodo_texto = "neste ano"
        data_inicio = f"{hoje.year}-01-01"
        data_fim = hoje.strftime("%Y-%m-%d")
    else:
        periodo_texto = "em todos os tempos"
        data_inicio = "2000-01-01"
        data_fim = hoje.strftime("%Y-%m-%d")
    
    # Busca despesas
    despesa_model = Despesa(Config.DATABASE)
    despesas = despesa_model.buscar(usuario_id, data_inicio, data_fim)
    
    if not despesas:
        return f"📊 Não há despesas registradas {periodo_texto}."
    
    # Calcula totais
    total = sum(d['valor'] for d in despesas)
    
    # Agrupa por categoria
    categorias = {}
    for despesa in despesas:
        cat = despesa['categoria']
        if cat not in categorias:
            categorias[cat] = 0
        categorias[cat] += despesa['valor']
    
    categorias_lista = sorted(categorias.items(), key=lambda x: x[1], reverse=True)
    
    # Monta relatório
    report = f"📊 *Relatório de despesas {periodo_texto}*\n\n"
    report += f"💰 Total gasto: *R$ {total:.2f}*\n\n"
    report += "🔍 *Por categoria:*\n"
    
    # Emojis por categoria
    emojis_categoria = get_emojis_categoria()
    
    for categoria, valor in categorias_lista:
        percent = (valor / total) * 100
        emoji = emojis_categoria.get(categoria.lower(), '📦')
        report += f"- {emoji} {categoria.capitalize()}: R$ {valor:.2f} ({percent:.1f}%)\n"
    
    # Últimas despesas
    report += "\n📝 *Últimas transações:*\n"
    despesas_ordenadas = sorted(despesas, key=lambda x: x['data'], reverse=True)
    
    for i, despesa in enumerate(despesas_ordenadas[:3]):
        data_formatada = datetime.strptime(despesa['data'], "%Y-%m-%d").strftime("%d/%m")
        emoji = emojis_categoria.get(despesa['categoria'].lower(), '📦')
        descricao_curta = despesa['descricao'][:20] + ('...' if len(despesa['descricao']) > 20 else '')
        report += f"{i+1}. {data_formatada}: R$ {despesa['valor']:.2f} - {emoji} {descricao_curta}\n"
    
    report += f"\n🔍 Veja mais detalhes em: {Config.WEBHOOK_BASE_URL}/despesas"
    
    return report

def processar_nova_despesa(mensagem, usuario_id):
    """Processa mensagem para criar nova despesa via webhook"""
    # Extrai informações da despesa
    processador = TextProcessor()
    dados_despesa = processador.extrair_informacoes_despesa(mensagem)
    
    if not dados_despesa or not dados_despesa.get("valor"):
        return (
            "Não consegui identificar um valor de despesa na sua mensagem. 🤔\n\n"
            "Por favor, inclua o valor gasto, por exemplo:\n"
            "• \"Almoço R$ 35\"\n"
            "• \"Paguei 50 reais de Uber hoje\"\n"
            "• \"Mercado 120,50\"\n\n"
            "Ou envie \"ajuda\" para ver todos os comandos."
        )
    
    try:
        # Salva a despesa
        despesa_model = Despesa(Config.DATABASE)
        despesa_id = despesa_model.criar(
            usuario_id=usuario_id,
            valor=dados_despesa["valor"],
            categoria=dados_despesa["categoria"],
            descricao=dados_despesa["descricao"],
            data=dados_despesa["data"],
            forma_pagamento=dados_despesa.get("forma_pagamento"),
            mensagem_original=mensagem
        )
        
        # Emoji da categoria
        emojis_categoria = get_emojis_categoria()
        emoji = emojis_categoria.get(dados_despesa["categoria"].lower(), '📦')
        
        # Resposta
        resposta = (
            f"✅ Despesa registrada!\n\n"
            f"💰 Valor: R$ {dados_despesa['valor']:.2f}\n"
            f"🏷️ Categoria: {emoji} {dados_despesa['categoria'].capitalize()}\n"
            f"📅 Data: {datetime.strptime(dados_despesa['data'], '%Y-%m-%d').strftime('%d/%m/%Y')}\n"
        )
        
        if dados_despesa.get("forma_pagamento"):
            resposta += f"💳 Forma de pagamento: {dados_despesa['forma_pagamento']}\n"
        
        resposta += f"\nSe a categoria estiver incorreta, envie:\n\"corrigir categoria para [categoria]\"\n\n"
        resposta += f"Veja todos os seus gastos em: {Config.WEBHOOK_BASE_URL}/despesas"
        
        return resposta
        
    except Exception as e:
        print(f'Erro ao salvar despesa via webhook: {e}')
        return f"Erro ao salvar despesa: {str(e)}"

def corrigir_ultima_categoria(usuario_id, nova_categoria):
    """Corrige a categoria da última despesa via webhook"""
    despesa_model = Despesa(Config.DATABASE)
    
    # Busca última despesa
    despesas = despesa_model.buscar(usuario_id, limit=1)
    
    if not despesas:
        return "Não encontrei nenhuma despesa recente para corrigir."
    
    ultima_despesa = despesas[0]
    categoria_antiga = ultima_despesa['categoria']
    
    # Categorias válidas
    categorias_validas = ["alimentação", "transporte", "moradia", "lazer", "saúde", "educação", "vestuário", "outros"]
    
    # Normaliza categoria
    nova_categoria_normalizada = nova_categoria.lower()
    
    # Mapeia categorias comuns
    mapeamento_categorias = {
        "alimentacao": "alimentação",
        "comida": "alimentação",
        "refeicao": "alimentação",
        "transporte": "transporte",
        "uber": "transporte",
        "taxi": "transporte",
        "moradia": "moradia",
        "casa": "moradia",
        "aluguel": "moradia",
        "lazer": "lazer",
        "diversao": "lazer",
        "saude": "saúde",
        "medico": "saúde",
        "educacao": "educação",
        "escola": "educação",
        "vestuario": "vestuário",
        "roupa": "vestuário"
    }
    
    if nova_categoria_normalizada in mapeamento_categorias:
        nova_categoria = mapeamento_categorias[nova_categoria_normalizada]
    elif nova_categoria_normalizada not in categorias_validas:
        return (
            f"Categoria '{nova_categoria}' não reconhecida.\n\n"
            f"Categorias válidas: {', '.join(categorias_validas)}"
        )
    
    # Atualiza categoria
    despesa_model.atualizar(ultima_despesa['id'], categoria=nova_categoria)
    
    # Emoji
    emojis_categoria = get_emojis_categoria()
    emoji = emojis_categoria.get(nova_categoria.lower(), '📦')
    
    return (
        f"✅ Categoria atualizada!\n\n"
        f"Despesa: {ultima_despesa['descricao']}\n"
        f"Valor: R$ {ultima_despesa['valor']:.2f}\n"
        f"Categoria antiga: {categoria_antiga.capitalize()}\n"
        f"Nova categoria: {emoji} {nova_categoria.capitalize()}"
    )

def excluir_ultima_despesa(usuario_id):
    """Exclui a última despesa via webhook"""
    despesa_model = Despesa(Config.DATABASE)
    
    # Busca última despesa
    despesas = despesa_model.buscar(usuario_id, limit=1)
    
    if not despesas:
        return "Não encontrei nenhuma despesa recente para excluir."
    
    ultima_despesa = despesas[0]
    
    try:
        # Exclui a despesa
        sucesso = despesa_model.excluir(ultima_despesa['id'])
        
        if sucesso:
            return (
                f"✅ Despesa excluída!\n\n"
                f"Despesa: {ultima_despesa['descricao']}\n"
                f"Valor: R$ {ultima_despesa['valor']:.2f}\n"
                f"Data: {datetime.strptime(ultima_despesa['data'], '%Y-%m-%d').strftime('%d/%m/%Y')}"
            )
        else:
            return "Erro ao excluir despesa."
            
    except Exception as e:
        print(f'Erro ao excluir despesa via webhook: {e}')
        return "Erro ao excluir despesa."

# ==================== FUNÇÕES AUXILIARES ====================

def get_categorias_padrao_despesa():
    """Retorna categorias padrão para despesas"""
    return [
        {'nome': 'Alimentação', 'icone': '🍽️', 'cor': '#FF6B6B'},
        {'nome': 'Transporte', 'icone': '🚗', 'cor': '#4ECDC4'},
        {'nome': 'Moradia', 'icone': '🏠', 'cor': '#45B7D1'},
        {'nome': 'Saúde', 'icone': '💊', 'cor': '#96CEB4'},
        {'nome': 'Educação', 'icone': '📚', 'cor': '#FFEAA7'},
        {'nome': 'Lazer', 'icone': '🎬', 'cor': '#DDA0DD'},
        {'nome': 'Vestuário', 'icone': '👕', 'cor': '#F39C12'},
        {'nome': 'Outros', 'icone': '📦', 'cor': '#95A5A6'}
    ]

def get_emojis_categoria():
    """Retorna mapeamento de emojis por categoria"""
    return {
        'alimentação': '🍽️',
        'transporte': '🚗',
        'moradia': '🏠',
        'saúde': '💊',
        'educação': '📚',
        'lazer': '🎬',
        'vestuário': '👕',
        'outros': '📦',
        'supermercado': '🛒',
        'restaurante': '🍴',
        'combustível': '⛽',
        'farmácia': '💊',
        'cinema': '🎭',
        'academia': '💪'
    }