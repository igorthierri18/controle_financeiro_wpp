from flask import Blueprint, request, url_for
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator
from database.supabase_models import Usuario, Despesa, Receita, TextProcessor
from config import Config
from datetime import datetime, timedelta
import re
import requests
import traceback
import os
import requests
from datetime import datetime, timedelta
import json
from io import BytesIO
from PIL import Image
import tempfile

# Criação do blueprint
webhook_bp = Blueprint('webhook', __name__)

@webhook_bp.route('/webhook', methods=['POST'])
def webhook():
    """Webhook para receber mensagens do WhatsApp via Twilio"""
    # Log para debug
    print("\n===== WEBHOOK RECEBIDO =====")
    print("Headers:", dict(request.headers))
    print("Form data:", dict(request.form))
    print("============================\n")
    
    # Validação da assinatura da Twilio (segurança adicional)
    validator = RequestValidator(Config.TWILIO_AUTH_TOKEN)
    request_valid = validator.validate(
        request.url,
        request.form,
        request.headers.get('X-Twilio-Signature', '')
    )
    
    # Em ambiente de desenvolvimento, você pode desativar essa validação
    if not Config.DEBUG and not request_valid:
        print("ERRO: Assinatura Twilio inválida!")
        return "Assinatura inválida", 403
    
    # Extrai informações da requisição
    mensagem = request.values.get('Body', '').strip()
    remetente = request.values.get('From', '')
    profile_name = request.values.get('ProfileName', '')
    
    # Inicializa a resposta
    resposta = MessagingResponse()
    
    try:
        # Processa a mensagem
        resposta_texto = processar_mensagem(mensagem, remetente, profile_name)
        resposta.message(resposta_texto)
    except Exception as e:
        # Log do erro para debug
        print(f"ERRO: {e}")
        traceback.print_exc()
        
        # Em caso de erro, envia uma mensagem amigável
        resposta.message(
            f"Ops! Encontramos um problema ao processar sua mensagem. "
            f"Por favor, tente novamente ou envie 'ajuda' para ver os comandos disponíveis."
        )
    
    return str(resposta)

def enviar_notificacoes_vencimentos():
    """Envia notificações de lembretes via WhatsApp"""
    from twilio.rest import Client
    
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
            f"🔔 *Lembrete de pagamento*\n\n"
            f"Você tem um lembrete para '{notificacao['titulo']}' que vence {dias_texto}.\n"
            f"Data: {notificacao['data']}\n"
            f"\nEnvie \"ajuda\" para ver os comandos disponíveis."
        )
        
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

def processar_mensagem(mensagem, remetente, profile_name=None):
    """Processa a mensagem recebida e retorna uma resposta"""
    # Remove o prefixo 'whatsapp:' do número do remetente
    if remetente.startswith('whatsapp:'):
        remetente = remetente[9:]
    
    # Obtém ou cria o usuário
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_celular(remetente)
    
    if not usuario:
        nome = profile_name if profile_name else None
        usuario_id = usuario_model.criar(celular=remetente, nome=nome)
    else:
        usuario_id = usuario['id']
        
        # Atualiza o nome se necessário
        if profile_name and (usuario.get('nome') is None or usuario.get('nome') == ''):
            usuario_model.atualizar(usuario_id, nome=profile_name)
    
    # Mensagem em minúsculas para facilitar a comparação
    mensagem_lower = mensagem.lower()
    
    # Processa diferentes tipos de mensagens
    if mensagem_lower in ['oi', 'olá', 'ola', 'hi', 'hello']:
        return get_mensagem_boas_vindas(usuario)
        
    elif mensagem_lower in ['ajuda', 'help', '?']:
        return get_mensagem_ajuda()
        
    elif mensagem_lower in ['resumo', 'relatório', 'relatorio', 'report']:
        return get_relatorio(usuario_id, 'mes')
        
    elif mensagem_lower == 'hoje':
        return get_relatorio(usuario_id, 'dia')
        
    elif mensagem_lower in ['semana', 'semanal']:
        return get_relatorio(usuario_id, 'semana')
        
    elif mensagem_lower in ['mês', 'mes', 'mensal']:
        return get_relatorio(usuario_id, 'mes')
        
    elif mensagem_lower in ['ano', 'anual']:
        return get_relatorio(usuario_id, 'ano')
    
    elif 'resumo' in mensagem_lower and ('gráfico' in mensagem_lower or 'grafico' in mensagem_lower):
        return get_relatorio_grafico(usuario_id, mensagem_lower)
    
    elif mensagem_lower == "planos" or mensagem_lower == "mudar plano" or mensagem_lower == "info planos" or mensagem_lower == "ver planos":
        return get_info_planos()
    
    elif mensagem_lower.startswith("corrigir categoria para "):
        nova_categoria = mensagem_lower.replace("corrigir categoria para ", "").strip()
        return corrigir_ultima_categoria(usuario_id, nova_categoria)
    
    else:
        # Processa como uma despesa
        return processar_despesa(mensagem, usuario_id)

def get_mensagem_boas_vindas(usuario):
    """Retorna uma mensagem de boas-vindas personalizada"""
    app_name = Config.APP_NAME
    
    if usuario and usuario.get('nome'):
        return (
            f"Olá, {usuario['nome']}! 👋\n\n"
            f"Bem-vindo ao {app_name}, seu assistente de controle financeiro!\n\n"
            f"Como posso ajudar hoje?\n\n"
            f"- Descreva uma despesa (ex: \"Almoço R$ 25,90\")\n"
            f"- Digite \"ajuda\" para ver todos os comandos\n"
            f"- Digite \"resumo\" para ver um relatório"
        )
    else:
        return (
            f"Olá! 👋\n\n"
            f"Bem-vindo ao {app_name}, seu assistente de controle financeiro!\n\n"
            f"Como posso ajudar hoje?\n\n"
            f"- Descreva uma despesa (ex: \"Almoço R$ 25,90\")\n"
            f"- Digite \"ajuda\" para ver todos os comandos\n"
            f"- Digite \"resumo\" para ver um relatório"
        )

def get_mensagem_ajuda():
    """Retorna a mensagem de ajuda"""
    return (
        "🤖 *Assistente de Controle de Gastos*\n\n"
        "Como usar:\n"
        "- 💬 Envie um texto: \"Almoço R$ 25,90\"\n"
        "- 📸 Recurso de foto de comprovante (em breve!)\n"
        "- 🎙️ Recurso de áudio (em breve!)\n\n"
        "Comandos disponíveis:\n"
        "- \"resumo\" ou \"relatório\": Ver um resumo geral\n"
        "- \"hoje\": Gastos de hoje\n"
        "- \"semana\": Relatório da última semana\n"
        "- \"mês\": Relatório do mês atual\n"
        "- \"ano\": Relatório do ano atual\n"
        "- \"resumo gráfico semana\": Envia imagem do gráfico\n"
        "- \"planos\": Informações sobre planos disponíveis\n"
        "- \"corrigir categoria para [categoria]\": Corrige a categoria da última despesa\n"
        "- \"ajuda\": Mostra esta mensagem\n\n"
        f"Acesse também: {Config.WEBHOOK_BASE_URL}/"
    )

def get_relatorio(usuario_id, periodo):
    """Gera um relatório de despesas para o usuário"""
    # Define o filtro de data
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
    else:  # all
        periodo_texto = "em todos os tempos"
        data_inicio = "2000-01-01"  # Data bem antiga para pegar tudo
    
    data_fim = hoje.strftime("%Y-%m-%d")
    
    # Obtém as despesas
    despesa_model = Despesa(Config.DATABASE)
    despesas = despesa_model.buscar(usuario_id, data_inicio, data_fim)
    
    if not despesas:
        return f"📊 Não há despesas registradas {periodo_texto}."
    
    # Calcula o total
    total = despesa_model.total_periodo(usuario_id, data_inicio, data_fim)
    
    # Obtém as despesas por categoria
    categorias = despesa_model.total_por_categoria(usuario_id, data_inicio, data_fim)
    
    # Cria uma mensagem com o relatório e emojis
    report = f"📊 *Relatório de despesas {periodo_texto}*\n\n"
    report += f"💰 Total gasto: *R$ {total:.2f}*\n\n"
    report += "🔍 *Detalhes por categoria:*\n"
    
    # Instancia o processador de texto para obter emojis
    text_processor = TextProcessor()
    
    for categoria in categorias:
        nome_categoria = categoria['categoria']
        valor = categoria['total']
        percent = (valor / total) * 100
        emoji = text_processor.get_categoria_emoji(nome_categoria)
        report += f"- {emoji} {nome_categoria.capitalize()}: R$ {valor:.2f} ({percent:.1f}%)\n"
    
    # Adiciona as últimas despesas (máximo 3)
    report += "\n📝 *Últimas transações:*\n"
    for i, despesa in enumerate(despesas[:3]):
        data = datetime.strptime(despesa['data'], "%Y-%m-%d").strftime("%d/%m")
        categoria_emoji = text_processor.get_categoria_emoji(despesa['categoria'])
        report += f"{i+1}. {data}: R$ {despesa['valor']:.2f} - {categoria_emoji} {despesa['descricao'][:20]}\n"
    
    report += f"\n🔍 Acesse {Config.WEBHOOK_BASE_URL}/ para análises detalhadas!"
    
    return report

def get_relatorio_grafico(usuario_id, mensagem):
    """Gera um relatório com imagem do gráfico"""
    # Verifica qual período foi solicitado
    if 'hoje' in mensagem or 'dia' in mensagem:
        periodo = 'dia'
    elif 'semana' in mensagem:
        periodo = 'semana'
    elif 'mês' in mensagem or 'mes' in mensagem:
        periodo = 'mes'
    elif 'ano' in mensagem:
        periodo = 'ano'
    else:
        periodo = 'mes'  # Padrão
    
    # Verifica qual tipo de gráfico foi solicitado
    if 'categoria' in mensagem:
        tipo = 'categoria'
    elif 'tempo' in mensagem:
        tipo = 'tempo'
    else:
        tipo = 'categoria'  # Padrão
    
    # URL para o gráfico
    url_grafico = f"{Config.WEBHOOK_BASE_URL}/api/grafico/imagem?tipo={tipo}&periodo={periodo}"
    
    # Na versão real, você enviaria essa URL via Twilio Media API
    # Para esta versão simplificada, apenas retornamos a informação
    return (
        f"📊 *Relatório gráfico solicitado*\n\n"
        f"Infelizmente não posso enviar imagens diretamente pelo WhatsApp Sandbox.\n\n"
        f"Acesse o gráfico em:\n{url_grafico}\n\n"
        f"Ou veja todos os relatórios completos em:\n{Config.WEBHOOK_BASE_URL}/dashboard"
    )

def get_info_planos():
    """Retorna informações sobre os planos disponíveis"""
    app_name = Config.APP_NAME
    
    # Obtém informações dos planos da Config
    # Usa get() com valores padrão para evitar KeyError
    plano_gratuito = getattr(Config, 'PLANO_GRATUITO', {})
    plano_premium = getattr(Config, 'PLANO_PREMIUM', {})
    plano_profissional = getattr(Config, 'PLANO_PROFISSIONAL', {})
    
    # Valores padrão se as chaves não existirem
    limite_transacoes_gratuito = plano_gratuito.get('limite_transacoes', 3000)
    limite_usuarios_gratuito = plano_gratuito.get('limite_usuarios', 1)
    exportacao_gratuito = plano_gratuito.get('exportacao_dados', False)
    
    limite_transacoes_premium = plano_premium.get('limite_transacoes', 20000)
    limite_usuarios_premium = plano_premium.get('limite_usuarios', 2)
    exportacao_premium = plano_premium.get('exportacao_dados', True)
    preco_premium = plano_premium.get('preco', 29.90)
    
    limite_transacoes_prof = "Ilimitado"
    if plano_profissional:
        limite_usuarios_prof = plano_profissional.get('limite_usuarios', 5)
        exportacao_prof = plano_profissional.get('exportacao_dados', True)
        preco_prof = plano_profissional.get('preco', 59.90)
    else:
        limite_usuarios_prof = 5
        exportacao_prof = True
        preco_prof = 59.90
    
    return (
        f"💳 *Planos {app_name}*\n\n"
        f"*Plano Gratuito*\n"
        f"- Preço: Grátis\n"
        f"- Até {limite_transacoes_gratuito} transações/mês\n"
        f"- Dashboard interativo: ✓\n"
        f"- Relatórios detalhados: ✗\n"
        f"- Exportação CSV: {'✓' if exportacao_gratuito else '✗'}\n"
        f"- Usuários por conta: {limite_usuarios_gratuito}\n\n"
        
        f"*Plano Premium*\n"
        f"- Preço: R$ {preco_premium:.2f}/mês\n"
        f"- Até {limite_transacoes_premium} transações/mês\n"
        f"- Dashboard interativo: ✓\n"
        f"- Relatórios detalhados: ✓\n"
        f"- Exportação CSV: {'✓' if exportacao_premium else '✗'}\n"
        f"- Usuários por conta: {limite_usuarios_premium}\n\n"
        
        f"*Plano Profissional*\n"
        f"- Preço: R$ {preco_prof:.2f}/mês\n"
        f"- Transações: {limite_transacoes_prof}\n"
        f"- Dashboard interativo: ✓\n"
        f"- Relatórios detalhados: ✓\n"
        f"- Exportação CSV: {'✓' if exportacao_prof else '✗'}\n"
        f"- Usuários por conta: {limite_usuarios_prof}\n\n"
        
        f"Para assinar, acesse:\n"
        f"{Config.WEBHOOK_BASE_URL}/planos"
    )

def corrigir_ultima_categoria(usuario_id, nova_categoria):
    """Corrige a categoria da última despesa registrada pelo usuário"""
    despesa_model = Despesa(Config.DATABASE)
    
    # Busca a última despesa do usuário
    despesas = despesa_model.buscar(usuario_id, limit=1)
    
    if not despesas:
        return "Não encontrei nenhuma despesa recente para corrigir."
    
    ultima_despesa = despesas[0]
    categoria_antiga = ultima_despesa['categoria']
    
    # Valida a nova categoria
    categorias_validas = ["alimentação", "transporte", "moradia", "lazer", "saúde", "educação", "vestuário", "outros"]
    
    # Normaliza a categoria (remove acentos, converte para minúsculas)
    import unidecode
    nova_categoria_normalizada = unidecode.unidecode(nova_categoria.lower())
    
    # Verifica se a categoria é válida ou encontra a mais próxima
    if nova_categoria_normalizada not in categorias_validas:
        # Mapeia categorias comuns escritas de forma diferente
        mapeamento_categorias = {
            "alimentacao": "alimentação",
            "comida": "alimentação",
            "refeicao": "alimentação",
            "refeição": "alimentação",
            "transporte": "transporte",
            "uber": "transporte",
            "taxi": "transporte",
            "onibus": "transporte",
            "mobilidade": "transporte",
            "moradia": "moradia",
            "casa": "moradia",
            "aluguel": "moradia",
            "apartamento": "moradia",
            "lazer": "lazer",
            "diversao": "lazer",
            "diversão": "lazer",
            "entretenimento": "lazer",
            "saude": "saúde",
            "medico": "saúde",
            "remedio": "saúde",
            "remédio": "saúde",
            "educacao": "educação",
            "escola": "educação",
            "estudos": "educação",
            "curso": "educação",
            "vestuario": "vestuário",
            "roupa": "vestuário",
            "calcado": "vestuário",
            "sapato": "vestuário",
            "tenis": "vestuário"
        }
        
        if nova_categoria_normalizada in mapeamento_categorias:
            nova_categoria = mapeamento_categorias[nova_categoria_normalizada]
        else:
            # Verifica similaridade para encontrar a categoria mais próxima
            categoria_mais_proxima = None
            maior_similaridade = 0
            
            for cat in categorias_validas:
                cat_normalizada = unidecode.unidecode(cat)
                # Cálculo de similaridade simples
                similaridade = sum(1 for a, b in zip(nova_categoria_normalizada, cat_normalizada) if a == b) / max(len(nova_categoria_normalizada), len(cat_normalizada))
                if similaridade > maior_similaridade and similaridade > 0.6:  # 60% de similaridade
                    maior_similaridade = similaridade
                    categoria_mais_proxima = cat
            
            if categoria_mais_proxima:
                nova_categoria = categoria_mais_proxima
            else:
                return (
                    f"Categoria '{nova_categoria}' não reconhecida.\n\n"
                    f"Categorias válidas: {', '.join(categorias_validas)}.\n\n"
                    f"Por favor, tente novamente com uma das categorias válidas."
                )
    
    # Atualiza a categoria da despesa
    despesa_model.atualizar(ultima_despesa['id'], categoria=nova_categoria)
    
    # Obtém emoji para a nova categoria
    processador = TextProcessor()
    emoji = processador.get_categoria_emoji(nova_categoria)
    
    return (
        f"✅ Categoria atualizada com sucesso!\n\n"
        f"Despesa: {ultima_despesa['descricao']}\n"
        f"Valor: R$ {ultima_despesa['valor']:.2f}\n"
        f"Categoria antiga: {categoria_antiga.capitalize()}\n"
        f"Nova categoria: {emoji} {nova_categoria.capitalize()}"
    )

def processar_despesa(mensagem, usuario_id):
    """Processa uma mensagem de texto para extrair e salvar uma despesa"""
    # Extrai informações da despesa
    processador = TextProcessor()
    dados_despesa = processador.extrair_informacoes_despesa(mensagem)
    
    if not dados_despesa or not dados_despesa["valor"]:
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
        emoji = processador.get_categoria_emoji(dados_despesa["categoria"])
        
        # Formata a resposta
        resposta = (
            f"✅ Despesa registrada!\n\n"
            f"💰 Valor: R$ {dados_despesa['valor']:.2f}\n"
            f"🏷️ Categoria: {emoji} {dados_despesa['categoria'].capitalize()}\n"
            f"📅 Data: {datetime.strptime(dados_despesa['data'], '%Y-%m-%d').strftime('%d/%m/%Y')}\n"
        )
        
        if dados_despesa.get("forma_pagamento"):
            resposta += f"💳 Forma de pagamento: {dados_despesa['forma_pagamento']}\n"
        
        # Adiciona instruções para corrigir a categoria se necessário
        resposta += f"\nSe a categoria estiver incorreta, envie:\n\"corrigir categoria para [categoria]\"\n\n"
        resposta += f"Acesse {Config.WEBHOOK_BASE_URL}/dashboard para visualizar seus gastos detalhados!"
        
        return resposta
        
    except Exception as e:
        # Log do erro
        print(f"Erro ao salvar despesa: {e}")
        return f"Erro ao salvar despesa: {str(e)}"