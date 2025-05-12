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

    # Adicione essas tabelas à função init_db em models.py

    # Tabela para rastreamento de origem (referral)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuario_referral (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        origem TEXT NOT NULL,
        data_registro TEXT,
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
    )
    ''')

    # Tabela para cupons de desconto
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cupons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL UNIQUE,
        tipo TEXT NOT NULL,
        valor REAL NOT NULL,
        data_inicio TEXT NOT NULL,
        data_fim TEXT,
        limite_usos INTEGER,
        usos_atuais INTEGER DEFAULT 0,
        ativo INTEGER DEFAULT 1,
        data_criacao TEXT
    )
    ''')

    # Tabela para uso de cupons
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cupom_usos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cupom_id INTEGER NOT NULL,
        usuario_id INTEGER NOT NULL,
        data_uso TEXT NOT NULL,
        FOREIGN KEY (cupom_id) REFERENCES cupons (id),
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS lembretes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        titulo TEXT NOT NULL,
        descricao TEXT,
        data TEXT NOT NULL,
        valor REAL,
        notificacao INTEGER DEFAULT 0,
        recorrente INTEGER DEFAULT 0,
        periodicidade TEXT,
        tipo_perfil TEXT DEFAULT 'pessoal',
        concluido INTEGER DEFAULT 0,
        data_criacao TEXT,
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categorias_personalizadas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        nome TEXT NOT NULL,
        nome_slug TEXT NOT NULL,
        icone TEXT,
        cor TEXT,
        tipo TEXT NOT NULL,
        tipo_perfil TEXT DEFAULT 'pessoal',
        data_criacao TEXT,
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS membros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        nome TEXT NOT NULL,
        email TEXT NOT NULL,
        celular TEXT,
        permissao TEXT NOT NULL,
        tipo_grupo TEXT NOT NULL,
        convite_aceito INTEGER DEFAULT 0,
        usuario_principal INTEGER DEFAULT 0,
        data_criacao TEXT,
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
    )
    ''')
    # cursor.execute('''
    # ALTER TABLE despesas ADD COLUMN foto_url TEXT DEFAULT NULL
    # ''')
    # cursor.execute('''
    # ALTER TABLE despesas ADD COLUMN audio_url TEXT DEFAULT NULL
    # ''')
    # cursor.execute('''
    # ALTER TABLE despesas ADD COLUMN ocr_data TEXT DEFAULT NULL
    # ''')
    
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
    
        # Modificação para init_db: adicione coluna admin na tabela usuarios
        cursor.execute('ALTER TABLE usuarios ADD COLUMN admin INTEGER DEFAULT 0')

    # Métodos adicionais para a classe Usuario:

    def definir_admin(self, usuario_id, admin=True):
        """
        Define um usuário como administrador
        
        Args:
            usuario_id: ID do usuário
            admin: True para tornar admin, False para remover
            
        Returns:
            bool: True se bem-sucedido
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE usuarios SET admin = ? WHERE id = ?",
            (1 if admin else 0, usuario_id)
        )
        
        conn.commit()
        conn.close()
        
        return True

    def listar_admins(self):
        """
        Lista todos os usuários administradores
        
        Returns:
            list: Lista de usuários administradores
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM usuarios WHERE admin = 1")
        
        admins = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return admins

    def eh_admin(self, usuario_id):
        """
        Verifica se um usuário é administrador
        
        Args:
            usuario_id: ID do usuário
            
        Returns:
            bool: True se for admin, False caso contrário
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT admin FROM usuarios WHERE id = ?", (usuario_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result is not None and result[0] == 1

class Membro:
    """Classe para manipulação de membros (família ou empresa)"""
    def __init__(self, db_path):
        self.db_path = db_path
    
    def criar(self, usuario_id, nome, email, tipo_grupo, permissao='visualizador', celular=None, usuario_principal=0):
        """Cria um novo membro"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        data_criacao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute('''
        INSERT INTO membros 
        (usuario_id, nome, email, celular, permissao, tipo_grupo, usuario_principal, data_criacao)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            usuario_id, nome, email, celular, permissao, tipo_grupo, usuario_principal, data_criacao
        ))
        
        conn.commit()
        membro_id = cursor.lastrowid
        conn.close()
        
        return membro_id
    
    def buscar(self, usuario_id, tipo_grupo=None):
        """Busca membros do usuário com filtros opcionais"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM membros WHERE usuario_id = ?"
        params = [usuario_id]
        
        if tipo_grupo:
            query += " AND tipo_grupo = ?"
            params.append(tipo_grupo)
        
        query += " ORDER BY usuario_principal DESC, nome ASC"
        
        cursor.execute(query, params)
        membros = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return membros
    
    def buscar_por_id(self, membro_id):
        """Busca um membro pelo ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM membros WHERE id = ?", (membro_id,))
        membro = cursor.fetchone()
        
        conn.close()
        
        return dict(membro) if membro else None
    
    def buscar_por_email(self, email, tipo_grupo=None):
        """Busca um membro pelo email"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM membros WHERE email = ?"
        params = [email]
        
        if tipo_grupo:
            query += " AND tipo_grupo = ?"
            params.append(tipo_grupo)
        
        cursor.execute(query, params)
        membro = cursor.fetchone()
        
        conn.close()
        
        return dict(membro) if membro else None
    
    def atualizar(self, membro_id, **kwargs):
        """Atualiza os dados de um membro"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        campos_permitidos = [
            'nome', 'email', 'celular', 'permissao', 'convite_aceito'
        ]
        
        # Filtra apenas os campos válidos
        campos = []
        valores = []
        
        for campo, valor in kwargs.items():
            if campo in campos_permitidos and valor is not None:
                campos.append(f"{campo} = ?")
                valores.append(valor)
        
        # Adiciona o ID do membro aos valores
        valores.append(membro_id)
        
        if campos:
            query = f"UPDATE membros SET {', '.join(campos)} WHERE id = ?"
            cursor.execute(query, tuple(valores))
            conn.commit()
        
        conn.close()
    
    def excluir(self, membro_id):
        """Exclui um membro"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Verifica se é o usuário principal
        cursor.execute("SELECT usuario_principal FROM membros WHERE id = ?", (membro_id,))
        resultado = cursor.fetchone()
        
        if resultado and resultado[0] == 1:
            conn.close()
            return False, "Não é possível excluir o usuário principal."
        
        cursor.execute("DELETE FROM membros WHERE id = ?", (membro_id,))
        
        conn.commit()
        rows_affected = cursor.rowcount
        conn.close()
        
        return True, rows_affected > 0
    
    def criar_usuario_principal(self, usuario_id):
        """Cria o registro do usuário principal"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Busca os dados do usuário
        cursor.execute("SELECT nome, email, celular FROM usuarios WHERE id = ?", (usuario_id,))
        usuario = cursor.fetchone()
        
        if not usuario:
            conn.close()
            return None
        
        nome, email, celular = usuario
        
        # Cria um registro para família
        self.criar(
            usuario_id=usuario_id,
            nome=nome,
            email=email,
            celular=celular,
            permissao='admin',
            tipo_grupo='familia',
            usuario_principal=1
        )
        
        # Cria um registro para empresa
        self.criar(
            usuario_id=usuario_id,
            nome=nome,
            email=email,
            celular=celular,
            permissao='admin',
            tipo_grupo='empresa',
            usuario_principal=1
        )
        
        conn.close()
        return True
    
    def enviar_convite(self, membro_id):
        """Envia um convite para o membro"""
        membro = self.buscar_por_id(membro_id)
        
        if not membro:
            return False, "Membro não encontrado."
        
        # Se tiver celular, envia por WhatsApp
        if membro.get('celular'):
            # Aqui implementaria o envio de convite por WhatsApp
            pass
        
        # Envia por email
        # Aqui implementaria o envio de convite por email
        
        return True, "Convite enviado com sucesso."
    
class Despesa:
    """Classe para manipulação de despesas"""
    def __init__(self, db_path):
        self.db_path = db_path
    
    def criar(self, usuario_id, valor, categoria=None, descricao=None, data=None, 
             forma_pagamento=None, parcelado=0, num_parcelas=1, mensagem_original=None, 
             tipo_perfil='pessoal', foto_url=None, audio_url=None, ocr_data=None):
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
        
        # Serializa ocr_data para JSON se for um dicionário
        if ocr_data is not None and isinstance(ocr_data, dict):
            ocr_data = json.dumps(ocr_data)
        
        cursor.execute('''
        INSERT INTO despesas 
        (usuario_id, valor, categoria, descricao, data, forma_pagamento, parcelado, 
        num_parcelas, data_criacao, mensagem_original, tipo_perfil, foto_url, audio_url, ocr_data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            usuario_id, valor, categoria, descricao, data, forma_pagamento, 
            parcelado, num_parcelas, data_criacao, mensagem_original, tipo_perfil, 
            foto_url, audio_url, ocr_data
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
    
    def total_por_categoria(self, usuario_id, data_inicio=None, data_fim=None, tipo_perfil=None):
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
            
        if tipo_perfil:
            query += " AND (tipo_perfil = ? OR tipo_perfil IS NULL)"
            params.append(tipo_perfil)
        
        query += " GROUP BY categoria ORDER BY total DESC"
        
        cursor.execute(query, params)
        resultado = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return resultado
    
    def total_por_dia(self, usuario_id, data_inicio=None, data_fim=None, tipo_perfil=None):
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
            
        if tipo_perfil:
            query += " AND (tipo_perfil = ? OR tipo_perfil IS NULL)"
            params.append(tipo_perfil)
        
        query += " GROUP BY data ORDER BY data"
        
        cursor.execute(query, params)
        resultado = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return resultado
    
    def total_periodo(self, usuario_id, data_inicio=None, data_fim=None, tipo_perfil=None):
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
            
        if tipo_perfil:
            query += " AND (tipo_perfil = ? OR tipo_perfil IS NULL)"
            params.append(tipo_perfil)
        
        cursor.execute(query, params)
        resultado = cursor.fetchone()
        
        conn.close()
        return resultado[0] if resultado and resultado[0] else 0

    
class CategoriaPersonalizada:
    """Classe para manipulação de categorias personalizadas"""
    def __init__(self, db_path):
        self.db_path = db_path
    
    def criar(self, usuario_id, nome, tipo, icone='📦', cor='#28a745', tipo_perfil='pessoal'):
        """Cria uma nova categoria personalizada"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Cria um slug para o nome (para usar em classes CSS)
        nome_slug = self.criar_slug(nome)
        
        data_criacao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute('''
        INSERT INTO categorias_personalizadas 
        (usuario_id, nome, nome_slug, icone, cor, tipo, tipo_perfil, data_criacao)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            usuario_id, nome, nome_slug, icone, cor, tipo, tipo_perfil, data_criacao
        ))
        
        conn.commit()
        categoria_id = cursor.lastrowid
        conn.close()
        
        return categoria_id
    
    def buscar(self, usuario_id, tipo=None, tipo_perfil=None):
        """Busca categorias do usuário com filtros opcionais"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM categorias_personalizadas WHERE usuario_id = ?"
        params = [usuario_id]
        
        if tipo:
            query += " AND tipo = ?"
            params.append(tipo)
        
        if tipo_perfil:
            query += " AND tipo_perfil = ?"
            params.append(tipo_perfil)
        
        query += " ORDER BY nome ASC"
        
        cursor.execute(query, params)
        categorias = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return categorias
    
    def buscar_por_id(self, categoria_id):
        """Busca uma categoria pelo ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM categorias_personalizadas WHERE id = ?", (categoria_id,))
        categoria = cursor.fetchone()
        
        conn.close()
        
        return dict(categoria) if categoria else None
    
    def atualizar(self, categoria_id, **kwargs):
        """Atualiza os dados de uma categoria"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        campos_permitidos = [
            'nome', 'icone', 'cor', 'tipo', 'tipo_perfil'
        ]
        
        # Atualiza o slug se o nome for alterado
        if 'nome' in kwargs:
            kwargs['nome_slug'] = self.criar_slug(kwargs['nome'])
        
        # Filtra apenas os campos válidos
        campos = []
        valores = []
        
        for campo, valor in kwargs.items():
            if campo in campos_permitidos and valor is not None:
                campos.append(f"{campo} = ?")
                valores.append(valor)
        
        # Adiciona o ID da categoria aos valores
        valores.append(categoria_id)
        
        if campos:
            query = f"UPDATE categorias_personalizadas SET {', '.join(campos)} WHERE id = ?"
            cursor.execute(query, tuple(valores))
            conn.commit()
        
        conn.close()
    
    def excluir(self, categoria_id):
        """Exclui uma categoria"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Primeiro verifica se existem transações usando esta categoria
        cursor.execute(
            "SELECT COUNT(*) FROM despesas WHERE categoria = (SELECT nome FROM categorias_personalizadas WHERE id = ?)",
            (categoria_id,)
        )
        count_despesas = cursor.fetchone()[0]
        
        cursor.execute(
            "SELECT COUNT(*) FROM receitas WHERE categoria = (SELECT nome FROM categorias_personalizadas WHERE id = ?)",
            (categoria_id,)
        )
        count_receitas = cursor.fetchone()[0]
        
        # Se existem transações, não permite excluir
        if count_despesas > 0 or count_receitas > 0:
            conn.close()
            return False, "Não é possível excluir esta categoria pois existem transações associadas a ela."
        
        # Se não existem transações, exclui a categoria
        cursor.execute("DELETE FROM categorias_personalizadas WHERE id = ?", (categoria_id,))
        
        conn.commit()
        rows_affected = cursor.rowcount
        conn.close()
        
        return True, rows_affected > 0
    
    def criar_slug(self, texto):
        """Cria um slug para o nome da categoria"""
        # Remove acentos
        import unicodedata
        texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
        
        # Converte para minúsculas e substitui espaços por underscores
        texto = texto.lower().replace(' ', '_')
        
        # Remove caracteres especiais
        import re
        texto = re.sub(r'[^a-z0-9_]', '', texto)
        
        return texto
    
# Classe para manipulação de lembretes
class Lembrete:
    """Classe para manipulação de lembretes"""
    def __init__(self, db_path):
        self.db_path = db_path
    
    def criar(self, usuario_id, titulo, data, notificacao=0, descricao=None, valor=None, 
             recorrente=0, periodicidade=None, tipo_perfil='pessoal'):
        """Cria um novo lembrete"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        data_criacao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute('''
        INSERT INTO lembretes 
        (usuario_id, titulo, descricao, data, valor, notificacao, recorrente, periodicidade, tipo_perfil, data_criacao)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            usuario_id, titulo, descricao, data, valor, notificacao, 
            recorrente, periodicidade, tipo_perfil, data_criacao
        ))
        
        conn.commit()
        lembrete_id = cursor.lastrowid
        conn.close()
        
        return lembrete_id
    
    def buscar(self, usuario_id, data_inicio=None, data_fim=None, tipo_perfil=None, concluido=None):
        """Busca lembretes do usuário com filtros opcionais"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM lembretes WHERE usuario_id = ?"
        params = [usuario_id]
        
        if data_inicio:
            query += " AND data >= ?"
            params.append(data_inicio)
        
        if data_fim:
            query += " AND data <= ?"
            params.append(data_fim)
        
        if tipo_perfil:
            query += " AND tipo_perfil = ?"
            params.append(tipo_perfil)
        
        if concluido is not None:
            query += " AND concluido = ?"
            params.append(concluido)
        
        query += " ORDER BY data ASC"
        
        cursor.execute(query, params)
        lembretes = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return lembretes
    
    def buscar_por_id(self, lembrete_id):
        """Busca um lembrete pelo ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM lembretes WHERE id = ?", (lembrete_id,))
        lembrete = cursor.fetchone()
        
        conn.close()
        
        return dict(lembrete) if lembrete else None
    
    def atualizar(self, lembrete_id, **kwargs):
        """Atualiza os dados de um lembrete"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        campos_permitidos = [
            'titulo', 'descricao', 'data', 'valor', 'notificacao',
            'recorrente', 'periodicidade', 'tipo_perfil', 'concluido'
        ]
        
        # Filtra apenas os campos válidos
        campos = []
        valores = []
        
        for campo, valor in kwargs.items():
            if campo in campos_permitidos and valor is not None:
                campos.append(f"{campo} = ?")
                valores.append(valor)
        
        # Adiciona o ID do lembrete aos valores
        valores.append(lembrete_id)
        
        if campos:
            query = f"UPDATE lembretes SET {', '.join(campos)} WHERE id = ?"
            cursor.execute(query, tuple(valores))
            conn.commit()
        
        conn.close()
    
    def excluir(self, lembrete_id):
        """Exclui um lembrete"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM lembretes WHERE id = ?", (lembrete_id,))
        
        conn.commit()
        rows_affected = cursor.rowcount
        conn.close()
        
        return rows_affected > 0
    
    def marcar_como_concluido(self, lembrete_id, concluido=1):
        """Marca um lembrete como concluído ou não concluído"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE lembretes SET concluido = ? WHERE id = ?",
            (concluido, lembrete_id)
        )
        
        conn.commit()
        rows_affected = cursor.rowcount
        conn.close()
        
        return rows_affected > 0
    
    def criar_recorrencia(self, lembrete_id):
        """Cria um novo lembrete com base em um lembrete recorrente"""
        # Busca o lembrete original
        lembrete_original = self.buscar_por_id(lembrete_id)
        
        if not lembrete_original or not lembrete_original.get('recorrente'):
            return None
        
        # Calcula a próxima data baseada na periodicidade
        periodicidade = lembrete_original.get('periodicidade')
        data_original = datetime.strptime(lembrete_original.get('data'), "%Y-%m-%d")
        
        if periodicidade == 'diaria':
            proxima_data = data_original + timedelta(days=1)
        elif periodicidade == 'semanal':
            proxima_data = data_original + timedelta(days=7)
        elif periodicidade == 'quinzenal':
            proxima_data = data_original + timedelta(days=15)
        elif periodicidade == 'mensal':
            # Calcula o mesmo dia do próximo mês
            if data_original.month == 12:
                proxima_data = data_original.replace(year=data_original.year + 1, month=1)
            else:
                proxima_data = data_original.replace(month=data_original.month + 1)
        elif periodicidade == 'anual':
            proxima_data = data_original.replace(year=data_original.year + 1)
        else:
            # Se a periodicidade não for reconhecida, usa mensal
            if data_original.month == 12:
                proxima_data = data_original.replace(year=data_original.year + 1, month=1)
            else:
                proxima_data = data_original.replace(month=data_original.month + 1)
        
        # Formata a data
        proxima_data_str = proxima_data.strftime("%Y-%m-%d")
        
        # Cria o novo lembrete
        novo_lembrete_id = self.criar(
            usuario_id=lembrete_original.get('usuario_id'),
            titulo=lembrete_original.get('titulo'),
            data=proxima_data_str,
            notificacao=lembrete_original.get('notificacao'),
            descricao=lembrete_original.get('descricao'),
            valor=lembrete_original.get('valor'),
            recorrente=lembrete_original.get('recorrente'),
            periodicidade=lembrete_original.get('periodicidade'),
            tipo_perfil=lembrete_original.get('tipo_perfil')
        )
        
        return novo_lembrete_id
    
    def lembretes_vencidos_hoje(self, usuario_id=None):
        """Retorna os lembretes que vencem hoje"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Data de hoje
        hoje = datetime.now().strftime("%Y-%m-%d")
        
        # Query base
        query = "SELECT * FROM lembretes WHERE data = ? AND concluido = 0"
        params = [hoje]
        
        # Se tiver usuário específico
        if usuario_id:
            query += " AND usuario_id = ?"
            params.append(usuario_id)
        
        cursor.execute(query, params)
        lembretes = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return lembretes
    
    def criar_notificacoes(self):
        """Cria notificações para lembretes com base no campo 'notificacao'"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Busca lembretes não concluídos com data futura
        hoje = datetime.now().strftime("%Y-%m-%d")
        
        cursor.execute(
            "SELECT * FROM lembretes WHERE concluido = 0 AND data > ?",
            (hoje,)
        )
        
        lembretes = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Lista para armazenar as notificações
        notificacoes = []
        
        # Para cada lembrete, calcula a data de notificação
        for lembrete in lembretes:
            dias_antes = lembrete.get('notificacao', 0)
            data_lembrete = datetime.strptime(lembrete.get('data'), "%Y-%m-%d")
            data_notificacao = data_lembrete - timedelta(days=dias_antes)
            
            # Se a data de notificação for hoje ou já passou, mas não chegou na data final
            hoje_dt = datetime.now()
            hoje_dt = hoje_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            
            if hoje_dt <= data_notificacao < data_lembrete:
                notificacoes.append({
                    'lembrete_id': lembrete.get('id'),
                    'usuario_id': lembrete.get('usuario_id'),
                    'titulo': lembrete.get('titulo'),
                    'data': lembrete.get('data'),
                    'dias_restantes': (data_lembrete - hoje_dt).days,
                    'tipo_perfil': lembrete.get('tipo_perfil')
                })
        
        return notificacoes


class Receita:
    """Classe para manipulação de receitas"""
    def __init__(self, db_path):
        self.db_path = db_path
    
    def criar(self, usuario_id, valor, categoria, descricao=None, data=None, 
             recorrente=0, periodicidade=None, tipo_perfil='pessoal', 
             foto_url=None, audio_url=None):
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
        (usuario_id, valor, categoria, descricao, data, data_criacao, recorrente, 
        periodicidade, tipo_perfil, foto_url, audio_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            usuario_id, valor, categoria, descricao, data, 
            data_criacao, recorrente, periodicidade, tipo_perfil, 
            foto_url, audio_url
        ))
        
        conn.commit()
        receita_id = cursor.lastrowid
        conn.close()
        
        return receita_id
    
    def buscar(self, usuario_id, data_inicio=None, data_fim=None, categoria=None, limit=None, tipo_perfil=None):
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
            
        if tipo_perfil:
            query += " AND (tipo_perfil = ? OR tipo_perfil IS NULL)"
            params.append(tipo_perfil)
        
        query += " ORDER BY data DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, params)
        receitas = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return receitas
    
    def buscar_por_id(self, receita_id):
        """Busca uma receita pelo ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM receitas WHERE id = ?", (receita_id,))
        receita = cursor.fetchone()
        
        conn.close()
        
        return dict(receita) if receita else None
    
    def atualizar(self, receita_id, **kwargs):
        """Atualiza os dados de uma receita"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        campos_permitidos = [
            'valor', 'categoria', 'descricao', 'data', 
            'recorrente', 'periodicidade', 'tipo_perfil'
        ]
        
        # Filtra apenas os campos válidos
        campos = []
        valores = []
        
        for campo, valor in kwargs.items():
            if campo in campos_permitidos and valor is not None:
                campos.append(f"{campo} = ?")
                valores.append(valor)
        
        # Adiciona o ID da receita aos valores
        valores.append(receita_id)
        
        if campos:
            query = f"UPDATE receitas SET {', '.join(campos)} WHERE id = ?"
            cursor.execute(query, tuple(valores))
            conn.commit()
        
        conn.close()
    
    def excluir(self, receita_id):
        """Exclui uma receita"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM receitas WHERE id = ?", (receita_id,))
        
        conn.commit()
        rows_affected = cursor.rowcount
        conn.close()
        
        return rows_affected > 0
    
    def total_por_categoria(self, usuario_id, data_inicio=None, data_fim=None, tipo_perfil=None):
        """Retorna o total de receitas agrupadas por categoria"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = """
        SELECT categoria, SUM(valor) as total
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
            
        if tipo_perfil:
            query += " AND (tipo_perfil = ? OR tipo_perfil IS NULL)"
            params.append(tipo_perfil)
        
        query += " GROUP BY categoria ORDER BY total DESC"
        
        cursor.execute(query, params)
        resultado = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return resultado
    
    def total_por_dia(self, usuario_id, data_inicio=None, data_fim=None, tipo_perfil=None):
        """Retorna o total de receitas agrupadas por dia"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = """
        SELECT data, SUM(valor) as total
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
            
        if tipo_perfil:
            query += " AND (tipo_perfil = ? OR tipo_perfil IS NULL)"
            params.append(tipo_perfil)
        
        query += " GROUP BY data ORDER BY data"
        
        cursor.execute(query, params)
        resultado = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return resultado
    
    def total_periodo(self, usuario_id, data_inicio=None, data_fim=None, tipo_perfil=None):
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
            
        if tipo_perfil:
            query += " AND (tipo_perfil = ? OR tipo_perfil IS NULL)"
            params.append(tipo_perfil)
        
        cursor.execute(query, params)
        resultado = cursor.fetchone()
        
        conn.close()
        return resultado[0] if resultado and resultado[0] else 0

    class Cupom:
        """Classe para gerenciar cupons de desconto"""
        def __init__(self, db_path):
            self.db_path = db_path
        
        def criar(self, codigo, tipo, valor, data_inicio, data_fim=None, limite_usos=None):
            """
            Cria um novo cupom de desconto
            
            Args:
                codigo: Código do cupom (string única)
                tipo: Tipo do cupom ('trial', 'desconto_percentual', 'desconto_fixo')
                valor: Valor do cupom (dias para trial, porcentagem ou valor fixo para desconto)
                data_inicio: Data de início de validade (YYYY-MM-DD)
                data_fim: Data de fim de validade (YYYY-MM-DD), opcional
                limite_usos: Limite de vezes que o cupom pode ser usado, opcional
                
            Returns:
                int: ID do cupom criado ou None se falhar
            """
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            data_criacao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            try:
                cursor.execute(
                    """
                    INSERT INTO cupons 
                    (codigo, tipo, valor, data_inicio, data_fim, limite_usos, data_criacao, ativo) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (codigo, tipo, valor, data_inicio, data_fim, limite_usos, data_criacao)
                )
                
                cupom_id = cursor.lastrowid
                conn.commit()
                conn.close()
                
                return cupom_id
            except sqlite3.IntegrityError:
                # O código do cupom já existe
                conn.close()
                return None
        
        def validar(self, codigo):
            """
            Valida se um cupom é válido para uso
            
            Args:
                codigo: Código do cupom
                
            Returns:
                dict: Dados do cupom se válido, None caso contrário
            """
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            hoje = datetime.now().strftime("%Y-%m-%d")
            
            cursor.execute(
                """
                SELECT * FROM cupons 
                WHERE codigo = ? AND ativo = 1 
                AND (data_fim IS NULL OR data_fim >= ?) 
                AND data_inicio <= ?
                """,
                (codigo, hoje, hoje)
            )
            
            cupom = cursor.fetchone()
            
            if not cupom:
                conn.close()
                return None
            
            # Verifica se o cupom atingiu o limite de usos
            if cupom['limite_usos'] is not None and cupom['usos_atuais'] >= cupom['limite_usos']:
                conn.close()
                return None
            
            conn.close()
            return dict(cupom)
        
        def aplicar(self, cupom_id, usuario_id):
            """
            Aplica um cupom a um usuário
            
            Args:
                cupom_id: ID do cupom
                usuario_id: ID do usuário
                
            Returns:
                bool: True se aplicado com sucesso, False caso contrário
            """
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verifica se o usuário já usou este cupom
            cursor.execute(
                "SELECT id FROM cupom_usos WHERE cupom_id = ? AND usuario_id = ?",
                (cupom_id, usuario_id)
            )
            
            if cursor.fetchone():
                conn.close()
                return False
            
            try:
                # Registra o uso do cupom
                data_uso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                cursor.execute(
                    "INSERT INTO cupom_usos (cupom_id, usuario_id, data_uso) VALUES (?, ?, ?)",
                    (cupom_id, usuario_id, data_uso)
                )
                
                # Incrementa o contador de usos
                cursor.execute(
                    "UPDATE cupons SET usos_atuais = usos_atuais + 1 WHERE id = ?",
                    (cupom_id,)
                )
                
                # Obtém os dados do cupom
                cursor.execute("SELECT * FROM cupons WHERE id = ?", (cupom_id,))
                cupom = cursor.fetchone()
                
                # Aplica o benefício do cupom ao usuário
                usuario_model = Usuario(self.db_path)
                usuario = usuario_model.buscar_por_id(usuario_id)
                
                if cupom[2] == 'trial':  # tipo 'trial'
                    dias_trial = int(cupom[3])  # valor do cupom (dias)
                    
                    # Define o plano como premium pelo período do trial
                    plano = 'premium'
                    data_inicio = datetime.now().strftime("%Y-%m-%d")
                    data_fim = (datetime.now() + timedelta(days=dias_trial)).strftime("%Y-%m-%d")
                    
                    # Insere uma assinatura temporária na tabela de assinaturas
                    cursor.execute(
                        """
                        INSERT INTO assinaturas 
                        (usuario_id, plano, data_inicio, data_fim, valor, status, forma_pagamento) 
                        VALUES (?, ?, ?, ?, 0, 'trial', 'cupom')
                        """,
                        (usuario_id, plano, data_inicio, data_fim)
                    )
                    
                    # Atualiza o plano do usuário
                    usuario_model.atualizar(usuario_id, plano=plano)
                
                # Outros tipos de cupom podem ser processados no momento do pagamento
                    
                conn.commit()
                conn.close()
                return True
            
            except Exception as e:
                print(f"Erro ao aplicar cupom: {e}")
                conn.rollback()
                conn.close()
                return False
        
        def listar_ativos(self):
            """
            Lista todos os cupons ativos
            
            Returns:
                list: Lista de cupons ativos
            """
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            hoje = datetime.now().strftime("%Y-%m-%d")
            
            cursor.execute(
                """
                SELECT * FROM cupons 
                WHERE ativo = 1 
                AND (data_fim IS NULL OR data_fim >= ?) 
                AND data_inicio <= ?
                ORDER BY data_criacao DESC
                """,
                (hoje, hoje)
            )
            
            cupons = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return cupons
        
        def desativar(self, cupom_id):
            """
            Desativa um cupom
            
            Args:
                cupom_id: ID do cupom
                
            Returns:
                bool: True se desativado com sucesso
            """
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "UPDATE cupons SET ativo = 0 WHERE id = ?",
                (cupom_id,)
            )
            
            conn.commit()
            conn.close()
            
            return True
    
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

class TextProcessor:
    """Classe para processamento de texto e extração de informações de despesas"""
    def __init__(self):
        # Categorias e palavras-chave
        self.categorias = {
            "alimentação": ["comida", "almoço", "jantar", "lanche", "restaurante", "mercado", 
                           "supermercado", "ifood", "refeição", "café", "padaria", "café da manhã", 
                           "cafeteria", "pizzaria", "bar", "lanchonete", "delivery", "fastfood", 
                           "hamburguer", "hamburger", "sushi", "churrasco", "sorvete", "sorveteria", 
                           "açaí", "acai", "feira", "pão", "padaria", "doce"],
            
            "transporte": ["uber", "99", "táxi", "taxi", "ônibus", "onibus", "metrô", "metro", 
                          "combustível", "combustivel", "gasolina", "alcool", "etanol", "diesel",
                          "passagem", "estacionamento", "pedágio", "pedágio", "transporte", 
                          "mobilidade", "carro", "moto", "bicicleta", "bike", "scooter", "patinete", 
                          "avião", "aéreo", "aereo", "voo", "gol", "latam", "azul", "tam", "viagem"],
            
            "moradia": ["aluguel", "condomínio", "condominio", "luz", "água", "agua", "gás", "gas", 
                       "internet", "iptu", "wifi", "apartamento", "casa", "energia", "conta de luz", 
                       "conta de água", "conta de gás", "seguro residencial", "reforma", "mobília", 
                       "móveis", "decoração", "decoracao", "manutenção", "manutencao", "conserto",
                       "encanador", "eletricista", "pintor", "pedreiro", "jardim", "jardineiro"],
            
            "lazer": ["cinema", "teatro", "show", "netflix", "spotify", "disney", "disney+", "hbo", 
                     "prime", "streaming", "viagem", "passeio", "bar", "balada", "festa", "ingresso", 
                     "museu", "parque", "clube", "academia", "esporte", "jogo", "livro", "revista", 
                     "música", "música", "hobby", "presente"],
            
            "saúde": ["remédio", "remedio", "consulta", "médico", "medico", "hospital", "farmácia", 
                     "farmacia", "exame", "plano de saúde", "dentista", "psicólogo", "terapia", 
                     "academia", "ginástica", "massagem", "fisioterapia", "nutricionista", "vitamina", 
                     "suplemento", "vacina", "seguro saúde", "clínica", "clinica", "laboratório", 
                     "oftalmologista", "pediatra", "dermatologista", "ortopedista", "cardiologista", 
                     "neurológista", "spa", "estética"],
            
            "educação": ["curso", "livro", "escola", "faculdade", "mensalidade", "material escolar", 
                        "universidade", "apostila", "matrícula", "pós-graduação", "mestrado", "doutorado", 
                        "ensino", "aula", "professor", "particular", "idioma", "inglês", "espanhol", 
                        "francês", "alemão", "licença", "certificação", "certificado", "diploma", 
                        "graduação", "especialização", "workshop", "seminário", "congresso", "palestra", 
                        "biblioteca", "assinatura", "revista", "jornal"],
            
            "vestuário": ["roupa", "calçado", "calcado", "sapato", "tênis", "tenis", "camisa", "calça", 
                         "vestido", "bermuda", "meia", "cueca", "sutiã", "jaqueta", "casaco", "blusa", 
                         "camiseta", "short", "saia", "pijama", "terno", "gravata", "moda", "acessório", 
                         "bolsa", "mochila", "carteira", "relógio", "óculos", "brinco", "colar", "anel", 
                         "pulseira", "chapéu", "boné", "loja"],
            
            "outros": ["diversos", "geral", "variados", "miscelânea", "outros"]
        }
        
        # Lista de serviços de streaming
        self.servicos_streaming = [
            "netflix", "spotify", "youtube premium", "youtube music", 
            "disney", "disney+", "amazon prime", "prime video", 
            "hbo", "hbo max", "deezer", "tidal", "apple music", 
            "apple tv", "paramount+", "globoplay", "crunchyroll", 
            "mubi", "telecine", "star+", "discovery+", "max", 
            "play", "watch", "hulu", "starz", "showtime"
        ]
        
        # Lista de estabelecimentos comuns e suas categorias
        self.estabelecimentos = {
            # Alimentação
            "mcdonalds": "alimentação", "burger king": "alimentação", "subway": "alimentação",
            "habib's": "alimentação", "pizza hut": "alimentação", "domino's": "alimentação",
            "outback": "alimentação", "madero": "alimentação", "china in box": "alimentação",
            "starbucks": "alimentação", "café": "alimentação", "cafeteria": "alimentação",
            "restaurante": "alimentação", "lanchonete": "alimentação", "padaria": "alimentação",
            "sorveteria": "alimentação", "pizzaria": "alimentação", "açougue": "alimentação",
            "mercado": "alimentação", "supermercado": "alimentação", "hortifruti": "alimentação",
            "confeitaria": "alimentação", "doceria": "alimentação", "pastelaria": "alimentação",
            "bar": "alimentação", "pub": "alimentação", "choperia": "alimentação", 
            "carrefour": "alimentação", "extra": "alimentação", "pão de açúcar": "alimentação",
            "assai": "alimentação", "atacadão": "alimentação", "dia": "alimentação",
            "sadia": "alimentação", "perdigão": "alimentação", "seara": "alimentação",
            "outback": "alimentação", "kfc": "alimentação", "giraffas": "alimentação",
            "ifood": "alimentação", "rappi": "alimentação", "james delivery": "alimentação",
            "uber eats": "alimentação", "99 food": "alimentação", "spoofEats": "alimentação",
            
            # Transporte
            "uber": "transporte", "99": "transporte", "cabify": "transporte",
            "posto": "transporte", "combustível": "transporte", "ipva": "transporte",
            "estacionamento": "transporte", "metrô": "transporte", "metro": "transporte",
            "ônibus": "transporte", "onibus": "transporte", "trem": "transporte",
            "brt": "transporte", "linha amarela": "transporte", "pedágio": "transporte",
            "oficina": "transporte", "concessionária": "transporte", "locadora": "transporte",
            "seguro auto": "transporte", "licenciamento": "transporte", "detran": "transporte",
            "passagem": "transporte", "aérea": "transporte", "voo": "transporte",
            "gol": "transporte", "latam": "transporte", "azul": "transporte",
            "shell": "transporte", "ipiranga": "transporte", "petrobras": "transporte",
            
            # Moradia
            "aluguel": "moradia", "condomínio": "moradia", "iptu": "moradia",
            "agua": "moradia", "luz": "moradia", "energia": "moradia", 
            "gás": "moradia", "internet": "moradia", "telefone": "moradia",
            "tv": "moradia", "móveis": "moradia", "eletrodoméstico": "moradia",
            "reforma": "moradia", "decoração": "moradia", "manutenção": "moradia",
            "seguro residencial": "moradia", "material de construção": "moradia",
            "leroy merlin": "moradia", "c&c": "moradia", "telhanorte": "moradia",
            "casas bahia": "moradia", "magazine luiza": "moradia", "ponto frio": "moradia",
            "tok&stok": "moradia", "etna": "moradia", "madeira madeira": "moradia",
            
            # Lazer
            "cinema": "lazer", "teatro": "lazer", "show": "lazer", "festival": "lazer",
            "ingresso": "lazer", "ingressos.com": "lazer", "ticketmaster": "lazer",
            "sympla": "lazer", "eventim": "lazer", "clube": "lazer", "festa": "lazer",
            "boate": "lazer", "balada": "lazer", "parque": "lazer", "museu": "lazer",
            "exposição": "lazer", "hotel": "lazer", "airbnb": "lazer", "booking": "lazer",
            "decolar": "lazer", "hospedagem": "lazer", "viagem": "lazer", "netflix": "lazer",
            "spotify": "lazer", "youtube": "lazer", "amazon prime": "lazer", "disney": "lazer",
            "globoplay": "lazer", "hbo": "lazer", "apple tv": "lazer", "jogo": "lazer",
            "steam": "lazer", "playstation": "lazer", "xbox": "lazer", "nintendo": "lazer",
            "livro": "lazer", "livraria": "lazer", "saraiva": "lazer", "cultura": "lazer",
            
            # Saúde
            "farmácia": "saúde", "drogaria": "saúde", "remédio": "saúde",
            "consulta": "saúde", "médico": "saúde", "hospital": "saúde",
            "laboratório": "saúde", "exame": "saúde", "clínica": "saúde",
            "dentista": "saúde", "psicólogo": "saúde", "fisioterapia": "saúde",
            "nutricionista": "saúde", "academia": "saúde", "suplemento": "saúde",
            "plano de saúde": "saúde", "convênio": "saúde", "seguro saúde": "saúde",
            "drogasil": "saúde", "pacheco": "saúde", "raia": "saúde", "ultrafarma": "saúde",
            "panvel": "saúde", "pague menos": "saúde", "amil": "saúde", "unimed": "saúde",
            "sulamerica": "saúde", "bradesco saúde": "saúde",
            
            # Educação
            "escola": "educação", "faculdade": "educação", "universidade": "educação",
            "curso": "educação", "aula": "educação", "professor": "educação",
            "material escolar": "educação", "livro didático": "educação", "apostila": "educação",
            "matrícula": "educação", "mensalidade": "educação", "uniforme": "educação",
            "estácio": "educação", "anhanguera": "educação", "laureate": "educação",
            "unip": "educação", "uninove": "educação", "fgv": "educação", "insper": "educação",
            "descomplica": "educação", "stoodi": "educação", "kultivi": "educação", 
            "coursera": "educação", "udemy": "educação", "alura": "educação",
            "inglês": "educação", "wizard": "educação", "fisk": "educação", "ccaa": "educação",
            
            # Vestuário
            "roupa": "vestuário", "calçado": "vestuário", "sapato": "vestuário",
            "tênis": "vestuário", "acessório": "vestuário", "bolsa": "vestuário",
            "mochila": "vestuário", "óculos": "vestuário", "relógio": "vestuário",
            "joia": "vestuário", "bijuteria": "vestuário", "malhar": "vestuário",
            "c&a": "vestuário", "renner": "vestuário", "riachuelo": "vestuário",
            "marisa": "vestuário", "zara": "vestuário", "hering": "vestuário",
            "forever 21": "vestuário", "youcom": "vestuário", "calvin klein": "vestuário",
            "nike": "vestuário", "adidas": "vestuário", "puma": "vestuário",
            "centauro": "vestuário", "decathlon": "vestuário", "netshoes": "vestuário",
            "dafiti": "vestuário", "chilli beans": "vestuário", "arezzo": "vestuário",
            "melissa": "vestuário", "havaianas": "vestuário"
        }
    
    def detectar_servico_streaming(self, texto):
        """Detecta se o texto contém referência a serviços de streaming"""
        texto_lower = texto.lower()
        
        for servico in self.servicos_streaming:
            if servico in texto_lower:
                return True
                
        # Verifica padrões comuns de serviços de streaming
        if "assinatura" in texto_lower and any(palavra in texto_lower for palavra in ["filme", "séries", "series", "assistir", "video", "vídeo", "stream"]):
            return True
            
        return False
    
    def extrair_informacoes_despesa(self, texto):
        """Extrai informações de despesa a partir de um texto"""
        from datetime import datetime, timedelta
        import re
        
        # Inicializa os dados da despesa
        dados_despesa = {
            "valor": None,
            "categoria": None,
            "descricao": texto,
            "data": datetime.now().strftime("%Y-%m-%d"),
            "forma_pagamento": None
        }
        
        # Converte para minúsculas e remove caracteres especiais
        texto_lower = texto.lower()
        texto_processado = re.sub(r'[^\w\s.,/:;$%]', ' ', texto_lower)
        
        # Verificações especiais
        
        # Verifica se é um serviço de streaming
        if self.detectar_servico_streaming(texto_lower):
            dados_despesa["categoria"] = "lazer"
        
        # Verifica se é uma descrição de salário
        if any(palavra in texto_lower for palavra in ["salario", "salário", "pagamento", "remuneração", "remuneracao", "provento", "contracheque"]):
            # É um salário, não uma despesa
            return None
        
        # Reconhecimento de estabelecimentos conhecidos
        for estabelecimento, categoria in self.estabelecimentos.items():
            if estabelecimento in texto_lower:
                dados_despesa["categoria"] = categoria
                if dados_despesa["descricao"] == texto:  # Se a descrição ainda não foi personalizada
                    dados_despesa["descricao"] = estabelecimento.capitalize()
                break
        
        # Extrai o valor monetário - algoritmo melhorado
        padroes_valor = [
            # Formatos comuns de preços e valores
            r'r\$\s*(\d+[.,]?\d*)',                    # R$ 50 ou R$50 ou R$ 50,90
            r'(\d+[.,]?\d*)\s*(?:reais|real)',         # 50 reais ou 50,90 reais
            r'(\d+[.,]?\d*)\s*(?:rs|r\$)',             # 50 rs ou 50,90 r$
            
            # Palavras-chave que indicam valores
            r'(?:valor|custo|preço|preco|paguei|gastei|comprei por)\s*(?:de|:)?\s*(?:r\$)?\s*(\d+[.,]?\d*)', 
            
            # Valores com vírgulas ou pontos em formatos específicos
            r'valor:?\s*(\d+[.,]\d{2})',               # valor: 50,90 ou valor 50.90
            r'total:?\s*(\d+[.,]\d{2})',               # total: 50,90 ou total 50.90
            
            # Extração de valor do texto de recibos e notas fiscais
            r'(?:total|valor total|vlr total|a pagar):?\s*(?:r\$)?\s*(\d+[.,]\d{2})',
            
            # Último recurso: qualquer número isolado que pareça um valor monetário
            r'(?:^|\s)(\d+[.,]\d{2})(?:\s|$)',         # 50,90 ou 50.90 isolado
            r'(?:^|\s)(\d+)(?:\s|$)'                   # Só um número isolado (50)
        ]
        
        for padrao in padroes_valor:
            matches = re.findall(padrao, texto_processado)
            if matches:
                try:
                    # Pega o maior valor encontrado
                    melhores_matches = []
                    for match in matches:
                        valor_str = match.replace(',', '.')
                        try:
                            melhores_matches.append(float(valor_str))
                        except ValueError:
                            continue
                    
                    if melhores_matches:
                        dados_despesa["valor"] = max(melhores_matches)
                        break
                except (ValueError, IndexError):
                    continue
        
        # Se não encontrou valor, retorna None
        if dados_despesa["valor"] is None:
            return None
        
        # Se ainda não definiu categoria e não é streaming, extrai categoria baseada em palavras-chave
        if not dados_despesa["categoria"]:
            for categoria, palavras_chave in self.categorias.items():
                for palavra in palavras_chave:
                    if palavra in texto_lower:
                        dados_despesa["categoria"] = categoria
                        break
                if dados_despesa["categoria"]:
                    break
        
        # Se ainda não encontrou categoria, verifica padrões específicos
        if not dados_despesa["categoria"]:
            # Assinaturas (não streaming) geralmente são recorrentes (mensalidade, anuidade)
            if "assinatura" in texto_lower or "mensalidade" in texto_lower or "anuidade" in texto_lower:
                if "academia" in texto_lower or "gym" in texto_lower:
                    dados_despesa["categoria"] = "saúde"
                elif "escola" in texto_lower or "faculdade" in texto_lower or "curso" in texto_lower:
                    dados_despesa["categoria"] = "educação"
                elif "internet" in texto_lower or "celular" in texto_lower or "telefone" in texto_lower:
                    dados_despesa["categoria"] = "moradia"
                else:
                    dados_despesa["categoria"] = "outros"
        
        # Se não encontrou categoria, usa "outros"
        if not dados_despesa["categoria"]:
            dados_despesa["categoria"] = "outros"
        
        # Extrai data (melhorado para reconhecer mais formatos)
        padroes_data = [
            # Formatos de datas
            r'(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?',  # 10/05 ou 10/05/2023 ou 10-05-2023
            r'(\d{1,2})\s+(?:de\s+)?(\w+)(?:\s+(?:de\s+)?(\d{2,4}))?', # 10 de maio ou 10 maio de 2023
            
            # Palavras-chave temporais
            r'(?:hoje|ontem|amanhã|amanha)',
            
            # Datas em contexto
            r'(?:dia|data|em)\s+(\d{1,2})[/-](\d{1,2})',  # dia 10/05 ou data 10-05
            r'(?:dia|data|em)\s+(\d{1,2})\s+(?:de\s+)?(\w+)' # dia 10 de maio
        ]
        
        meses = {
            'janeiro': 1, 'jan': 1, 'fevereiro': 2, 'fev': 2, 'março': 3, 'mar': 3,
            'abril': 4, 'abr': 4, 'maio': 5, 'mai': 5, 'junho': 6, 'jun': 6,
            'julho': 7, 'jul': 7, 'agosto': 8, 'ago': 8, 'setembro': 9, 'set': 9,
            'outubro': 10, 'out': 10, 'novembro': 11, 'nov': 11, 'dezembro': 12, 'dez': 12
        }
        
        for padrao in padroes_data:
            matches = re.findall(padrao, texto_lower)
            if matches:
                if isinstance(matches[0], tuple) and len(matches[0]) >= 2:
                    try:
                        # Formato numérico (10/05)
                        if matches[0][0].isdigit() and matches[0][1].isdigit():
                            dia = int(matches[0][0])
                            mes = int(matches[0][1])
                            ano = datetime.now().year
                            
                            if len(matches[0]) > 2 and matches[0][2]:
                                ano_str = matches[0][2]
                                if len(ano_str) == 2:
                                    ano = 2000 + int(ano_str)
                                else:
                                    ano = int(ano_str)
                        
                        # Formato textual (10 de maio)
                        elif matches[0][0].isdigit() and not matches[0][1].isdigit():
                            dia = int(matches[0][0])
                            mes_nome = matches[0][1].lower()
                            
                            # Encontra o mês pelo nome
                            mes = None
                            for nome, num in meses.items():
                                if mes_nome.startswith(nome):
                                    mes = num
                                    break
                            
                            if not mes:
                                continue  # Se não encontrou o mês, pula para o próximo padrão
                            
                            ano = datetime.now().year
                            if len(matches[0]) > 2 and matches[0][2]:
                                ano_str = matches[0][2]
                                if len(ano_str) == 2:
                                    ano = 2000 + int(ano_str)
                                else:
                                    ano = int(ano_str)
                        
                        # Validação da data
                        if dia > 31 or mes > 12:
                            continue
                        
                        data_obj = datetime(ano, mes, dia)
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
        
        # Extrai forma de pagamento (algoritmo melhorado)
        padroes_pagamento = [
            # Formas de pagamento explícitas
            r'(?:pag(?:amento|uei|ar|o)|comprei)(?:\s+(?:com|no|usando|via|por|pelo))?\s+(cartão|cartao|crédito|credito|débito|debito|dinheiro|pix|boleto)',
            r'(?:no|com|usando|via|por|pelo)\s+(cartão|cartao|crédito|credito|débito|debito|dinheiro|pix|boleto)',
            
            # Palavras-chave específicas
            r'(?:visa|master(?:card)?|elo|american express|amex|nubank|banco)\b',
            
            # Formatos comuns em recibos
            r'forma(?:\s+de)?\s+pagamento:?\s+([\w\s]+)',
            r'(?:pago|pagamento):?\s+([\w\s]+)'
        ]
        
        for padrao in padroes_pagamento:
            matches = re.findall(padrao, texto_lower)
            if matches:
                forma = matches[0].lower() if isinstance(matches[0], str) else matches[0][0].lower()
                
                # Mapeia para formas de pagamento padronizadas
                if forma in ['cartão', 'cartao'] or any(card in forma for card in ['visa', 'master', 'elo', 'amex']):
                    dados_despesa["forma_pagamento"] = "Cartão"
                elif forma in ['crédito', 'credito'] or 'cred' in forma:
                    dados_despesa["forma_pagamento"] = "Crédito"
                elif forma in ['débito', 'debito'] or 'deb' in forma:
                    dados_despesa["forma_pagamento"] = "Débito"
                elif forma == 'dinheiro' or forma == 'especie' or forma == 'espécie':
                    dados_despesa["forma_pagamento"] = "Dinheiro"
                elif forma == 'pix' or 'pix' in forma:
                    dados_despesa["forma_pagamento"] = "PIX"
                elif forma == 'boleto' or 'boleto' in forma:
                    dados_despesa["forma_pagamento"] = "Boleto"
                elif 'transferência' in forma or 'transf' in forma or 'ted' in forma or 'doc' in forma:
                    dados_despesa["forma_pagamento"] = "Transferência"
                break
        
        # Se identificamos um estabelecimento, podemos usar como descrição se ainda não tiver uma específica
        if dados_despesa["descricao"] == texto and "categoria" in dados_despesa:
            # Tenta encontrar o estabelecimento que correspondeu à categoria
            for estabelecimento, categoria in self.estabelecimentos.items():
                if categoria == dados_despesa["categoria"] and estabelecimento in texto_lower:
                    dados_despesa["descricao"] = estabelecimento.capitalize()
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
            "vendas": "🛒",
            "serviços": "🔧",
            "assinaturas": "📅",
            "royalties": "📊",
            "fornecedores": "🏭",
            "salários": "👥",
            "impostos": "📑",
            "aluguel": "🏢",
            "equipamentos": "⚙️",
            "marketing": "📢",
            "outros": "📦",
            "outros_empresarial": "📦"
        }
        
        return emojis.get(categoria, "📦")
    
    def extrair_info_de_texto_longo(self, texto):
        """Extrai todas as informações relevantes de um texto longo (como transcrição de áudio)"""
        from datetime import datetime, timedelta
        import re
        
        # Divide o texto em sentenças
        sentenças = re.split(r'[.!?]\s+', texto)
        
        # Analisa cada sentença para extrair informações
        melhores_dados = None
        
        for sentença in sentenças:
            if len(sentença) < 5:  # Ignora sentenças muito curtas
                continue
            
            # Extrai informações desta sentença
            dados = self.extrair_informacoes_despesa(sentença)
            
            # Se encontrou valor, pode ser uma transação
            if dados and dados.get('valor'):
                if melhores_dados is None or (dados.get('valor') > melhores_dados.get('valor')):
                    melhores_dados = dados
        
        # Se não encontrou nada analisando sentenças individuais, tenta o texto completo
        if melhores_dados is None:
            melhores_dados = self.extrair_informacoes_despesa(texto)
        
        return melhores_dados
    
    def processar_texto_nota_fiscal(self, texto):
        """Processa texto extraído de uma nota fiscal via OCR"""
        import re
        
        # Inicializa dados
        dados = {
            "valor": None,
            "data": datetime.now().strftime("%Y-%m-%d"),
            "estabelecimento": None,
            "categoria": "outros"
        }
        
        # Expressões comuns em notas fiscais
        padrao_estabelecimento = r'(?:razão social|nome fantasia|estabelecimento):\s*([^\n]+)'
        padrao_cnpj = r'cnpj:?\s*(\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})'
        padrao_data = r'(?:data(?:\s+de)?\s+(?:emissão|emis|compra):?\s*)(\d{1,2}[-./]\d{1,2}[-./]\d{2,4})'
        padrao_total = r'(?:total|valor\s+a\s+pagar|valor\s+total|vr\.\s*total):?\s*(?:r\$)?\s*(\d+[.,]\d{2})'
        
        # Busca estabelecimento
        match = re.search(padrao_estabelecimento, texto.lower())
        if match:
            dados["estabelecimento"] = match.group(1).strip()
        
        # Busca CNPJ (pode ajudar a identificar o estabelecimento)
        match = re.search(padrao_cnpj, texto.lower())
        if match:
            cnpj = match.group(1)
            # Poderia ter um banco de dados de CNPJs para identificar estabelecimentos
        
        # Busca data
        match = re.search(padrao_data, texto.lower())
        if match:
            data_str = match.group(1)
            try:
                # Converte para formato YYYY-MM-DD
                if '/' in data_str:
                    dia, mes, ano = data_str.split('/')
                elif '.' in data_str:
                    dia, mes, ano = data_str.split('.')
                elif '-' in data_str:
                    dia, mes, ano = data_str.split('-')
                else:
                    raise ValueError("Formato de data não reconhecido")
                
                # Ajusta o ano se necessário
                if len(ano) == 2:
                    ano = '20' + ano
                
                dados["data"] = f"{ano}-{int(mes):02d}-{int(dia):02d}"
            except Exception as e:
                print(f"Erro ao processar data: {e}")
        
        # Busca valor total
        match = re.search(padrao_total, texto.lower())
        if match:
            try:
                valor_str = match.group(1).replace(',', '.')
                dados["valor"] = float(valor_str)
            except Exception as e:
                print(f"Erro ao processar valor: {e}")
        
        # Se não encontrou valor total, tenta encontrar qualquer valor monetário
        if dados["valor"] is None:
            padrao_valor = r'(?:r\$)?\s*(\d+[.,]\d{2})'
            matches = re.findall(padrao_valor, texto.lower())
            if matches:
                try:
                    # Pega o maior valor encontrado (provavelmente o total)
                    valores = [float(v.replace(',', '.')) for v in matches]
                    dados["valor"] = max(valores)
                except Exception as e:
                    print(f"Erro ao processar valores: {e}")
        
        # Tenta determinar a categoria com base no estabelecimento
        if dados["estabelecimento"]:
            estabelecimento_lower = dados["estabelecimento"].lower()
            
            for nome, categoria in self.estabelecimentos.items():
                if nome in estabelecimento_lower:
                    dados["categoria"] = categoria
                    break
        
        return dados