import os
from dotenv import load_dotenv
import psycopg2
from psycopg2 import sql

load_dotenv()

class Config:
    # Configurações básicas
    SECRET_KEY = os.environ.get('SECRET_KEY', 'chave_secreta_de_desenvolvimento')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True') == 'True'

    # Configurações do Supabase (PostgreSQL)
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_ANON_KEY')
    
    # Configurações do PostgreSQL direto (opcional)
    POSTGRES_USER = os.environ.get('POSTGRES_USER')
    POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD')
    POSTGRES_HOST = os.environ.get('POSTGRES_HOST')
    POSTGRES_PORT = os.environ.get('POSTGRES_PORT', '5432')
    POSTGRES_DB = os.environ.get('POSTGRES_DB', 'postgres')
    
    # Configurações da Twilio (WhatsApp)
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')

    WHATSAPP_JOIN_CODE = os.environ.get('WHATSAPP_JOIN_CODE')
    WHATSAPP_NUMBER = os.environ.get('WHATSAPP_NUMBER')

    WEBHOOK_BASE_URL = os.environ.get('WEBHOOK_BASE_URL', 'http://localhost:8080')

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
    
    @classmethod
    def get_database(cls):
        """Retorna a conexão com o Supabase"""
        from supabase import create_client
        return create_client(cls.SUPABASE_URL, cls.SUPABASE_KEY)

    @classmethod
    def get_postgres_uri(cls):
        """Retorna a URI de conexão direta com o PostgreSQL (se necessário)"""
        if all([cls.POSTGRES_USER, cls.POSTGRES_PASSWORD, cls.POSTGRES_HOST]):
            return f"postgresql://{cls.POSTGRES_USER}:{cls.POSTGRES_PASSWORD}@{cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}/{cls.POSTGRES_DB}"
        return None