from flask import Blueprint, request, jsonify, session, send_file
from database.models import Usuario, Despesa, Receita, TextProcessor
from functools import wraps
import os
import tempfile
from werkzeug.utils import secure_filename
from datetime import datetime
import traceback
import io
from config import Config

# Criação do blueprint
uploads_bp = Blueprint('uploads', __name__)

# Diretório para salvar os arquivos enviados
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_AUDIO = {'mp3', 'wav', 'ogg', 'm4a'}

# Certifica-se de que o diretório existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Middleware para verificar login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return jsonify({"error": "Não autorizado"}), 401
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename, allowed_extensions):
    """Verifica se o arquivo tem uma extensão permitida"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

# ===== ROTAS DE UPLOAD =====

@uploads_bp.route('/api/upload/imagem', methods=['POST'])
@login_required
def upload_imagem():
    """API para fazer upload de imagens"""
    if 'file' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "Nenhum arquivo selecionado"}), 400
    
    if file and allowed_file(file.filename, ALLOWED_EXTENSIONS):
        try:
            # Cria um nome de arquivo seguro
            filename = secure_filename(file.filename)
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            
            # Caminho completo para salvar o arquivo
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            
            # Salva o arquivo
            file.save(filepath)
            
            # URL relativa para acessar a imagem
            url = f"/static/uploads/{filename}"
            
            # Se for uma imagem de comprovante, tenta fazer OCR
            ocr_resultado = None
            if request.form.get('tipo') == 'comprovante':
                ocr_resultado = processar_ocr_imagem(filepath)
            
            return jsonify({
                "success": True, 
                "url": url, 
                "filename": filename,
                "ocr_resultado": ocr_resultado
            }), 201
            
        except Exception as e:
            print(f"Erro no upload de imagem: {str(e)}")
            traceback.print_exc()
            return jsonify({"error": "Erro interno do servidor"}), 500
    
    return jsonify({"error": "Formato de arquivo não permitido"}), 400

@uploads_bp.route('/api/upload/audio', methods=['POST'])
@login_required
def upload_audio():
    """API para fazer upload de arquivos de áudio"""
    if 'file' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "Nenhum arquivo selecionado"}), 400
    
    if file and allowed_file(file.filename, ALLOWED_AUDIO):
        try:
            # Cria um nome de arquivo seguro
            filename = secure_filename(file.filename)
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            
            # Caminho completo para salvar o arquivo
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            
            # Salva o arquivo
            file.save(filepath)
            
            # URL relativa para acessar o áudio
            url = f"/static/uploads/{filename}"
            
            # Processa o áudio para extrair informações
            resultado_audio = processar_audio_transacao(filepath)
            
            return jsonify({
                "success": True, 
                "url": url, 
                "filename": filename,
                "texto": resultado_audio.get('texto', ''),
                "dados_extraidos": resultado_audio.get('dados_extraidos')
            }), 201
            
        except Exception as e:
            print(f"Erro no upload de áudio: {str(e)}")
            traceback.print_exc()
            return jsonify({"error": "Erro interno do servidor"}), 500
    
    return jsonify({"error": "Formato de arquivo não permitido"}), 400

@uploads_bp.route('/api/upload/documento', methods=['POST'])
@login_required
def upload_documento():
    """API para fazer upload de documentos (PDF, DOC, etc.)"""
    if 'file' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "Nenhum arquivo selecionado"}), 400
    
    # Extensões permitidas para documentos
    allowed_docs = {'pdf', 'doc', 'docx', 'txt'}
    
    if file and allowed_file(file.filename, allowed_docs):
        try:
            # Cria um nome de arquivo seguro
            filename = secure_filename(file.filename)
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            
            # Caminho completo para salvar o arquivo
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            
            # Salva o arquivo
            file.save(filepath)
            
            # URL relativa para acessar o documento
            url = f"/static/uploads/{filename}"
            
            # Processa o documento se for necessário
            resultado_documento = processar_documento(filepath, file.filename)
            
            return jsonify({
                "success": True, 
                "url": url, 
                "filename": filename,
                "tipo": file.filename.rsplit('.', 1)[1].lower(),
                "texto_extraido": resultado_documento.get('texto', ''),
                "dados_extraidos": resultado_documento.get('dados_extraidos')
            }), 201
            
        except Exception as e:
            print(f"Erro no upload de documento: {str(e)}")
            traceback.print_exc()
            return jsonify({"error": "Erro interno do servidor"}), 500
    
    return jsonify({"error": "Formato de arquivo não permitido"}), 400

@uploads_bp.route('/api/upload/multiplos', methods=['POST'])
@login_required
def upload_multiplos():
    """API para fazer upload de múltiplos arquivos"""
    if 'files' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    
    files = request.files.getlist('files')
    
    if not files or all(f.filename == '' for f in files):
        return jsonify({"error": "Nenhum arquivo selecionado"}), 400
    
    resultados = []
    erros = []
    
    for file in files:
        if file.filename == '':
            continue
            
        try:
            # Determina o tipo de arquivo
            extensao = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
            
            if extensao in ALLOWED_EXTENSIONS:
                # Processa como imagem
                resultado = processar_upload_imagem(file)
            elif extensao in ALLOWED_AUDIO:
                # Processa como áudio
                resultado = processar_upload_audio(file)
            else:
                erros.append(f"Formato não suportado: {file.filename}")
                continue
            
            if resultado:
                resultados.append(resultado)
            else:
                erros.append(f"Erro ao processar: {file.filename}")
                
        except Exception as e:
            erros.append(f"Erro em {file.filename}: {str(e)}")
    
    return jsonify({
        "success": len(resultados) > 0,
        "resultados": resultados,
        "erros": erros,
        "total_processados": len(resultados),
        "total_erros": len(erros)
    }), 201 if len(resultados) > 0 else 400

# ===== ROTAS DE PROCESSAMENTO =====

@uploads_bp.route('/api/processar-imagem', methods=['POST'])
@login_required
def processar_imagem():
    """Processa uma imagem para extrair informações de despesa"""
    # Verifica se foi enviada uma imagem
    if 'imagem' not in request.files:
        return jsonify({"error": "Nenhuma imagem enviada"}), 400
    
    imagem = request.files['imagem']
    
    # Verifica se o arquivo é válido
    if imagem.filename == '':
        return jsonify({"error": "Nenhuma imagem selecionada"}), 400
    
    # Verifica a extensão do arquivo
    if not allowed_file(imagem.filename, ALLOWED_EXTENSIONS):
        return jsonify({"error": "Formato de arquivo não permitido"}), 400
    
    try:
        # Gera um nome único para o arquivo
        filename = secure_filename(imagem.filename)
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        
        # Caminho completo para o arquivo
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        # Salva o arquivo
        imagem.save(filepath)
        
        # URL relativa para acessar a imagem
        url_imagem = f"/static/uploads/{filename}"
        
        # Processa OCR para extrair informações
        dados_ocr = processar_ocr_imagem(filepath)
        
        return jsonify({
            "success": True,
            "url_imagem": url_imagem,
            "dados_ocr": dados_ocr
        })
        
    except Exception as e:
        print(f"Erro ao processar imagem: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@uploads_bp.route('/api/processar-audio', methods=['POST'])
@login_required
def processar_audio():
    """Processa um áudio para extrair informações de despesa"""
    # Verifica se foi enviado um áudio
    if 'audio' not in request.files:
        return jsonify({"error": "Nenhum áudio enviado"}), 400
    
    audio = request.files['audio']
    
    # Verifica se o arquivo é válido
    if audio.filename == '':
        return jsonify({"error": "Nenhum áudio selecionado"}), 400
    
    # Verifica a extensão do arquivo
    if not allowed_file(audio.filename, ALLOWED_AUDIO):
        return jsonify({"error": "Formato de arquivo não permitido"}), 400
    
    try:
        filename = secure_filename(audio.filename)
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        audio.save(filepath)
        url_audio = f"/static/uploads/{filename}"

        # Processa o áudio
        resultado_audio = processar_audio_transacao(filepath)

        return jsonify({
            "success": True,
            "url_audio": url_audio,
            "texto_transcrito": resultado_audio.get('texto', ''),
            "dados": resultado_audio.get('dados_extraidos')
        })

    except Exception as e:
        print(f"Erro ao processar áudio: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ===== ROTAS DE DOWNLOAD =====

@uploads_bp.route('/api/download/<filename>', methods=['GET'])
@login_required
def download_arquivo(filename):
    """API para download de arquivos enviados pelo usuário"""
    try:
        # Verifica se o arquivo existe
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        if not os.path.exists(filepath):
            return jsonify({"error": "Arquivo não encontrado"}), 404
        
        # TODO: Verificar se o arquivo pertence ao usuário logado (implementar controle de acesso)
        
        return send_file(filepath, as_attachment=True)
        
    except Exception as e:
        print(f"Erro no download: {str(e)}")
        return jsonify({"error": "Erro interno do servidor"}), 500

@uploads_bp.route('/api/arquivos', methods=['GET'])
@login_required
def listar_arquivos():
    """Lista arquivos enviados pelo usuário"""
    try:
        usuario_id = session.get('usuario_id')
        
        # TODO: Implementar busca de arquivos por usuário no banco de dados
        # Por enquanto, lista todos os arquivos na pasta (não recomendado para produção)
        
        arquivos = []
        if os.path.exists(UPLOAD_FOLDER):
            for filename in os.listdir(UPLOAD_FOLDER):
                if os.path.isfile(os.path.join(UPLOAD_FOLDER, filename)):
                    filepath = os.path.join(UPLOAD_FOLDER, filename)
                    stat = os.stat(filepath)
                    
                    arquivos.append({
                        'nome': filename,
                        'tamanho': stat.st_size,
                        'data_modificacao': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                        'url': f"/static/uploads/{filename}"
                    })
        
        return jsonify({
            "success": True,
            "arquivos": arquivos,
            "total": len(arquivos)
        })
        
    except Exception as e:
        print(f"Erro ao listar arquivos: {str(e)}")
        return jsonify({"error": "Erro interno do servidor"}), 500

@uploads_bp.route('/api/arquivo/<filename>', methods=['DELETE'])
@login_required
def excluir_arquivo(filename):
    """Exclui um arquivo enviado pelo usuário"""
    try:
        # Verifica se o arquivo existe
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        if not os.path.exists(filepath):
            return jsonify({"error": "Arquivo não encontrado"}), 404
        
        # TODO: Verificar se o arquivo pertence ao usuário logado
        
        # Exclui o arquivo
        os.remove(filepath)
        
        return jsonify({
            "success": True,
            "message": "Arquivo excluído com sucesso"
        })
        
    except Exception as e:
        print(f"Erro ao excluir arquivo: {str(e)}")
        return jsonify({"error": "Erro interno do servidor"}), 500

# ===== FUNÇÕES AUXILIARES =====

def processar_ocr_imagem(filepath):
    """Processa OCR em uma imagem para extrair informações de nota fiscal"""
    try:
        # Aqui seria implementado o OCR real usando pytesseract ou outra biblioteca
        # Para este exemplo, simulamos alguns resultados
        
        # Simula extração de dados de uma nota fiscal
        dados_simulados = {
            "detectado": True,
            "valor": round(50 + 200 * (datetime.now().microsecond / 1000000), 2),
            "data": datetime.now().strftime("%Y-%m-%d"),
            "estabelecimento": "Supermercado ABC",
            "categoria_sugerida": "alimentação",
            "cnpj": "12.345.678/0001-90",
            "endereco": "Rua das Flores, 123"
        }
        
        # Usa o TextProcessor para processar os dados extraídos
        processor = TextProcessor()
        dados_processados = processor.processar_texto_nota_fiscal(
            f"Estabelecimento: {dados_simulados['estabelecimento']}\n"
            f"Valor total: R$ {dados_simulados['valor']}\n"
            f"Data: {dados_simulados['data']}"
        )
        
        return {
            **dados_simulados,
            "dados_processados": dados_processados
        }
        
    except Exception as e:
        print(f"Erro no OCR: {str(e)}")
        return {
            "detectado": False,
            "erro": str(e)
        }

def processar_audio_transacao(filepath):
    """Processa um arquivo de áudio para extrair informações de transação"""
    try:
        # Aqui seria implementada a transcrição real usando speech_recognition ou outra biblioteca
        # Para este exemplo, simulamos a transcrição
        
        # Simula transcrição de áudio
        textos_exemplo = [
            "Comprei no supermercado hoje gastei 157 reais e 50 centavos",
            "Paguei 35 reais no almoço de hoje no restaurante",
            "Gasolina do carro 89 reais no posto",
            "Compras do mês 234 reais no mercado"
        ]
        
        import random
        texto_transcrito = random.choice(textos_exemplo)
        
        # Processa o texto para extrair informações da despesa
        processor = TextProcessor()
        dados_despesa = processor.extrair_informacoes_despesa(texto_transcrito)
        
        return {
            "texto": texto_transcrito,
            "dados_extraidos": dados_despesa,
            "confianca": 0.95  # Simulado
        }
        
    except Exception as e:
        print(f"Erro na transcrição de áudio: {str(e)}")
        return {
            "texto": "",
            "dados_extraidos": None,
            "erro": str(e)
        }

def processar_documento(filepath, filename):
    """Processa um documento para extrair informações"""
    try:
        extensao = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        if extensao == 'pdf':
            return processar_pdf(filepath)
        elif extensao in ['doc', 'docx']:
            return processar_word(filepath)
        elif extensao == 'txt':
            return processar_txt(filepath)
        else:
            return {"texto": "", "dados_extraidos": None}
            
    except Exception as e:
        print(f"Erro ao processar documento: {str(e)}")
        return {"texto": "", "dados_extraidos": None, "erro": str(e)}

def processar_pdf(filepath):
    """Processa um arquivo PDF"""
    # Implementação simulada - em produção usaria PyPDF2 ou similar
    return {
        "texto": "Texto extraído do PDF (simulado)",
        "dados_extraidos": None
    }

def processar_word(filepath):
    """Processa um arquivo Word"""
    # Implementação simulada - em produção usaria python-docx
    return {
        "texto": "Texto extraído do Word (simulado)",
        "dados_extraidos": None
    }

def processar_txt(filepath):
    """Processa um arquivo de texto"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            texto = f.read()
        
        # Processa o texto para extrair informações
        processor = TextProcessor()
        dados_extraidos = processor.extrair_info_de_texto_longo(texto)
        
        return {
            "texto": texto,
            "dados_extraidos": dados_extraidos
        }
        
    except Exception as e:
        return {"texto": "", "dados_extraidos": None, "erro": str(e)}

def processar_upload_imagem(file):
    """Função auxiliar para processar upload de imagem individual"""
    try:
        filename = secure_filename(file.filename)
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        url = f"/static/uploads/{filename}"
        dados_ocr = processar_ocr_imagem(filepath)
        
        return {
            "tipo": "imagem",
            "filename": filename,
            "url": url,
            "dados_ocr": dados_ocr
        }
        
    except Exception as e:
        print(f"Erro no processamento de imagem: {str(e)}")
        return None

def processar_upload_audio(file):
    """Função auxiliar para processar upload de áudio individual"""
    try:
        filename = secure_filename(file.filename)
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        url = f"/static/uploads/{filename}"
        resultado_audio = processar_audio_transacao(filepath)
        
        return {
            "tipo": "audio",
            "filename": filename,
            "url": url,
            "texto": resultado_audio.get('texto', ''),
            "dados_extraidos": resultado_audio.get('dados_extraidos')
        }
        
    except Exception as e:
        print(f"Erro no processamento de áudio: {str(e)}")
        return None