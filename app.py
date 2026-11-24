import csv
import hmac
import io
import os
import re
import secrets
from calendar import monthrange
from datetime import date, timedelta
from pathlib import Path

import click
import mysql.connector
from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from banco import conectar, consultar, executar, transacao
from cliente import Cliente
from funcionario import Funcionario
from quarto import Quarto
from reserva import Reserva, agora, movimentar
from validacao import cpf_valido, data, dinheiro, inteiro, telefone_valido, texto

app = Flask(__name__)
chave = os.getenv('SECRET_KEY', '')
if len(chave) < 32 or chave.startswith('troque-'):
    raise RuntimeError('Configure SECRET_KEY no .env com uma chave aleatória de pelo menos 32 caracteres.')
app.config.update(
    SECRET_KEY=chave, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.getenv('COOKIE_SECURE') == '1',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8), MAX_CONTENT_LENGTH=64 * 1024,
)
HASH_INEXISTENTE = generate_password_hash(secrets.token_urlsafe(32))
MODULOS = {'clientes': 'Hóspedes', 'quartos': 'Quartos', 'funcionarios': 'Funcionários'}
MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
         'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']


@app.before_request
def proteger():
    g.usuario = None
    if request.endpoint == 'static':
        return
    if 'usuario_id' in session:
        usuarios = consultar('SELECT id,login,perfil FROM usuarios WHERE id=%s AND ativo=1', (session['usuario_id'],))
        if usuarios:
            g.usuario = usuarios[0]
        else:
            session.clear()
    if request.endpoint != 'login' and not g.usuario:
        return redirect(url_for('login'))
    if request.method == 'POST':
        recebido = request.form.get('csrf_token', '')
        esperado = session.get('csrf_token', '')
        if not esperado or not hmac.compare_digest(esperado.encode(), recebido.encode()):
            abort(400, description='Formulário expirado. Recarregue a página e tente novamente.')


@app.context_processor
def contexto():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)
    return {'csrf_token': session['csrf_token'], 'usuario': g.get('usuario'), 'hoje': agora().date()}


@app.after_request
def cabecalhos(resposta):
    resposta.headers['X-Content-Type-Options'] = 'nosniff'
    resposta.headers['X-Frame-Options'] = 'DENY'
    resposta.headers['Referrer-Policy'] = 'same-origin'
    resposta.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    if request.endpoint != 'static':
        resposta.headers['Cache-Control'] = 'no-store'
    return resposta


@app.errorhandler(mysql.connector.Error)
def erro_banco(erro):
    # Apenas o código técnico vai para o log; dados e credenciais não são exibidos.
    app.logger.error('Erro MySQL: %s', erro.errno)
    return render_template('erro.html', banco_indisponivel=True,
                           mensagem='Banco indisponível ou operação concorrente. Tente novamente.'), 503


@app.errorhandler(400)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(413)
def erro_pagina(erro):
    mensagens = {400: 'Formulário inválido ou expirado. Recarregue a página.',
                 403: 'Seu perfil não permite esta operação.', 404: 'Registro ou página não encontrado.',
                 413: 'Formulário maior que o limite permitido.'}
    return render_template('erro.html', mensagem=mensagens[erro.code]), erro.code


def exigir_admin():
    if g.usuario['perfil'] != 'admin':
        abort(403)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nome = request.form.get('login', '').strip().lower()
        senha = request.form.get('senha', '')
        valido = False
        with transacao() as cursor:
            cursor.execute('SELECT * FROM usuarios WHERE login=%s FOR UPDATE', (nome,))
            usuario = cursor.fetchone()
            hash_senha = usuario['senha_hash'] if usuario else HASH_INEXISTENTE
            senha_correta = check_password_hash(hash_senha, senha)
            if usuario and usuario['ativo']:
                bloqueado = usuario['bloqueado_ate'] and usuario['bloqueado_ate'] > agora()
                if not bloqueado and senha_correta:
                    valido = True
                    cursor.execute('UPDATE usuarios SET tentativas=0,bloqueado_ate=NULL WHERE id=%s', (usuario['id'],))
                elif not bloqueado:
                    tentativas = usuario['tentativas'] + 1
                    ate = None
                    if tentativas >= 5:
                        ate = agora() + timedelta(minutes=15)
                        tentativas = 0
                    cursor.execute('UPDATE usuarios SET tentativas=%s,bloqueado_ate=%s WHERE id=%s', (tentativas, ate, usuario['id']))
        if valido:
            session.clear()
            session['usuario_id'] = usuario['id']
            session.permanent = True
            return redirect(url_for('inicio'))
        flash('Credenciais inválidas ou acesso temporariamente bloqueado.', 'error')
    return render_template('login.html')


@app.post('/sair')
def sair():
    session.clear()
    return redirect(url_for('login'))


def lista_reservas():
    return consultar('''SELECT r.*, c.nome AS cliente, q.numero AS quarto, f.nome AS funcionario
        FROM reservas r JOIN clientes c ON c.id=r.cliente_id JOIN quartos q ON q.id=r.quarto_id
        LEFT JOIN funcionarios f ON f.id=r.funcionario_id ORDER BY r.id DESC''')


def resumo():
    return consultar('''SELECT
        (SELECT COUNT(*) FROM quartos WHERE ativo=1) AS quartos,
        (SELECT COUNT(*) FROM quartos WHERE ativo=1 AND status='ocupado') AS ocupados,
        (SELECT COUNT(*) FROM quartos WHERE ativo=1 AND status='desocupado') AS livres,
        (SELECT COUNT(*) FROM clientes WHERE ativo=1) AS clientes,
        (SELECT COUNT(*) FROM funcionarios WHERE ativo=1) AS funcionarios,
        (SELECT COUNT(*) FROM reservas WHERE status IN ('reservada','hospedada')) AS reservas,
        (SELECT COUNT(*) FROM reservas WHERE status='hospedada') AS hospedagens''')[0]


@app.get('/')
def inicio():
    hora = agora().hour
    saudacao = 'Bom dia' if hora < 12 else 'Boa tarde' if hora < 18 else 'Boa noite'
    return render_template('index.html', pagina='inicio', titulo='Visão geral', resumo=resumo(),
                           saudacao=saudacao, reservas=lista_reservas()[:5], pagamentos=lista_pagamentos()[:5])


def mostrar_cadastro(modulo):
    # O nome da tabela vem desta lista fixa, nunca do formulário.
    if modulo not in MODULOS:
        abort(404)
    if modulo == 'funcionarios':
        exigir_admin()
    busca = request.args.get('busca', '').strip()[:100]
    coluna = 'numero' if modulo == 'quartos' else 'nome'
    cpf_sql = '' if modulo == 'quartos' else ' OR cpf LIKE %s'
    valores = ['%' + busca + '%']
    if modulo != 'quartos':
        valores.append('%' + busca + '%')
    registros = consultar(f'SELECT * FROM {modulo} WHERE ({coluna} LIKE %s{cpf_sql}) ORDER BY ativo DESC,id DESC', valores)
    edicao = None
    if request.args.get('editar'):
        if modulo == 'quartos':
            exigir_admin()
        try:
            codigo = inteiro(request.args.get('editar'), 'Código')
        except ValueError:
            abort(404)
        itens = consultar(f'SELECT * FROM {modulo} WHERE id=%s', (codigo,))
        if not itens:
            abort(404)
        edicao = itens[0]
    return render_template('cadastro.html', pagina=modulo, titulo=MODULOS[modulo],
                           modulo=modulo, registros=registros, edicao=edicao, busca=busca)


def codigo_form():
    valor = request.form.get('id')
    return inteiro(valor, 'Código') if valor else None


def verificar_edicao(cursor, tabela, codigo):
    if codigo:
        cursor.execute(f'SELECT id FROM {tabela} WHERE id=%s AND ativo=1 FOR UPDATE', (codigo,))
        if not cursor.fetchone():
            raise ValueError('Registro inexistente ou inativo.')


@app.route('/clientes', methods=['GET', 'POST'])
def clientes():
    if request.method == 'POST':
        try:
            codigo = codigo_form()
            nascimento = data(request.form.get('nascimento'), 'Nascimento') if request.form.get('nascimento') else None
            if nascimento and nascimento > agora().date():
                raise ValueError('Nascimento não pode estar no futuro.')
            email = request.form.get('email', '').strip()
            if len(email) > 100 or (email and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email)):
                raise ValueError('E-mail inválido.')
            cliente = Cliente(texto(request.form.get('nome'), 'Nome', 100),
                              cpf_valido(request.form.get('cpf')), telefone_valido(request.form.get('telefone')),
                              nascimento, email)
            valores = (cliente.get_nome(), cliente.get_cpf(), cliente.get_telefone(), cliente.nascimento, cliente.email)
            with transacao() as cursor:
                verificar_edicao(cursor, 'clientes', codigo)
                if codigo:
                    cursor.execute('UPDATE clientes SET nome=%s,cpf=%s,telefone=%s,nascimento=%s,email=%s WHERE id=%s', valores + (codigo,))
                else:
                    cursor.execute('INSERT INTO clientes (nome,cpf,telefone,nascimento,email) VALUES (%s,%s,%s,%s,%s)', valores)
            flash('Hóspede salvo com sucesso.')
        except ValueError as erro:
            flash(str(erro), 'error')
        except mysql.connector.IntegrityError:
            flash('CPF já cadastrado, inclusive em registros inativos.', 'error')
        return redirect(url_for('clientes', editar=request.form.get('id') or None))
    return mostrar_cadastro('clientes')


@app.route('/quartos', methods=['GET', 'POST'])
def quartos():
    if request.method == 'POST':
        exigir_admin()
        try:
            codigo = codigo_form()
            tipo = texto(request.form.get('tipo'), 'Tipo', 30)
            if tipo not in ('Solteiro', 'Casal', 'Familia', 'Suite'):
                raise ValueError('Selecione um tipo de quarto válido.')
            quarto = Quarto(tipo, dinheiro(request.form.get('valor_diaria'), 'Diária'),
                            inteiro(request.form.get('numero'), 'Número do quarto'),
                            valor_mensal=dinheiro(request.form.get('valor_mensal') or '0', 'Valor mensal', True),
                            capacidade=inteiro(request.form.get('capacidade'), 'Capacidade', 1, 20),
                            banheiro=request.form.get('banheiro') == 'on')
            valores = (quarto.get_numero(), quarto.get_tipo(), quarto.get_valor_diaria(),
                       quarto.get_valor_mensal(), quarto.capacidade, quarto.banheiro)
            with transacao() as cursor:
                verificar_edicao(cursor, 'quartos', codigo)
                if codigo:
                    cursor.execute('UPDATE quartos SET numero=%s,tipo=%s,valor_diaria=%s,valor_mensal=%s,capacidade=%s,banheiro=%s WHERE id=%s', valores + (codigo,))
                else:
                    cursor.execute('INSERT INTO quartos (numero,tipo,valor_diaria,valor_mensal,capacidade,banheiro) VALUES (%s,%s,%s,%s,%s,%s)', valores)
            flash('Quarto salvo com sucesso.')
        except ValueError as erro:
            flash(str(erro), 'error')
        except mysql.connector.IntegrityError:
            flash('Número de quarto já cadastrado, inclusive em registros inativos.', 'error')
        return redirect(url_for('quartos', editar=request.form.get('id') or None))
    return mostrar_cadastro('quartos')


@app.route('/funcionarios', methods=['GET', 'POST'])
def funcionarios():
    exigir_admin()
    if request.method == 'POST':
        try:
            codigo = codigo_form()
            funcionario = Funcionario(texto(request.form.get('nome'), 'Nome', 100),
                                      cpf_valido(request.form.get('cpf')), telefone_valido(request.form.get('telefone')),
                                      texto(request.form.get('cargo'), 'Cargo', 60))
            valores = (funcionario.get_nome(), funcionario.cpf, funcionario.telefone, funcionario.get_cargo())
            with transacao() as cursor:
                verificar_edicao(cursor, 'funcionarios', codigo)
                if codigo:
                    cursor.execute('UPDATE funcionarios SET nome=%s,cpf=%s,telefone=%s,cargo=%s WHERE id=%s', valores + (codigo,))
                else:
                    cursor.execute('INSERT INTO funcionarios (nome,cpf,telefone,cargo) VALUES (%s,%s,%s,%s)', valores)
            flash('Funcionário salvo com sucesso.')
        except ValueError as erro:
            flash(str(erro), 'error')
        except mysql.connector.IntegrityError:
            flash('CPF já cadastrado, inclusive em registros inativos.', 'error')
        return redirect(url_for('funcionarios', editar=request.form.get('id') or None))
    return mostrar_cadastro('funcionarios')


@app.post('/cadastros/<modulo>/<int:codigo>/situacao')
def situacao(modulo, codigo):
    exigir_admin()
    if modulo not in MODULOS:
        abort(404)
    try:
        with transacao() as cursor:
            cursor.execute(f'SELECT * FROM {modulo} WHERE id=%s FOR UPDATE', (codigo,))
            registro = cursor.fetchone()
            if not registro:
                abort(404)
            if registro['ativo']:
                coluna = {'clientes': 'cliente_id', 'quartos': 'quarto_id', 'funcionarios': 'funcionario_id'}[modulo]
                cursor.execute(f"SELECT id FROM reservas WHERE {coluna}=%s AND status IN ('reservada','hospedada') FOR UPDATE", (codigo,))
                if cursor.fetchall():
                    raise ValueError('Finalize ou cancele as reservas ativas antes de desativar.')
            cursor.execute(f'UPDATE {modulo} SET ativo=%s WHERE id=%s', (not registro['ativo'], codigo))
        flash('Situação atualizada. O histórico foi preservado.')
    except ValueError as erro:
        flash(str(erro), 'error')
    return redirect(url_for(modulo))


@app.route('/reservas', methods=['GET', 'POST'])
def reservas():
    if request.method == 'POST':
        try:
            funcionario = request.form.get('funcionario_id')
            reserva = Reserva(inteiro(request.form.get('cliente_id'), 'Hóspede'),
                              inteiro(request.form.get('quarto_id'), 'Quarto'),
                              data(request.form.get('entrada'), 'Entrada'), data(request.form.get('saida'), 'Saída'),
                              inteiro(funcionario, 'Funcionário') if funcionario else None)
            reserva.salvar()
            flash('Reserva criada. O valor da diária foi preservado nesta reserva.')
        except ValueError as erro:
            flash(str(erro), 'error')
        return redirect(url_for('reservas'))
    entrada = request.args.get('entrada', '')
    saida = request.args.get('saida', '')
    disponiveis = consultar('SELECT * FROM quartos WHERE ativo=1 ORDER BY numero')
    if entrada or saida:
        try:
            inicio = data(entrada, 'Entrada')
            fim = data(saida, 'Saída')
            if fim <= inicio:
                raise ValueError('Saída deve ser posterior à entrada.')
            disponiveis = consultar('''SELECT * FROM quartos q WHERE ativo=1 AND NOT EXISTS
                (SELECT 1 FROM reservas r WHERE r.quarto_id=q.id AND r.status IN ('reservada','hospedada')
                AND r.entrada < %s AND r.saida > %s) ORDER BY numero''', (fim, inicio))
        except ValueError as erro:
            flash(str(erro), 'error')
            disponiveis = []
    return render_template('reservas.html', pagina='reservas', titulo='Hospedagens', reservas=lista_reservas(),
                           clientes=consultar('SELECT id,nome,cpf FROM clientes WHERE ativo=1 ORDER BY nome'),
                           quartos=disponiveis, funcionarios=consultar('SELECT id,nome FROM funcionarios WHERE ativo=1 ORDER BY nome'),
                           entrada=entrada, saida=saida)


@app.post('/reservas/<int:codigo>/<acao>')
def acao_reserva(codigo, acao):
    try:
        movimentar(codigo, acao)
        flash('Hospedagem atualizada com sucesso.')
    except ValueError as erro:
        flash(str(erro), 'error')
    return redirect(url_for('reservas'))


def lista_pagamentos():
    return consultar('''SELECT p.*,c.nome AS cliente FROM pagamentos p
        JOIN reservas r ON r.id=p.reserva_id JOIN clientes c ON c.id=r.cliente_id ORDER BY p.id DESC''')


@app.route('/pagamentos', methods=['GET', 'POST'])
def pagamentos():
    if request.method == 'POST':
        try:
            codigo = inteiro(request.form.get('reserva_id'), 'Reserva')
            valor = dinheiro(request.form.get('valor'))
            forma = request.form.get('forma')
            status = request.form.get('status')
            if forma not in ('Dinheiro', 'Cartao', 'PIX', 'Transferencia') or status not in ('Pago', 'Pendente'):
                raise ValueError('Selecione forma e situação válidas.')
            with transacao() as cursor:
                cursor.execute('SELECT * FROM reservas WHERE id=%s FOR UPDATE', (codigo,))
                reserva = cursor.fetchone()
                if not reserva or reserva['status'] == 'cancelada':
                    raise ValueError('Selecione uma reserva válida.')
                cursor.execute('SELECT valor FROM pagamentos WHERE reserva_id=%s FOR UPDATE', (codigo,))
                acumulado = sum(item['valor'] for item in cursor.fetchall())
                if acumulado + valor > reserva['total']:
                    raise ValueError('Os pagamentos e pendências não podem exceder o total da reserva.')
                cursor.execute('INSERT INTO pagamentos (reserva_id,valor,forma,status,recebido_em) VALUES (%s,%s,%s,%s,%s)',
                               (codigo, valor, forma, status, agora() if status == 'Pago' else None))
            flash('Pagamento registrado.')
        except ValueError as erro:
            flash(str(erro), 'error')
        return redirect(url_for('pagamentos'))
    return render_template('pagamentos.html', pagina='pagamentos', titulo='Pagamentos',
                           pagamentos=lista_pagamentos(), reservas=lista_reservas())


@app.post('/pagamentos/<int:codigo>/confirmar')
def confirmar_pagamento(codigo):
    with transacao() as cursor:
        cursor.execute('SELECT * FROM pagamentos WHERE id=%s FOR UPDATE', (codigo,))
        pagamento = cursor.fetchone()
        if not pagamento:
            abort(404)
        if pagamento['status'] == 'Pendente':
            cursor.execute("UPDATE pagamentos SET status='Pago',recebido_em=%s WHERE id=%s", (agora(), codigo))
    flash('Pagamento confirmado.')
    return redirect(url_for('pagamentos'))


@app.get('/relatorios')
def relatorios():
    exigir_admin()
    hoje = agora().date()
    tipo_padrao = 'personalizado' if 'inicio' in request.args or 'fim' in request.args else 'mes'
    tipo = request.args.get('tipo', tipo_padrao)
    try:
        if tipo not in ('mes', 'ano', 'personalizado'):
            raise ValueError('Selecione um período válido.')
        ano = inteiro(request.args.get('ano', hoje.year), 'Ano', 1000, 9998)
        mes = inteiro(request.args.get('mes', hoje.month), 'Mês', 1, 12)
        if tipo == 'personalizado':
            inicio = data(request.args.get('inicio', hoje.replace(day=1).isoformat()), 'Data inicial')
            fim = data(request.args.get('fim', hoje.isoformat()), 'Data final')
        elif tipo == 'ano':
            inicio = date(ano, 1, 1)
            fim = date(ano, 12, 31)
        else:
            inicio = date(ano, mes, 1)
            fim = date(ano, mes, monthrange(ano, mes)[1])
        if fim == date.max:
            raise ValueError('O período não pode terminar no último dia do ano 9999.')
        if fim < inicio or (fim - inicio).days > 3660:
            raise ValueError('Selecione um período de até dez anos, com fim posterior ao início.')
    except ValueError as erro:
        flash(str(erro), 'error')
        return redirect(url_for('relatorios'))
    itens = consultar('''SELECT p.*,c.nome AS cliente FROM pagamentos p JOIN reservas r ON r.id=p.reserva_id
        JOIN clientes c ON c.id=r.cliente_id WHERE p.status='Pendente' OR
        (p.recebido_em >= %s AND p.recebido_em < %s) ORDER BY p.id DESC''', (inicio, fim + timedelta(days=1)))
    recebido = sum(p['valor'] for p in itens if p['status'] == 'Pago')
    pendente = sum(p['valor'] for p in itens if p['status'] == 'Pendente')
    pagos = [p for p in itens if p['status'] == 'Pago']
    pendencias = [p for p in itens if p['status'] == 'Pendente']
    operacao = consultar('''SELECT
        SUM(checkin_em >= %s AND checkin_em < %s) AS entradas,
        SUM(checkout_em >= %s AND checkout_em < %s) AS saidas FROM reservas''',
        (inicio, fim + timedelta(days=1), inicio, fim + timedelta(days=1)))[0]
    # Agrupa os recebimentos por mês, incluindo meses sem movimentação.
    receita_mensal = []
    primeiro = inicio.replace(day=1)
    while primeiro <= fim:
        valor = sum(p['valor'] for p in pagos if p['recebido_em'].year == primeiro.year
                    and p['recebido_em'].month == primeiro.month)
        receita_mensal.append({'ano': primeiro.year, 'mes': primeiro.month,
                               'rotulo': MESES[primeiro.month - 1][:3].lower(), 'valor': valor})
        if primeiro.year == fim.year and primeiro.month == fim.month:
            break
        primeiro = date(primeiro.year + 1, 1, 1) if primeiro.month == 12 else date(primeiro.year, primeiro.month + 1, 1)
    maior_receita = max([1] + [item['valor'] for item in receita_mensal])
    if request.args.get('formato') == 'csv':
        memoria = io.StringIO(newline='')
        escritor = csv.writer(memoria, delimiter=';')
        escritor.writerow(['Pagamento', 'Reserva', 'Hóspede', 'Valor', 'Forma', 'Status', 'Recebido em'])
        for p in itens:
            nome = p['cliente']
            # Evita que planilhas executem nomes iniciados por fórmulas.
            if nome.lstrip().startswith(('=', '+', '-', '@')):
                nome = "'" + nome
            escritor.writerow([p['id'], p['reserva_id'], nome, p['valor'], p['forma'], p['status'], p['recebido_em'] or ''])
        return app.response_class('\ufeff' + memoria.getvalue(), mimetype='text/csv',
                                  headers={'Content-Disposition': 'attachment; filename=relatorio-hotel.csv'})
    return render_template('relatorios.html', pagina='relatorios', titulo='Relatórios', pagamentos=itens,
                           inicio=inicio, fim=fim, recebido=recebido, pendente=pendente, resumo=resumo(),
                           tipo=tipo, ano=ano, mes=mes, meses=MESES, pagos=pagos, pendencias=pendencias,
                           operacao=operacao, receita_mensal=receita_mensal, maior_receita=maior_receita)


@app.cli.command('iniciar-banco')
def iniciar_banco():
    """Cria as tabelas sem apagar dados existentes."""
    conexao = conectar()
    cursor = conexao.cursor()
    try:
        sql = Path(__file__).with_name('banco.sql').read_text(encoding='utf-8')
        for comando in sql.split(';'):
            if comando.strip():
                cursor.execute(comando)
        conexao.commit()
    finally:
        cursor.close()
        conexao.close()
    click.echo('Tabelas criadas. Nenhum usuário padrão foi adicionado.')


@app.cli.command('criar-usuario')
@click.option('--login', prompt=True)
@click.option('--perfil', type=click.Choice(['admin', 'recepcao']), default='recepcao', prompt=True)
@click.password_option(confirmation_prompt=True)
def criar_usuario(login, perfil, password):
    """Cria um acesso independente do cadastro de funcionários."""
    login = login.strip().lower()
    if not re.fullmatch(r'[a-z0-9_.-]{3,60}', login) or len(password) < 12 or len(password) > 128:
        raise click.ClickException('Login: 3 a 60 letras/números/_.-. Senha: 12 a 128 caracteres.')
    try:
        executar('INSERT INTO usuarios (login,senha_hash,perfil) VALUES (%s,%s,%s)',
                 (login, generate_password_hash(password), perfil))
    except mysql.connector.IntegrityError:
        raise click.ClickException('Login já cadastrado.') from None
    click.echo('Usuário criado.')


@app.cli.command('desativar-usuario')
@click.argument('login')
def desativar_usuario(login):
    """Revoga o acesso, incluindo sessões já abertas."""
    executar('UPDATE usuarios SET ativo=0 WHERE login=%s', (login.strip().lower(),))
    click.echo('Acesso desativado, se existente.')


@app.cli.command('criar-admin')
def criar_admin():
    """Cria o administrador inicial usando somente configurações locais do .env."""
    login = os.getenv('ADMIN_INITIAL_LOGIN', 'admin').strip().lower()
    senha = os.getenv('ADMIN_INITIAL_PASSWORD', '')
    if not re.fullmatch(r'[a-z0-9_.-]{3,60}', login) or not 12 <= len(senha) <= 128:
        raise click.ClickException('Configure ADMIN_INITIAL_LOGIN e ADMIN_INITIAL_PASSWORD no .env; a senha precisa ter de 12 a 128 caracteres.')
    try:
        executar('INSERT INTO usuarios (login,senha_hash,perfil) VALUES (%s,%s,%s)',
                 (login, generate_password_hash(senha), 'admin'))
    except mysql.connector.IntegrityError:
        click.echo('O login já existe. A senha, o perfil e a situação da conta foram preservados.')
        return
    click.echo('Administrador inicial criado. A senha foi armazenada somente como hash.')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
