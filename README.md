# Hotel São João Evangelista

Sistema de gerenciamento hoteleiro em **Python 3.12+ e Django 5.2 LTS**, com interface em português, Bootstrap 5, JavaScript local, PostgreSQL em produção e SQLite para desenvolvimento. Horários em `America/Sao_Paulo` e valores em reais.

## Iniciar no Windows

No PowerShell, dentro da pasta do projeto:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Abra <http://127.0.0.1:8000>. Entre com o superusuário criado. Ele acessa todas as funções independentemente do perfil. Cadastre os demais usuários em **Funcionários**, escolhendo Administrador, Recepcionista ou Limpeza. Não há senha padrão ou credencial de produção no repositório. Não é necessário ativar o ambiente no PowerShell.

Se `py -3.12` não existir, instale Python 3.12 ou superior e utilize o caminho completo do executável. No Linux/macOS, use `python3.12 -m venv .venv` e `.venv/bin/python` nos comandos seguintes.

### Demonstração opcional

Em uma base sem hóspedes ou quartos, depois de criar o superusuário:

```powershell
.\.venv\Scripts\python.exe manage.py seed_demo --with-reservations
```

Cria 12 quartos, 4 hóspedes explicitamente fictícios e reservas para o dia da execução. Não cria usuários ou senhas, não sobrescreve dados existentes e só funciona com `DEBUG=true`. Sem a opção `--with-reservations`, cria apenas quartos e hóspedes. O painel usa os registros do banco; não contém indicadores fixos de demonstração.

## O que funciona

- Login nativo do Django, troca de senha, logout por POST, limitação de tentativas por usuário, sessões de oito horas e três perfis com autorização no servidor.
- Painel com ocupação real, disponibilidade para hoje, fila de limpeza, chegadas, saídas vencidas e previstas, recebimentos do dia e ações rápidas.
- Quartos: cadastro, edição, categoria, capacidade, diária, situação operacional, ativação e bloqueios por período. A ocupação é independente da situação operacional.
- Hóspedes: cadastro, edição, pesquisa por nome/CPF/telefone e histórico. CPF opcional com dígitos verificadores, unicidade e mascaramento nas listas e exportações. Mesmo nome normalizado e telefone não gera cadastro duplicado.
- Reservas em duas etapas: período e disponibilidade; quarto, hóspede e confirmação. Datas, capacidade e conflitos são validados no servidor. A saída e a próxima entrada podem acontecer no mesmo dia.
- A diária contratada fica preservada. Alterações de datas antes do check-in recalculam o total usando essa diária e o desconto autorizado, sem reduzir o valor abaixo do já recebido. Para trocar de quarto, cancele a reserva sem recebimentos e faça outra.
- Check-in com horário efetivo e período válido; check-out somente após quitar o saldo. A saída coloca o quarto em limpeza. Uma hospedagem vencida continua impedindo nova entrada até ser encerrada.
- Cancelamento e não comparecimento com motivo, responsável e horário. Ausências só podem ser registradas a partir da data prevista de entrada.
- Pagamentos parciais e múltiplos em dinheiro, Pix, crédito, débito e transferência; valores decimais, saldo e prevenção de recebimento acima do total. O mesmo formulário reenviado não registra o pagamento duas vezes.
- Descontos autorizados pelo administrador com justificativa e auditoria.
- Financeiro com receita diária, mensal, por período e forma de pagamento, e todos os saldos pendentes atuais.
- Excel: sete exportações (`Hóspedes`, `Quartos`, `Reservas`, `Hospedagens`, `Pagamentos`, `Financeiro`, `Ocupação prevista`), modelos de importação e conferência antes da gravação. Cabeçalhos, filtros, datas, moeda e larguras formatadas.
- Layout responsivo, navegação por teclado, link para pular ao conteúdo, campos com rótulos, erros em português, estados com texto e cor, foco visível e confirmação para operações destrutivas.

## Uso cotidiano

1. Cadastre os quartos e funcionários com um administrador.
2. Cadastre o hóspede, coletando somente os dados necessários.
3. Clique em **Nova reserva**, consulte o período e selecione o quarto. Um novo hóspede pode ser cadastrado em outra aba; atualize a tela da reserva depois de salvar o cadastro.
4. Confirme a reserva. Para reservas pendentes, abra **Editar reserva** e escolha **Confirmada** antes da entrada.
5. Abra a reserva, confira os dados e clique em **Realizar check-in**.
6. Registre cada valor efetivamente recebido em **Registrar pagamento**.
7. Confira o saldo e confirme o check-out. A limpeza libera o quarto em sua própria tela.

## Perfis e acesso

| Função | Administrador | Recepcionista | Limpeza |
|---|---|---|---|
| Painel operacional | Sim | Sim | Redirecionado à limpeza |
| Consultar quartos | Sim | Sim | Somente fila de limpeza |
| Cadastrar/editar/bloquear quartos | Sim | Não | Não |
| Hóspedes, reservas, entrada e saída | Sim | Sim | Não |
| Registrar pagamentos / consultar conta da reserva | Sim | Sim | Não |
| Descontos e relatórios financeiros consolidados | Sim | Não | Não |
| Importar hóspedes | Sim | Sim | Não |
| Importar quartos | Sim | Não | Não |
| Exportar cadastros e operação | Sim | Sim | Não |
| Concluir limpeza | Sim | Não | Sim |
| Gerenciar funcionários | Sim | Não | Não |

As permissões são aplicadas nas views **e nos serviços de negócio**. Alterar o HTML ou enviar um POST diretamente não concede acesso. Os perfis são controlados pelo campo `User.role`, não por permissões avulsas do Django Admin. O `/admin/` é reservado à consulta técnica da auditoria por superusuários; a operação ocorre nas telas próprias. Desative funcionários pela tela **Funcionários**; não exclua responsáveis por registros históricos.

## Arquitetura e integridade

| Pasta | Responsabilidade |
|---|---|
| `config/` | Configuração por ambiente, banco, rotas e WSGI |
| `core/` | Painel, permissões, componentes de formulário, segurança e auditoria |
| `usuarios/` | Usuário personalizado, perfis, login e funcionários |
| `hospedes/` | Cadastros, CPF e histórico |
| `quartos/` | Inventário, situação operacional e bloqueios por data |
| `reservas/` | Disponibilidade, reservas e transições da hospedagem |
| `financeiro/` | Recebimentos e consolidação financeira |
| `relatorios/` | OpenPyXL, exportações e importação com prévia |
| `templates/`, `static/` | Django Templates, Bootstrap local, CSS e JavaScript |
| `.github/workflows/tests.yml` | Validação automática em SQLite e PostgreSQL 17 |

As regras de reserva, bloqueio e pagamento ficam em `services.py`, com transações atômicas. No PostgreSQL, todas as operações disputam o bloqueio da mesma linha do quarto (`SELECT FOR UPDATE`), antes da reserva. Uma restrição `EXCLUDE USING gist` sobre `daterange(..., '[)')` impede sobreposições de reservas ativas, inclusive em gravações diretas. A migration instala `btree_gist`; o usuário de migração deve poder instalar a extensão, ou o DBA deve instalá-la previamente. Uma constraint adicional permite apenas uma hospedagem ativa por quarto. Bloqueios de manutenção usam os mesmos locks nas operações da aplicação.

O SQLite utiliza transações `IMMEDIATE` e espera de até 20 segundos para serializar escritas. É destinado ao desenvolvimento e à demonstração, com menor capacidade de concorrência. Use PostgreSQL para operação compartilhada em produção. Não altere reservas, pagamentos ou bloqueios diretamente pelo ORM em scripts de manutenção: utilize os serviços para preservar as regras entre tabelas e a auditoria.

## Excel: limites e regras

- Importação de `.xlsx` de até **2 MB**, **1.000 linhas**, 150 entradas no ZIP, até 20 MB descompactados e 2.000 caracteres por célula.
- Utilize a aba `Dados`, os cabeçalhos exatos dos modelos e a aba `Instruções`. Datas de nascimento: `AAAA-MM-DD`. Categorias de quarto: `single`, `double`, `twin`, `family`, `suite`. Ativo: `sim` ou `nao`.
- CPF, telefone e número do quarto devem ser células de texto para manter zeros à esquerda. Telefones não devem começar com `+`; use somente os dígitos.
- Fórmulas, conteúdo iniciado por `= + - @`, macros, objetos incorporados, vínculos externos, compactação excessiva e arquivos inválidos são rejeitados. `defusedxml` protege o parsing XML. Texto que poderia virar fórmula é neutralizado nas exportações.
- A prévia mostra até 50 linhas e todos os erros encontrados. Nada é salvo antes da confirmação; dados e permissões são validados novamente. Qualquer erro cancela a importação inteira. Duplicidades não sobrescrevem cadastros.
- A prévia expira em 15 minutos e fica na sessão no banco de dados, vinculada ao usuário. Execute `clearsessions` diariamente para remover sessões expiradas.
- Exportações limitadas a 20.000 registros e 366 dias. O financeiro possui abas de recebimentos, receita diária, mensal, forma de pagamento e saldos atuais. O período limita os recebimentos; saldos atuais independem dele.
- Ocupação é **prevista/contratada**, calculada pelas datas das reservas não canceladas e pelo inventário atual de quartos; não é uma reconstrução histórica do inventário nem uma medição por hora de presença física.

## Verificações e testes

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test --noinput
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
```

A suíte cobre cadastros, CPF e duplicidade, datas, capacidade, sobreposições e rotatividade, preservação de diária, entrada/saída, cancelamento/ausência, pagamentos parciais, valores inválidos, desconto, reenvio de pagamento, permissões e CSRF, renderização das telas e importação/exportação Excel. Testes com threads disputam o mesmo quarto, o saldo do pagamento e um bloqueio de manutenção. O teste de inserção direta contra a constraint de exclusão é específico do PostgreSQL; fica ignorado no SQLite e é executado no job PostgreSQL do GitHub Actions.

## PostgreSQL e produção

Configure o `.env` (segredos reais ficam apenas no servidor):

```dotenv
DEBUG=false
SECRET_KEY=gere-uma-chave-longa-exclusiva-e-aleatoria
ALLOWED_HOSTS=hotel.seudominio.com.br
CSRF_TRUSTED_ORIGINS=https://hotel.seudominio.com.br
DB_ENGINE=postgresql
DB_NAME=hotel
DB_USER=hotel
DB_PASSWORD=defina-no-servidor
DB_HOST=localhost
DB_PORT=5432
TRUST_PROXY=false
SECURE_SSL_REDIRECT=true
```

Gere a chave com `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` no servidor e armazene-a no `.env` com acesso restrito. Configure PostgreSQL, execute migrations, crie o administrador e rode:

```powershell
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe manage.py check --deploy --fail-level WARNING
.\.venv\Scripts\waitress-serve.exe --listen=127.0.0.1:8000 --threads=8 config.wsgi:application
```

Use proxy reverso com HTTPS e certificado válido. Se ativar `TRUST_PROXY=true`, o proxy deve substituir/remover `X-Forwarded-Proto` enviado pelos clientes e ser o único ponto de acesso ao servidor. Configure o limite de requisição do proxy em 6 MB. Cookies seguros, HSTS, CSRF, XSS, política de conteúdo e proibição de cache para páginas pessoais ficam ativos. Não use `runserver` como servidor de produção. Bootstrap é servido localmente e não requer CDN ou acesso externo durante o uso.

### Docker opcional

Docker não é necessário para o desenvolvimento com SQLite. Com Docker instalado, copie `.env.example` para `.env`, defina `DB_PASSWORD` e uma `SECRET_KEY` exclusiva, depois:

```powershell
docker compose up --build -d
docker compose exec web python manage.py createsuperuser
```

O Compose oferece PostgreSQL 17 persistente e a aplicação em `127.0.0.1:8000`. No teste local, use `DEBUG=true`. Para produção, ajuste HTTPS, proxy, nomes de host e monitoração. O Dockerfile usa um usuário sem privilégios e Waitress. Não exponha a porta do banco à internet.

## Privacidade, auditoria e backup

- Colete apenas os dados necessários à operação. CPF e nascimento são opcionais. Evite dados sensíveis nas observações.
- Recepcionistas visualizam dados pessoais necessários ao atendimento. Limpeza visualiza apenas número, categoria e capacidade dos quartos a limpar.
- Senhas são protegidas pelo hash nativo do Django. Não há integração bancária nem armazenamento de números de cartão.
- Ações importantes geram `AuditEvent`, com funcionário, horário, tipo e identificador do objeto. A auditoria não replica CPF, telefone ou observações pessoais. Justificativas de descontos ficam na auditoria; não inclua informações pessoais nelas.
- Defina com o hotel uma política de retenção, revisão de acessos e atendimento a solicitações LGPD. A base técnica não substitui essa política operacional.
- Consulte [docs/OPERACAO.md](docs/OPERACAO.md) para backup, restauração e rotina de manutenção.

## Limites desta versão e próximos passos

Estão fora desta versão: estornos e reembolsos, cobrança automática de diárias extras, alteração de período após o check-in, troca de quarto durante a hospedagem, acompanhantes individuais, consumo de frigobar, emissão fiscal, canais externos de reserva e integrações bancárias. Reservas com pagamentos não podem ser canceladas até existir um fluxo formal de estorno; o sistema informa a restrição e mantém os recebimentos íntegros. Não há exclusão física de cadastros pela interface.

O próximo passo recomendado é homologar os fluxos com a recepção em uma base de teste PostgreSQL, revisar acessibilidade com usuários reais, configurar backup externo e HTTPS e então planejar estornos e prorrogação da estadia. Docker e infraestrutura HTTPS precisam ser validados no ambiente de destino.

Fontes técnicas: [Django 5.2](https://docs.djangoproject.com/en/5.2/), [constraints PostgreSQL](https://docs.djangoproject.com/en/5.2/ref/contrib/postgres/constraints/), [checklist de implantação](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/), [Bootstrap](https://getbootstrap.com/docs/5.3/). O Bootstrap mantém sua licença MIT em `static/vendor/BOOTSTRAP-LICENSE.txt`.
