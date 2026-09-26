# Checklist — Estudante 1

Status deste pacote:

## RF20 — Bronze
- [x] projeto Hop e configuração versionável
- [x] ambiente `desafio4-dev`
- [x] metadata PostgreSQL reutilizável
- [x] credenciais fora dos pipelines
- [x] CSV `catalogo.csv`
- [x] JSON `interacoes.json`
- [x] JSON `comentarios.json`
- [x] schema `bronze`
- [x] `origem`, `data_hora_ingestao`, `id_execucao`
- [x] preservação dos campos de negócio como texto na Bronze

## RF21 — Silver
- [x] schema `silver`
- [x] padronização de texto/categorias/domínios
- [x] conversão segura de datas e números
- [x] tratamento de obrigatórios/ausentes
- [x] duplicidades por chave de negócio
- [x] referência de usuário ao acervo do Desafio 1
- [x] referência de conteúdo à Silver/acervo do Desafio 1
- [x] válidos separados de quarentena

## RF22 — Workflow
- [x] Bronze antes de Silver
- [x] falha crítica interrompe dependências
- [x] início/fim/duração/resultado por etapa
- [x] estado final `SUCESSO`, `SUCESSO_COM_RESSALVAS` ou `FALHA`
- [x] execução manual/CLI
- [x] exemplo de cron
- [x] compensação da Silver parcial em falha crítica
- [ ] integração final `Qualidade -> Gold -> metadados` depende dos artefatos dos Estudantes 2 e 3

## RF23 — Erros e recuperação
- [x] id/origem/regra/data/mensagem/payload
- [x] erro de linha vai à quarentena sem derrubar as demais linhas
- [x] correção e reprocessamento por procedure
- [x] simulação de arquivo inexistente
- [x] simulação de regra inválida
- [x] simulação de conexão indisponível

## Validação feita neste pacote
- [x] todos os `.hpl` e `.hwf` são XML bem-formados
- [x] scripts `.sh` passaram em `bash -n`
- [ ] execução real no Apache Hop local
- [ ] execução real contra o PostgreSQL/Docker local

Os dois itens finais precisam ser executados na máquina da equipe porque dependem das versões/serviços instalados.
