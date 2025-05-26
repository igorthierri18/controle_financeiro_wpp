# rotas/lembretes.py
from flask import Blueprint, render_template, redirect, url_for, request, flash, session, jsonify
from database.models import Usuario, Lembrete
from functools import wraps
from datetime import datetime, timedelta
from config import Config

# Blueprint principal do módulo
lembretes_bp = Blueprint('lembretes', __name__, url_prefix='/lembretes')

# Middleware para verificar login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# ==================== ROTAS WEB ====================

@lembretes_bp.route('/')
@login_required
def index():
    """Página principal de lembretes"""
    usuario_id = session.get('usuario_id')
    
    # Busca dados do usuário
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_id(usuario_id)
    
    # Busca lembretes
    lembrete_model = Lembrete(Config.DATABASE)
    
    lembretes_pessoais = lembrete_model.buscar(
        usuario_id=usuario_id,
        tipo_perfil='pessoal',
        concluido=0
    )
    
    lembretes_empresariais = lembrete_model.buscar(
        usuario_id=usuario_id,
        tipo_perfil='empresarial',
        concluido=0
    )
    
    return render_template(
        'lembretes/index.html',
        app_name=Config.APP_NAME,
        usuario=usuario,
        lembretes_pessoais=lembretes_pessoais,
        lembretes_empresariais=lembretes_empresariais
    )

@lembretes_bp.route('/adicionar', methods=['POST'])
@login_required
def adicionar():
    """Adicionar um novo lembrete"""
    usuario_id = session.get('usuario_id')
    
    # Obtém os dados do formulário
    titulo = request.form.get('titulo')
    data = request.form.get('data')
    valor = request.form.get('valor', '')
    descricao = request.form.get('descricao', '')
    notificacao = int(request.form.get('notificacao', 0))
    recorrente = request.form.get('recorrente', '') == 'on'
    periodicidade = request.form.get('periodicidade') if recorrente else None
    tipo_perfil = request.form.get('tipo_perfil', 'pessoal')
    
    # Validações básicas
    if not titulo or not data:
        flash('Por favor, preencha os campos obrigatórios.', 'error')
        return redirect(url_for('lembretes.index'))
    
    # Converte o valor para float se fornecido
    if valor:
        try:
            valor = float(valor.replace(',', '.'))
        except ValueError:
            flash('Valor inválido.', 'error')
            return redirect(url_for('lembretes.index'))
    else:
        valor = None
    
    # Cria o lembrete
    lembrete_model = Lembrete(Config.DATABASE)
    lembrete_model.criar(
        usuario_id=usuario_id,
        titulo=titulo,
        data=data,
        notificacao=notificacao,
        descricao=descricao,
        valor=valor,
        recorrente=1 if recorrente else 0,
        periodicidade=periodicidade,
        tipo_perfil=tipo_perfil
    )
    
    flash('Lembrete adicionado com sucesso!', 'success')
    return redirect(url_for('lembretes.index'))

@lembretes_bp.route('/concluir/<int:lembrete_id>', methods=['POST'])
@login_required
def concluir(lembrete_id):
    """Marcar um lembrete como concluído"""
    usuario_id = session.get('usuario_id')
    
    # Verifica se o lembrete pertence ao usuário
    lembrete_model = Lembrete(Config.DATABASE)
    lembrete = lembrete_model.buscar_por_id(lembrete_id)
    
    if not lembrete or lembrete.get('usuario_id') != usuario_id:
        flash('Lembrete não encontrado ou acesso negado.', 'error')
        return redirect(url_for('lembretes.index'))
    
    # Marca como concluído
    lembrete_model.marcar_como_concluido(lembrete_id)
    
    # Se for recorrente, cria a próxima ocorrência
    if lembrete.get('recorrente'):
        lembrete_model.criar_recorrencia(lembrete_id)
    
    flash('Lembrete marcado como concluído!', 'success')
    return redirect(url_for('lembretes.index'))

@lembretes_bp.route('/excluir/<int:lembrete_id>', methods=['POST'])
@login_required
def excluir(lembrete_id):
    """Excluir um lembrete"""
    usuario_id = session.get('usuario_id')
    
    # Verifica se o lembrete pertence ao usuário
    lembrete_model = Lembrete(Config.DATABASE)
    lembrete = lembrete_model.buscar_por_id(lembrete_id)
    
    if not lembrete or lembrete.get('usuario_id') != usuario_id:
        flash('Lembrete não encontrado ou acesso negado.', 'error')
        return redirect(url_for('lembretes.index'))
    
    # Exclui o lembrete
    lembrete_model.excluir(lembrete_id)
    
    flash('Lembrete excluído com sucesso!', 'success')
    return redirect(url_for('lembretes.index'))

# ==================== ROTAS API ====================

@lembretes_bp.route('/api')
@login_required
def api_listar():
    """API para obter lembretes do usuário"""
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
    
    return jsonify(lembretes)

@lembretes_bp.route('/api', methods=['POST'])
@login_required
def api_criar():
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

@lembretes_bp.route('/api/<int:lembrete_id>', methods=['PUT'])
@login_required
def api_atualizar(lembrete_id):
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
        
        for campo in ['titulo', 'data', 'notificacao', 'descricao', 'valor', 'recorrente', 'periodicidade', 'tipo_perfil', 'concluido']:
            if campo in dados:
                if campo in ['notificacao', 'recorrente', 'concluido']:
                    campos_update[campo] = int(dados[campo])
                elif campo == 'valor':
                    campos_update[campo] = float(dados[campo]) if dados[campo] else None
                else:
                    campos_update[campo] = dados[campo]
        
        # Atualiza o lembrete
        lembrete_model.atualizar(lembrete_id, **campos_update)
        
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@lembretes_bp.route('/api/<int:lembrete_id>', methods=['DELETE'])
@login_required
def api_excluir(lembrete_id):
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

@lembretes_bp.route('/api/<int:lembrete_id>/concluir', methods=['PUT'])
@login_required
def api_concluir(lembrete_id):
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

# ==================== WEBHOOKS ====================

def processar_webhook_lembrete(mensagem, usuario_id):
    """Processa comandos de lembrete via webhook"""
    mensagem_lower = mensagem.lower()
    
    # Comando para listar lembretes
    if mensagem_lower in ['lembretes', 'meus lembretes', 'listar lembretes']:
        return get_lista_lembretes(usuario_id)
    
    # Comando para adicionar lembrete
    elif mensagem_lower.startswith('lembrar '):
        return processar_novo_lembrete(mensagem[8:], usuario_id)
    
    # Comando para concluir lembrete
    elif mensagem_lower.startswith('concluir lembrete '):
        return processar_concluir_lembrete(mensagem[18:], usuario_id)
    
    return None

def get_lista_lembretes(usuario_id):
    """Retorna lista de lembretes pendentes"""
    lembrete_model = Lembrete(Config.DATABASE)
    lembretes = lembrete_model.buscar(
        usuario_id=usuario_id,
        concluido=0
    )
    
    if not lembretes:
        return "📅 Você não tem lembretes pendentes."
    
    resposta = "📅 *Seus lembretes pendentes:*\n\n"
    
    for i, lembrete in enumerate(lembretes[:5], 1):  # Máximo 5 lembretes
        data_lembrete = datetime.strptime(lembrete['data'], '%Y-%m-%d')
        data_formatada = data_lembrete.strftime('%d/%m/%Y')
        
        resposta += f"{i}. {lembrete['titulo']}\n"
        resposta += f"   📅 {data_formatada}\n"
        
        if lembrete.get('valor'):
            resposta += f"   💰 R$ {lembrete['valor']:.2f}\n"
        
        if lembrete.get('descricao'):
            resposta += f"   📝 {lembrete['descricao'][:30]}...\n"
        
        resposta += "\n"
    
    if len(lembretes) > 5:
        resposta += f"... e mais {len(lembretes) - 5} lembretes.\n\n"
    
    resposta += "Para ver todos os lembretes, acesse o dashboard: " + Config.WEBHOOK_BASE_URL + "/lembretes"
    
    return resposta

def processar_novo_lembrete(texto, usuario_id):
    """Processa a criação de um novo lembrete via texto"""
    # Exemplo de processamento simples
    # "pagar conta de luz dia 15 R$ 150"
    
    try:
        # Busca por padrões no texto
        import re
        
        # Procura por data (formato dd, dd/mm, dd/mm/yyyy)
        data_match = re.search(r'dia (\d{1,2})(?:/(\d{1,2})(?:/(\d{4}))?)?', texto.lower())
        
        # Procura por valor (R$ xx,xx ou xx reais)
        valor_match = re.search(r'r\$?\s*(\d+(?:[,.]\d{2})?)', texto.lower())
        
        # O título é o texto sem as partes identificadas
        titulo = texto.strip()
        
        # Remove partes identificadas do título
        if data_match:
            titulo = titulo.replace(data_match.group(0), '').strip()
        if valor_match:
            titulo = titulo.replace(valor_match.group(0), '').strip()
        
        # Define a data
        hoje = datetime.now()
        if data_match:
            dia = int(data_match.group(1))
            mes = int(data_match.group(2)) if data_match.group(2) else hoje.month
            ano = int(data_match.group(3)) if data_match.group(3) else hoje.year
            
            # Se o dia já passou neste mês, agenda para o próximo mês
            if mes == hoje.month and dia < hoje.day:
                if mes == 12:
                    mes = 1
                    ano += 1
                else:
                    mes += 1
            
            data_lembrete = f"{ano}-{mes:02d}-{dia:02d}"
        else:
            # Se não especificar data, agenda para amanhã
            data_lembrete = (hoje + timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Define o valor
        valor = None
        if valor_match:
            valor_str = valor_match.group(1).replace(',', '.')
            valor = float(valor_str)
        
        # Cria o lembrete
        lembrete_model = Lembrete(Config.DATABASE)
        lembrete_id = lembrete_model.criar(
            usuario_id=usuario_id,
            titulo=titulo,
            data=data_lembrete,
            notificacao=1,  # Habilita notificação por padrão
            valor=valor,
            tipo_perfil='pessoal'
        )
        
        # Monta a resposta
        data_formatada = datetime.strptime(data_lembrete, '%Y-%m-%d').strftime('%d/%m/%Y')
        resposta = f"✅ Lembrete criado com sucesso!\n\n"
        resposta += f"📋 {titulo}\n"
        resposta += f"📅 {data_formatada}\n"
        
        if valor:
            resposta += f"💰 R$ {valor:.2f}\n"
        
        resposta += f"\n🔔 Você receberá uma notificação no dia."
        
        return resposta
        
    except Exception as e:
        return f"❌ Não consegui criar o lembrete.\n\nExemplo de uso:\n\"lembrar pagar conta de luz dia 15 R$ 150\""

def processar_concluir_lembrete(texto, usuario_id):
    """Processa a conclusão de um lembrete"""
    try:
        # Busca lembretes que contenham o texto
        lembrete_model = Lembrete(Config.DATABASE)
        lembretes = lembrete_model.buscar(
            usuario_id=usuario_id,
            concluido=0
        )
        
        # Procura lembrete similar
        lembrete_encontrado = None
        for lembrete in lembretes:
            if texto.lower() in lembrete['titulo'].lower():
                lembrete_encontrado = lembrete
                break
        
        if not lembrete_encontrado:
            return f"❌ Não encontrei nenhum lembrete com '{texto}'.\n\nEnvie 'lembretes' para ver seus lembretes pendentes."
        
        # Marca como concluído
        lembrete_model.marcar_como_concluido(lembrete_encontrado['id'])
        
        # Se for recorrente, cria próxima ocorrência
        if lembrete_encontrado.get('recorrente'):
            lembrete_model.criar_recorrencia(lembrete_encontrado['id'])
        
        resposta = f"✅ Lembrete concluído!\n\n"
        resposta += f"📋 {lembrete_encontrado['titulo']}\n"
        
        if lembrete_encontrado.get('recorrente'):
            resposta += f"\n🔄 Como é um lembrete recorrente, criei a próxima ocorrência."
        
        return resposta
        
    except Exception as e:
        return f"❌ Erro ao concluir lembrete: {str(e)}"

# ==================== SINCRONIZAÇÃO ====================

@lembretes_bp.route('/sincronizar_agenda', methods=['POST'])
@login_required
def sincronizar_agenda():
    """Sincroniza os lembretes com o Google Calendar"""
    # Implementação da sincronização com Google Calendar
    flash('Funcionalidade de sincronização com Google Calendar será implementada em breve.', 'info')
    return redirect(url_for('lembretes.index'))

# ==================== NOTIFICAÇÕES ====================

def enviar_notificacoes_lembretes():
    """Função para enviar notificações de lembretes (chamada por cron/scheduler)"""
    from twilio.rest import Client
    
    try:
        # Inicializa o cliente Twilio
        client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)
        
        # Busca os lembretes para notificação
        lembrete_model = Lembrete(Config.DATABASE)
        notificacoes = lembrete_model.criar_notificacoes()
        
        mensagens_enviadas = 0
        
        # Para cada lembrete, envia uma notificação
        for notificacao in notificacoes:
            # Busca o usuário
            usuario_model = Usuario(Config.DATABASE)
            usuario = usuario_model.buscar_por_id(notificacao['usuario_id'])
            
            if not usuario or not usuario.get('celular'):
                continue
            
            # Formata a mensagem
            dias_texto = "hoje" if notificacao['dias_restantes'] == 0 else f"em {notificacao['dias_restantes']} dias"
            mensagem = (
                f"🔔 *Lembrete*\n\n"
                f"Você tem um lembrete '{notificacao['titulo']}' que vence {dias_texto}.\n"
                f"📅 Data: {notificacao['data']}\n"
            )
            
            if notificacao.get('valor'):
                mensagem += f"💰 Valor: R$ {notificacao['valor']:.2f}\n"
            
            mensagem += f"\n📱 Acesse: {Config.WEBHOOK_BASE_URL}/lembretes"
            
            try:
                # Envia a mensagem via Twilio
                message = client.messages.create(
                    body=mensagem,
                    from_=Config.TWILIO_PHONE_NUMBER,
                    to=f"whatsapp:+{usuario['celular']}"
                )
                
                mensagens_enviadas += 1
            except Exception as e:
                print(f"Erro ao enviar notificação: {e}")
        
        return mensagens_enviadas
        
    except Exception as e:
        print(f"Erro no sistema de notificações: {e}")
        return 0