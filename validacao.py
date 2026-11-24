import re
from datetime import date
from decimal import Decimal, InvalidOperation


def texto(valor, campo, limite):
    valor = (valor or '').strip()
    if not valor or len(valor) > limite:
        raise ValueError(f'{campo}: preencha entre 1 e {limite} caracteres.')
    return valor


def inteiro(valor, campo, minimo=1, maximo=999999):
    try:
        numero = int(valor)
    except (ValueError, TypeError):
        raise ValueError(f'{campo}: informe um número inteiro.') from None
    if numero < minimo or numero > maximo:
        raise ValueError(f'{campo}: informe um valor entre {minimo} e {maximo}.')
    return numero


def dinheiro(valor, campo='Valor', permitir_zero=False):
    try:
        numero = Decimal(str(valor).replace(',', '.'))
        if not numero.is_finite() or numero.as_tuple().exponent < -2:
            raise ValueError()
        if numero < 0 or (numero == 0 and not permitir_zero) or numero > Decimal('99999999.99'):
            raise ValueError()
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f'{campo}: informe um valor válido com até duas casas decimais.') from None
    return numero


def data(valor, campo):
    try:
        return date.fromisoformat(valor)
    except (ValueError, TypeError):
        raise ValueError(f'{campo}: informe uma data válida.') from None


def cpf_valido(valor):
    valor = re.sub(r'[.\-\s]', '', valor or '')
    if not re.fullmatch(r'[0-9]{11}', valor) or len(set(valor)) == 1:
        raise ValueError('CPF inválido.')
    for tamanho in (9, 10):
        soma = 0
        for indice in range(tamanho):
            soma += int(valor[indice]) * (tamanho + 1 - indice)
        if (soma * 10 % 11) % 10 != int(valor[tamanho]):
            raise ValueError('CPF inválido.')
    return valor


def telefone_valido(valor):
    valor = re.sub(r'[()\-\s]', '', valor or '')
    if not re.fullmatch(r'[0-9]{10,11}', valor):
        raise ValueError('Telefone: informe DDD e número, com 10 ou 11 dígitos.')
    return valor
