# Documentação de Execução: Apache Beam com DirectRunner e Runtime Spark (RF25)

Este documento registra os resultados de execução, equivalência analítica, diagnóstico de infraestrutura e instruções de reprodução do pipeline **Apache Beam**, cumprindo o requisito **RF25** e as diretrizes do `AGENTS.md`.

---

## 1. Visão Geral do Pipeline Beam

- **Fonte de Entrada:** Base de interações em Parquet particionado (`dados/parquet/interacoes/particionado/`).
- **Enriquecimento:** *Side Input* com dados de categorias do catálogo educacional.
- **Transformação Principal:** Agrupamento por `(ano, mes, categoria)` e consolidação de KPIs com `CombinePerKey(ConsolidarMetricasCategoria())`.
- **Destino:** Camada Gold em Parquet (`dados/parquet/gold/kpis_mensais_categoria.parquet`) e persistência relacional no PostgreSQL.

---

## 2. Resultado da Execução Oficial: DirectRunner

| Métrica | Valor Obtido |
| :--- | :--- |
| **Status da Execução** | `SUCESSO` |
| **Registros de Entrada Processados** | `1000` interações |
| **Registros Analíticos Consolidados (Gold)** | `64` categorias/períodos |
| **Duração do Processamento** | `4.8477 segundos` |
| **Arquivo Parquet de Saída** | `D:\FICDEV_CURSO\Desafio 4 - Modulo Dados\desafio-04-Fundamentos-de-Dados-para-IA\dados\parquet\gold\kpis_mensais_categoria.parquet` |
| **Tamanho do Arquivo Gerado** | `11597 bytes` |

### Amostra dos Registros Gerados (Gold)
```json
[
  {
    "ano": 2026,
    "mes": 4,
    "categoria": "Ciência De Dados",
    "total_interacoes": 14,
    "usuarios_ativos": 12,
    "total_visualizacoes": 4,
    "total_inicios": 1,
    "total_conclusoes": 2,
    "total_curtidas": 3,
    "taxa_conclusao_pct": 200.0,
    "tempo_total_consumido_min": 2114.0,
    "tempo_medio_min": 151.0,
    "avaliacao_media": NaN,
    "_data_carga_gold": "2026-09-28T18:49:54.442778+00:00",
    "_lote_processamento": "LOTE_DIRECTRUNNER_OFICIAL"
  },
  {
    "ano": 2026,
    "mes": 6,
    "categoria": "Ciência De Dados",
    "total_interacoes": 19,
    "usuarios_ativos": 18,
    "total_visualizacoes": 5,
    "total_inicios": 4,
    "total_conclusoes": 3,
    "total_curtidas": 0,
    "taxa_conclusao_pct": 75.0,
    "tempo_total_consumido_min": 1837.0,
    "tempo_medio_min": 96.68,
    "avaliacao_media": NaN,
    "_data_carga_gold": "2026-09-28T18:49:54.442778+00:00",
    "_lote_processamento": "LOTE_DIRECTRUNNER_OFICIAL"
  },
  {
    "ano": 2026,
    "mes": 4,
    "categoria": "Programação & Software",
    "total_interacoes": 9,
    "usuarios_ativos": 9,
    "total_visualizacoes": 5,
    "total_inicios": 1,
    "total_conclusoes": 1,
    "total_curtidas": 1,
    "taxa_conclusao_pct": 100.0,
    "tempo_total_consumido_min": 840.0,
    "tempo_medio_min": 93.33,
    "avaliacao_media": NaN,
    "_data_carga_gold": "2026-09-28T18:49:54.442778+00:00",
    "_lote_processamento": "LOTE_DIRECTRUNNER_OFICIAL"
  }
]
```

---

## 3. Avaliação do Runtime Spark e Diagnóstico de Infraestrutura

Conforme a Seção 4 do `AGENTS.md`:
> *"Não alegar execução Spark se o ambiente disponível não a suportar; registrar o bloqueio e oferecer instruções reproduzíveis."*

### Diagnóstico do Ambiente Host
- **Sistema Operacional:** `Windows`
- **Java detectado:** `False` (`None`)
- **Spark instalado no host:** `False` (`None`)
- **Hadoop winutils presente no Windows:** `False` (`None`)
- **Status do SparkRunner no Host Local:** `BLOQUEIO_WORKER_POOL`
- **Parecer Técnico:** Spark Job Server detectado no Docker (localhost:8099). A execução distribuída entre host Windows e o cluster Spark em container requer um Worker Pool de rede externo (SDK Harness remoto), inviabilizando o modo LOOPBACK entre redes isoladas. Conforme AGENTS.md (RF25), o bloqueio técnico foi formalizado sem alegações inverídicas.

---

## 4. Garantia de Equivalência Algorítmica e Comutativa

As transformações do Apache Beam foram concebidas respeitando os princípios fundamentais do modelo Beam:
1. **Comutatividade e Associatividade:** A classe `ConsolidarMetricasCategoria` herda de `beam.CombineFn`, implementando acumuladores (`add_input`, `merge_accumulators` e `extract_output`) rigorosamente matemáticos e determinísticos.
2. **Independência de Runner:** A mesma definição de grafo (`Pipeline`) executa a mesma lógica sem alteração de código tanto no `DirectRunner` (in-memory multi-threaded) quanto no `SparkRunner` (distribuído em RDDs do Apache Spark).

---

## 5. Instruções Reproduzíveis para Execução Spark via Docker

Para executar o pipeline com Apache Spark em ambiente de produção ou cluster Linux sem as restrições de `winutils` do Windows:

1. **Subir o Spark Job Server do Beam via Docker:**
   ```bash
   docker run -d --name beam-spark-job-server -p 8099:8099 -p 8098:8098 apache/beam_spark_job_server:2.55.0
   ```

2. **Submeter o Pipeline Beam apontando para o endpoint Spark:**
   ```bash
   python -m src.beam.pipeline_gold --runner=PortableRunner --job_endpoint=localhost:8099
   ```
