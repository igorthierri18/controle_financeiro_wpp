from flask import Blueprint, request, url_for
from twilio.twiml.messaging_response import MessagingResponse
from database.models import Usuario, Despesa, Receita, TextProcessor
from config import Config
from datetime import datetime, timedelta
import re
import requests

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
    
    # Extrai informações da requisição
    mensagem = request.values.get('Body', '').strip()
    remetente = request.values.get('From', '')
    
    # Inicializa a resposta
    resposta = MessagingResponse()
    
    try:
        # Processa a mensagem
        resposta_texto = processar_mensagem(mensagem, remetente)
        resposta.message(resposta_texto)
    except Exception as e:
        # Log do erro para debug
        import traceback
        print(f"ERRO: {e}")
        traceback.print_exc()
        
        # Em caso de erro, envia uma mensagem amigável
        resposta.message(
            f"Ops! Encontramos um problema ao processar sua mensagem. "
            f"Por favor, tente novamente ou envie 'ajuda' para ver os comandos disponíveis."
        )
    
    return str(resposta)

def processar_mensagem(mensagem, remetente):
    """Processa a mensagem recebida e retorna uma resposta"""
    # Remove o prefixo 'whatsapp:' do número do remetente
    if remetente.startswith('whatsapp:'):
        remetente = remetente[9:]
    
    # Obtém ou cria o usuário
    usuario_model = Usuario(Config.DATABASE)
    usuario = usuario_model.buscar_por_celular(remetente)
    
    if not usuario:
        usuario_id = usuario_model.criar(celular=remetente)
    else:
        usuario_id = usuario['id']
    
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
    
    elif "planos" in mensagem_lower or "assinatura" in mensagem_lower or "premium" in mensagem_lower:
        return get_info_planos()
    
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
    plano_gratuito = Config.PLANO_GRATUITO
    plano_premium = Config.PLANO_PREMIUM
    
    return (
        f"💳 *Planos {app_name}*\n\n"
        f"*Plano Gratuito*\n"
        f"- Preço: Grátis\n"
        f"- {plano_gratuito['limite_categorias']} categorias personalizáveis\n"
        f"- {plano_gratuito['limite_relatorios']} tipos de relatórios\n"
        f"- Exportação CSV: {'✓' if plano_gratuito['exportacao_csv'] else '✗'}\n"
        f"- Reconhecimento de imagens: {'✓' if plano_gratuito['reconhecimento_imagem'] else '✗'}\n\n"
        
        f"*Plano Premium*\n"
        f"- Preço: R$ {plano_premium['preco']:.2f}/mês\n"
        f"- {plano_premium['limite_categorias']} categorias personalizáveis\n"
        f"- {plano_premium['limite_relatorios']} tipos de relatórios\n"
        f"- Exportação CSV: {'✓' if plano_premium['exportacao_csv'] else '✗'}\n"
        f"- Reconhecimento de imagens: {'✓' if plano_premium['reconhecimento_imagem'] else '✗'}\n"
        f"- Até {plano_premium['limite_usuarios']} usuários\n\n"
        
        f"Para assinar, acesse:\n"
        f"{Config.WEBHOOK_BASE_URL}/planos"
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
        
        resposta += f"\nAcesse {Config.WEBHOOK_BASE_URL}/dashboard para visualizar seus gastos detalhados!"
        
        return resposta
        
    except Exception as e:
        # Log do erro
        print(f"Erro ao salvar despesa: {e}")
        return f"Erro ao salvar despesa: {str(e)}"