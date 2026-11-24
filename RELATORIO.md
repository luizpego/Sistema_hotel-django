# Relatório de entrega — 23/11/2026

## Implementação

Sistema Flask com MySQL, orientação a objetos simples e formulários HTML com GET/POST.
Foram implementados cadastro, consulta, edição, desativação e reativação de hóspedes,
quartos e funcionários; reservas por período, disponibilidade, check-in, check-out,
cancelamento, cálculo por diárias, dashboard real, pagamentos parciais e relatórios CSV.
Inclui autenticação, perfis admin/recepção, hash de senha, CSRF, validações em Python,
SQL parametrizado e transações com bloqueio para evitar reservas simultâneas conflitantes.

A classe Cliente original foi aproveitada. Os métodos de Quarto foram corrigidos para
ficarem dentro da classe, mantendo seus atributos, inclusive o valor mensal informativo.
O app original não persistia os dados e o HTML tinha formulários aninhados; a integração
agora salva no MySQL e utiliza formulários separados. Não foram adicionados frameworks de frontend ou ORM.

A referência GitHub da interface não estava acessível. Foi usado o HTML fornecido
posteriormente pelo usuário, preservando cores, marca H, menu, tipografia do sistema,
cartões e tabelas. Como não havia arquivos de imagem nesse HTML, não há imagens externas
pendentes de carregamento. O CSS é local e o sistema não precisa de JavaScript.

## Arquivos

Comparação com a pasta original:

- Modificados: `app.py`, `cliente.py`, `quarto.py`, `templates/index.html`.
- Preservado: `.gitignore`.
- Criados: `funcionario.py`, `reserva.py`, `banco.py`, `validacao.py`, `banco.sql`,
  `.env.example`, `requirements.txt`, `README.md`, `RELATORIO.md`, `static/style.css`,
  `templates/base.html`, `templates/login.html`, `templates/erro.html`,
  `templates/cadastro.html`, `templates/reservas.html`, `templates/pagamentos.html`,
  `templates/relatorios.html` e `tests/test_sistema.py`.

Como o repositório de destino só continha um atalho, esses fontes aparecem como arquivos
adicionados no Git. Os dois commits anteriores e o atalho foram preservados.
Os fontes da pasta original recebem um backup ZIP separado antes da atualização.

## Verificação executada

Python 3.14.5, Flask 3.1.3, MySQL Connector 26.10.0 e MySQL Server 8.0.46.
Foi iniciada uma instância MySQL isolada em 127.0.0.1:13307 com diretório em `work`,
senha aleatória e bancos descartáveis. Nenhum banco existente do usuário foi alterado.

Resultado: **11 testes de integração aprovados em 24,145 segundos** com MySQL real:

1. Login, bloqueio após cinco erros, hash e revogação de sessão.
2. Cadastro, consulta, edição, desativação e reativação dos três módulos.
3. Cancelamento, datas inválidas, check-in futuro e cliente inativo.
4. Check-in, check-out, ocupação, dashboard e histórico após desativação.
5. CPF e número duplicados, CPF/telefone/e-mail/data e valores inválidos.
6. Acesso anônimo, perfis, CSRF ausente/inválido e logout.
7. Pagamentos, limite do total, confirmação idempotente, relatório e CSV.
8. Conflito de reservas, consulta de disponibilidade, períodos adjacentes e diária preservada.
9. Duas reservas concorrentes no mesmo quarto: uma confirmada e outra recusada.
10. Todas as páginas, links internos, CSS e tokens CSRF dos formulários POST.
11. Tentativas de injeção SQL e escape de conteúdo HTML.

O aplicativo foi executado com Waitress em 127.0.0.1:5050 e acessado pelo navegador.
Login, cadastro de hóspede pelo formulário, atualização dos números reais e navegação
foram conferidos com dados fictícios. Foram inspecionados o painel em tela estreita,
o cadastro e as hospedagens em desktop. Uma captura do painel foi salva na entrega.

## Executar e configurar

Siga o README: criar `.venv`, instalar `requirements.txt`, copiar `.env.example` para
`.env`, gerar SECRET_KEY, criar banco e usuário MySQL, preencher as configurações,
executar `flask --app app iniciar-banco`, criar um usuário admin e executar `python app.py`.
O endereço padrão é http://127.0.0.1:5000. Não há conta/senha padrão.

MySQL foi encontrado instalado. As credenciais do banco de uso real não foram
fornecidas; a aplicação não foi configurada para acessar bancos existentes. Os testes
comprovaram a comunicação com o servidor isolado. `.env` e dados fictícios não são enviados ao Git.

## Limitações

Sem estornos, emissão fiscal, integração bancária, descontos, cobrança mensal automática,
alteração/prorrogação de reservas ou cobrança de atraso. A diária mensal é informativa.
Check-out antecipado mantém o valor contratado; atrasos exigem tratamento operacional.
Sem recuperação de senha por e-mail, MFA, paginação ou auditoria completa. Contas são
criadas e revogadas pelo terminal. Relatórios usam intervalo de datas e não incluem gráficos.
Antes do uso em hotel real, configurar HTTPS, backup e políticas de operação, conforme o README.

## Git

Destino verificado: https://github.com/luizpego/Sistema_hotel-django.git
Branch de trabalho: `main`, baseada em `0512463` (e no ancestral `423973c`).
Mensagem de commit exigida: `interface do sistema`. Sem force push e sem envio para a referência visual.
O resultado final do commit e do push é informado na mensagem de entrega, após a execução.
