import os
import psycopg2
from psycopg2 import sql

# Configurações PostgreSQL do Supabase
POSTGRES_HOST = os.environ.get('POSTGRES_HOST', 'db.bunafenqbfbnmcjzygpg.supabase.co')
POSTGRES_PORT = os.environ.get('POSTGRES_PORT', '5432')
POSTGRES_DB = os.environ.get('POSTGRES_DB', 'postgres')
POSTGRES_USER = os.environ.get('POSTGRES_USER', 'postgres')
POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD', 'E8X1cCvtNTFZ780J')

def testar_conexao_postgres():
    try:
        # String de conexão
        conn_string = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
        
        # Conectar ao banco
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()
        
        print("✅ Conexão PostgreSQL estabelecida!")
        
        # Verificar se a tabela usuarios existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'usuarios'
                AND table_schema = 'public'
            );
        """)
        
        tabela_existe = cursor.fetchone()[0]
        
        if tabela_existe:
            print("✅ Tabela 'usuarios' encontrada!")
            
            # Contar registros
            cursor.execute("SELECT COUNT(*) FROM usuarios;")
            count = cursor.fetchone()[0]
            print(f"📊 Total de registros: {count}")
            
            # Mostrar estrutura da tabela
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'usuarios'
                AND table_schema = 'public'
                ORDER BY ordinal_position;
            """)
            
            colunas = cursor.fetchall()
            print("\n📋 Estrutura da tabela:")
            for col_name, data_type, nullable in colunas:
                nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
                print(f"  - {col_name}: {data_type} ({nullable_str})")
            
            # Mostrar alguns registros
            if count > 0:
                cursor.execute("SELECT * FROM usuarios LIMIT 3;")
                registros = cursor.fetchall()
                
                # Pegar nomes das colunas
                col_names = [desc[0] for desc in cursor.description]
                
                print(f"\n🔍 Primeiros registros:")
                for i, registro in enumerate(registros, 1):
                    print(f"  {i}. {dict(zip(col_names, registro))}")
        
        else:
            print("❌ Tabela 'usuarios' não encontrada!")
            
            # Listar tabelas disponíveis
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            
            tabelas = cursor.fetchall()
            print("\n📋 Tabelas disponíveis:")
            for (tabela,) in tabelas:
                print(f"  - {tabela}")
        
        # Fechar conexões
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na conexão PostgreSQL: {str(e)}")
        return False

def criar_tabela_usuarios_se_nao_existir():
    """Cria a tabela usuarios se ela não existir"""
    try:
        conn_string = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()
        
        # SQL para criar tabela usuarios
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE,
            telefone VARCHAR(20),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        cursor.execute(create_table_sql)
        conn.commit()
        
        print("✅ Tabela 'usuarios' criada ou já existia!")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao criar tabela: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔄 Testando conexão PostgreSQL com Supabase...\n")
    
    # Testar conexão
    if testar_conexao_postgres():
        print("\n✅ Todos os testes concluídos com sucesso!")
    else:
        print("\n❌ Falha nos testes de conexão")
        
        # Opção para criar tabela se não existir
        print("\n🔧 Tentando criar tabela 'usuarios'...")
        criar_tabela_usuarios_se_nao_existir()