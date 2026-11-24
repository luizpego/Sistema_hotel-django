import os
from contextlib import contextmanager

import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def conectar():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST', '127.0.0.1'), port=int(os.getenv('DB_PORT', '3306')),
        user=os.getenv('DB_USER', 'hotel_app'), password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'sistema_hotel'), charset='utf8mb4',
        connection_timeout=5, autocommit=False,
    )


@contextmanager
def transacao():
    # Um erro desfaz todas as alterações da operação.
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)
    try:
        yield cursor
        conexao.commit()
    except Exception:
        conexao.rollback()
        raise
    finally:
        cursor.close()
        conexao.close()


def consultar(sql, valores=()):
    with transacao() as cursor:
        cursor.execute(sql, valores)
        return cursor.fetchall()


def executar(sql, valores=()):
    with transacao() as cursor:
        cursor.execute(sql, valores)
        return cursor.lastrowid
