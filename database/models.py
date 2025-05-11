import os
import sqlite3
from datetime import datetime
import re

# Ensure the database directory exists
def init_db(db_path):
    """Inicializa o banco de dados"""
    # Garante que o diretório existe
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Conecta ao banco de dados
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Cria as tabelas se não existirem
    
    # Tabela de usuários
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        celular TEXT UNIQUE,
        nome TEXT,
        email TEXT UNIQUE,
        senha TEXT,
        data_criacao TEXT,
        ultimo_acesso TEXT,
        plano TEXT DEFAULT 'gratuito',
        data_assinatura TEXT,
        data_vencimento TEXT,
        ativo INTEGER DEFAULT 1
    )
    ''')
    
    # Tabela de despesas
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS despesas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        valor REAL NOT NULL,
        categoria TEXT,
        descricao TEXT,
        data TEXT,
        forma_pagamento TEXT,
        parcelado INTEGER DEFAULT 0,
        num_parcelas INTEGER DEFAULT 1,
        data_criacao TEXT,
        mensagem_original TEXT,
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
    )
    ''')
    
    # Tabela de receitas
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS receitas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        valor REAL NOT NULL,
        categoria TEXT,
        descricao TEXT,
        data TEXT,
        data_criacao TEXT,
        recorrente INTEGER DEFAULT 0,
        periodicidade TEXT,
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
    )
    ''')
    
    # Tabela de categorias personalizadas
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categorias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        nome TEXT NOT NULL,
        tipo TEXT NOT NULL, -- 'despesa' ou 'receita'
        icone TEXT,
        cor TEXT,
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
    )
    ''')
    
    # Tabela de assinaturas
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS assinaturas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        plano TEXT NOT NULL,
        data_inicio TEXT,
        data_fim TEXT,
        valor REAL,
        status TEXT,
        forma_pagamento TEXT,
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
    )
    ''')
    
    # Tabela de tokens de recuperação de senha
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tokens_recuperacao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        token TEXT NOT NULL,
        data_criacao TEXT,
        data_expiracao TEXT,
        utilizado INTEGER DEFAULT 0,
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
    )
    ''')
    
    # Tabela de sessões
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sessoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        token TEXT NOT NULL,
        data_criacao TEXT,
        data_expiracao TEXT,
        ip_address TEXT,
        user_agent TEXT,
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
    )
    ''')
    
    conn.commit()
    conn.close()
    
    print(f"Banco de dados inicializado em: {db_path}")


class Usuario:
    """Classe para manipulação de usuários"""
    def __init__(self, db_path):
        self.db_path = db_path
    
    def criar(self, celular, nome=None, email=None, senha=None):
        """Cria um novo usuário"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        data_criacao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute(
            "INSERT INTO usuarios (celular, nome, email, senha, data_criacao) VALUES (?, ?, ?, ?, ?)",
            (celular, nome, email, senha, data_criacao)
        )
        
        conn.commit()
        usuario_id = cursor.lastrowid
        conn.close()
        
        return usuario_id
    
    def buscar_por_celular(self, celular):
        """Busca um usuário pelo número de celular"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM usuarios WHERE celular = ?", (celular,))
        usuario = cursor.fetchone()
        
        conn.close()
        
        return dict(usuario) if usuario else None
    
    def buscar_por_id(self, usuario_id):
        """Busca um usuário pelo ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,))
        usuario = cursor.fetchone()
        
        conn.close()
        
        return dict(usuario) if usuario else None
    
    def buscar_por_email(self, email):
        """Busca um usuário pelo email"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
        usuario = cursor.fetchone()
        
        conn.close()
        
        return dict(usuario) if usuario else None
    
    def atualizar(self, usuario_id, nome=None, email=None, senha=None, plano=None):
        """Atualiza os dados de um usuário"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Constrói a consulta dinamicamente com base nos campos fornecidos
        campos = []
        valores = []
        
        if nome is not None:
            campos.append("nome = ?")
            valores.append(nome)
        
        if email is not None:
            campos.append("email = ?")
            valores.append(email)
        
        if senha is not None:
            campos.append("senha = ?")
            valores.append(senha)
        
        if plano is not None:
            campos.append("plano = ?")
            valores.append(plano)
        
        # Adiciona o ID do usuário aos valores
        valores.append(usuario_id)
        
        if campos:
            query = f"UPDATE usuarios SET {', '.join(campos)} WHERE id = ?"
            cursor.execute(query, tuple(valores))
            conn.commit()
        
        conn.close()
    
    def registrar_acesso(self, usuario_id):
        """Registra o último acesso do usuário"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        ultimo_acesso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute(
            "UPDATE usuarios SET ultimo_acesso = ? WHERE id = ?",
            (ultimo_acesso, usuario_id)
        )
        
        conn.commit()
        conn.close()
    
    def validar_credenciais(self, email, senha):
        """Valida as credenciais do usuário"""
        usuario = self.buscar_por_email(email)
        
        if not usuario:
            return None
        
        # Em um sistema real, usaríamos bcrypt para verificar a senha
        if usuario['senha'] == senha:
            return usuario['id']
        
        return None
    
    def criar_sessao(self, usuario_id, ip_address=None, user_agent=None):
        """Cria uma nova sessão para o usuário"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        import secrets
        token = secrets.token_hex(32)
        
        data_criacao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Sessão expira em 30 dias
        data_expiracao = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute(
            "INSERT INTO sessoes (usuario_id, token, data_criacao, data_expiracao, ip_address, user_agent) VALUES (?, ?, ?, ?, ?, ?)",
            (usuario_id, token, data_criacao, data_expiracao, ip_address, user_agent)
        )
        
        conn.commit()
        conn.close()
        
        return token


class Despesa:
    """Classe para manipulação de despesas"""
    def __init__(self, db_path):
        self.db_path = db_path
    
    def criar(self, usuario_id, valor, categoria=None, descricao=None, data=None, 
             forma_pagamento=None, parcelado=0, num_parcelas=1, mensagem_original=None):
        """Cria uma nova despesa"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Define valores padrão
        if data is None:
            data = datetime.now().strftime("%Y-%m-%d")
        
        if descricao is None:
            descricao = "Despesa sem descrição"
        
        if categoria is None:
            categoria = "outros"
        
        data_criacao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute('''
        INSERT INTO despesas 
        (usuario_id, valor, categoria, descricao, data, forma_pagamento, parcelado, num_parcelas, data_criacao, mensagem_original)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            usuario_id, valor, categoria, descricao, data, forma_pagamento, 
            parcelado, num_parcelas, data_criacao, mensagem_original
        ))
        
        conn.commit()
        despesa_id = cursor.lastrowid
        conn.close()
        
        return despesa_id
    
    def buscar(self, usuario_id, data_inicio=None, data_fim=None, categoria=None, limit=None):
        """Busca despesas do usuário com filtros opcionais"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM despesas WHERE usuario_id = ?"
        params = [usuario_id]
        
        if data_inicio:
            query += " AND data >= ?"
            params.append(data_inicio)
        
        if data_fim:
            query += " AND data <= ?"
            params.append(data_fim)
        
        if categoria:
            query += " AND categoria = ?"
            params.append(categoria)
        
        query += " ORDER BY data DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, params)
        despesas = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return despesas
    
    def buscar_por_id(self, despesa_id):
        """Busca uma despesa pelo ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM despesas WHERE id = ?", (despesa_id,))
        despesa = cursor.fetchone()
        
        conn.close()
        
        return dict(despesa) if despesa else None
    
    def atualizar(self, despesa_id, **kwargs):
        """Atualiza os dados de uma despesa"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        campos_permitidos = [
            'valor', 'categoria', 'descricao', 'data', 
            'forma_pagamento', 'parcelado', 'num_parcelas'
        ]
        
        # Filtra apenas os campos válidos
        campos = []
        valores = []
        
        for campo, valor in kwargs.items():
            if campo in campos_permitidos and valor is not None:
                campos.append(f"{campo} = ?")
                valores.append(valor)
        
        # Adiciona o ID da despesa aos valores
        valores.append(despesa_id)
        
        if campos:
            query = f"UPDATE despesas SET {', '.join(campos)} WHERE id = ?"
            cursor.execute(query, tuple(valores))
            conn.commit()
        
        conn.close()
    
    def excluir(self, despesa_id):
        """Exclui uma despesa"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM despesas WHERE id = ?", (despesa_id,))
        
        conn.commit()
        rows_affected = cursor.rowcount
        conn.close()
        
        return rows_affected > 0
    
    def total_por_categoria(self, usuario_id, data_inicio=None, data_fim=None):
        """Retorna o total de despesas agrupadas por categoria"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = """
        SELECT categoria, SUM(valor) as total
        FROM despesas
        WHERE usuario_id = ?
        """
        params = [usuario_id]
        
        if data_inicio:
            query += " AND data >= ?"
            params.append(data_inicio)
        
        if data_fim:
            query += " AND data <= ?"
            params.append(data_fim)
        
        query += " GROUP BY categoria ORDER BY total DESC"
        
        cursor.execute(query, params)
        resultado = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return resultado
    
    def total_por_dia(self, usuario_id, data_inicio=None, data_fim=None):
        """Retorna o total de despesas agrupadas por dia"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = """
        SELECT data, SUM(valor) as total
        FROM despesas
        WHERE usuario_id = ?
        """
        params = [usuario_id]
        
        if data_inicio:
            query += " AND data >= ?"
            params.append(data_inicio)
        
        if data_fim:
            query += " AND data <= ?"
            params.append(data_fim)
        
        query += " GROUP BY data ORDER BY data"
        
        cursor.execute(query, params)
        resultado = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return resultado
    
    def total_periodo(self, usuario_id, data_inicio=None, data_fim=None):
        """Retorna o total de despesas no período"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
        SELECT SUM(valor) as total
        FROM despesas
        WHERE usuario_id = ?
        """
        params = [usuario_id]
        
        if data_inicio:
            query += " AND data >= ?"
            params.append(data_inicio)
        
        if data_fim:
            query += " AND data <= ?"
            params.append(data_fim)
        
        cursor.execute(query, params)
        resultado = cursor.fetchone()
        
        conn.close()
        return resultado[0] if resultado and resultado[0] else 0


class Receita:
    """Classe para manipulação de receitas"""
    def __init__(self, db_path):
        self.db_path = db_path
    
    def criar(self, usuario_id, valor, categoria, descricao=None, data=None, recorrente=0, periodicidade=None):
        """Cria uma nova receita"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Define valores padrão
        if data is None:
            data = datetime.now().strftime("%Y-%m-%d")
        
        if descricao is None:
            descricao = "Receita sem descrição"
        
        data_criacao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute('''
        INSERT INTO receitas 
        (usuario_id, valor, categoria, descricao, data, data_criacao, recorrente, periodicidade)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            usuario_id, valor, categoria, descricao, data, 
            data_criacao, recorrente, periodicidade
        ))
        
        conn.commit()
        receita_id = cursor.lastrowid
        conn.close()
        
        return receita_id
    
    def buscar(self, usuario_id, data_inicio=None, data_fim=None, categoria=None, limit=None):
        """Busca receitas do usuário com filtros opcionais"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM receitas WHERE usuario_id = ?"
        params = [usuario_id]
        
        if data_inicio:
            query += " AND data >= ?"
            params.append(data_inicio)
        
        if data_fim:
            query += " AND data <= ?"
            params.append(data_fim)
        
        if categoria:
            query += " AND categoria = ?"
            params.append(categoria)
        
        query += " ORDER BY data DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, params)
        receitas = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return receitas
    
    def total_periodo(self, usuario_id, data_inicio=None, data_fim=None):
        """Retorna o total de receitas no período"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
        SELECT SUM(valor) as total
        FROM receitas
        WHERE usuario_id = ?
        """
        params = [usuario_id]
        
        if data_inicio:
            query += " AND data >= ?"
            params.append(data_inicio)
        
        if data_fim:
            query += " AND data <= ?"
            params.append(data_fim)
        
        cursor.execute(query, params)
        resultado = cursor.fetchone()
        
        conn.close()
        return resultado[0] if resultado and resultado[0] else 0


class TextProcessor:
    """Classe para processamento de texto e extração de informações de despesas"""
    def __init__(self):
        # Categorias e palavras-chave
        self.categorias = {
            "alimentação": ["comida", "almoço", "jantar", "lanche", "restaurante", "mercado", "supermercado"],
            "transporte": ["uber", "99", "táxi", "taxi", "ônibus", "onibus", "metrô", "metro", "combustível", "combustivel", "gasolina"],
            "moradia": ["aluguel", "condomínio", "condominio", "luz", "água", "agua", "gás", "gas", "internet"],
            "lazer": ["cinema", "teatro", "show", "netflix", "spotify", "streaming", "viagem"],
            "saúde": ["remédio", "remedio", "consulta", "médico", "medico", "hospital", "farmácia", "farmacia"],
            "educação": ["curso", "livro", "escola", "faculdade", "mensalidade"],
            "vestuário": ["roupa", "calçado", "calcado", "sapato", "tênis", "tenis"]
        }
    
    def extrair_informacoes_despesa(self, texto):
        """Extrai informações de despesa a partir de um texto"""
        from datetime import datetime, timedelta
        
        # Inicializa os dados da despesa
        dados_despesa = {
            "valor": None,
            "categoria": None,
            "descricao": texto,
            "data": datetime.now().strftime("%Y-%m-%d"),
            "forma_pagamento": None
        }
        
        # Converte para minúsculas
        texto_lower = texto.lower()
        
        # Extrai o valor monetário
        padroes_valor = [
            r'r\$\s*(\d+[.,]?\d*)',                    # R$ 50 ou R$50 ou R$ 50,90
            r'(\d+[.,]?\d*)\s*(?:reais|real)',         # 50 reais ou 50,90 reais
            r'(\d+[.,]?\d*)\s*(?:rs|r\$)',             # 50 rs ou 50,90 r$
            r'(?:valor|custo|preço|preco|paguei|gastei)\s*(?:de|:)?\s*(?:r\$)?\s*(\d+[.,]?\d*)', # valor de 50, paguei 50
            r'(\d+[.,]?\d*)',                          # Só um número (50 ou 50,90)
        ]
        
        for padrao in padroes_valor:
            matches = re.findall(padrao, texto_lower)
            if matches:
                try:
                    valor_str = matches[0].replace(',', '.')
                    dados_despesa["valor"] = float(valor_str)
                    break
                except (ValueError, IndexError):
                    continue
        
        # Se não encontrou valor, retorna None
        if dados_despesa["valor"] is None:
            return None
        
        # Extrai categoria baseada em palavras-chave
        for categoria, palavras_chave in self.categorias.items():
            for palavra in palavras_chave:
                if palavra in texto_lower:
                    dados_despesa["categoria"] = categoria
                    break
            if dados_despesa["categoria"]:
                break
        
        # Se não encontrou categoria, usa "outros"
        if not dados_despesa["categoria"]:
            dados_despesa["categoria"] = "outros"
        
        # Extrai data
        padroes_data = [
            r'(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?',  # 10/05 ou 10/05/2023
            r'(?:hoje|ontem|amanhã|amanha)'              # hoje, ontem, amanhã
        ]
        
        for padrao in padroes_data:
            matches = re.findall(padrao, texto_lower)
            if matches:
                if isinstance(matches[0], tuple) and len(matches[0]) >= 2:
                    try:
                        dia, mes, ano = matches[0]
                        if not ano:
                            ano = datetime.now().year
                        elif len(ano) == 2:
                            ano = f"20{ano}"
                        
                        data_obj = datetime(int(ano), int(mes), int(dia))
                        dados_despesa["data"] = data_obj.strftime("%Y-%m-%d")
                        break
                    except (ValueError, IndexError):
                        continue
                elif isinstance(matches[0], str) or (isinstance(matches[0], tuple) and len(matches[0]) == 1):
                    data_palavra = matches[0] if isinstance(matches[0], str) else matches[0][0]
                    if data_palavra in ['hoje', 'today']:
                        dados_despesa["data"] = datetime.now().strftime("%Y-%m-%d")
                    elif data_palavra in ['ontem', 'yesterday']:
                        ontem = datetime.now() - timedelta(days=1)
                        dados_despesa["data"] = ontem.strftime("%Y-%m-%d")
                    elif data_palavra in ['amanhã', 'amanha', 'tomorrow']:
                        amanha = datetime.now() + timedelta(days=1)
                        dados_despesa["data"] = amanha.strftime("%Y-%m-%d")
                    break
        
        # Se "hoje" estiver no texto, define a data como hoje
        if "hoje" in texto_lower:
            dados_despesa["data"] = datetime.now().strftime("%Y-%m-%d")
        
        # Extrai forma de pagamento
        padroes_pagamento = [
            r'(?:pag(?:amento|uei|ar|o)|comprei)(?:\s+(?:com|no|usando|via|por|pelo))?\s+(cartão|cartao|crédito|credito|débito|debito|dinheiro|pix|boleto)',
            r'(?:no|com|usando|via|por|pelo)\s+(cartão|cartao|crédito|credito|débito|debito|dinheiro|pix|boleto)'
        ]
        
        for padrao in padroes_pagamento:
            matches = re.findall(padrao, texto_lower)
            if matches:
                forma = matches[0].lower()
                if forma in ['cartão', 'cartao']:
                    dados_despesa["forma_pagamento"] = "Cartão"
                elif forma in ['crédito', 'credito']:
                    dados_despesa["forma_pagamento"] = "Crédito"
                elif forma in ['débito', 'debito']:
                    dados_despesa["forma_pagamento"] = "Débito"
                elif forma == 'dinheiro':
                    dados_despesa["forma_pagamento"] = "Dinheiro"
                elif forma == 'pix':
                    dados_despesa["forma_pagamento"] = "PIX"
                elif forma == 'boleto':
                    dados_despesa["forma_pagamento"] = "Boleto"
                break
        
        return dados_despesa
    
    def get_categoria_emoji(self, categoria):
        """Retorna um emoji para cada categoria"""
        emojis = {
            "alimentação": "🍽️",
            "transporte": "🚗",
            "moradia": "🏠",
            "saúde": "⚕️",
            "educação": "📚",
            "lazer": "🎭",
            "vestuário": "👕",
            "salario": "💰",
            "freelance": "💼",
            "investimento": "📈",
            "presente": "🎁",
            "outros": "📦"
        }
        
        return emojis.get(categoria, "📦")
    
    # Métodos a serem adicionados à classe Usuario no arquivo models.py

def mudar_plano(self, usuario_id, plano, periodo='mensal', valor=0.0, forma_pagamento=None):
    """
    Muda o plano do usuário e registra a assinatura
    
    Args:
        usuario_id: ID do usuário
        plano: Nome do plano ('gratuito', 'premium', 'profissional')
        periodo: Período de assinatura ('mensal' ou 'anual')
        valor: Valor da assinatura
        forma_pagamento: Forma de pagamento utilizada
    
    Returns:
        int: ID da assinatura criada ou None se for plano gratuito
    """
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    
    # Atualiza o plano do usuário
    self.atualizar(usuario_id, plano=plano)
    
    # Se for plano gratuito, apenas registra a mudança de plano
    if plano == 'gratuito':
        # Cancela assinaturas ativas
        cursor.execute(
            "UPDATE assinaturas SET status = 'cancelado' WHERE usuario_id = ? AND status = 'ativo'",
            (usuario_id,)
        )
        conn.commit()
        conn.close()
        return None
    
    # Define datas de início e fim da assinatura
    data_inicio = datetime.now().strftime("%Y-%m-%d")
    if periodo == 'anual':
        data_fim = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
    else:  # mensal
        data_fim = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    
    # Verifica se já existe uma assinatura ativa
    cursor.execute(
        "SELECT id FROM assinaturas WHERE usuario_id = ? AND status = 'ativo'",
        (usuario_id,)
    )
    assinatura_antiga = cursor.fetchone()
    
    # Se existir, cancela a assinatura atual
    if assinatura_antiga:
        cursor.execute(
            "UPDATE assinaturas SET status = 'cancelado' WHERE id = ?",
            (assinatura_antiga[0],)
        )
    
    # Cria a nova assinatura
    cursor.execute(
        "INSERT INTO assinaturas (usuario_id, plano, data_inicio, data_fim, valor, status, forma_pagamento) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (usuario_id, plano, data_inicio, data_fim, valor, 'ativo', forma_pagamento)
    )
    
    # Obtém o ID da nova assinatura
    assinatura_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return assinatura_id

def cancelar_assinatura(self, usuario_id):
    """
    Cancela a assinatura ativa do usuário e reverte para o plano gratuito
    
    Args:
        usuario_id: ID do usuário
    
    Returns:
        bool: True se o cancelamento foi bem-sucedido, False caso contrário
    """
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    
    # Verifica se existe uma assinatura ativa
    cursor.execute(
        "SELECT id FROM assinaturas WHERE usuario_id = ? AND status = 'ativo'",
        (usuario_id,)
    )
    assinatura = cursor.fetchone()
    
    if not assinatura:
        conn.close()
        return False
    
    # Atualiza o status da assinatura para 'cancelado'
    cursor.execute(
        "UPDATE assinaturas SET status = 'cancelado' WHERE id = ?",
        (assinatura[0],)
    )
    
    # Atualiza o plano do usuário para 'gratuito'
    self.atualizar(usuario_id, plano='gratuito')
    
    conn.commit()
    conn.close()
    
    return True

def obter_assinatura_ativa(self, usuario_id):
    """
    Obtém a assinatura ativa do usuário
    
    Args:
        usuario_id: ID do usuário
    
    Returns:
        dict: Dados da assinatura ativa ou None se não houver
    """
    conn = sqlite3.connect(self.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM assinaturas WHERE usuario_id = ? AND status = 'ativo'",
        (usuario_id,)
    )
    assinatura = cursor.fetchone()
    
    conn.close()
    
    return dict(assinatura) if assinatura else None