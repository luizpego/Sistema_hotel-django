# Operação, backup e restauração

## Rotina do responsável pelo hotel

Diariamente: revisar saídas em atraso, saldos pendentes e fila de limpeza; conferir os pagamentos com os comprovantes; verificar o último backup bem-sucedido. Semanalmente: testar acesso de cada perfil e conferir contas desativadas. Mensalmente: restaurar um backup em uma base isolada e registrar o resultado.

Mantenha o sistema atualizado dentro do Django 5.2 LTS. O Dependabot propõe atualizações de dependências e GitHub Actions; revise os testes antes de aprovar. Instale correções de segurança prontamente.

## PostgreSQL: backup

Utilize as ferramentas da mesma versão principal do PostgreSQL (17 no Compose), com autenticação por arquivo `pgpass` protegido ou gerenciador de segredos; não grave senhas nos scripts ou no Git. Exemplo de backup no servidor:

```powershell
New-Item -ItemType Directory -Force backups
pg_dump -h localhost -U hotel -d hotel -Fc -f backups/hotel.dump
pg_restore --list backups/hotel.dump
```

No Compose:

```powershell
docker compose exec db pg_dump -U hotel -d hotel -Fc -f /tmp/hotel.dump
docker compose cp db:/tmp/hotel.dump backups/hotel.dump
```

Armazene cópias criptografadas fora do servidor, com acesso restrito e política de retenção definida pelo hotel (sugestão inicial: 7 diários, 4 semanais, 12 mensais). Faça um backup adicional antes de cada atualização. O arquivo contém dados pessoais: não o envie ao GitHub nem por canais públicos. Monitore falhas e espaço em disco.

## Restaurar e verificar

Primeiro use uma **nova base de homologação**. A restauração pode substituir dados se executada contra uma base existente; mantenha a base de produção protegida.

```powershell
createdb -h localhost -U hotel hotel_restauracao
pg_restore -h localhost -U hotel -d hotel_restauracao --no-owner --exit-on-error backups/hotel.dump
```

Aponte um `.env` separado para `hotel_restauracao`, sem disponibilizar essa base ao público. Execute `manage.py check`, `manage.py migrate --check`, teste login, confira quantidade de hóspedes/quartos/reservas e valide uma conta e seu histórico de pagamentos. Registre data, operador, arquivo e resultado. Só planeje a substituição de produção após validar a restauração e interromper as escritas.

## SQLite local

Pare o servidor de desenvolvimento antes de copiar `db.sqlite3`, ou use a API `sqlite3.Connection.backup()` para obter uma cópia consistente. Para restaurar localmente, pare o servidor, preserve o arquivo atual e substitua-o pela cópia validada. SQLite é a opção de desenvolvimento; produção compartilhada usa PostgreSQL.

## Sessões e tentativas de login

Execute diariamente `python manage.py clearsessions` usando o ambiente virtual. As prévias Excel ficam na sessão no banco e são removidas junto com as sessões expiradas.

O bloqueio de login ocorre após oito tentativas para o mesmo usuário, por 15 minutos desde a última tentativa aceita. O contador armazena uma chave HMAC, não o nome ou IP. Caso necessário, um responsável técnico pode remover contadores com mais de um dia utilizando `LoginAttempt.objects.filter(last_at__lt=timezone.now()-timedelta(days=1)).delete()` em um comando de manutenção. Adicione também limite global de requisições no proxy para proteção contra abuso distribuído.

## Conferência antes de abrir ao público

- `DEBUG=false`, chave exclusiva, `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS` corretos.
- PostgreSQL, migrations e `btree_gist` aplicados.
- `collectstatic` executado e `check --deploy --fail-level WARNING` aprovado.
- HTTPS, cookies seguros, proxy confiável e limitação de upload configurados.
- Usuários reais com senha individual e perfil adequado; contas de demonstração removidas ou desativadas.
- Backup externo e restauração testados; monitoração de erros, disponibilidade e espaço em disco.
- Homologação de reserva, recebimento, entrada, saída, limpeza e Excel pela equipe.
