import os
from flask import Flask
from config import Config
from database.models import init_db
from rotas.web_rotas import web_bp
from rotas.api_rotas import api_bp
from rotas.webhook_rotas import webhook_bp

# Criação do aplicativo Flask
app = Flask(__name__)
app.config.from_object(Config)

# Inicializa o banco de dados
init_db(app.config['DATABASE'])

# Registra os blueprints
app.register_blueprint(web_bp)
app.register_blueprint(api_bp, url_prefix='/api')
app.register_blueprint(webhook_bp)

# Execução do aplicativo
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])