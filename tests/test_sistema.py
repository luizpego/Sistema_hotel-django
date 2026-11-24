"""Integração com MySQL real. Use somente um DB_NAME iniciado por test_."""
import os
import re
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path
from threading import Barrier

if not os.getenv('DB_NAME', '').startswith('test_'):
    raise RuntimeError('Testes precisam de banco descartável com nome iniciado por test_.')

from app import app
from banco import consultar, executar, transacao
from reserva import Reserva, agora
from validacao import cpf_valido, dinheiro


class Formularios(HTMLParser):
    def __init__(self):
        super().__init__()
        self.formularios = []
        self.atual = None
        self.links = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'form':
            self.atual = {'metodo': attrs.get('method', 'get'), 'csrf': False}
            self.formularios.append(self.atual)
        if tag == 'input' and attrs.get('name') == 'csrf_token' and self.atual:
            self.atual['csrf'] = bool(attrs.get('value'))
        if tag in ('a', 'link'):
            self.links.add(attrs.get('href', ''))

    def handle_endtag(self, tag):
        if tag == 'form':
            self.atual = None


class SistemaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config.update(TESTING=True)
        resultado = app.test_cli_runner().invoke(args=['iniciar-banco'])
        if resultado.exit_code:
            raise RuntimeError(resultado.output) from resultado.exception

    def setUp(self):
        with transacao() as cursor:
            for tabela in ('pagamentos', 'reservas', 'usuarios', 'funcionarios', 'quartos', 'clientes'):
                cursor.execute('DELETE FROM ' + tabela)
        self.senha = 'Senha-ficticia-para-teste-123!'
        for login, perfil in [('admin', 'admin'), ('recepcao', 'recepcao')]:
            resultado = app.test_cli_runner().invoke(args=['criar-usuario', '--login', login,
                '--perfil', perfil, '--password', self.senha])
            self.assertEqual(resultado.exit_code, 0, resultado.output)
        self.client = app.test_client()
        self.entrar()

    def token(self, client=None):
        client = client or self.client
        with client.session_transaction() as sessao:
            return sessao['csrf_token']

    def entrar(self, nome='admin', client=None):
        client = client or self.client
        self.assertEqual(client.get('/login').status_code, 200)
        resposta = client.post('/login', data={'login': nome, 'senha': self.senha,
                                              'csrf_token': self.token(client)}, follow_redirects=True)
        self.assertEqual(resposta.status_code, 200)
        return resposta

    def postar(self, url, valores=None, client=None):
        client = client or self.client
        valores = dict(valores or {})
        valores['csrf_token'] = self.token(client)
        return client.post(url, data=valores, follow_redirects=True)

    def cadastrar(self):
        self.assertIn('salvo', self.postar('/clientes', {'nome': 'Hóspede Fictício', 'cpf': '529.982.247-25',
            'telefone': '(11) 99999-9999', 'email': 'teste@example.invalid', 'nascimento': '1990-05-01'}).get_data(as_text=True))
        self.assertIn('salvo', self.postar('/quartos', {'numero': '101', 'tipo': 'Casal',
            'valor_diaria': '150.50', 'valor_mensal': '3000', 'capacidade': '2', 'banheiro': 'on'}).get_data(as_text=True))
        self.postar('/funcionarios', {'nome': 'Funcionário Fictício', 'cpf': '11144477735',
            'telefone': '11988888888', 'cargo': 'Recepcionista'})
        cliente = consultar('SELECT id FROM clientes')[0]['id']
        quarto = consultar('SELECT id FROM quartos')[0]['id']
        funcionario = consultar('SELECT id FROM funcionarios')[0]['id']
        return cliente, quarto, funcionario

    def reservar(self, cliente, quarto, funcionario=None, dias=2):
        hoje = agora().date()
        resposta = self.postar('/reservas', {'cliente_id': cliente, 'quarto_id': quarto,
            'funcionario_id': funcionario or '', 'entrada': hoje.isoformat(),
            'saida': (hoje + timedelta(days=dias)).isoformat()})
        self.assertEqual(resposta.status_code, 200)
        return consultar('SELECT * FROM reservas ORDER BY id DESC')[0]

    def test_rotas_navegacao_css_e_csrf_dos_formularios(self):
        urls = ['/', '/clientes', '/quartos', '/funcionarios', '/reservas', '/pagamentos', '/relatorios']
        for url in urls:
            with self.subTest(url=url):
                resposta = self.client.get(url)
                self.assertEqual(resposta.status_code, 200)
                parser = Formularios()
                parser.feed(resposta.get_data(as_text=True))
                for form in parser.formularios:
                    if form['metodo'].lower() == 'post':
                        self.assertTrue(form['csrf'])
                for link in parser.links:
                    if link.startswith('/'):
                        self.assertEqual(self.client.get(link).status_code, 200, link)
                self.assertIn("default-src 'self'", resposta.headers['Content-Security-Policy'])
        self.assertEqual(self.client.get('/inexistente').status_code, 404)
        self.assertEqual(self.client.get('/static/style.css').status_code, 200)

    def test_login_csrf_logout_e_permissoes(self):
        anonimo = app.test_client()
        for url in ['/', '/clientes', '/quartos', '/reservas', '/pagamentos', '/relatorios', '/funcionarios']:
            self.assertEqual(anonimo.get(url).status_code, 302)
        self.assertEqual(self.client.post('/clientes', data={'nome': 'x'}).status_code, 400)
        self.assertEqual(self.client.post('/clientes', data={'csrf_token': 'á'}).status_code, 400)
        recepcao = app.test_client()
        self.entrar('recepcao', recepcao)
        for url in ['/funcionarios', '/relatorios']:
            self.assertEqual(recepcao.get(url).status_code, 403)
        for url in ['/funcionarios', '/quartos', '/cadastros/clientes/1/situacao']:
            self.assertEqual(self.postar(url, client=recepcao).status_code, 403)
        self.assertEqual(self.postar('/sair').status_code, 200)
        self.assertEqual(self.client.get('/').status_code, 302)

    def test_bloqueio_login_hash_e_revogacao(self):
        self.postar('/sair')
        self.client.get('/login')
        for _ in range(5):
            self.postar('/login', {'login': 'admin', 'senha': 'errada'})
        self.assertIn('bloqueado', self.postar('/login', {'login': 'admin', 'senha': self.senha}).get_data(as_text=True))
        usuario = consultar("SELECT * FROM usuarios WHERE login='admin'")[0]
        self.assertNotEqual(usuario['senha_hash'], self.senha)
        self.assertIsNotNone(usuario['bloqueado_ate'])
        executar('UPDATE usuarios SET bloqueado_ate=NULL WHERE id=%s', (usuario['id'],))
        self.entrar()
        resultado = app.test_cli_runner().invoke(args=['desativar-usuario', 'admin'])
        self.assertEqual(resultado.exit_code, 0)
        self.assertEqual(self.client.get('/').status_code, 302)

    def test_cadastros_consulta_edicao_desativacao_reativacao(self):
        cliente, quarto, funcionario = self.cadastrar()
        self.assertIn('Hóspede Fictício', self.client.get('/clientes?busca=52998224725').get_data(as_text=True))
        self.assertIn('101', self.client.get('/quartos?busca=101').get_data(as_text=True))
        self.assertIn('Funcionário Fictício', self.client.get('/funcionarios?busca=Fict').get_data(as_text=True))
        for modulo, codigo in [('clientes', cliente), ('quartos', quarto), ('funcionarios', funcionario)]:
            self.assertEqual(self.client.get(f'/{modulo}?editar={codigo}').status_code, 200)
        self.postar('/clientes', {'id': cliente, 'nome': 'Nome Editado', 'cpf': '52998224725', 'telefone': '11999999999'})
        self.postar('/quartos', {'id': quarto, 'numero': '102', 'tipo': 'Suite', 'valor_diaria': '200', 'capacidade': '3'})
        self.postar('/funcionarios', {'id': funcionario, 'nome': 'Equipe Editada', 'cpf': '11144477735', 'telefone': '11988888888', 'cargo': 'Gerente'})
        self.assertEqual(consultar('SELECT nome FROM clientes')[0]['nome'], 'Nome Editado')
        self.assertEqual(consultar('SELECT numero FROM quartos')[0]['numero'], 102)
        self.assertEqual(consultar('SELECT cargo FROM funcionarios')[0]['cargo'], 'Gerente')
        for modulo, codigo in [('clientes', cliente), ('quartos', quarto), ('funcionarios', funcionario)]:
            self.postar(f'/cadastros/{modulo}/{codigo}/situacao')
            self.assertEqual(consultar('SELECT ativo FROM ' + modulo)[0]['ativo'], 0)
            self.postar(f'/cadastros/{modulo}/{codigo}/situacao')
            self.assertEqual(consultar('SELECT ativo FROM ' + modulo)[0]['ativo'], 1)

    def test_duplicados_e_validacao_dados(self):
        self.cadastrar()
        resposta = self.postar('/clientes', {'nome': 'Duplicado', 'cpf': '52998224725', 'telefone': '11999999999'})
        self.assertIn('CPF já cadastrado', resposta.get_data(as_text=True))
        resposta = self.postar('/quartos', {'numero': '101', 'tipo': 'Casal', 'valor_diaria': '100', 'capacidade': '2'})
        self.assertIn('já cadastrado', resposta.get_data(as_text=True))
        resposta = self.postar('/funcionarios', {'nome': 'Duplicado', 'cpf': '11144477735', 'telefone': '11988888888', 'cargo': 'Gerente'})
        self.assertIn('CPF já cadastrado', resposta.get_data(as_text=True))
        for valores in [{'cpf': '00000000000'}, {'cpf': '12345678901'}, {'telefone': 'abc'}, {'nascimento': '2999-01-01'}, {'email': 'invalido'}]:
            cadastro = {'nome': 'Teste', 'cpf': '12345678909', 'telefone': '11999999999'}
            cadastro.update(valores)
            self.postar('/clientes', cadastro)
        self.assertEqual(len(consultar('SELECT id FROM clientes')), 1)
        for valor in ['NaN', 'Infinity', '-1', '1.001', '0', '999999999999999999999']:
            with self.assertRaises(ValueError):
                dinheiro(valor)
        self.assertEqual(cpf_valido('529.982.247-25'), '52998224725')
        self.assertEqual(self.client.get('/clientes?editar=abc').status_code, 404)

    def test_reserva_conflito_disponibilidade_e_diaria_preservada(self):
        cliente, quarto, funcionario = self.cadastrar()
        r = self.reservar(cliente, quarto, funcionario)
        self.assertEqual(r['total'], Decimal('301.00'))
        self.reservar(cliente, quarto, funcionario)
        self.assertEqual(len(consultar('SELECT id FROM reservas')), 1)
        hoje = agora().date()
        resposta = self.client.get(f'/reservas?entrada={hoje}&saida={hoje + timedelta(days=2)}')
        self.assertNotIn(f'<option value="{quarto}">Quarto', resposta.get_data(as_text=True))
        seguinte = Reserva(cliente, quarto, hoje + timedelta(days=2), hoje + timedelta(days=3))
        seguinte.salvar()
        executar('UPDATE quartos SET valor_diaria=999 WHERE id=%s', (quarto,))
        self.assertEqual(consultar('SELECT total FROM reservas WHERE id=%s', (r['id'],))[0]['total'], Decimal('301.00'))
        for modulo, codigo in [('clientes', cliente), ('quartos', quarto), ('funcionarios', funcionario)]:
            self.assertIn('reservas ativas', self.postar(f'/cadastros/{modulo}/{codigo}/situacao').get_data(as_text=True))
            self.assertEqual(consultar('SELECT ativo FROM ' + modulo + ' WHERE id=%s', (codigo,))[0]['ativo'], 1)

    def test_checkin_checkout_dashboard_historico(self):
        cliente, quarto, _ = self.cadastrar()
        r = self.reservar(cliente, quarto)
        self.postar(f"/reservas/{r['id']}/checkout")
        self.assertEqual(consultar('SELECT status FROM reservas')[0]['status'], 'reservada')
        self.postar(f"/reservas/{r['id']}/checkin")
        self.assertEqual(consultar('SELECT status FROM quartos')[0]['status'], 'ocupado')
        self.assertEqual(consultar('SELECT status FROM reservas')[0]['status'], 'hospedada')
        self.assertIn('Quartos ocupados', self.client.get('/').get_data(as_text=True))
        self.postar(f"/reservas/{r['id']}/cancelar")
        self.assertEqual(consultar('SELECT status FROM reservas')[0]['status'], 'hospedada')
        self.postar(f"/reservas/{r['id']}/checkout")
        self.assertEqual(consultar('SELECT status FROM quartos')[0]['status'], 'desocupado')
        self.assertIsNotNone(consultar('SELECT checkout_em FROM reservas')[0]['checkout_em'])
        for modulo, codigo in [('clientes', cliente), ('quartos', quarto)]:
            self.postar(f'/cadastros/{modulo}/{codigo}/situacao')
        self.assertEqual(len(consultar('SELECT id FROM reservas')), 1)
        self.assertIn('Hóspede Fictício', self.client.get('/reservas').get_data(as_text=True))

    def test_cancelamento_datas_e_inativos(self):
        cliente, quarto, _ = self.cadastrar()
        hoje = agora().date()
        for entrada, saida in [(hoje, hoje), (hoje-timedelta(days=1), hoje), (hoje+timedelta(days=2), hoje)]:
            with self.assertRaises(ValueError):
                Reserva(cliente, quarto, entrada, saida).salvar()
        r = Reserva(cliente, quarto, hoje+timedelta(days=3), hoje+timedelta(days=4)).salvar()
        self.postar(f'/reservas/{r}/checkin')
        self.assertEqual(consultar('SELECT status FROM reservas')[0]['status'], 'reservada')
        self.postar(f'/reservas/{r}/cancelar')
        self.assertEqual(consultar('SELECT status FROM reservas')[0]['status'], 'cancelada')
        self.postar(f'/cadastros/clientes/{cliente}/situacao')
        with self.assertRaises(ValueError):
            Reserva(cliente, quarto, hoje, hoje+timedelta(days=1)).salvar()

    def test_pagamentos_confirmacao_relatorio_csv(self):
        cliente, quarto, _ = self.cadastrar()
        r = self.reservar(cliente, quarto)
        self.postar('/pagamentos', {'reserva_id': r['id'], 'valor': '100.50', 'forma': 'PIX', 'status': 'Pendente'})
        p = consultar('SELECT * FROM pagamentos')[0]
        self.assertIsNone(p['recebido_em'])
        self.postar(f"/reservas/{r['id']}/cancelar")
        self.assertEqual(consultar('SELECT status FROM reservas')[0]['status'], 'reservada')
        self.postar('/pagamentos', {'reserva_id': r['id'], 'valor': '999', 'forma': 'PIX', 'status': 'Pago'})
        self.assertEqual(len(consultar('SELECT id FROM pagamentos')), 1)
        self.postar(f"/pagamentos/{p['id']}/confirmar")
        p = consultar('SELECT * FROM pagamentos')[0]
        self.assertEqual(p['status'], 'Pago')
        self.assertIsNotNone(p['recebido_em'])
        self.postar(f"/pagamentos/{p['id']}/confirmar")
        self.assertEqual(consultar('SELECT recebido_em FROM pagamentos')[0]['recebido_em'], p['recebido_em'])
        self.postar('/pagamentos', {'reserva_id': r['id'], 'valor': '200.50', 'forma': 'Dinheiro', 'status': 'Pago'})
        self.assertIn('301,00', self.client.get('/relatorios').get_data(as_text=True))
        self.assertIn('text/csv', self.client.get('/relatorios?formato=csv').content_type)
        self.assertIn('100.50', self.client.get('/relatorios?formato=csv').get_data(as_text=True))

    def test_reservas_simultaneas(self):
        cliente, quarto, _ = self.cadastrar()
        outro = executar('INSERT INTO clientes (nome,cpf,telefone) VALUES (%s,%s,%s)', ('Outro fictício','12345678909','11999999999'))
        barreira = Barrier(2)
        def tentar(codigo):
            barreira.wait(timeout=10)
            try:
                Reserva(codigo, quarto, agora().date(), agora().date()+timedelta(days=2)).salvar()
                return 'criada'
            except ValueError:
                return 'conflito'
        with ThreadPoolExecutor(max_workers=2) as pool:
            resultados = list(pool.map(tentar, [cliente, outro]))
        self.assertCountEqual(resultados, ['criada', 'conflito'])
        self.assertEqual(len(consultar('SELECT id FROM reservas')), 1)

    def test_sql_injection_e_html_escapado(self):
        cliente, quarto, _ = self.cadastrar()
        self.assertEqual(self.client.get("/clientes?busca=' OR 1=1 --").status_code, 200)
        self.assertEqual(len(consultar('SELECT id FROM clientes')), 1)
        self.postar('/clientes', {'id': cliente, 'nome': '<script>alert(1)</script>', 'cpf': '52998224725', 'telefone': '11999999999'})
        html = self.client.get('/clientes').get_data(as_text=True)
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>alert(1)</script>', html)


if __name__ == '__main__':
    unittest.main()
