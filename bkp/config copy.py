import os

class Config:
    # Configurações básicas do Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'chave_secreta_de_desenvolvimento')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True') == 'True'
    
    # Configurações de servidor
    HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
    PORT = int(os.environ.get('FLASK_PORT', 8080))
    
    # Banco de dados
    DATABASE = os.environ.get('DATABASE_PATH', 'database/financas.db')
    
    # Configurações da Twilio
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', 'AC44f80c30e4bb518bd8c4a0e48ce0e5cb')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', 'cd4ee54cc121bc56cbe4e0b50b71c426')
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', 'whatsapp:+12083468766')
    
    # Configurações da aplicação
    APP_NAME = 'DespeZap'
    APP_DESCRIPTION = 'Controle financeiro fácil via WhatsApp'
    
    # URL base para o webhook (em produção)
    # Esta URL é usada para gerar o QR code e instruções de conexão
    WEBHOOK_BASE_URL = os.environ.get('WEBHOOK_BASE_URL', 'http://localhost:5000')
    
    # Código de ativação do WhatsApp Sandbox
    WHATSAPP_JOIN_CODE = os.environ.get('WHATSAPP_JOIN_CODE', 'join successful-angle')
    WHATSAPP_NUMBER = os.environ.get('WHATSAPP_NUMBER', '+1 415 523 8886')
    
    # Configurações de upload
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'static/uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Configurações de email (para recuperação de senha)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', '')
    
    # Configurações de segurança
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False') == 'True'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Configurações de cache (Redis, se disponível)
    REDIS_URL = os.environ.get('REDIS_URL', None)
    CACHE_TYPE = 'simple'  # ou 'redis' se Redis estiver configurado
    
    # Configurações de logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/app.log')
    
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
    
    # Configurações de pagamento (Stripe, PagSeguro, etc.)
    STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY', '')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
    PAGSEGURO_EMAIL = os.environ.get('PAGSEGURO_EMAIL', '')
    PAGSEGURO_TOKEN = os.environ.get('PAGSEGURO_TOKEN', '')
    
    # Configurações de APIs externas
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
    
    # Configurações de timezone
    TIMEZONE = os.environ.get('TIMEZONE', 'America/Sao_Paulo')
    
    # Configurações de rate limiting
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')
    
    # Configurações de backup
    BACKUP_INTERVAL_HOURS = int(os.environ.get('BACKUP_INTERVAL_HOURS', 24))
    BACKUP_RETENTION_DAYS = int(os.environ.get('BACKUP_RETENTION_DAYS', 30))
    
    # Configurações de desenvolvimento
    TESTING = os.environ.get('TESTING', 'False') == 'True'
    WTF_CSRF_ENABLED = os.environ.get('WTF_CSRF_ENABLED', 'True') == 'True'
    
    @classmethod
    def get_plano_config(cls, plano_nome):
        """Retorna configurações do plano especificado"""
        planos = {
            'gratuito': cls.PLANO_GRATUITO,
            'premium': cls.PLANO_PREMIUM,
            'familia': cls.PLANO_FAMILIA,
            'empresarial': cls.PLANO_EMPRESARIAL
        }
        return planos.get(plano_nome.lower(), cls.PLANO_GRATUITO)
    
    @classmethod
    def init_app(cls, app):
        """Inicializa configurações específicas da aplicação"""
        # Cria diretórios necessários
        import os
        os.makedirs('logs', exist_ok=True)
        os.makedirs('database', exist_ok=True)
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
        
        # Configura logging
        if not app.debug and not app.testing:
            import logging
            from logging.handlers import RotatingFileHandler
            
            file_handler = RotatingFileHandler(
                cls.LOG_FILE, 
                maxBytes=10240000, 
                backupCount=10
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(getattr(logging, cls.LOG_LEVEL))
            app.logger.addHandler(file_handler)
            app.logger.setLevel(getattr(logging, cls.LOG_LEVEL))
            app.logger.info('Aplicação iniciada')

class DevelopmentConfig(Config):
    """Configurações específicas para desenvolvimento"""
    DEBUG = True
    TESTING = False
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    """Configurações específicas para produção"""
    DEBUG = False
    TESTING = False
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_SECURE = True
    
    # Em produção, certifique-se de definir essas variáveis de ambiente
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Log para syslog em produção
        import logging
        from logging.handlers import SysLogHandler
        syslog_handler = SysLogHandler()
        syslog_handler.setLevel(logging.WARNING)
        app.logger.addHandler(syslog_handler)

class TestingConfig(Config):
    """Configurações para testes"""
    TESTING = True
    WTF_CSRF_ENABLED = False
    DATABASE = ':memory:'  # SQLite em memória para testes

# Dicionário de configurações disponíveis
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}