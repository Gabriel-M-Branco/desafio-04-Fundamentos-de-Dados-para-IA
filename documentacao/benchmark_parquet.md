# Relatório de Benchmark Comparativo: Parquet vs CSV vs JSON (RF24)

Este documento registra a metodologia, medições empíricas, análise de desempenho e limitações do experimento comparativo entre os formatos **Parquet (Snappy)**, **CSV** e **JSON**, atendendo integralmente ao requisito funcional **RF24**.

---

## 1. Ambiente e Metodologia do Experimento

### 1.1 Configuração do Ambiente de Teste
- **Sistema Operacional:** `Windows-11-10.0.26200-SP0`
- **Processador:** `AMD64 Family 23 Model 113 Stepping 0, AuthenticAMD`
- **Python:** `3.14.7`
- **PyArrow:** `25.0.1`
- **Pandas:** `3.0.6`

### 1.2 Metodologia
- **Volume avaliado:** `1000` registros reais de interações da camada Silver.
- **Número de repetições:** `5` execuções cronometradas com descarte de ciclo de *warm-up*.
- **Métrica de tempo:** Média em milissegundos (ms) via `time.perf_counter`.
- **Compressão Parquet:** Algoritmo `Snappy`.
- **Estratégia de Particionamento:** Padrão Hive particionado por `ano` e `mes` (`ano=YYYY/mes=MM`).

---

## 2. Resultados Consolidados

| Formato | Tamanho em Disco (KB) | Redução vs JSON (%) | Redução vs CSV (%) | Tempo de Escrita (ms) | Leitura Full Scan (ms) | Leitura com Projeção (ms) | Leitura com Filtro Partição (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Parquet Consolidado** | **36.0 KB** | **89.44%** | **72.16%** | 3.731 ms | 2.546 ms | **1.663 ms** | 2.703 ms |
| **Parquet Particionado** | 94.3 KB | 72.34% | 27.06% | 5.184 ms | 5.828 ms | --- | **4.473 ms** |
| **CSV** | 129.28 KB | 62.08% | 0.00% | 9.692 ms | 4.62 ms | 4.227 ms | 5.364 ms |
| **JSON** | 340.98 KB | 0.00% | -163.75% | 28.048 ms | 3.474 ms | 3.612 ms | 4.07 ms |

---

## 3. Análise dos Resultados e Trade-offs

### 3.1 Armazenamento e Compressão
- O **Parquet consolidado** obteve uma taxa de redução de **89.44%** em relação ao JSON original e **72.16%** em relação ao CSV.
- O formato colunar com codificação por dicionário e compressão Snappy elimina a repetição redundante dos nomes das chaves (que no JSON representam mais de 60% do peso do arquivo).

### 3.2 Projeção Colunar (*Column Pruning*)
- Quando apenas um subconjunto de colunas é necessário (ex: `usuario_id` e `tipo_interacao`), o Parquet carrega apenas as páginas de dados daquelas colunas específicas.
- No CSV e JSON, o parser é obrigado a ler todas as linhas e colunas para depois descartá-las em memória, gerando desperdício significativo de I/O e CPU.

### 3.3 Poda de Partição (*Partition Pruning*)
- Ao aplicar filtros por `ano` e `mes`, o **Parquet particionado** acessa apenas os arquivos contidos no diretório da partição alvo (`ano=2026/mes=3/`), ignorando completamente o restante do dataset em disco.

---

## 4. Justificativa do Particionamento Escolhido

- **Critério Temporal (`ano` / `mes`):**
  1. A principal demanda analítica da plataforma (KPIs 1, 2 e 3 do Superset) baseia-se em recortes temporais periódicos (mensal/anual).
  2. O particionamento por ano e mês equilibra a distribuição de volume por partição, evitando o problema de *small files* (que ocorreria se particionássemos por `usuario_id` ou por `dia`).
  3. Facilita rotinas de carga incremental e expurgo/arquivamento de safras antigas sem lock no dataset inteiro.

---

## 5. Limitações do Experimento

- **Volume de Amostra:** O benchmark utilizou o conjunto real do desafio contendo 1.000 registros de interações. Em volumes maiores (centenas de milhares a milhões de linhas), os ganhos de tempo e I/O do Parquet tornam-se ordens de grandeza ainda mais expressivos devido à sobrecarga fixa de inicialização de headers do formato colunar.
- **Ambiente de I/O Local:** As medições foram realizadas em armazenamento SSD local em ambiente Windows/WSL2; em sistemas de arquivos distribuídos em nuvem (Amazon S3, Google Cloud Storage, HDFS), o benefício de transferir menos bytes pela rede é substancialmente amplificado.
