import os

class Config:
    # Configurações básicas
    SECRET_KEY = os.environ.get('SECRET_KEY', 'chave_secreta_de_desenvolvimento')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True') == 'True'
    
    # Banco de dados
    DATABASE = os.environ.get('DATABASE_PATH', 'database/financas.db')
    
    # Configurações da Twilio
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', 'AC44f80c30e4bb518bd8c4a0e48ce0e5cb')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', 'cd4ee54cc121bc56cbe4e0b50b71c426')
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', 'whatsapp:+12083468766')
    
    # Configurações da aplicação
    APP_NAME = 'DespeZap'
    APP_DESCRIPTION = 'Controle financeiro fácil via WhatsApp'
    
    # Configurações de assinatura
    PLANO_GRATUITO = {
    'nome': 'Gratuito',
    'preco': 0,
    'limite_transacoes': 3000,
    'relatorios_detalhados': False,
    'dashboard_interativo': True,
    'exportacao_dados': False,
    'suporte': 'E-mail',
    'limite_usuarios': 1
    }

    PLANO_PREMIUM = {
        'nome': 'Premium',
        'preco': 29.90,
        'limite_transacoes': 20000,
        'relatorios_detalhados': True,
        'dashboard_interativo': True,
        'exportacao_dados': True,
        'suporte': 'Chat/E-mail',
        'limite_usuarios': 2
    }

    PLANO_PROFISSIONAL = {
        'nome': 'Profissional',
        'preco': 59.90,
        'limite_transacoes': float('inf'),  # Ilimitado
        'relatorios_detalhados': True,
        'dashboard_interativo': True,
        'exportacao_dados': True,
        'suporte': 'Prioritário',
        'limite_usuarios': 5
    }

    
    # URL base para o webhook (em produção)
    # Esta URL é usada para gerar o QR code e instruções de conexão
    WEBHOOK_BASE_URL = os.environ.get('WEBHOOK_BASE_URL', 'http://localhost:8080')
    
    # Código de ativação do WhatsApp Sandbox
    WHATSAPP_JOIN_CODE = os.environ.get('WHATSAPP_JOIN_CODE', 'join successful-angle')
    WHATSAPP_NUMBER = os.environ.get('WHATSAPP_NUMBER', '+1 415 523 8886')