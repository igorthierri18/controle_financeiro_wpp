from flask import Blueprint, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator
from database.models import Usuario, TextProcessor
from config import Config
import traceback

webhook_bp = Blueprint('webhook', __name__, url_prefix='/webhook')

@webhook_bp.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    """Webhook centralizado do WhatsApp via Twilio"""
    print("\n===== WEBHOOK RECEBIDO =====")
    print("Headers:", dict(request.headers))
    print("Form data:", dict(request.form))
    print("============================\n")
    
    # Validação da assinatura da Twilio
    validator = RequestValidator(Config.TWILIO_AUTH_TOKEN)
    request_valid = validator.validate(
        request.url,
        request.form,
        request.headers.get('X-Twilio-Signature', '')
    )
    
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
        resposta_texto = processar_mensagem_webhook(mensagem, remetente, profile_name)
        resposta.message(resposta_texto)
    except Exception as e:
        print(f"ERRO: {e}")
        traceback.print_exc()
        
        resposta.message(
            f"Ops! Encontramos um problema ao processar sua mensagem. "
            f"Por favor, tente novamente ou envie 'ajuda' para ver os comandos disponíveis."
        )
    
    return str(resposta)

def processar_mensagem_webhook(mensagem, remetente, profile_name=None):
    """Processa mensagem e redireciona para o módulo apropriado"""
    # Remove o prefixo 'whatsapp:' do número
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
    
    mensagem_lower = mensagem.lower()
    
    # Comandos gerais
    if mensagem_lower in ['oi', 'olá', 'ola', 'hi', 'hello']:
        return get_mensagem_boas_vindas(usuario)
        
    elif mensagem_lower in ['ajuda', 'help', '?']:
        return get_mensagem_ajuda()
    
    # Redireciona para módulos específicos
    from rotas.lembretes import processar_webhook_lembrete
    from rotas.despesas import processar_webhook_despesa
    from rotas.receitas import processar_webhook_receita
    
    # Tenta processar como lembrete
    resposta_lembrete = processar_webhook_lembrete(mensagem, usuario_id)
    if resposta_lembrete:
        return resposta_lembrete
    
    # Tenta processar como receita
    resposta_receita = processar_webhook_receita(mensagem, usuario_id)
    if resposta_receita:
        return resposta_receita
    
    # Se não for nenhum dos anteriores, tenta processar como despesa
    return processar_webhook_despesa(mensagem, usuario_id)

def get_mensagem_boas_vindas(usuario):
    """Retorna mensagem de boas-vindas"""
    if usuario and usuario.get('nome'):
        return (
            f"Olá, {usuario['nome']}! 👋\n\n"
            f"Bem-vindo ao {Config.APP_NAME}!\n\n"
            f"Como posso ajudar hoje?\n\n"
            f"- Descreva uma despesa (ex: \"Almoço R$ 25,90\")\n"
            f"- Digite \"ajuda\" para ver todos os comandos\n"
            f"- Digite \"resumo\" para ver um relatório"
        )
    else:
        return (
            f"Olá! 👋\n\n"
            f"Bem-vindo ao {Config.APP_NAME}!\n\n"
            f"Como posso ajudar hoje?\n\n"
            f"- Descreva uma despesa (ex: \"Almoço R$ 25,90\")\n"
            f"- Digite \"ajuda\" para ver todos os comandos\n"
            f"- Digite \"resumo\" para ver um relatório"
        )

def get_mensagem_ajuda():
    """Retorna mensagem de ajuda"""
    return (
        "🤖 *Assistente de Controle de Gastos*\n\n"
        "Como usar:\n"
        "- 💬 Envie um texto: \"Almoço R$ 25,90\"\n"
        "- 📸 Foto de comprovante (em breve!)\n"
        "- 🎙️ Áudio (em breve!)\n\n"
        "Comandos disponíveis:\n"
        "- \"resumo\": Ver resumo geral\n"
        "- \"hoje\": Gastos de hoje\n"
        "- \"semana\": Relatório da semana\n"
        "- \"mês\": Relatório do mês\n"
        "- \"lembretes\": Ver lembretes pendentes\n"
        "- \"lembrar [texto]\": Criar lembrete\n"
        "- \"planos\": Informações sobre planos\n"
        "- \"ajuda\": Mostra esta mensagem\n\n"
        f"Acesse também: {Config.WEBHOOK_BASE_URL}/"
    )