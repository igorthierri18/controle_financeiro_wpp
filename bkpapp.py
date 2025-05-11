import os
import io
import re
import cv2
import json
import wave
import numpy as np
import sqlite3
import tempfile
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import pandas as pd
import plotly
import plotly.express as px

# Configuração para o reconhecimento óptico de caracteres, se disponível
try:
    import pytesseract
    # Configuração do pytesseract para Windows (descomente se necessário)
    # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    OCR_AVAILABLE = True
except ImportError:
    print("Aviso: pytesseract não está instalado. O reconhecimento de comprovantes por imagem terá funcionalidade limitada.")
    OCR_AVAILABLE = False

# Configuração para reconhecimento de voz, se disponível
try:
    from vosk import Model, KaldiRecognizer
    VOSK_AVAILABLE = True
except ImportError:
    print("Aviso: vosk não está instalado. O reconhecimento de áudio terá funcionalidade limitada.")
    VOSK_AVAILABLE = False

# Inicialização do aplicativo Flask
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'chave_secreta_de_desenvolvimento')

# Configurações
DATABASE_PATH = os.environ.get('DATABASE_PATH', 'expenses.db')
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', 'AC44f80c30e4bb518bd8c4a0e48ce0e5cb')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')  # Substitua pelo seu token
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', 'whatsapp:+14155238886')
VOSK_MODEL_PATH = os.environ.get('VOSK_MODEL_PATH', 'vosk-model-pt')

# Inicializa o cliente Twilio
try:
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    print("Cliente Twilio inicializado com sucesso.")
except Exception as e:
    print(f"Erro ao inicializar o cliente Twilio: {e}")
    twilio_client = None

# Estados de conversa do usuário (para manter contexto no WhatsApp)
user_states = {}

# Categorias comuns de despesas
EXPENSE_CATEGORIES = [
    "alimentação", "mercado", "restaurante", "lanchonete", "padaria", "café",
    "transporte", "uber", "táxi", "ônibus", "metrô", "combustível", "estacionamento",
    "moradia", "aluguel", "condomínio", "luz", "água", "gás", "internet",
    "lazer", "cinema", "show", "viagem", "festa", "bar", "streaming",
    "saúde", "farmácia", "remédio", "consulta", "exame", "academia",
    "educação", "curso", "livro", "escola", "faculdade",
    "vestuário", "roupa", "calçado", "acessório",
    "outros"
]

# Padrões de análise de texto para mensagens WhatsApp
CHAT_PATTERNS = {
    'greeting': r'\b(oi|olá|ola|e aí|eai|hey|hi|hello)\b',
    'help': r'\b(ajuda|help|socorro|instrução|instruções|comando|comandos)\b',
    'summary': r'\b(resumo|relatório|relatorio|report|summary|balanço|balanco)\b',
    'period': {
        'day': r'\b(hoje|day|dia)\b',
        'week': r'\b(semana|week|semanal)\b',
        'month': r'\b(mês|mes|month|mensal)\b',
        'year': r'\b(ano|year|anual)\b'
    }
}

#############################################################
# CLASSE DE RECONHECIMENTO DE COMPROVANTES EM IMAGENS       #
#############################################################

class ReceiptRecognizer:
    """Classe para reconhecer e extrair informações de comprovantes de compra"""
    
    def __init__(self):
        # Padrões de expressões regulares para extrair informações
        self.patterns = {
            'valor': [
                r'R\$\s*(\d+[.,]\d{2})',
                r'VALOR\s*(?:TOTAL|FINAL)?:?\s*R?\$?\s*(\d+[.,]\d{2})',
                r'TOTAL:?\s*R?\$?\s*(\d+[.,]\d{2})',
                r'(?:DÉBITO|DEBITO|CRÉDITO|CREDITO|DINHEIRO).*?(\d+[.,]\d{2})',
            ],
            'estabelecimento': [
                r'ESTABELECIMENTO:?\s*(.+?)(?:\n|$)',
                r'NOME:?\s*(.+?)(?:\n|$)',
                r'(?:MERCADO|SUPERMERCADO|LOJA|FARMÁCIA|FARMACIA|RESTAURANTE|POSTO)[\s:]([^,\n]+)',
            ],
            'data': [
                r'DATA:?\s*(\d{2}/\d{2}/\d{2,4})',
                r'(\d{2}/\d{2}/\d{2,4})',
                r'DATA:?\s*(\d{2}\.\d{2}\.\d{2,4})',
                r'(\d{2}\.\d{2}\.\d{2,4})',
            ],
            'pagamento': [
                r'(DÉBITO|DEBITO|CRÉDITO|CREDITO|DINHEIRO|PIX)',
                r'FORMA\s*(?:DE)?\s*PAGAMENTO:?\s*(DÉBITO|DEBITO|CRÉDITO|CREDITO|DINHEIRO|PIX)',
            ]
        }

    def download_image(self, url: str) -> Optional[str]:
        """Baixa uma imagem de uma URL"""
        try:
            response = requests.get(url)
            if response.status_code == 200:
                # Cria um arquivo temporário
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                temp_file.write(response.content)
                temp_file.close()
                return temp_file.name
            else:
                print(f"Erro ao baixar a imagem. Status code: {response.status_code}")
                return None
        except Exception as e:
            print(f"Erro ao baixar a imagem: {e}")
            return None

    def preprocess_image(self, image_path: str) -> np.ndarray:
        """Pré-processa a imagem para melhorar o OCR"""
        if not OCR_AVAILABLE:
            return None
            
        # Carrega a imagem
        image = cv2.imread(image_path)
        
        # Converte para escala de cinza
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Aplica threshold adaptativo para lidar com diferentes condições de iluminação
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Redimensiona a imagem para melhorar o OCR (melhor desempenho em imagens maiores)
        scale_percent = 200  # aumenta em 200%
        width = int(thresh.shape[1] * scale_percent / 100)
        height = int(thresh.shape[0] * scale_percent / 100)
        dim = (width, height)
        resized = cv2.resize(thresh, dim, interpolation=cv2.INTER_CUBIC)
        
        return resized

    def extract_text(self, image_path: str) -> str:
        """Extrai texto da imagem usando OCR"""
        if not OCR_AVAILABLE:
            return "OCR não disponível. Instale pytesseract."
            
        try:
            # Pré-processa a imagem
            processed_image = self.preprocess_image(image_path)
            
            # Extrai o texto usando pytesseract (configuração para recibos em português)
            text = pytesseract.image_to_string(
                processed_image, 
                lang='por',  # Português
                config='--oem 3 --psm 6'  # Configuração para texto em bloco
            )
            
            return text
        except Exception as e:
            print(f"Erro ao extrair texto: {e}")
            return ""
        finally:
            # Remove o arquivo temporário se ele existir e for uma imagem baixada
            if os.path.exists(image_path) and 'temp' in image_path:
                try:
                    os.remove(image_path)
                    print(f"Arquivo temporário removido: {image_path}")
                except:
                    pass

    def find_pattern(self, text: str, patterns: list) -> Optional[str]:
        """Procura por um padrão no texto"""
        for pattern in patterns:
            matches = re.search(pattern, text, re.IGNORECASE)
            if matches:
                return matches.group(1).strip()
        return None

    def extract_receipt_info(self, image_url: str) -> Dict[str, Any]:
        """Extrai informações de um comprovante de compra"""
        # Baixa a imagem se for uma URL, ou usa o caminho local
        if image_url.startswith(('http://', 'https://')):
            image_path = self.download_image(image_url)
            if not image_path:
                return {
                    "success": False,
                    "message": "Não foi possível baixar a imagem."
                }
        else:
            image_path = image_url
            
        if not OCR_AVAILABLE:
            return {
                "success": False,
                "message": "OCR não disponível. Instale pytesseract para reconhecimento de imagens."
            }

        # Extrai o texto da imagem
        text = self.extract_text(image_path)
        
        # Se não conseguiu extrair texto suficiente
        if len(text) < 10:
            return {
                "success": False,
                "message": "Não foi possível extrair texto suficiente da imagem."
            }
        
        # Procura por informações específicas
        valor = self.find_pattern(text, self.patterns['valor'])
        estabelecimento = self.find_pattern(text, self.patterns['estabelecimento'])
        data = self.find_pattern(text, self.patterns['data'])
        pagamento = self.find_pattern(text, self.patterns['pagamento'])
        
        # Processa o valor para formato numérico
        amount = None
        if valor:
            try:
                amount = float(valor.replace('.', '').replace(',', '.'))
            except ValueError:
                amount = None
        
        # Processa a data
        date = None
        if data:
            try:
                # Tenta vários formatos de data
                if '/' in data:
                    parts = data.split('/')
                elif '.' in data:
                    parts = data.split('.')
                else:
                    parts = []
                
                if len(parts) == 3:
                    day, month, year = parts
                    if len(year) == 2:
                        year = f"20{year}"
                    date = f"{year}-{month}-{day}"
            except Exception:
                date = datetime.now().strftime("%Y-%m-%d")
        
        # Categoriza com base no estabelecimento
        category = self.categorize_expense(estabelecimento, text)
        
        # Formata o nome do estabelecimento
        if estabelecimento:
            # Limita o tamanho e normaliza
            estabelecimento = estabelecimento[:50].title()
        
        # Determina o tipo de pagamento
        payment_type = "Débito"  # Padrão
        if pagamento:
            payment_type = pagamento.title()
        
        return {
            "success": True,
            "amount": amount,
            "description": estabelecimento if estabelecimento else "Compra",
            "date": date if date else datetime.now().strftime("%Y-%m-%d"),
            "category": category,
            "payment_type": payment_type,
            "raw_text": text,
        }
    
    def categorize_expense(self, establishment: Optional[str], text: str) -> str:
        """Categoriza a despesa com base no estabelecimento e no texto"""
        # Texto para análise (combina estabelecimento e texto completo)
        analysis_text = (establishment or "") + " " + text
        analysis_text = analysis_text.lower()
        
        # Lista de palavras-chave por categoria
        categories = {
            "alimentação": ["mercado", "supermercado", "alimento", "comida", "restaurante", "lanchonete", 
                           "padaria", "açougue", "hortifruti", "ifood", "delivery", "marmita"],
            "transporte": ["uber", "taxi", "99", "combustível", "gasolina", "etanol", "alcool", "posto", 
                          "estacionamento", "pedágio", "metrô", "ônibus", "passagem"],
            "moradia": ["aluguel", "condomínio", "água", "luz", "gás", "internet", "telefone", "iptu", 
                       "reforma", "manutenção"],
            "saúde": ["farmácia", "drogaria", "remédio", "consulta", "exame", "médico", "dentista", 
                     "plano de saúde", "academia", "natação"],
            "educação": ["escola", "faculdade", "curso", "livro", "material", "mensalidade"],
            "lazer": ["cinema", "teatro", "show", "streaming", "netflix", "spotify", "viagem", 
                     "hotel", "passeio", "bar", "bebida"],
            "vestuário": ["roupa", "calçado", "sapato", "tênis", "acessório", "bolsa"],
        }
        
        # Verifica cada categoria
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in analysis_text:
                    return category
        
        # Categoria padrão se nenhuma for identificada
        return "outros"

#############################################################
# FUNÇÕES PARA BANCO DE DADOS                               #
#############################################################

def setup_database():
    """Configura o banco de dados se ele não existir"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Cria a tabela de despesas
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        category TEXT,
        description TEXT,
        date TEXT,
        payment_method TEXT,
        created_at TEXT,
        original_message TEXT
    )
    ''')
    
    # Cria a tabela de receitas
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS incomes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        category TEXT,
        description TEXT,
        date TEXT,
        created_at TEXT
    )
    ''')
    
    # Cria a tabela de usuários
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone_number TEXT UNIQUE,
        name TEXT,
        email TEXT,
        created_at TEXT
    )
    ''')
    
    conn.commit()
    conn.close()
    
    print(f"Banco de dados inicializado em {DATABASE_PATH}")

def get_or_create_user(phone_number):
    """Obtém ou cria um usuário com base no número de telefone"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Verifica se o usuário existe
    cursor.execute("SELECT id FROM users WHERE phone_number = ?", (phone_number,))
    user = cursor.fetchone()
    
    if user:
        user_id = user[0]
    else:
        # Cria um novo usuário
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO users (phone_number, created_at) VALUES (?, ?)",
            (phone_number, created_at)
        )
        conn.commit()
        user_id = cursor.lastrowid
    
    conn.close()
    return user_id

def save_expense(user_id, amount, category=None, description=None, date=None, payment_method=None, original_message=None):
    """Salva uma despesa no banco de dados"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Define valores padrão se necessário
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    if description is None:
        description = "Despesa sem descrição"
    
    if category is None:
        category = "outros"
    
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Insere a despesa
    cursor.execute('''
    INSERT INTO expenses 
    (user_id, amount, category, description, date, payment_method, created_at, original_message)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, amount, category, description, date, payment_method, created_at, original_message))
    
    conn.commit()
    expense_id = cursor.lastrowid
    conn.close()
    
    return expense_id

def save_income(user_id, amount, category, description, date):
    """Salva uma receita no banco de dados"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Insere a receita
    cursor.execute('''
    INSERT INTO incomes 
    (user_id, amount, category, description, date, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, amount, category, description, date, created_at))
    
    conn.commit()
    income_id = cursor.lastrowid
    conn.close()
    
    return income_id

def get_user_expenses(user_id, start_date=None, end_date=None):
    """Obtém as despesas de um usuário"""
    conn = sqlite3.connect(DATABASE_PATH)
    
    # Parâmetros da consulta
    params = [user_id]
    sql = "SELECT * FROM expenses WHERE user_id = ?"
    
    if start_date:
        sql += " AND date >= ?"
        params.append(start_date)
    
    if end_date:
        sql += " AND date <= ?"
        params.append(end_date)
    
    sql += " ORDER BY date DESC"
    
    # Executa a consulta
    df = pd.read_sql_query(
        sql,
        conn,
        params=tuple(params)
    )
    
    conn.close()
    return df

def get_user_incomes(user_id, start_date=None, end_date=None):
    """Obtém as receitas de um usuário"""
    conn = sqlite3.connect(DATABASE_PATH)
    
    # Parâmetros da consulta
    params = [user_id]
    sql = "SELECT * FROM incomes WHERE user_id = ?"
    
    if start_date:
        sql += " AND date >= ?"
        params.append(start_date)
    
    if end_date:
        sql += " AND date <= ?"
        params.append(end_date)
    
    sql += " ORDER BY date DESC"
    
    # Executa a consulta
    df = pd.read_sql_query(
        sql,
        conn,
        params=tuple(params)
    )
    
    conn.close()
    return df

def get_expenses_by_category(user_id, start_date=None, end_date=None):
    """Obtém os gastos por categoria"""
    conn = sqlite3.connect(DATABASE_PATH)
    
    # Parâmetros da consulta
    params = [user_id]
    sql = """
    SELECT category, SUM(amount) as total 
    FROM expenses 
    WHERE user_id = ?
    """
    
    if start_date:
        sql += " AND date >= ?"
        params.append(start_date)
    
    if end_date:
        sql += " AND date <= ?"
        params.append(end_date)
    
    sql += " GROUP BY category ORDER BY total DESC"
    
    # Executa a consulta
    df = pd.read_sql_query(
        sql,
        conn,
        params=tuple(params)
    )
    
    conn.close()
    return df

def get_total_expenses(user_id, start_date=None, end_date=None):
    """Obtém o total de despesas de um usuário"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Parâmetros da consulta
    params = [user_id]
    sql = "SELECT SUM(amount) FROM expenses WHERE user_id = ?"
    
    if start_date:
        sql += " AND date >= ?"
        params.append(start_date)
    
    if end_date:
        sql += " AND date <= ?"
        params.append(end_date)
    
    # Executa a consulta
    cursor.execute(sql, tuple(params))
    result = cursor.fetchone()[0]
    
    conn.close()
    return result if result else 0

def get_total_incomes(user_id, start_date=None, end_date=None):
    """Obtém o total de receitas de um usuário"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Parâmetros da consulta
    params = [user_id]
    sql = "SELECT SUM(amount) FROM incomes WHERE user_id = ?"
    
    if start_date:
        sql += " AND date >= ?"
        params.append(start_date)
    
    if end_date:
        sql += " AND date <= ?"
        params.append(end_date)
    
    # Executa a consulta
    cursor.execute(sql, tuple(params))
    result = cursor.fetchone()[0]
    
    conn.close()
    return result if result else 0

#############################################################
# FUNÇÕES PARA PROCESSAMENTO DE MENSAGENS E ÁUDIO           #
#############################################################

def extract_expense_from_text(text):
    """Extrai informações de despesa de um texto usando regex"""
    # Inicializa os dados de despesa
    expense_data = {
        "amount": None,
        "category": None,
        "description": text,
        "date": datetime.now().strftime("%Y-%m-%d")
    }
    
    # Converte para minúsculas para facilitar a busca
    text_lower = text.lower()
    
    # Extrai o valor monetário usando expressões regulares
    # Procura por padrões como: 50 reais, R$ 50, 50,90, etc.
    amount_patterns = [
        r'r\$\s*(\d+[.,]?\d*)',  # R$ 50 ou R$50 ou R$ 50,90
        r'(\d+[.,]?\d*)\s*(?:reais|real)',  # 50 reais ou 50,90 reais
        r'(\d+[.,]?\d*)',  # Só um número (50 ou 50,90)
    ]
    
    for pattern in amount_patterns:
        matches = re.findall(pattern, text_lower)
        if matches:
            # Pega o primeiro match e converte para float
            try:
                amount_str = matches[0].replace(',', '.')
                expense_data["amount"] = float(amount_str)
                break
            except (ValueError, IndexError):
                continue
    
    # Se não encontrou valor, retorna None
    if expense_data["amount"] is None:
        return None
    
    # Extrai categoria comparando palavras do texto com lista de categorias
    words = re.findall(r'\b\w+\b', text_lower)
    for word in words:
        if word in EXPENSE_CATEGORIES:
            expense_data["category"] = word
            break
    
    # Se não encontrou categoria, tenta encontrar uma categoria que esteja no texto
    if expense_data["category"] is None:
        for category in EXPENSE_CATEGORIES:
            if category in text_lower:
                expense_data["category"] = category
                break
    
    # Se ainda não tem categoria, usa "outros"
    if expense_data["category"] is None:
        expense_data["category"] = "outros"
    
    # Tenta extrair uma data (simplificado - pode melhorar com bibliotecas como dateparser)
    date_patterns = [
        r'(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?',  # 10/05 ou 10/05/2023
        r'(?:hoje|ontem|amanhã)'  # hoje, ontem, amanhã
    ]
    
    for pattern in date_patterns:
        matches = re.findall(pattern, text_lower)
        if matches and isinstance(matches[0], tuple) and len(matches[0]) >= 2:
            try:
                # Se encontrou uma data completa (dia/mês/ano)
                day, month, year = matches[0]
                if not year:
                    year = datetime.now().year
                elif len(year) == 2:
                    year = f"20{year}"
                
                date_obj = datetime(int(year), int(month), int(day))
                expense_data["date"] = date_obj.strftime("%Y-%m-%d")
                break
            except (ValueError, IndexError):
                continue
        elif matches and isinstance(matches[0], str):
            if matches[0] == 'hoje':
                expense_data["date"] = datetime.now().strftime("%Y-%m-%d")
                break
            elif matches[0] == 'ontem':
                yesterday = datetime.now() - timedelta(days=1)
                expense_data["date"] = yesterday.strftime("%Y-%m-%d")
                break
    
    return expense_data

def categorize_expense(text):
    """Categoriza a despesa com base no texto"""
    # Lista de palavras-chave por categoria
    categories = {
        "alimentação": ["mercado", "supermercado", "alimento", "comida", "restaurante", "lanchonete", 
                       "padaria", "açougue", "hortifruti", "ifood", "delivery", "marmita"],
        "transporte": ["uber", "taxi", "99", "combustível", "gasolina", "etanol", "alcool", "posto", 
                      "estacionamento", "pedágio", "metrô", "ônibus", "passagem"],
        "moradia": ["aluguel", "condomínio", "água", "luz", "gás", "internet", "telefone", "iptu", 
                   "reforma", "manutenção"],
        "saúde": ["farmácia", "drogaria", "remédio", "consulta", "exame", "médico", "dentista", 
                 "plano de saúde", "academia", "natação"],
        "educação": ["escola", "faculdade", "curso", "livro", "material", "mensalidade"],
        "lazer": ["cinema", "teatro", "show", "streaming", "netflix", "spotify", "viagem", 
                 "hotel", "passeio", "bar", "bebida"],
        "vestuário": ["roupa", "calçado", "sapato", "tênis", "acessório", "bolsa"],
    }
    
    text_lower = text.lower()
    
    # Verifica cada categoria
    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword in text_lower:
                return category
    
    # Categoria padrão se nenhuma for identificada
    return "outros"

def download_audio_from_url(url):
    """Baixa um arquivo de áudio de uma URL"""
    try:
        response = requests.get(url)
        if response.status_code == 200:
            # Cria um arquivo temporário
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            temp_file.write(response.content)
            temp_file.close()
            return temp_file.name
        else:
            print(f"Erro ao baixar o áudio. Status code: {response.status_code}")
            return None
    except Exception as e:
        print(f"Erro ao baixar o áudio: {e}")
        return None

def transcribe_audio(audio_file_path):
    """Transcreve um arquivo de áudio para texto usando Vosk"""
    if not VOSK_AVAILABLE:
        return "Biblioteca Vosk não instalada. A transcrição de áudio não está disponível."
    
    try:
        # Verifica se o modelo está disponível
        model_path = VOSK_MODEL_PATH
        if not os.path.exists(model_path):
            error_msg = f"Modelo Vosk não encontrado em {model_path}."
            print(error_msg)
            print("Baixe o modelo em: https://alphacephei.com/vosk/models")
            return f"{error_msg} Baixe o modelo e configure VOSK_MODEL_PATH."
        
        # Converte MP3 para WAV (Vosk precisa de WAV)
        wav_file_path = audio_file_path.replace('.mp3', '.wav')
        try:
            # Usando ffmpeg se disponível
            import subprocess
            print("Convertendo áudio com ffmpeg...")
            subprocess.run(['ffmpeg', '-i', audio_file_path, wav_file_path], check=True)
            print("Conversão concluída.")
        except:
            # Fallback para pydub se ffmpeg não estiver disponível
            try:
                print("Tentando converter com pydub...")
                from pydub import AudioSegment
                audio = AudioSegment.from_mp3(audio_file_path)
                audio.export(wav_file_path, format="wav")
                print("Conversão com pydub concluída.")
            except Exception as e:
                error_msg = f"Erro ao converter áudio: {e}"
                print(error_msg)
                return f"{error_msg}. Instale ffmpeg ou pydub."
        
        # Carrega o modelo
        model = Model(model_path)
        
        # Abre o arquivo de áudio
        wf = wave.open(wav_file_path, "rb")
        
        # Cria o reconhecedor
        rec = KaldiRecognizer(model, wf.getframerate())
        rec.SetWords(True)
        
        # Processa o áudio em chunks
        result = ""
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                result += json.loads(rec.Result())["text"] + " "
        
        # Obtém o resultado final
        final_result = json.loads(rec.FinalResult())
        result += final_result["text"]
        
        # Limpa os arquivos temporários
        try:
            os.remove(wav_file_path)
        except:
            pass
        
        return result.strip()
    except Exception as e:
        print(f"Erro ao transcrever áudio: {e}")
        return None
    finally:
        # Remove o arquivo temporário MP3
        try:
            os.remove(audio_file_path)
        except:
            pass

def get_expense_report(user_id, period="month"):
    """Gera um relatório de despesas para o usuário"""
    # Define o filtro de data
    today = datetime.now()
    
    if period == "day":
        period_str = "hoje"
        start_date = today.strftime("%Y-%m-%d")
    elif period == "week":
        period_str = "na última semana"
        start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    elif period == "month":
        period_str = "neste mês"
        start_date = f"{today.year}-{today.month:02d}-01"
    elif period == "year":
        period_str = "neste ano"
        start_date = f"{today.year}-01-01"
    else:  # all
        period_str = "em todos os tempos"
        start_date = "2000-01-01"  # Data bem antiga para pegar tudo
    
    # Obtém as despesas
    df_expenses = get_user_expenses(user_id, start_date)
    
    if df_expenses.empty:
        return f"📊 Não há despesas registradas {period_str}."
    
    # Calcula totais
    total = df_expenses['amount'].sum()
    by_category = df_expenses.groupby('category')['amount'].sum().sort_values(ascending=False)
    
    # Cria uma mensagem com o relatório e emojis
    report = f"📊 *Relatório de despesas {period_str}*\n\n"
    report += f"💰 Total gasto: *R$ {total:.2f}*\n\n"
    report += "🔍 *Detalhes por categoria:*\n"
    
    for category, amount in by_category.items():
        percent = (amount / total) * 100
        emoji = get_category_emoji(category)
        report += f"- {emoji} {category.capitalize()}: R$ {amount:.2f} ({percent:.1f}%)\n"
    
    # Adiciona as últimas despesas (máximo 3)
    report += "\n📝 *Últimas transações:*\n"
    for i, (_, row) in enumerate(df_expenses.head(3).iterrows()):
        date = datetime.strptime(row['date'], "%Y-%m-%d").strftime("%d/%m")
        category_emoji = get_category_emoji(row['category'])
        report += f"{i+1}. {date}: R$ {row['amount']:.2f} - {category_emoji} {row['description'][:20]}\n"
    
    report += "\n🔍 Acesse o painel web para análises detalhadas!"
    
    return report

def get_category_emoji(category):
    """Retorna um emoji adequado para cada categoria"""
    emojis = {
        "alimentação": "🍽️",
        "transporte": "🚗",
        "moradia": "🏠",
        "saúde": "⚕️",
        "educação": "📚",
        "lazer": "🎭",
        "vestuário": "👕",
        "outros": "📦"
    }
    
    return emojis.get(category, "📦")

def process_expense_message(text, user_id):
    """Processa uma mensagem de texto para extrair e salvar uma despesa"""
    # Extrai informações da despesa
    expense_data = extract_expense_from_text(text)
    
    if expense_data is None or expense_data["amount"] is None:
        return (
            "Não consegui identificar um valor de despesa na sua mensagem. 🤔\n\n"
            "Por favor, inclua o valor gasto, por exemplo:\n"
            "• \"Almoço R$ 35\"\n"
            "• \"Paguei 50 reais de Uber hoje\"\n"
            "• \"Mercado 120,50\"\n\n"
            "Ou envie uma foto do comprovante! 📸"
        )
    
    # Salva a despesa
    expense_id = save_expense(
        user_id=user_id,
        amount=expense_data["amount"],
        category=expense_data["category"],
        description=expense_data["description"],
        date=expense_data["date"],
        original_message=text
    )
    
    # Emoji com base na categoria
    emoji = get_category_emoji(expense_data["category"])
    
    # Formata a resposta
    response = (
        f"✅ Despesa registrada!\n\n"
        f"💰 Valor: R$ {expense_data['amount']:.2f}\n"
        f"🏷️ Categoria: {emoji} {expense_data['category'].capitalize()}\n"
        f"📅 Data: {datetime.strptime(expense_data['date'], '%Y-%m-%d').strftime('%d/%m/%Y')}\n\n"
        f"Acesse o painel web para visualizar seus gastos detalhados!"
    )
    
    return response

#############################################################
# HANDLER DE MENSAGENS DO WHATSAPP                          #
#############################################################

def handle_webhook(request_values):
    """Processa um webhook do Twilio"""
    # Extrai informações da requisição
    incoming_msg = request_values.get('Body', '').strip()
    sender = request_values.get('From', '')
    
    # Remove o prefixo 'whatsapp:' do número
    if sender.startswith('whatsapp:'):
        sender = sender[9:]
    
    # Inicializa a resposta
    resp = MessagingResponse()
    
    # Verifica se é uma mensagem de mídia/imagem
    num_media = int(request_values.get('NumMedia', 0))
    
    try:
        if num_media > 0:
            # Processa mídia (comprovante)
            return handle_media(request_values, sender, resp)
        else:
            # Processa texto
            return handle_text(incoming_msg, sender, resp)
    except Exception as e:
        # Em caso de erro, envia uma mensagem amigável
        resp.message(f"Ops! Encontramos um pequeno problema ao processar sua mensagem. Por favor, tente novamente ou envie 'ajuda' para ver os comandos disponíveis. Erro: {str(e)}")
        return str(resp)

def handle_media(request_values, sender, resp):
    """Processa mensagens com mídia (fotos de comprovantes)"""
    # Obtém a URL da mídia
    media_url = request_values.get('MediaUrl0', '')
    media_type = request_values.get('MediaContentType0', '')
    
    # Verifica se é uma imagem
    if 'image' in media_type:
        # Inicializa o reconhecedor de comprovantes
        recognizer = ReceiptRecognizer()
        
        # Tenta extrair informações do comprovante
        recognition_result = recognizer.extract_receipt_info(media_url)
        
        if recognition_result["success"]:
            # Obtém dados do comprovante
            amount = recognition_result["amount"]
            description = recognition_result["description"]
            date = recognition_result["date"]
            category = recognition_result["category"]
            
            # Obtém ou cria o usuário
            user_id = get_or_create_user(sender)
            
            # Salva a despesa
            expense_id = save_expense(
                user_id=user_id,
                amount=amount,
                category=category,
                description=description,
                date=date,
                original_message=f"Imagem de comprovante - {description}"
            )
            
            # Formata a resposta
            formatted_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d/%m/%Y") if date else "hoje"
            
            # Emoji com base na categoria
            emoji = get_category_emoji(category)
            
            # Mensagem de sucesso
            success_message = (
                f"✅ Transação Registrada com Sucesso! ✅\n\n"
                f"📊 Resumo da Transação:\n"
                f"──────────────────────\n"
                f"📝 Descrição: {description}\n"
                f"💰 Valor: R$ {amount:.2f}\n"
                f"🏷️ Categoria: {emoji} {category.capitalize()}\n"
                f"📅 Data: {formatted_date}\n"
                f"✓ Pago: ✅\n"
                f"──────────────────────\n\n"
                f"Sua transação foi registrada com muito gosto! Saboreie! 😋\n"
            )
            
            resp.message(success_message)
        else:
            # Não conseguiu extrair informações
            resp.message(
                "Não consegui identificar um comprovante nesta imagem. 🤔\n\n"
                "Por favor, certifique-se que a foto está nítida e mostra claramente o valor e o estabelecimento.\n\n"
                "Você também pode registrar manualmente enviando uma mensagem como:\n"
                "'Almoço R$ 25,90'"
            )
    else:
        # Não é uma imagem
        resp.message(
            "Por favor, envie apenas fotos de comprovantes. 📸\n"
            "Para registrar despesas, você pode:\n"
            "- Tirar foto do comprovante\n"
            "- Enviar mensagem de texto com valor\n"
            "- Enviar áudio descrevendo a despesa"
        )
    
    return str(resp)

def handle_text(incoming_msg, sender, resp):
    """Processa mensagens de texto"""
    # Obtém ou cria o usuário
    user_id = get_or_create_user(sender)
    
    # Converte o texto para minúsculas
    msg_lower = incoming_msg.lower()
    
    # Verifica se é uma saudação
    if re.search(CHAT_PATTERNS['greeting'], msg_lower):
        resp.message(
            f"Olá! 👋 Bem-vindo ao seu assistente de controle financeiro!\n\n"
            f"Como posso ajudar hoje?\n\n"
            f"- Envie uma *foto de comprovante* 📸\n"
            f"- Descreva uma despesa (ex: \"Almoço R$ 25,90\")\n"
            f"- Digite \"ajuda\" para ver todos os comandos\n"
            f"- Digite \"resumo\" para ver um relatório"
        )
    
    # Verifica se é um pedido de ajuda
    elif re.search(CHAT_PATTERNS['help'], msg_lower):
        help_text = (
            "🤖 *Assistente de Controle de Gastos*\n\n"
            "Como usar:\n"
            "- 📸 Envie uma *foto do comprovante*\n"
            "- 💬 Envie um texto: \"Almoço R$ 25,90\"\n"
            "- 🎙️ Envie uma mensagem de voz\n\n"
            "Comandos disponíveis:\n"
            "- \"resumo\" ou \"relatório\": Ver um resumo geral\n"
            "- \"hoje\": Gastos de hoje\n"
            "- \"semana\": Relatório da última semana\n"
            "- \"mês\": Relatório do mês atual\n"
            "- \"ano\": Relatório do ano atual\n"
            "- \"ajuda\": Mostra esta mensagem\n\n"
            "Para ver mais detalhes, acesse o painel web!"
        )
        resp.message(help_text)
    
    # Verifica se é um pedido de resumo
    elif re.search(CHAT_PATTERNS['summary'], msg_lower):
        # Verifica se há um período específico
        period = "month"  # Padrão
        
        for p, pattern in CHAT_PATTERNS['period'].items():
            if re.search(pattern, msg_lower):
                period = p
                break
        
        # Obtém o relatório do período
        report = get_expense_report(user_id, period)
        resp.message(report)
    
    # Verifica se é um pedido de relatório de período específico
    elif any(re.search(pattern, msg_lower) for pattern in CHAT_PATTERNS['period'].values()):
        period = "month"  # Padrão
        
        for p, pattern in CHAT_PATTERNS['period'].items():
            if re.search(pattern, msg_lower):
                period = p
                break
        
        # Obtém o relatório do período
        report = get_expense_report(user_id, period)
        resp.message(report)
    
    # Caso contrário, tenta processar como uma despesa
    else:
        expense_response = process_expense_message(incoming_msg, user_id)
        resp.message(expense_response)
    
    return str(resp)

#############################################################
# CRIAÇÃO DE TEMPLATES HTML                                  #
#############################################################

def create_templates():
    """Cria os arquivos de template HTML necessários"""
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    # Template da página inicial
    index_html = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Controle de Gastos via WhatsApp</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #28a745, #218838);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .container {
                max-width: 1000px;
                padding: 20px;
            }
            
            .hero-card {
                background-color: white;
                border-radius: 20px;
                overflow: hidden;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            }
            
            .hero-image {
                width: 100%;
                height: auto;
            }
            
            .hero-content {
                padding: 30px;
            }
            
            .hero-content h1 {
                font-size: 32px;
                font-weight: 700;
                color: #28a745;
                margin-bottom: 15px;
            }
            
            .hero-content p {
                color: #6c757d;
                font-size: 18px;
                line-height: 1.6;
                margin-bottom: 25px;
            }
            
            .feature-icon {
                font-size: 24px;
                margin-right: 15px;
                color: #28a745;
            }
            
            .feature-item {
                display: flex;
                align-items: center;
                margin-bottom: 15px;
            }
            
            .feature-text {
                font-size: 16px;
            }
            
            .qr-container {
                background-color: #f8f9fa;
                border-radius: 15px;
                padding: 20px;
                text-align: center;
                margin-top: 20px;
                margin-bottom: 25px;
            }
            
            .qr-code {
                max-width: 180px;
                margin: 0 auto;
            }
            
            .btn-primary {
                background-color: #28a745;
                border-color: #28a745;
                border-radius: 30px;
                font-weight: 600;
                padding: 10px 25px;
                font-size: 16px;
            }
            
            .btn-primary:hover {
                background-color: #218838;
                border-color: #218838;
            }
            
            @media (max-width: 767px) {
                .hero-content {
                    padding: 20px;
                }
                
                .hero-content h1 {
                    font-size: 24px;
                }
                
                .hero-content p {
                    font-size: 16px;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="row hero-card">
                <div class="col-md-6">
                    <div class="hero-content">
                        <h1>Controle Financeiro Inteligente pelo WhatsApp</h1>
                        <p>Gerencie suas finanças sem complicação! Envie uma foto do recibo, uma mensagem de texto ou um áudio, e nosso sistema cuidará do resto.</p>
                        
                        <div class="feature-item">
                            <i class="bi bi-camera feature-icon"></i>
                            <span class="feature-text">Tire fotos de comprovantes para registro automático</span>
                        </div>
                        
                        <div class="feature-item">
                            <i class="bi bi-mic feature-icon"></i>
                            <span class="feature-text">Envie mensagens de voz descrevendo seus gastos</span>
                        </div>
                        
                        <div class="feature-item">
                            <i class="bi bi-bar-chart feature-icon"></i>
                            <span class="feature-text">Acompanhe seus gastos com relatórios detalhados</span>
                        </div>
                        
                        <div class="qr-container">
                            <p><strong>Adicione nosso assistente no WhatsApp</strong></p>
                            <img src="https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=https://wa.me/14155238886?text=join%20apple-yellow" class="qr-code">
                            <p class="mt-2 text-muted">Ou envie "join apple-yellow" para +1 415 523 8886</p>
                        </div>
                        
                        <a href="/dashboard" class="btn btn-primary btn-lg d-block">Acessar Painel de Controle</a>
                    </div>
                </div>
                <div class="col-md-6 d-none d-md-block">
                    <img src="https://source.unsplash.com/random/600x900/?finance,money" class="hero-image" style="object-fit: cover; height: 100%;">
                </div>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """
    
    # Template do dashboard
    dashboard_html = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Controle Financeiro</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            :root {
                --primary-color: #28a745;
                --secondary-color: #e74c3c;
                --background-color: #f8f9fa;
                --card-bg: #ffffff;
                --text-color: #333;
                --text-muted: #6c757d;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: var(--background-color);
                color: var(--text-color);
                padding-bottom: 70px; /* Espaço para a navbar */
            }
            
            .navbar-brand {
                font-weight: bold;
                display: flex;
                align-items: center;
            }
            
            .app-logo {
                height: 30px;
                margin-right: 8px;
            }
            
            .header-card {
                background-color: var(--primary-color);
                color: white;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                margin-bottom: 20px;
                padding: 15px;
                position: relative;
                overflow: hidden;
            }
            
            .header-card h2 {
                font-size: 20px;
                margin-bottom: 5px;
            }
            
            .header-card p {
                font-size: 28px;
                font-weight: bold;
                margin-bottom: 0;
            }
            
            .header-card .subtitle {
                font-size: 14px;
                opacity: 0.8;
            }
            
            .header-card .icon {
                position: absolute;
                right: 20px;
                top: 50%;
                transform: translateY(-50%);
                font-size: 38px;
                opacity: 0.3;
            }
            
            .card {
                border-radius: 12px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
                margin-bottom: 20px;
                border: none;
            }
            
            .card-header {
                background-color: var(--card-bg);
                border-bottom: 1px solid rgba(0, 0, 0, 0.05);
                padding: 15px 20px;
                font-weight: 600;
                font-size: 16px;
                border-radius: 12px 12px 0 0 !important;
            }
            
            .chart {
                height: 300px;
                width: 100%;
            }
            
            .tab-content {
                padding-top: 15px;
            }
            
            .category-pill {
                border-radius: 20px;
                padding: 5px 12px;
                font-size: 12px;
                font-weight: 500;
            }
            
            .expense-item {
                padding: 12px 15px;
                border-bottom: 1px solid rgba(0, 0, 0, 0.05);
            }
            
            .expense-item:last-child {
                border-bottom: none;
            }
            
            .expense-item-title {
                font-weight: 500;
                margin-bottom: 0;
                font-size: 14px;
            }
            
            .expense-item-subtitle {
                color: var(--text-muted);
                font-size: 12px;
            }
            
            .expense-item-amount {
                font-weight: 600;
                color: var(--secondary-color);
                font-size: 15px;
            }
            
            .bottom-nav {
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                background-color: white;
                box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.1);
                z-index: 1000;
                border-top-left-radius: 15px;
                border-top-right-radius: 15px;
            }
            
            .bottom-nav .nav-link {
                text-align: center;
                padding: 12px 0;
                color: var(--text-muted);
                display: flex;
                flex-direction: column;
                align-items: center;
                font-size: 10px;
            }
            
            .bottom-nav .nav-link.active {
                color: var(--primary-color);
            }
            
            .bottom-nav .nav-link i {
                font-size: 22px;
                margin-bottom: 2px;
            }
            
            .bottom-nav .fab-button {
                position: absolute;
                top: -20px;
                left: 50%;
                transform: translateX(-50%);
                width: 50px;
                height: 50px;
                background-color: var(--primary-color);
                border-radius: 50%;
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 24px;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
            }
            
            .period-buttons {
                display: flex;
                overflow-x: auto;
                white-space: nowrap;
                padding: 10px 0;
                margin-bottom: 10px;
            }
            
            .period-buttons .btn {
                flex: 0 0 auto;
                border-radius: 20px;
                margin-right: 10px;
                font-size: 13px;
                padding: 6px 15px;
            }
            
            .transaction-date {
                font-size: 14px;
                font-weight: 500;
                margin-top: 15px;
                margin-bottom: 10px;
                color: var(--text-muted);
            }
            
            /* Estilos responsivos */
            @media (max-width: 576px) {
                .header-card {
                    margin-bottom: 15px;
                    padding: 12px;
                }
                
                .header-card p {
                    font-size: 24px;
                }
                
                .chart {
                    height: 250px;
                }
                
                .card-header {
                    padding: 12px 15px;
                }
            }
            
            .category-alimentação { background-color: #FFA726; }
            .category-transporte { background-color: #42A5F5; }
            .category-moradia { background-color: #66BB6A; }
            .category-saúde { background-color: #EC407A; }
            .category-educação { background-color: #AB47BC; }
            .category-lazer { background-color: #26C6DA; }
            .category-vestuário { background-color: #8D6E63; }
            .category-outros { background-color: #78909C; }
        </style>
    </head>
    <body>
        <nav class="navbar navbar-expand bg-white shadow-sm mb-3">
            <div class="container">
                <a class="navbar-brand" href="#">
                    <span class="text-success">Controle Financeiro</span>
                </a>
                <div class="d-flex">
                    <button class="btn btn-sm btn-outline-success me-2">
                        <i class="bi bi-calendar-event"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-secondary">
                        <i class="bi bi-gear"></i>
                    </button>
                </div>
            </div>
        </nav>
        
        <div class="container">
            <!-- Seletores de período -->
            <div class="period-buttons">
                <button class="btn btn-sm btn-outline-success period-btn" data-period="day">Hoje</button>
                <button class="btn btn-sm btn-success period-btn" data-period="week">Esta semana</button>
                <button class="btn btn-sm btn-outline-success period-btn" data-period="month">Este mês</button>
                <button class="btn btn-sm btn-outline-success period-btn" data-period="year">Este ano</button>
                <button class="btn btn-sm btn-outline-success period-btn" data-period="custom">Personalizado</button>
            </div>
            
            <!-- Cartões de resumo -->
            <div class="row">
                <div class="col-md-6 col-lg-3 mb-3">
                    <div class="header-card">
                        <h2>Despesas</h2>
                        <p id="total-expenses">R$ 0,00</p>
                        <span class="subtitle" id="period-subtitle">nesta semana</span>
                        <div class="icon">
                            <i class="bi bi-cash"></i>
                        </div>
                    </div>
                </div>
                <div class="col-md-6 col-lg-3 mb-3">
                    <div class="header-card" style="background-color: #4a6cf7;">
                        <h2>Receitas</h2>
                        <p id="total-incomes">R$ 0,00</p>
                        <span class="subtitle" id="period-subtitle-income">nesta semana</span>
                        <div class="icon">
                            <i class="bi bi-wallet2"></i>
                        </div>
                    </div>
                </div>
                <div class="col-md-6 col-lg-3 mb-3">
                    <div class="header-card" style="background-color: #6440fb;">
                        <h2>Saldo</h2>
                        <p id="total-balance">R$ 0,00</p>
                        <span class="subtitle" id="period-subtitle-balance">nesta semana</span>
                        <div class="icon">
                            <i class="bi bi-piggy-bank"></i>
                        </div>
                    </div>
                </div>
                <div class="col-md-6 col-lg-3 mb-3">
                    <div class="header-card" style="background-color: #34c759;">
                        <h2>Economia</h2>
                        <p id="economy-percent">0%</p>
                        <span class="subtitle" id="period-subtitle-economy">nesta semana</span>
                        <div class="icon">
                            <i class="bi bi-graph-up-arrow"></i>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Gráfico por categoria -->
            <div class="card mb-4">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <span>Gráfico por categoria</span>
                    <div class="dropdown">
                        <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown">
                            <i class="bi bi-three-dots-vertical"></i>
                        </button>
                        <ul class="dropdown-menu dropdown-menu-end">
                            <li><a class="dropdown-item" href="/api/export/csv">Exportar dados</a></li>
                            <li><a class="dropdown-item" href="#">Ver detalhes</a></li>
                        </ul>
                    </div>
                </div>
                <div class="card-body">
                    <div id="category-chart" class="chart"></div>
                </div>
            </div>
            
            <!-- Últimas transações -->
            <div class="card">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <span>Últimas transações</span>
                    <a href="#" class="text-decoration-none text-success">Ver todas</a>
                </div>
                <div class="card-body p-0">
                    <ul class="nav nav-tabs nav-fill" id="transactionTabs" role="tablist">
                        <li class="nav-item" role="presentation">
                            <button class="nav-link active" id="all-tab" data-bs-toggle="tab" data-bs-target="#all-pane" type="button" role="tab">Todas</button>
                        </li>
                        <li class="nav-item" role="presentation">
                            <button class="nav-link" id="expense-tab" data-bs-toggle="tab" data-bs-target="#expense-pane" type="button" role="tab">Despesas</button>
                        </li>
                        <li class="nav-item" role="presentation">
                            <button class="nav-link" id="income-tab" data-bs-toggle="tab" data-bs-target="#income-pane" type="button" role="tab">Receitas</button>
                        </li>
                    </ul>
                    <div class="tab-content" id="transactionTabsContent">
                        <div class="tab-pane fade show active" id="all-pane" role="tabpanel" tabindex="0">
                            <div id="all-transactions-container">
                                <!-- Transações serão carregadas via JavaScript -->
                                <div class="text-center py-4">
                                    <div class="spinner-border text-success" role="status">
                                        <span class="visually-hidden">Carregando...</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="tab-pane fade" id="expense-pane" role="tabpanel" tabindex="0">
                            <div id="expense-transactions-container">
                                <!-- Despesas serão carregadas via JavaScript -->
                                <div class="text-center py-4">
                                    <div class="spinner-border text-success" role="status">
                                        <span class="visually-hidden">Carregando...</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="tab-pane fade" id="income-pane" role="tabpanel" tabindex="0">
                            <div id="income-transactions-container">
                                <!-- Receitas serão carregadas via JavaScript -->
                                <div class="text-center py-4">
                                    <div class="spinner-border text-success" role="status">
                                        <span class="visually-hidden">Carregando...</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Barra de navegação inferior -->
        <div class="bottom-nav">
            <div class="container">
                <div class="row">
                    <div class="col-3">
                        <a href="#" class="nav-link active">
                            <i class="bi bi-house-door"></i>
                            <span>Início</span>
                        </a>
                    </div>
                    <div class="col-3">
                        <a href="#" class="nav-link">
                            <i class="bi bi-graph-up"></i>
                            <span>Relatórios</span>
                        </a>
                    </div>
                    <div class="col-3">
                        <a href="#" class="nav-link">
                            <i class="bi bi-bell"></i>
                            <span>Alertas</span>
                        </a>
                    </div>
                    <div class="col-3">
                        <a href="#" class="nav-link">
                            <i class="bi bi-person"></i>
                            <span>Perfil</span>
                        </a>
                    </div>
                </div>
                <a href="#" class="fab-button" data-bs-toggle="modal" data-bs-target="#addExpenseModal">
                    <i class="bi bi-plus"></i>
                </a>
            </div>
        </div>
        
        <!-- Modal para adicionar despesa -->
        <div class="modal fade" id="addExpenseModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Adicionar Transação</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Fechar"></button>
                    </div>
                    <div class="modal-body">
                        <ul class="nav nav-tabs mb-3" id="addTransactionTabs" role="tablist">
                            <li class="nav-item" role="presentation">
                                <button class="nav-link active" id="add-expense-tab" data-bs-toggle="tab" data-bs-target="#add-expense-pane" type="button" role="tab">Despesa</button>
                            </li>
                            <li class="nav-item" role="presentation">
                                <button class="nav-link" id="add-income-tab" data-bs-toggle="tab" data-bs-target="#add-income-pane" type="button" role="tab">Receita</button>
                            </li>
                        </ul>
                        <div class="tab-content" id="addTransactionTabsContent">
                            <div class="tab-pane fade show active" id="add-expense-pane" role="tabpanel">
                                <form id="expense-form">
                                    <div class="mb-3">
                                        <label for="expense-amount" class="form-label">Valor</label>
                                        <div class="input-group">
                                            <span class="input-group-text">R$</span>
                                            <input type="number" class="form-control" id="expense-amount" name="amount" step="0.01" placeholder="0,00" required>
                                        </div>
                                    </div>
                                    <div class="mb-3">
                                        <label for="expense-description" class="form-label">Descrição</label>
                                        <input type="text" class="form-control" id="expense-description" name="description" placeholder="Ex: Supermercado" required>
                                    </div>
                                    <div class="mb-3">
                                        <label for="expense-category" class="form-label">Categoria</label>
                                        <select class="form-select" id="expense-category" name="category" required>
                                            <option value="alimentação">🍽️ Alimentação</option>
                                            <option value="transporte">🚗 Transporte</option>
                                            <option value="moradia">🏠 Moradia</option>
                                            <option value="saúde">⚕️ Saúde</option>
                                            <option value="educação">📚 Educação</option>
                                            <option value="lazer">🎭 Lazer</option>
                                            <option value="vestuário">👕 Vestuário</option>
                                            <option value="outros">📦 Outros</option>
                                        </select>
                                    </div>
                                    <div class="mb-3">
                                        <label for="expense-date" class="form-label">Data</label>
                                        <input type="date" class="form-control" id="expense-date" name="date" required>
                                    </div>
                                    <div class="mb-3">
                                        <label for="expense-payment" class="form-label">Método de Pagamento</label>
                                        <select class="form-select" id="expense-payment" name="payment_method">
                                            <option value="Dinheiro">Dinheiro</option>
                                            <option value="Débito">Cartão de Débito</option>
                                            <option value="Crédito">Cartão de Crédito</option>
                                            <option value="PIX">PIX</option>
                                        </select>
                                    </div>
                                    <div class="d-grid">
                                        <button type="submit" class="btn btn-success">Salvar Despesa</button>
                                    </div>
                                </form>
                            </div>
                            <div class="tab-pane fade" id="add-income-pane" role="tabpanel">
                                <form id="income-form">
                                    <div class="mb-3">
                                        <label for="income-amount" class="form-label">Valor</label>
                                        <div class="input-group">
                                            <span class="input-group-text">R$</span>
                                            <input type="number" class="form-control" id="income-amount" name="amount" step="0.01" placeholder="0,00" required>
                                        </div>
                                    </div>
                                    <div class="mb-3">
                                        <label for="income-description" class="form-label">Descrição</label>
                                        <input type="text" class="form-control" id="income-description" name="description" placeholder="Ex: Salário" required>
                                    </div>
                                    <div class="mb-3">
                                        <label for="income-category" class="form-label">Categoria</label>
                                        <select class="form-select" id="income-category" name="category" required>
                                            <option value="salario">Salário</option>
                                            <option value="freelance">Freelance</option>
                                            <option value="rendimento">Rendimento</option>
                                            <option value="presente">Presente</option>
                                            <option value="outros">Outros</option>
                                        </select>
                                    </div>
                                    <div class="mb-3">
                                        <label for="income-date" class="form-label">Data</label>
                                        <input type="date" class="form-control" id="income-date" name="date" required>
                                    </div>
                                    <div class="d-grid">
                                        <button type="submit" class="btn btn-success">Salvar Receita</button>
                                    </div>
                                </form>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            // Variáveis globais
            let currentPeriod = 'week';
            let categoryData = [];
            let allTransactions = [];
            
            // Função para formatar data
            function formatDate(dateStr) {
                const date = new Date(dateStr);
                return date.toLocaleDateString('pt-BR');
            }
            
            // Função para formatar valor monetário
            function formatCurrency(value) {
                return 'R$ ' + parseFloat(value).toFixed(2).replace('.', ',');
            }
            
            // Função para carregar os dados com base no período selecionado
            async function loadData(period = 'week') {
                currentPeriod = period;
                
                // Atualiza os subtítulos com o período selecionado
                let periodText = 'nesta semana';
                if (period === 'day') periodText = 'hoje';
                if (period === 'month') periodText = 'neste mês';
                if (period === 'year') periodText = 'neste ano';
                if (period === 'custom') periodText = 'no período selecionado';
                
                document.getElementById('period-subtitle').textContent = periodText;
                document.getElementById('period-subtitle-income').textContent = periodText;
                document.getElementById('period-subtitle-balance').textContent = periodText;
                document.getElementById('period-subtitle-economy').textContent = periodText;
                
                try {
                    // Carrega as despesas por categoria
                    const response = await fetch(`/api/chart/by_category?period=${period}`);
                    const chartData = await response.json();
                    
                    // Atualiza o gráfico
                    updateCategoryChart(chartData);
                    
                    // Carrega as transações
                    const expensesResponse = await fetch(`/api/expenses?period=${period}`);
                    const expenses = await expensesResponse.json();
                    
                    // TODO: Adicionar chamada para carregar receitas quando implementado
                    const incomes = []; // Mock para receitas
                    
                    // Combina despesas e receitas
                    allTransactions = [...expenses].sort((a, b) => new Date(b.date) - new Date(a.date));
                    
                    // Atualiza os totais
                    updateTotals(expenses, incomes);
                    
                    // Atualiza as listas de transações
                    updateTransactionLists(expenses, incomes);
                } catch (error) {
                    console.error('Erro ao carregar dados:', error);
                }
            }
            
            // Função para atualizar o gráfico de categorias
            function updateCategoryChart(chartData) {
                const data = chartData.data || [];
                const layout = chartData.layout || {};
                
                // Salva os dados para uso global
                categoryData = data;
                
                // Renderiza o gráfico
                Plotly.newPlot('category-chart', data, layout, { responsive: true });
            }
            
            // Função para atualizar os totais nos cards
            function updateTotals(expenses, incomes) {
                // Calcula o total de despesas
                const totalExpenses = expenses.reduce((sum, item) => sum + item.amount, 0);
                document.getElementById('total-expenses').textContent = formatCurrency(totalExpenses);
                
                // Calcula o total de receitas
                const totalIncomes = incomes.reduce((sum, item) => sum + (item.amount || 0), 0);
                document.getElementById('total-incomes').textContent = formatCurrency(totalIncomes);
                
                // Calcula o saldo
                const balance = totalIncomes - totalExpenses;
                document.getElementById('total-balance').textContent = formatCurrency(balance);
                
                // Calcula a porcentagem de economia
                let economyPercent = 0;
                if (totalIncomes > 0) {
                    economyPercent = ((totalIncomes - totalExpenses) / totalIncomes) * 100;
                }
                document.getElementById('economy-percent').textContent = `${economyPercent.toFixed(1)}%`;
            }
            
            // Função para agrupar transações por data
            function groupTransactionsByDate(transactions) {
                const groups = {};
                
                transactions.forEach(transaction => {
                    const date = transaction.date;
                    if (!groups[date]) {
                        groups[date] = [];
                    }
                    groups[date].push(transaction);
                });
                
                return groups;
            }
            
            // Função para criar o HTML de uma transação
            function createTransactionHTML(transaction, isIncome = false) {
                const date = new Date(transaction.date);
                const hours = transaction.created_at ? new Date(transaction.created_at).getHours() : 12;
                const minutes = transaction.created_at ? new Date(transaction.created_at).getMinutes() : 0;
                
                // Determina o emoji e a cor com base na categoria
                let emoji = '📦';
                let categoryClass = 'category-outros';
                
                if (isIncome) {
                    emoji = '💰';
                    categoryClass = 'bg-success';
                } else {
                    // Mapeia categorias para emojis
                    const categoryEmojis = {
                        'alimentação': '🍽️',
                        'transporte': '🚗',
                        'moradia': '🏠',
                        'saúde': '⚕️',
                        'educação': '📚',
                        'lazer': '🎭',
                        'vestuário': '👕',
                        'outros': '📦'
                    };
                    
                    emoji = categoryEmojis[transaction.category] || '📦';
                    categoryClass = `category-${transaction.category}`;
                }
                
                return `
                <div class="expense-item d-flex justify-content-between align-items-center">
                    <div class="d-flex align-items-center">
                        <div class="category-pill me-3 ${categoryClass} text-white">${emoji}</div>
                        <div>
                            <h6 class="expense-item-title">${transaction.description}</h6>
                            <p class="expense-item-subtitle">${hours}:${minutes.toString().padStart(2, '0')} • ${isIncome ? 'Receita' : transaction.category.charAt(0).toUpperCase() + transaction.category.slice(1)}</p>
                        </div>
                    </div>
                    <div class="expense-item-amount" style="color: ${isIncome ? '#28a745' : '#e74c3c'}">${isIncome ? '+' : '-'} ${formatCurrency(transaction.amount)}</div>
                </div>
                `;
            }
            
            // Função para atualizar as listas de transações
            function updateTransactionLists(expenses, incomes) {
                // Agrupa transações por data
                const groupedExpenses = groupTransactionsByDate(expenses);
                const groupedIncomes = groupTransactionsByDate(incomes);
                
                // Combina todas as transações
                const allDates = [...new Set([...Object.keys(groupedExpenses), ...Object.keys(groupedIncomes)])].sort().reverse();
                
                // Containers para as listas
                const allContainer = document.getElementById('all-transactions-container');
                const expenseContainer = document.getElementById('expense-transactions-container');
                const incomeContainer = document.getElementById('income-transactions-container');
                
                // Limpa os containers
                allContainer.innerHTML = '';
                expenseContainer.innerHTML = '';
                incomeContainer.innerHTML = '';
                
                // Se não há transações
                if (allDates.length === 0) {
                    const emptyMessage = `
                    <div class="text-center py-5">
                        <i class="bi bi-receipt text-muted" style="font-size: 48px;"></i>
                        <p class="mt-3 text-muted">Nenhuma transação encontrada neste período.</p>
                    </div>
                    `;
                    allContainer.innerHTML = emptyMessage;
                    expenseContainer.innerHTML = emptyMessage;
                    incomeContainer.innerHTML = emptyMessage;
                    return;
                }
                
                // Preenche as listas
                allDates.forEach(date => {
                    const dateObj = new Date(date);
                    const formattedDate = dateObj.toLocaleDateString('pt-BR', { day: 'numeric', month: 'long', year: 'numeric' });
                    
                    // Para todas as transações
                    if (groupedExpenses[date] || groupedIncomes[date]) {
                        allContainer.innerHTML += `<div class="transaction-date ps-3">${formattedDate}</div>`;
                        
                        // Adiciona despesas
                        if (groupedExpenses[date]) {
                            groupedExpenses[date].forEach(expense => {
                                allContainer.innerHTML += createTransactionHTML(expense, false);
                            });
                        }
                        
                        // Adiciona receitas
                        if (groupedIncomes[date]) {
                            groupedIncomes[date].forEach(income => {
                                allContainer.innerHTML += createTransactionHTML(income, true);
                            });
                        }
                    }
                    
                    // Para despesas
                    if (groupedExpenses[date]) {
                        expenseContainer.innerHTML += `<div class="transaction-date ps-3">${formattedDate}</div>`;
                        groupedExpenses[date].forEach(expense => {
                            expenseContainer.innerHTML += createTransactionHTML(expense, false);
                        });
                    }
                    
                    // Para receitas
                    if (groupedIncomes[date]) {
                        incomeContainer.innerHTML += `<div class="transaction-date ps-3">${formattedDate}</div>`;
                        groupedIncomes[date].forEach(income => {
                            incomeContainer.innerHTML += createTransactionHTML(income, true);
                        });
                    }
                });
            }
            
            // Função para adicionar uma nova despesa
            async function addExpense(event) {
                event.preventDefault();
                const form = document.getElementById('expense-form');
                const formData = new FormData(form);
                
                try {
                    const response = await fetch('/api/expenses', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(Object.fromEntries(formData)),
                    });
                    
                    if (response.ok) {
                        // Fecha o modal
                        const modal = bootstrap.Modal.getInstance(document.getElementById('addExpenseModal'));
                        modal.hide();
                        
                        // Limpa o formulário
                        form.reset();
                        
                        // Recarrega os dados
                        loadData(currentPeriod);
                        
                        // Exibe mensagem de sucesso
                        alert('Despesa adicionada com sucesso!');
                    } else {
                        alert('Erro ao adicionar despesa. Por favor, tente novamente.');
                    }
                } catch (error) {
                    console.error('Erro:', error);
                    alert('Erro ao adicionar despesa. Por favor, tente novamente.');
                }
            }
            
            // Função para adicionar uma nova receita
            async function addIncome(event) {
                event.preventDefault();
                const form = document.getElementById('income-form');
                const formData = new FormData(form);
                
                try {
                    const response = await fetch('/api/incomes', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(Object.fromEntries(formData)),
                    });
                    
                    if (response.ok) {
                        // Fecha o modal
                        const modal = bootstrap.Modal.getInstance(document.getElementById('addExpenseModal'));
                        modal.hide();
                        
                        // Limpa o formulário
                        form.reset();
                        
                        // Recarrega os dados
                        loadData(currentPeriod);
                        
                        // Exibe mensagem de sucesso
                        alert('Receita adicionada com sucesso!');
                    } else {
                        alert('Erro ao adicionar receita. Por favor, tente novamente.');
                    }
                } catch (error) {
                    console.error('Erro:', error);
                    alert('Erro ao adicionar receita. Por favor, tente novamente.');
                }
            }
            
            // Inicialização
            document.addEventListener('DOMContentLoaded', function() {
                // Define a data atual como padrão para os campos de data
                const today = new Date().toISOString().split('T')[0];
                document.getElementById('expense-date').value = today;
                document.getElementById('income-date').value = today;
                
                // Event listeners para os formulários
                document.getElementById('expense-form').addEventListener('submit', addExpense);
                document.getElementById('income-form').addEventListener('submit', addIncome);
                
                // Event listeners para os botões de período
                document.querySelectorAll('.period-btn').forEach(button => {
                    button.addEventListener('click', function() {
                        // Remove a classe ativa de todos os botões
                        document.querySelectorAll('.period-btn').forEach(btn => {
                            btn.classList.remove('btn-success');
                            btn.classList.add('btn-outline-success');
                        });
                        
                        // Adiciona a classe ativa ao botão clicado
                        this.classList.remove('btn-outline-success');
                        this.classList.add('btn-success');
                        
                        // Carrega os dados do período selecionado
                        loadData(this.dataset.period);
                    });
                });
                
                // Carrega os dados iniciais
                loadData(currentPeriod);
                
                // Ajusta o tamanho do gráfico ao redimensionar a janela
                window.addEventListener('resize', function() {
                    if (categoryData.length > 0) {
                        Plotly.relayout('category-chart', {
                            width: document.getElementById('category-chart').offsetWidth
                        });
                    }
                });
            });
        </script>
    </body>
    </html>
    """
    
    # Salva os templates
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(index_html)
    
    with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
        f.write(dashboard_html)
    
    print("Templates HTML criados com sucesso.")

#############################################################
# ROTAS DO FLASK                                            #
#############################################################

@app.route('/')
def index():
    """Página inicial"""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Página do painel de controle"""
    return render_template('dashboard.html')

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook para receber mensagens do WhatsApp via Twilio"""
    return handle_webhook(request.values)

@app.route('/send_test_message')
def send_test_message():
    """Rota para enviar uma mensagem de teste para um número específico"""
    to_number = request.args.get('to', '')
    
    if not to_number:
        return jsonify({"error": "Número de telefone não fornecido", "usage": "Use ?to=+5511XXXXXXXX"})
    
    if not twilio_client:
        return jsonify({"error": "Cliente Twilio não está configurado"})
    
    message = "Olá! Este é um teste do seu sistema de controle de gastos via WhatsApp. Responda com 'ajuda' para ver os comandos disponíveis."
    
    try:
        # Certifique-se que o número está no formato correto para o WhatsApp
        if not to_number.startswith('whatsapp:'):
            to_number = f'whatsapp:{to_number}'
        
        # Enviar a mensagem
        message_obj = twilio_client.messages.create(
            from_=TWILIO_PHONE_NUMBER,
            body=message,
            to=to_number
        )
        
        return jsonify({
            "success": True, 
            "message_sid": message_obj.sid, 
            "sent_to": to_number
        })
    except Exception as e:
        return jsonify({
            "success": False, 
            "error": str(e)
        })

@app.route('/api/expenses')
def get_expenses_api():
    """API para obter todas as despesas"""
    period = request.args.get('period', 'month')
    
    # Define o período (dia, semana, mês, ano)
    today = datetime.now()
    
    if period == 'day':
        start_date = today.strftime("%Y-%m-%d")
    elif period == 'week':
        start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    elif period == 'month':
        start_date = f"{today.year}-{today.month:02d}-01"
    elif period == 'year':
        start_date = f"{today.year}-01-01"
    else:
        start_date = None
    
    # Dados para teste (TODO: remover quando houver dados reais)
    # Verifica se há dados no banco de dados
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM expenses")
    count = cursor.fetchone()[0]
    conn.close()
    
    if count == 0:
        # Não há dados, usa dados de exemplo
        example_data = [
            {
                "id": 1,
                "user_id": 1,
                "amount": 79.96,
                "category": "alimentação",
                "description": "Mercado Dia",
                "date": (today - timedelta(days=0)).strftime("%Y-%m-%d"),
                "payment_method": "Débito",
                "created_at": (today - timedelta(days=0)).strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "id": 2,
                "user_id": 1,
                "amount": 24.50,
                "category": "transporte",
                "description": "Uber",
                "date": (today - timedelta(days=0)).strftime("%Y-%m-%d"),
                "payment_method": "Crédito",
                "created_at": (today - timedelta(days=0)).strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "id": 3,
                "user_id": 1,
                "amount": 54.00,
                "category": "lazer",
                "description": "Cinema Shopping",
                "date": (today - timedelta(days=1)).strftime("%Y-%m-%d"),
                "payment_method": "Crédito",
                "created_at": (today - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "id": 4,
                "user_id": 1,
                "amount": 120.00,
                "category": "moradia",
                "description": "Internet",
                "date": (today - timedelta(days=3)).strftime("%Y-%m-%d"),
                "payment_method": "Débito",
                "created_at": (today - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "id": 5,
                "user_id": 1,
                "amount": 45.80,
                "category": "saúde",
                "description": "Farmácia",
                "date": (today - timedelta(days=4)).strftime("%Y-%m-%d"),
                "payment_method": "Dinheiro",
                "created_at": (today - timedelta(days=4)).strftime("%Y-%m-%d %H:%M:%S")
            }
        ]
        return jsonify(example_data)
    
    # Obtém os dados do banco de dados
    conn = sqlite3.connect(DATABASE_PATH)
    
    query = "SELECT * FROM expenses WHERE 1=1"
    params = []
    
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    
    query += " ORDER BY date DESC, created_at DESC"
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    return jsonify(df.to_dict(orient='records'))

@app.route('/api/expenses', methods=['POST'])
def add_expense_api():
    """API para adicionar uma despesa"""
    data = request.json
    
    if not data or 'amount' not in data or 'description' not in data or 'category' not in data or 'date' not in data:
        return jsonify({"error": "Dados incompletos"}), 400
    
    try:
        # Obtém os dados da requisição
        amount = float(data['amount'])
        category = data['category']
        description = data['description']
        date = data['date']
        payment_method = data.get('payment_method', None)
        
        # Usuário fixo para este exemplo
        user_id = 1
        
        # Salva a despesa
        expense_id = save_expense(
            user_id=user_id,
            amount=amount,
            category=category,
            description=description,
            date=date,
            payment_method=payment_method
        )
        
        return jsonify({"success": True, "id": expense_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/incomes', methods=['POST'])
def add_income_api():
    """API para adicionar uma receita"""
    data = request.json
    
    if not data or 'amount' not in data or 'description' not in data or 'category' not in data or 'date' not in data:
        return jsonify({"error": "Dados incompletos"}), 400
    
    try:
        # Obtém os dados da requisição
        amount = float(data['amount'])
        category = data['category']
        description = data['description']
        date = data['date']
        
        # Usuário fixo para este exemplo
        user_id = 1
        
        # Salva a receita
        income_id = save_income(
            user_id=user_id,
            amount=amount,
            category=category,
            description=description,
            date=date
        )
        
        return jsonify({"success": True, "id": income_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/chart/by_category')
def get_chart_by_category():
    """API para obter dados do gráfico de despesas por categoria"""
    period = request.args.get('period', 'month')
    
    # Define o período (dia, semana, mês, ano)
    today = datetime.now()
    
    if period == 'day':
        start_date = today.strftime("%Y-%m-%d")
    elif period == 'week':
        start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    elif period == 'month':
        start_date = f"{today.year}-{today.month:02d}-01"
    elif period == 'year':
        start_date = f"{today.year}-01-01"
    else:
        start_date = None
    
    # Usuário fixo para este exemplo
    user_id = 1
    
    # Obtém os dados do banco de dados
    df = get_expenses_by_category(user_id, start_date)
    
    if df.empty:
        # Dados de exemplo para quando não há registros
        example_data = {
            'category': ['alimentação', 'transporte', 'moradia', 'lazer', 'saúde'],
            'total': [540.25, 320.40, 150.00, 180.50, 59.50]
        }
        df = pd.DataFrame(example_data)
    
    # Define cores para as categorias
    colors = {
        'alimentação': '#FFA726',
        'transporte': '#42A5F5',
        'moradia': '#66BB6A',
        'saúde': '#EC407A',
        'educação': '#AB47BC',
        'lazer': '#26C6DA',
        'vestuário': '#8D6E63',
        'outros': '#78909C'
    }
    
    # Mapeia categorias para cores
    category_colors = [colors.get(cat, '#78909C') for cat in df['category']]
    
    # Calcula o total
    total = df['total'].sum()
    
    # Cria o gráfico
    pie_data = [{
        'values': df['total'].tolist(),
        'labels': df['category'].tolist(),
        'type': 'pie',
        'hole': 0.6,
        'textinfo': 'label+percent',
        'textposition': 'outside',
        'marker': {
            'colors': category_colors
        }
    }]
    
    pie_layout = {
        'margin': {'l': 10, 'r': 10, 't': 10, 'b': 10},
        'showlegend': False,
        'height': 300,
        'annotations': [{
            'font': {'size': 14},
            'showarrow': False,
            'text': f'R$ {total:.2f}',
            'x': 0.5,
            'y': 0.5
        }]
    }
    
    return jsonify({'data': pie_data, 'layout': pie_layout})

@app.route('/api/chart/by_time')
def get_chart_by_time():
    """API para obter dados do gráfico de despesas ao longo do tempo"""
    period = request.args.get('period', 'month')
    
    # Define o período (dia, semana, mês, ano)
    today = datetime.now()
    
    if period == 'day':
        start_date = today.strftime("%Y-%m-%d")
    elif period == 'week':
        start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    elif period == 'month':
        start_date = f"{today.year}-{today.month:02d}-01"
    elif period == 'year':
        start_date = f"{today.year}-01-01"
    else:
        start_date = None
    
    # Usuário fixo para este exemplo
    user_id = 1
    
    # Obtém as despesas do banco de dados
    conn = sqlite3.connect(DATABASE_PATH)
    
    query = """
    SELECT date, SUM(amount) as total 
    FROM expenses 
    WHERE user_id = ?
    """
    params = [user_id]
    
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    
    query += " GROUP BY date ORDER BY date"
    
    df = pd.read_sql_query(query, conn, params=tuple(params))
    conn.close()
    
    if df.empty:
        # Dados de exemplo para quando não há registros
        example_dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(5)]
        example_values = [120.35, 85.50, 200.80, 150.20, 79.96]
        df = pd.DataFrame({'date': example_dates, 'total': example_values})
    
    # Cria o gráfico
    line_data = [{
        'x': df['date'].tolist(),
        'y': df['total'].tolist(),
        'type': 'scatter',
        'mode': 'lines+markers',
        'line': {'color': '#28a745', 'width': 3},
        'marker': {'color': '#28a745', 'size': 8}
    }]
    
    line_layout = {
        'margin': {'l': 40, 'r': 10, 't': 10, 'b': 40},
        'showlegend': False,
        'height': 300,
        'xaxis': {
            'title': 'Data',
            'tickformat': '%d/%m'
        },
        'yaxis': {
            'title': 'Valor (R$)'
        }
    }
    
    return jsonify({'data': line_data, 'layout': line_layout})

@app.route('/api/export/csv')
def export_csv():
    """Exporta todas as despesas como CSV"""
    # Usuário fixo para este exemplo
    user_id = 1
    
    # Obtém as despesas do banco de dados
    conn = sqlite3.connect(DATABASE_PATH)
    df = pd.read_sql_query("SELECT * FROM expenses WHERE user_id = ? ORDER BY date DESC", conn, params=(user_id,))
    conn.close()
    
    if df.empty:
        return "Não há despesas para exportar", 404
    
    # Reformata as colunas
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%d/%m/%Y')
    df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%d/%m/%Y %H:%M:%S')
    
    # Traduz os nomes das colunas
    column_names = {
        'id': 'ID',
        'user_id': 'ID do Usuário',
        'amount': 'Valor',
        'category': 'Categoria',
        'description': 'Descrição',
        'date': 'Data',
        'payment_method': 'Método de Pagamento',
        'created_at': 'Criado em',
        'original_message': 'Mensagem Original'
    }
    df = df.rename(columns=column_names)
    
    # Cria um arquivo CSV em memória
    csv_data = df.to_csv(index=False)
    
    # Retorna o CSV como um arquivo para download
    return send_file(
        io.BytesIO(csv_data.encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name='despesas.csv'
    )

# Inicialização do aplicativo
def init():
    """Inicializa o aplicativo"""
    setup_database()
    create_templates()

# Ponto de entrada do aplicativo
if __name__ == '__main__':
    # Inicializa o banco de dados e os templates
    init()
    
    # Inicia o servidor Flask
    print(f"\nIniciando o servidor na porta 5000...")
    print(f"Acesse o painel em: http://localhost:5000/")
    app.run(debug=True, host='0.0.0.0', port=5000)