# Entrega do Estudante 1 — RF20, RF21, RF22 e RF23

## Arquitetura

```text
catalogo.csv -----------\
interacoes.json ----------> Apache Hop -> Bronze -> padronização/validação -> Silver
comentarios.json --------/                                    |
                                                               +--> Quarentena
```

A Bronze é auditável e preserva os dados recebidos. A Silver converte tipos, padroniza valores, identifica duplicidades e verifica referências. Registros reprovados ficam disponíveis para correção e reprocessamento.

## RF20 — Bronze

Pipelines:
- `hop/pipelines/bronze_catalogo.hpl`
- `hop/pipelines/bronze_interacoes.hpl`
- `hop/pipelines/bronze_comentarios.hpl`

Destino:
- `bronze.catalogo_raw`
- `bronze.interacoes_raw`
- `bronze.comentarios_raw`

Auditoria: `origem`, `data_hora_ingestao`, `id_execucao`.

A conexão `PostgreSQL` é metadata reutilizável. Credenciais são resolvidas por variáveis de ambiente e não ficam nos `.hpl`.

## RF21 — Silver

Pipelines:
- `hop/pipelines/silver_catalogo.hpl`
- `hop/pipelines/silver_interacoes.hpl`
- `hop/pipelines/silver_comentarios.hpl`

Regras principais:
- trim e redução de espaços;
- tipos: Curso, Vídeo, Artigo e Podcast;
- níveis: Básico, Intermediário e Avançado;
- datas convertidas com segurança;
- IDs positivos;
- `tempo_consumido_min >= 0`;
- `percentual_conclusao` entre 0 e 100;
- avaliação entre 1 e 5;
- tags em minúsculas e sem repetição quando o valor é JSON válido;
- duplicidade de catálogo por `conteudo_id`;
- duplicidade de interação por `(usuario_id, conteudo_id, tipo_interacao, data_hora)`;
- duplicidade de comentário por `(usuario_id, conteudo_id, data, comentario)`;
- usuário existente na base válida do Desafio 1;
- conteúdo existente na Silver ou no acervo válido do Desafio 1.

Padronização de nomes nas interações:
`tempo_consumido -> tempo_consumido_min` e `avaliacao_atribuida -> avaliacao`.

## RF22 — Workflow

`hop/workflows/carga_aluno1.hwf` executa:

```text
setup -> preparação idempotente -> preflight Desafio 1
-> Bronze catálogo -> Bronze interações -> Bronze comentários
-> Silver catálogo -> Silver interações -> Silver comentários
-> estado final
```

As tabelas `controle.execucao_workflow` e `controle.execucao_etapa` registram início, fim, duração, resultado e detalhes.

Estados: `SUCESSO`, `SUCESSO_COM_RESSALVAS` e `FALHA`.

Em falha crítica, a Silver parcial do mesmo `RUN_ID` é removida como compensação, a Bronze é preservada e o workflow termina em `Abort`.

Execução manual: `bash hop/run-aluno1.sh`.

Agendamento às 03:00, exemplo:

```cron
0 3 * * * cd /CAMINHO/desafio-04-Fundamentos-de-Dados-para-IA && HOP_HOME=/CAMINHO/apache-hop bash hop/run-aluno1.sh >> logs/cron_aluno1.log 2>&1
```

O workflow final da equipe acrescentará depois: `Qualidade -> Gold -> publicação de metadados`.

## RF23 — Quarentena e recuperação

`quarentena.registros` mantém entidade, identificador, origem, regra violada, mensagem, data, `id_execucao`, payload e dados de reprocessamento.

Erros de regra não encerram a carga das demais linhas. Falhas críticas de arquivo ou conexão encerram o workflow.

Simulações:
- `hop/testes/falha_arquivo.sh`
- `hop/testes/falha_conexao.sh`
- `hop/testes/falha_regra.sql`

A procedure `controle.reenfileirar_quarentena(...)` reinsere o payload corrigido na Bronze com novo `RUN_ID`, preservando a evidência original.

## Evidências para a apresentação

Use `sql/aluno1_evidencias.sql` e capture:
1. workflow em sucesso ou sucesso com ressalvas;
2. contagens Bronze;
3. contagens Silver;
4. uma linha de quarentena;
5. falha de arquivo;
6. falha de conexão;
7. falha de regra;
8. reprocessamento.
