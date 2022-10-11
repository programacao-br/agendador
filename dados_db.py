import sqlite3
import os


#cria ou abre o banco de dados, cria a tabela caso não exista
nome_db = f'{os.getcwd()}/agenda.db'
def cria_tabela():
    """
    Cria o banco de dados [agenda.db] e a tabela [tarefas] caso não existam\n
    <- bool return - Retorna True em caso de sucesso
    """
    retorno = False
    try:
        conexao = sqliteConnection = sqlite3.connect(nome_db)
        sql = 'create table if not exists tarefas (id INTEGER PRIMARY KEY AUTOINCREMENT, '
        sql+= 'nome TEXT NOT NULL, tarefa TXT NOT NULL, meses TEXT NOT NULL, dias TEXT, '
        sql+= 'horas TEXT NOT NULL, minutos INT NOT NULL, repetir INT NOT NULL, ultima TEXT, '
        sql+= 'proxima TEXT, estado INT, especificos TEXT, diretorio TEXT)'
        ponteiro = conexao.cursor()
        ponteiro.execute(sql)
        ponteiro.close()
        retorno = True
        print("Banco de dados e tabela criados com sucesso")
    except sqlite3.Error as error:
        print(f'Erro criando a tabela, erro: {error}')
    finally:
        if conexao:
            conexao.close()
    
    return retorno

#adiciona um regostro na tabela
def adiciona_registro(nome:str, tarefa:str, meses:str, dias:str, horas:str, minutos:int, repetir:int,
                    ultima:str, proxima:str, estado:int, especifico:str, diretorio:str) -> bool:
    """
    Adiciona um registro na tabela\n
    <- bool return - Retorna True em caso de sucesso
    """
    retorno = False
    try:
        conexao = sqliteConnection = sqlite3.connect(nome_db)
        ponteiro = sqliteConnection.cursor()

        sqlite_insert = """ INSERT INTO tarefas
                                (nome, tarefa, meses, dias, horas, minutos, repetir, ultima, proxima, estado, especificos,diretorio) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

        data_tuple = (nome, tarefa, meses, dias, horas, minutos, repetir, ultima, proxima, estado, especifico, diretorio)
        ponteiro.execute(sqlite_insert, data_tuple)
        conexao.commit()
        ponteiro.close()
        retorno = True
    except sqlite3.Error as error:
        print(f'Erro adicionando registro, erro: {error}')
    finally:
        if conexao:
            conexao.close()
    
    return retorno

#deleta o registro informado
def deleta_registro(id:int) -> bool:
    """
    Deleta o registro informado\n
    -> int id - umero do registro a ser deletado\n
    <- bool return - Retorna True em caso de sucesso
    """
    retorno = False
    try:
        conexao = sqliteConnection = sqlite3.connect(nome_db)
        ponteiro = sqliteConnection.cursor()
        
        sql_delete = """DELETE from tarefas where id = ?"""
        ponteiro.execute(sql_delete, (id,))
        conexao.commit()
        ponteiro.close()
        retorno = True
    except sqlite3.Error as error:
        print(f"Ocorreu um erro ao deletar o registro. Erro:{error}")
    finally:
        if conexao:
            conexao.close()
    
    return retorno

#atualiza o registro informado
def atualiza_registro(id:int,nome:str, tarefa:str, meses:str, dias:str, horas:str, minutos:int, repetir:int,
                    ultima:str, proxima:str, estado:int, especifico:str, diretorio:str) -> bool:
    """
    Atualiza um registro na tabela\n
    -> int id - ID do registro a ser atualizado\n
    -> *args - Os novos valores dos campos\n
    <- bool return - Retorna True em caso de sucesso
    """
    retorno = False
    try:
        conexao = sqliteConnection = sqlite3.connect(nome_db)
        ponteiro = sqliteConnection.cursor()

        sqlite_update = """UPDATE tarefas SET nome = ? , tarefa = ? , 
                        meses = ? , dias = ? , horas = ? , minutos = ? , 
                        repetir = ? , ultima = ? , proxima = ? , estado = ? , 
                        especificos = ? , diretorio = ? WHERE id = ?"""

        
        campos=(nome, tarefa, meses, dias, horas, minutos, repetir, ultima, proxima, estado, especifico, diretorio, id)
        ponteiro.execute(sqlite_update, campos)
        conexao.commit()
        ponteiro.close()
        retorno = True
    except sqlite3.Error as error:
        print(f'Erro atualizando o registro id: {id}, erro: {error}')
    finally:
        if conexao:
            conexao.close()
    
    return retorno

#retorna os registros
def retorna_registro(id:int) -> list:
    """
    Retorna os registros que sejam >= ao id informado\n
    -> int id - Numero do id inicial\n
    <- list return - Retorna uma lista contendo uma string de cada registro
    """
    retorno = []
    try:
        conexao = sqliteConnection = sqlite3.connect(nome_db)
        ponteiro = sqliteConnection.cursor()
        #repare que a posição dos campos de retorno foram alterados para que a lista mostre na ordem correta
        sql_fetch = """SELECT id, nome, ultima, proxima, estado, tarefa, meses, dias, horas, minutos, repetir, especificos,diretorio FROM tarefas WHERE id >= ? ORDER BY id"""
        ponteiro.execute(sql_fetch, (id,))
        record = ponteiro.fetchall()
        for row in record:
            reg = (row[0],row[1],row[2],row[3],row[4],row[5],row[6],row[7],row[8],row[9],row[10], row[11],row[12])
            retorno.append(reg)

        ponteiro.close()
    except sqlite3.Error as error:
        print(f"Ocorreu um erro ao verificar o registro. Erro:{error}")
    finally:
        if conexao:
            conexao.close()
    
    return retorno

#atualiza um campo especifico
def atualiza_campo(id:int, campo:str,valor:str) -> None:
    """
    Atualiza o campo informado com o novo valor.\n
    -> int id - ID da tarefa.\n
    -> str campo - Nome do campo a ser atualizado\n
    -> str valor - Novo valor para o campo
    <- None - Essa funçaõ não retorna valores.
    """
    try:
        conexao = sqliteConnection = sqlite3.connect(nome_db)
        ponteiro = sqliteConnection.cursor()
        
        sql_update = f"""UPDATE tarefas SET {campo} = ? where id = ?"""
        ponteiro.execute(sql_update, (valor, id))
        conexao.commit()
        ponteiro.close()
    except sqlite3.Error as error:
        print(f"Ocorreu um erro ao tentar atualizar o registro. Erro:{error}")
    finally:
        if conexao:
            conexao.close()

#retorna o id caso o nome seja encontrado
def localiza_registro(nome:str) -> int or None:
    """
    Retorna o id do registro caso o nome da tarefa seja encontrada\n
    -> str nome - Nome da tarefa a ser localizada\n
    <- int ou None return - Se encontrado retorna o id.
    """
    reg=None
    try:
        conexao = sqliteConnection = sqlite3.connect(nome_db)
        ponteiro = sqliteConnection.cursor()
        sql_fetch = f"SELECT id FROM tarefas WHERE nome = '{nome}' LIMIT 1"
        ponteiro.execute(sql_fetch)
        record = ponteiro.fetchall()
        if len(record) > 0:
            reg = record[0][0]
        ponteiro.close()
    except sqlite3.Error as error:
        print(f"Ocorreu um erro ao verificar o registro. Erro:{error}")
    finally:
        if conexao:
            conexao.close()

    return reg
