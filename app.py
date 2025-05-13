import os
from flask import Flask
from config import Config
# from database.models import init_db
from database.supabase_models import init_supabase_db
from rotas.web_rotas import web_bp
from rotas.api_rotas import api_bp
from rotas.webhook_rotas import webhook_bp
from datetime import datetime, timedelta

# Criação do aplicativo Flask
app = Flask(__name__)
app.config.from_object(Config)

# Inicializa o banco de dados
# init_db(app.config['DATABASE'])
init_supabase_db()

# Registra os blueprints
app.register_blueprint(web_bp)
app.register_blueprint(api_bp, url_prefix='/api')
app.register_blueprint(webhook_bp)

# Registrar filtros personalizados para Jinja2
@app.template_filter('format_date')
def format_date(date_str):
    """Formata uma data para exibição"""
    if not date_str:
        return ''
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%d/%m/%Y')
    except:
        return date_str

@app.template_filter('to_date')
def to_date(date_str):
    """Converte uma string para objeto datetime"""
    if not date_str:
        return datetime.now()
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except:
        return datetime.now()

@app.template_filter('format_currency')
def format_currency(value):
    """Formata um valor monetário"""
    if value is None:
        return 'R$ 0,00'
    return f"R$ {float(value):,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')

# Adicione uma variável global para o template
@app.context_processor
def inject_today():
    return {'today': datetime.now()}

# Execução do aplicativo
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])