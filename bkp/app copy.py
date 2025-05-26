from flask import Flask, render_template
from config import Config
import os

def create_app():
    """Factory function para criar a aplicação Flask"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Configurações da sessão
    app.secret_key = Config.SECRET_KEY
    
    # Registra a rota principal DENTRO da factory function
    register_main_rotas(app)
    
    # Registra todos os blueprints
    register_blueprints(app)
    
    # Handlers de erro
    register_error_handlers(app)
    
    # Comandos CLI
    register_cli_commands(app)
    
    return app

def register_main_rotas(app):
    """Registra as rotas principais da aplicação"""
    
    @app.route('/')
    def index():
        """Página inicial"""
        from flask import session, redirect, url_for
        
        # Se já estiver logado, redireciona para o dashboard
        if 'usuario_id' in session:
            return redirect(url_for('dashboard.html'))
        
        # Dados para a página inicial
        return render_template(
            'index.html',
            app_name=Config.APP_NAME,
            whatsapp_code=getattr(Config, 'WHATSAPP_JOIN_CODE', ''),
            whatsapp_number=getattr(Config, 'WHATSAPP_NUMBER', '')
        )

def register_blueprints(app):
    """Registra todos os blueprints da aplicação"""
    
    # Rotas de autenticação
    from rotas.auth import auth_bp
    app.register_blueprint(auth_bp)
    
    # Dashboard principal
    from rotas.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)
    
    # Módulos funcionais
    from rotas.lembretes import lembretes_bp
    app.register_blueprint(lembretes_bp)
    
    from rotas.despesas import despesas_bp
    app.register_blueprint(despesas_bp)
    
    from rotas.receitas import receitas_bp
    app.register_blueprint(receitas_bp)
    
    from rotas.dividas import dividas_bp
    app.register_blueprint(dividas_bp)
    
    from rotas.categorias import categorias_bp
    app.register_blueprint(categorias_bp)
    
    from rotas.membros import membros_bp
    app.register_blueprint(membros_bp)
    
    from rotas.relatorios import relatorios_bp
    app.register_blueprint(relatorios_bp)
    
    from rotas.planos import planos_bp
    app.register_blueprint(planos_bp)
    
    # Webhooks centralizados
    from bkp.webhooks import webhook_bp
    app.register_blueprint(webhook_bp)
    
    # Upload de arquivos
    from rotas.uploads import uploads_bp
    app.register_blueprint(uploads_bp)

    from rotas.perfil import perfil_bp
    app.register_blueprint(perfil_bp)


def register_error_handlers(app):
    """Registra handlers de erro"""
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

def register_cli_commands(app):
    """Registra comandos CLI personalizados"""
    
    @app.cli.command()
    def init_db():
        """Inicializa o banco de dados"""
        from database.models import inicializar_banco
        inicializar_banco(Config.DATABASE)
        print("Banco de dados inicializado com sucesso!")
    
    @app.cli.command()
    def send_reminders():
        """Envia lembretes via WhatsApp"""
        from rotas.lembretes import enviar_notificacoes_lembretes
        count = enviar_notificacoes_lembretes()
        print(f"Enviadas {count} notificações de lembretes.")

# Criação da app
app = create_app()

if __name__ == '__main__':
    # Cria o diretório de uploads se não existir
    os.makedirs('static/uploads', exist_ok=True)
    
    # Executa a aplicação
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )