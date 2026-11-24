# Hotel Barbosa — Python, Flask e MySQL

Continuação dos fontes originais `app.py`, `cliente.py`, `quarto.py` e `templates/index.html`.
A identidade visual utiliza o HTML fornecido pelo proprietário: azul-marinho, azul, dourado,
menu lateral, cartões e tabelas. O repositório visual informado retornou “Repository not found”;
o HTML enviado depois foi usado como referência. Não havia imagens externas nesse HTML.
O destino Git continha somente `sistema_hotel.lnk`; o histórico e o atalho foram preservados.

## Instalar e executar no Windows

Requisitos: Python 3.11 ou superior e MySQL 8.0.16 ou superior. O MySQL Server 8.0 foi
encontrado neste computador. O Workbench é uma interface; o serviço MySQL também deve estar iniciado.
Abra o terminal na pasta deste README:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copie a chave gerada para `SECRET_KEY` no `.env`. Preencha também o usuário, senha,
host, porta e nome do banco. O exemplo não contém credenciais reais e não é uma configuração pronta.

No MySQL Workbench, conecte-se com uma conta administradora e execute os comandos abaixo.
Substitua a senha ilustrativa por uma senha exclusiva. Não use a conta root no aplicativo:

```sql
CREATE DATABASE sistema_hotel CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'hotel_app'@'localhost' IDENTIFIED BY 'SUBSTITUA_POR_SENHA_FORTE';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, REFERENCES
ON sistema_hotel.* TO 'hotel_app'@'localhost';
```

Use `DB_HOST=localhost` se necessário para corresponder ao usuário criado. Ajuste a porta
ao serviço instalado. As tabelas são criadas pelo arquivo `banco.sql`, sem apagar dados:

```powershell
.\.venv\Scripts\python -m flask --app app iniciar-banco
.\.venv\Scripts\python -m flask --app app criar-usuario --login administrador --perfil admin
.\.venv\Scripts\python app.py
```

A senha é solicitada de forma oculta e precisa ter de 12 a 128 caracteres. Não existe
usuário ou senha padrão. Acesse http://127.0.0.1:5000 e entre com o usuário criado.
Também é possível abrir `banco.sql` no Workbench, selecionar o banco criado e executá-lo.
Após a criação das tabelas, o administrador do banco pode revogar CREATE e REFERENCES do usuário da aplicação.

Para criar um recepcionista ou revogar um acesso:

```powershell
.\.venv\Scripts\python -m flask --app app criar-usuario --login recepcao --perfil recepcao
.\.venv\Scripts\python -m flask --app app desativar-usuario recepcao
```

O cadastro de funcionários descreve a equipe; a conta de usuário controla o acesso.
São cadastros separados. Apenas o administrador mantém quartos e funcionários,
desativa cadastros e acessa relatórios. A recepção consulta quartos, cadastra e edita
hóspedes e opera reservas e pagamentos. Revogar um usuário invalida também suas sessões abertas.

## Funcionamento e regras

- Hóspedes: cadastro, consulta por nome/CPF, edição, desativação e reativação. CPF é
  normalizado e validado pelos dígitos verificadores; telefone exige DDD e 10 ou 11 dígitos.
- Quartos: número único, tipo, capacidade, banheiro, diária e valor mensal informativo.
  A cobrança implementada usa diárias; o valor mensal não gera cobrança automática.
- Funcionários: nome, CPF único, telefone e cargo. Associação opcional à reserva.
- Reservas: entrada e saída previstas, cliente e quarto ativos. A saída precisa ser
  posterior à entrada. O dia de saída pode ser o dia de entrada da próxima reserva.
  Consulte a disponibilidade pelas duas datas antes de escolher o quarto.
- A confirmação usa uma transação e `SELECT ... FOR UPDATE` no quarto. Assim, duas
  requisições concorrentes não confirmam o mesmo período. Os demais dados também são
  verificados novamente dentro da transação. Um conflito técnico pode pedir nova tentativa.
- Check-in: apenas dentro do período reservado e com quarto fisicamente desocupado.
  Check-out libera o quarto e registra a saída real, preservando o período contratado.
  O total é o número de noites reservadas multiplicado pela diária registrada na reserva.
  Mudanças futuras na diária do quarto não alteram valores já contratados.
- Reservas futuras mantêm o quarto desocupado até o check-in. O dashboard mostra a
  ocupação física atual; o filtro de disponibilidade considera reservas por período.
- Desativação preserva o histórico e os números/CPFs únicos. É bloqueada quando há
  reservas ativas associadas. Cadastros inativos podem ser reativados.
- Reservas sem check-in nem pagamentos podem ser canceladas. Com pagamentos lançados,
  o cancelamento é bloqueado para preservar o financeiro.
- Pagamentos: valores parciais, pendentes ou pagos. A soma não pode superar o total
  contratado. Confirmar um pagamento duas vezes não duplica o recebimento.
- Relatórios: recebimentos no período pela data de confirmação e todos os pagamentos
  pendentes lançados. Exportação CSV protegida contra fórmulas em nomes. O relatório
  não representa contas a receber ainda não lançadas na tela de pagamentos.

## Segurança e operação

SQL parametrizado, hash de senha Werkzeug, CSRF em todos os POSTs, cookies HttpOnly e
SameSite, sessão de oito horas, saída por POST, bloqueio de conta por quinze minutos
após cinco erros e autorização conferida no servidor. O Jinja escapa os valores HTML.
Credenciais e dados pessoais não são registrados em logs da aplicação. `.env` e `.venv`
são ignorados pelo Git. Os testes usam dados fictícios.

O servidor de desenvolvimento executa sem debug e somente no computador local.
Para servir o aplicativo de forma mais estável, na pasta do projeto:

```powershell
.\.venv\Scripts\waitress-serve --host=127.0.0.1 --port=5000 app:app
```

Antes de uso real por uma rede, configure um proxy HTTPS, `COOKIE_SECURE=1`, backup
regular do MySQL e permissões do banco com privilégio mínimo. A aplicação não configura
HTTPS, firewall ou backup automaticamente. Proteja o `.env` com as permissões do Windows.
Para disponibilizar em rede, configure o proxy de forma consciente; o endereço padrão é local.

## Como entender o código

- `app.py`: recebe `request.form.get()`, valida e chama SQL ou a classe Reserva;
  envia os resultados ao HTML com `render_template()`.
- `cliente.py`, `quarto.py`, `funcionario.py`: objetos simples com atributos e getters.
  Os métodos do Quarto original foram colocados dentro da classe.
- `reserva.py`: cálculo e transações de reserva, check-in, check-out e cancelamento.
- `banco.py`: conexão, consultas e uma função de transação. `with transacao()` abre
  a conexão, confirma ao terminar e desfaz alterações em caso de erro.
- `validacao.py`: regras de CPF, telefone, datas, inteiros e valores monetários com Decimal.
- `banco.sql`: tabelas, índices e chaves estrangeiras que protegem o histórico.
- `templates/`: HTML Jinja; `base.html` reaproveita o menu e a proteção dos formulários.
- `static/style.css`: estilo adaptado da interface fornecida, inclusive para celular.
- `tests/test_sistema.py`: testes com cliente Flask e MySQL real, inclusive concorrência.

Os poucos nomes de tabela montados no SQL vêm de uma lista fixa no Python. Valores
de formulário e busca sempre são enviados pelos parâmetros `%s` do conector.

## Repetir os testes

Crie um banco separado, por exemplo `test_sistema_hotel`, conceda acesso a ele e configure
DB_NAME para esse banco somente durante os testes. Use um `.env` separado ou variáveis
do terminal. **Os testes limpam todas as tabelas desse banco antes de cada caso.**
O teste recusa nomes de banco que não começam por `test_` e não substitui MySQL por SQLite.

```powershell
.\.venv\Scripts\python -m unittest discover -s tests -v
```

Use os mesmos DB_HOST, DB_PORT, DB_USER, DB_PASSWORD e SECRET_KEY descritos acima,
apontando exclusivamente para o banco descartável. Consulte `RELATORIO.md` para o resultado da entrega.

## Limitações desta versão

Não inclui emissão fiscal, integração bancária, estornos, alteração de períodos já
reservados, prorrogação automática, descontos, cobrança de excedentes ou cobrança mensal.
Saída antecipada mantém o total contratado; atraso na saída precisa ser tratado pelo
responsável. Mesmo após a saída prevista, um quarto fisicamente ocupado impede novo check-in.
Não há recuperação de senha por e-mail, MFA ou trilha completa de auditoria. A criação
e revogação de contas são feitas pelo terminal administrativo. As listas não têm paginação.
Relatórios oferecem os filtros mensal, anual e personalizado, gráfico dos recebimentos,
exportação CSV e impressão pelo navegador.

## Administrador inicial

Para criar um administrador inicial com o login desejado, preencha localmente no `.env`:

```dotenv
ADMIN_INITIAL_LOGIN=admin
ADMIN_INITIAL_PASSWORD=
```

Defina a senha no campo vazio (de 12 a 128 caracteres) e execute:

```powershell
.\.venv\Scripts\python -m flask --app app criar-admin
```

O comando usa hash de senha e preserva qualquer conta que já possua esse login,
sem redefinir a senha, o perfil ou a situação. Remova ADMIN_INITIAL_PASSWORD do `.env`
após a criação. A senha genérica solicitada foi criada somente na base local de prévia;
ela não é incluída nos arquivos do Git. Use uma senha exclusiva para uso real.
