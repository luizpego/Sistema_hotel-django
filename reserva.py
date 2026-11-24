from datetime import datetime
from zoneinfo import ZoneInfo

from banco import consultar, transacao


def agora():
    return datetime.now(ZoneInfo('America/Sao_Paulo')).replace(tzinfo=None)


class Reserva:
    def __init__(self, cliente_id, quarto_id, entrada, saida, funcionario_id=None):
        self.cliente_id = cliente_id
        self.quarto_id = quarto_id
        self.entrada = entrada
        self.saida = saida
        self.funcionario_id = funcionario_id

    def calcular_total(self, diaria):
        return (self.saida - self.entrada).days * diaria

    def salvar(self):
        if self.entrada < agora().date() or self.saida <= self.entrada:
            raise ValueError('Entrada deve ser hoje ou futura; saída deve ser posterior à entrada.')
        with transacao() as cursor:
            cursor.execute('SELECT ativo FROM clientes WHERE id=%s FOR UPDATE', (self.cliente_id,))
            cliente = cursor.fetchone()
            if not cliente or not cliente['ativo']:
                raise ValueError('Selecione um cliente ativo.')
            # O bloqueio serializa reservas simultâneas para o mesmo quarto.
            cursor.execute('SELECT * FROM quartos WHERE id=%s FOR UPDATE', (self.quarto_id,))
            quarto = cursor.fetchone()
            if not quarto or not quarto['ativo']:
                raise ValueError('Selecione um quarto ativo.')
            if self.funcionario_id:
                cursor.execute('SELECT ativo FROM funcionarios WHERE id=%s FOR UPDATE', (self.funcionario_id,))
                funcionario = cursor.fetchone()
                if not funcionario or not funcionario['ativo']:
                    raise ValueError('Selecione um funcionário ativo.')
            cursor.execute('''SELECT id FROM reservas WHERE quarto_id=%s
                AND status IN ('reservada','hospedada') AND entrada < %s AND saida > %s
                FOR UPDATE''', (self.quarto_id, self.saida, self.entrada))
            if cursor.fetchall():
                raise ValueError('O quarto já possui reserva nesse período.')
            total = self.calcular_total(quarto['valor_diaria'])
            if total > 9999999999:
                raise ValueError('O total da hospedagem excede o limite permitido.')
            cursor.execute('''INSERT INTO reservas
                (cliente_id,quarto_id,funcionario_id,entrada,saida,diaria,total)
                VALUES (%s,%s,%s,%s,%s,%s,%s)''',
                (self.cliente_id, self.quarto_id, self.funcionario_id, self.entrada,
                 self.saida, quarto['valor_diaria'], total))
            return cursor.lastrowid


def movimentar(reserva_id, acao):
    registros = consultar('SELECT quarto_id FROM reservas WHERE id=%s', (reserva_id,))
    if not registros:
        raise ValueError('Reserva não encontrada.')
    with transacao() as cursor:
        cursor.execute('SELECT * FROM quartos WHERE id=%s FOR UPDATE', (registros[0]['quarto_id'],))
        quarto = cursor.fetchone()
        cursor.execute('SELECT * FROM reservas WHERE id=%s FOR UPDATE', (reserva_id,))
        reserva = cursor.fetchone()
        momento = agora()
        if acao == 'checkin':
            if reserva['status'] != 'reservada':
                raise ValueError('Check-in permitido apenas para reservas confirmadas.')
            if not reserva['entrada'] <= momento.date() < reserva['saida']:
                raise ValueError('Check-in deve ocorrer dentro do período reservado.')
            if quarto['status'] == 'ocupado' or not quarto['ativo']:
                raise ValueError('O quarto não está disponível para entrada.')
            cursor.execute("UPDATE reservas SET status='hospedada',checkin_em=%s WHERE id=%s", (momento, reserva_id))
            cursor.execute("UPDATE quartos SET status='ocupado' WHERE id=%s", (quarto['id'],))
        elif acao == 'checkout':
            if reserva['status'] != 'hospedada':
                raise ValueError('Check-out permitido apenas após o check-in.')
            cursor.execute("UPDATE reservas SET status='finalizada',checkout_em=%s WHERE id=%s", (momento, reserva_id))
            cursor.execute("UPDATE quartos SET status='desocupado' WHERE id=%s", (quarto['id'],))
        elif acao == 'cancelar':
            if reserva['status'] != 'reservada':
                raise ValueError('Somente reservas sem check-in podem ser canceladas.')
            cursor.execute('SELECT id FROM pagamentos WHERE reserva_id=%s FOR UPDATE', (reserva_id,))
            if cursor.fetchall():
                raise ValueError('Reserva com pagamentos não pode ser cancelada.')
            cursor.execute("UPDATE reservas SET status='cancelada' WHERE id=%s", (reserva_id,))
        else:
            raise ValueError('Ação inválida.')
