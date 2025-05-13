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
        'limite_transacoes': 100,  # 100 transações/mês
        'dashboard': 'básico',
        'categorias': 'limitadas (8)',
        'usuarios': 1,
        'perfil_empresarial': False,
        'exportacao_dados': False,
        'lembretes_automaticos': False,
        'relatorios_detalhados': False,
        'suporte': 'E-mail'
    }

    PLANO_PREMIUM = {
        'nome': 'Premium',
        'preco': 29.90,
        'limite_transacoes': float('inf'),  # Transações ilimitadas
        'dashboard': 'completo',
        'categorias': 'personalizadas e ilimitadas',
        'usuarios': 3,
        'perfil_empresarial': False,
        'exportacao_dados': 'CSV',
        'lembretes_automaticos': True,
        'relatorios_detalhados': True,
        'suporte': 'Chat/E-mail'
    }

    PLANO_FAMILIA = {
        'nome': 'Família',
        'preco': 32.90,
        'limite_transacoes': float('inf'),  # Transações ilimitadas
        'dashboard': 'completo',
        'categorias': 'personalizadas e ilimitadas',
        'usuarios': 5,
        'perfil_empresarial': True,
        'grupos': 'familiares ilimitados',
        'exportacao_dados': 'CSV/Excel',
        'lembretes_automaticos': True,
        'relatorios_detalhados': True,
        'integracao_google': True,
        'suporte': 'Chat/E-mail'
    }

    PLANO_EMPRESARIAL = {
        'nome': 'Empresarial',
        'preco': 39.90,
        'limite_transacoes': float('inf'),  # Transações ilimitadas
        'dashboard': 'completo',
        'categorias': 'personalizadas e ilimitadas',
        'usuarios': float('inf'),  # Usuários ilimitados
        'perfil_empresarial': True,
        'grupos': 'ilimitados',
        'exportacao_dados': 'todos os formatos',
        'lembretes_automaticos': True,
        'relatorios_detalhados': True,
        'api_integracao': True,
        'integracao_google': True,
        'suporte': 'prioritário'
    }
    
    # URL base para o webhook (em produção)
    # Esta URL é usada para gerar o QR code e instruções de conexão
    WEBHOOK_BASE_URL = os.environ.get('WEBHOOK_BASE_URL', 'http://localhost:8080')
    
    # Código de ativação do WhatsApp Sandbox
    WHATSAPP_JOIN_CODE = os.environ.get('WHATSAPP_JOIN_CODE', 'join successful-angle')
    WHATSAPP_NUMBER = os.environ.get('WHATSAPP_NUMBER', '+1 415 523 8886')