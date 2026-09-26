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
| **Duração do Processamento** | `0.4019 segundos` |
| **Arquivo Parquet de Saída** | `C:\Users\branco\Documents\GitHub\desafio-04-Fundamentos-de-Dados-para-IA\dados\parquet\gold\kpis_mensais_categoria.parquet` |
| **Tamanho do Arquivo Gerado** | `11597 bytes` |

### Amostra dos Registros Gerados (Gold)
```json
[
  {
    "ano": 2026,
    "mes": 3,
    "categoria": "Devops & Cloud",
    "total_interacoes": 20,
    "usuarios_ativos": 19,
    "total_visualizacoes": 5,
    "total_inicios": 5,
    "total_conclusoes": 4,
    "total_curtidas": 3,
    "taxa_conclusao_pct": 80.0,
    "tempo_total_consumido_min": 1233.0,
    "tempo_medio_min": 61.65,
    "avaliacao_media": NaN,
    "_data_carga_gold": "2026-09-26T17:21:51.078375+00:00",
    "_lote_processamento": "LOTE_DIRECTRUNNER_OFICIAL"
  },
  {
    "ano": 2026,
    "mes": 2,
    "categoria": "Engenharia De Dados",
    "total_interacoes": 18,
    "usuarios_ativos": 17,
    "total_visualizacoes": 7,
    "total_inicios": 3,
    "total_conclusoes": 4,
    "total_curtidas": 2,
    "taxa_conclusao_pct": 133.33,
    "tempo_total_consumido_min": 5056.0,
    "tempo_medio_min": 280.89,
    "avaliacao_media": NaN,
    "_data_carga_gold": "2026-09-26T17:21:51.078375+00:00",
    "_lote_processamento": "LOTE_DIRECTRUNNER_OFICIAL"
  },
  {
    "ano": 2026,
    "mes": 5,
    "categoria": "Engenharia De Dados",
    "total_interacoes": 21,
    "usuarios_ativos": 20,
    "total_visualizacoes": 9,
    "total_inicios": 0,
    "total_conclusoes": 4,
    "total_curtidas": 2,
    "taxa_conclusao_pct": 0.0,
    "tempo_total_consumido_min": 5261.0,
    "tempo_medio_min": 250.52,
    "avaliacao_media": NaN,
    "_data_carga_gold": "2026-09-26T17:21:51.078375+00:00",
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
- **Java detectado:** `True` (`None`)
- **Spark instalado no host:** `False` (`None`)
- **Hadoop winutils presente no Windows:** `False` (`None`)
- **Status do SparkRunner no Host Local:** `ERRO_COMUNICACAO_WORKER`
- **Parecer Técnico:** Job Server alcançado no Docker, mas execução distribuída requer SDK harness remoto: Pipeline BeamApp-root-0926172152-e744d455_ebb47ed4-8454-41cf-957b-0997f7a996a3 failed in state FAILED: org.apache.spark.SparkException: Job aborted due to stage failure: Task 3 in stage 0.0 failed 1 times, most recent failure: Lost task 3.0 in stage 0.0 (TID 3, localhost, executor driver): org.apache.beam.vendor.guava.v26_0_jre.com.google.common.util.concurrent.UncheckedExecutionException: org.apache.beam.vendor.grpc.v1p48p1.io.grpc.StatusRuntimeException: UNAVAILABLE: io exception
	at org.apache.beam.vendor.guava.v26_0_jre.com.google.common.cache.LocalCache$Segment.get(LocalCache.java:2050)
	at org.apache.beam.vendor.guava.v26_0_jre.com.google.common.cache.LocalCache.get(LocalCache.java:3952)
	at org.apache.beam.vendor.guava.v26_0_jre.com.google.common.cache.LocalCache.getOrLoad(LocalCache.java:3974)
	at org.apache.beam.vendor.guava.v26_0_jre.com.google.common.cache.LocalCache$LocalLoadingCache.get(LocalCache.java:4958)
	at org.apache.beam.vendor.guava.v26_0_jre.com.google.common.cache.LocalCache$LocalLoadingCache.getUnchecked(LocalCache.java:4964)
	at org.apache.beam.runners.fnexecution.control.DefaultJobBundleFactory$SimpleStageBundleFactory.<init>(DefaultJobBundleFactory.java:451)
	at org.apache.beam.runners.fnexecution.control.DefaultJobBundleFactory$SimpleStageBundleFactory.<init>(DefaultJobBundleFactory.java:436)
	at org.apache.beam.runners.fnexecution.control.DefaultJobBundleFactory.forStage(DefaultJobBundleFactory.java:303)
	at org.apache.beam.runners.fnexecution.control.DefaultExecutableStageContext.getStageBundleFactory(DefaultExecutableStageContext.java:38)
	at org.apache.beam.runners.fnexecution.control.ReferenceCountingExecutableStageContextFactory$WrappedContext.getStageBundleFactory(ReferenceCountingExecutableStageContextFactory.java:207)
	at org.apache.beam.runners.spark.translation.SparkExecutableStageFunction.call(SparkExecutableStageFunction.java:142)
	at org.apache.beam.runners.spark.translation.SparkExecutableStageFunction.call(SparkExecutableStageFunction.java:81)
	at org.apache.spark.api.java.JavaRDDLike$$anonfun$fn$4$1.apply(JavaRDDLike.scala:153)
	at org.apache.spark.api.java.JavaRDDLike$$anonfun$fn$4$1.apply(JavaRDDLike.scala:153)
	at org.apache.spark.rdd.RDD$$anonfun$mapPartitions$1$$anonfun$apply$23.apply(RDD.scala:823)
	at org.apache.spark.rdd.RDD$$anonfun$mapPartitions$1$$anonfun$apply$23.apply(RDD.scala:823)
	at org.apache.spark.rdd.MapPartitionsRDD.compute(MapPartitionsRDD.scala:52)
	at org.apache.spark.rdd.RDD.computeOrReadCheckpoint(RDD.scala:346)
	at org.apache.spark.rdd.RDD.iterator(RDD.scala:310)
	at org.apache.spark.rdd.MapPartitionsRDD.compute(MapPartitionsRDD.scala:52)
	at org.apache.spark.rdd.RDD.computeOrReadCheckpoint(RDD.scala:346)
	at org.apache.spark.rdd.RDD$$anonfun$7.apply(RDD.scala:359)
	at org.apache.spark.rdd.RDD$$anonfun$7.apply(RDD.scala:357)
	at org.apache.spark.storage.BlockManager$$anonfun$doPutIterator$1.apply(BlockManager.scala:1165)
	at org.apache.spark.storage.BlockManager$$anonfun$doPutIterator$1.apply(BlockManager.scala:1156)
	at org.apache.spark.storage.BlockManager.doPut(BlockManager.scala:1091)
	at org.apache.spark.storage.BlockManager.doPutIterator(BlockManager.scala:1156)
	at org.apache.spark.storage.BlockManager.getOrElseUpdate(BlockManager.scala:882)
	at org.apache.spark.rdd.RDD.getOrCompute(RDD.scala:357)
	at org.apache.spark.rdd.RDD.iterator(RDD.scala:308)
	at org.apache.spark.rdd.MapPartitionsRDD.compute(MapPartitionsRDD.scala:52)
	at org.apache.spark.rdd.RDD.computeOrReadCheckpoint(RDD.scala:346)
	at org.apache.spark.rdd.RDD.iterator(RDD.scala:310)
	at org.apache.spark.rdd.MapPartitionsRDD.compute(MapPartitionsRDD.scala:52)
	at org.apache.spark.rdd.RDD.computeOrReadCheckpoint(RDD.scala:346)
	at org.apache.spark.rdd.RDD$$anonfun$7.apply(RDD.scala:359)
	at org.apache.spark.rdd.RDD$$anonfun$7.apply(RDD.scala:357)
	at org.apache.spark.storage.BlockManager$$anonfun$doPutIterator$1.apply(BlockManager.scala:1165)
	at org.apache.spark.storage.BlockManager$$anonfun$doPutIterator$1.apply(BlockManager.scala:1156)
	at org.apache.spark.storage.BlockManager.doPut(BlockManager.scala:1091)
	at org.apache.spark.storage.BlockManager.doPutIterator(BlockManager.scala:1156)
	at org.apache.spark.storage.BlockManager.getOrElseUpdate(BlockManager.scala:882)
	at org.apache.spark.rdd.RDD.getOrCompute(RDD.scala:357)
	at org.apache.spark.rdd.RDD.iterator(RDD.scala:308)
	at org.apache.spark.rdd.MapPartitionsRDD.compute(MapPartitionsRDD.scala:52)
	at org.apache.spark.rdd.RDD.computeOrReadCheckpoint(RDD.scala:346)
	at org.apache.spark.rdd.RDD.iterator(RDD.scala:310)
	at org.apache.spark.scheduler.ResultTask.runTask(ResultTask.scala:90)
	at org.apache.spark.scheduler.Task.run(Task.scala:123)
	at org.apache.spark.executor.Executor$TaskRunner$$anonfun$10.apply(Executor.scala:411)
	at org.apache.spark.util.Utils$.tryWithSafeFinally(Utils.scala:1360)
	at org.apache.spark.executor.Executor$TaskRunner.run(Executor.scala:417)
	at java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1149)
	at java.util.concurrent.ThreadPoolExecutor$Worker.run(ThreadPoolExecutor.java:624)
	at java.lang.Thread.run(Thread.java:750)
Caused by: org.apache.beam.vendor.grpc.v1p48p1.io.grpc.StatusRuntimeException: UNAVAILABLE: io exception
	at org.apache.beam.vendor.grpc.v1p48p1.io.grpc.stub.ClientCalls.toStatusRuntimeException(ClientCalls.java:271)
	at org.apache.beam.vendor.grpc.v1p48p1.io.grpc.stub.ClientCalls.getUnchecked(ClientCalls.java:252)
	at org.apache.beam.vendor.grpc.v1p48p1.io.grpc.stub.ClientCalls.blockingUnaryCall(ClientCalls.java:165)
	at org.apache.beam.model.fnexecution.v1.BeamFnExternalWorkerPoolGrpc$BeamFnExternalWorkerPoolBlockingStub.startWorker(BeamFnExternalWorkerPoolGrpc.java:225)
	at org.apache.beam.runners.fnexecution.environment.ExternalEnvironmentFactory.createEnvironment(ExternalEnvironmentFactory.java:113)
	at org.apache.beam.runners.fnexecution.control.DefaultJobBundleFactory$1.load(DefaultJobBundleFactory.java:252)
	at org.apache.beam.runners.fnexecution.control.DefaultJobBundleFactory$1.load(DefaultJobBundleFactory.java:231)
	at org.apache.beam.vendor.guava.v26_0_jre.com.google.common.cache.LocalCache$LoadingValueReference.loadFuture(LocalCache.java:3528)
	at org.apache.beam.vendor.guava.v26_0_jre.com.google.common.cache.LocalCache$Segment.loadSync(LocalCache.java:2277)
	at org.apache.beam.vendor.guava.v26_0_jre.com.google.common.cache.LocalCache$Segment.lockedGetOrLoad(LocalCache.java:2154)
	at org.apache.beam.vendor.guava.v26_0_jre.com.google.common.cache.LocalCache$Segment.get(LocalCache.java:2044)
	... 54 more
Caused by: org.apache.beam.vendor.grpc.v1p48p1.io.netty.channel.AbstractChannel$AnnotatedConnectException: finishConnect(..) failed: Connection refused: localhost/0:0:0:0:0:0:0:1:59013
Caused by: java.net.ConnectException: finishConnect(..) failed: Connection refused
	at org.apache.beam.vendor.grpc.v1p48p1.io.netty.channel.unix.Errors.newConnectException0(Errors.java:155)
	at org.apache.beam.vendor.grpc.v1p48p1.io.netty.channel.unix.Errors.handleConnectErrno(Errors.java:128)
	at org.apache.beam.vendor.grpc.v1p48p1.io.netty.channel.unix.Socket.finishConnect(Socket.java:321)
	at org.apache.beam.vendor.grpc.v1p48p1.io.netty.channel.epoll.AbstractEpollChannel$AbstractEpollUnsafe.doFinishConnect(AbstractEpollChannel.java:710)
	at org.apache.beam.vendor.grpc.v1p48p1.io.netty.channel.epoll.AbstractEpollChannel$AbstractEpollUnsafe.finishConnect(AbstractEpollChannel.java:687)
	at org.apache.beam.vendor.grpc.v1p48p1.io.netty.channel.epoll.AbstractEpollChannel$AbstractEpollUnsafe.epollOutReady(AbstractEpollChannel.java:567)
	at org.apache.beam.vendor.grpc.v1p48p1.io.netty.channel.epoll.EpollEventLoop.processReady(EpollEventLoop.java:477)
	at org.apache.beam.vendor.grpc.v1p48p1.io.netty.channel.epoll.EpollEventLoop.run(EpollEventLoop.java:385)
	at org.apache.beam.vendor.grpc.v1p48p1.io.netty.util.concurrent.SingleThreadEventExecutor$4.run(SingleThreadEventExecutor.java:995)
	at org.apache.beam.vendor.grpc.v1p48p1.io.netty.util.internal.ThreadExecutorMap$2.run(ThreadExecutorMap.java:74)
	at org.apache.beam.vendor.grpc.v1p48p1.io.netty.util.concurrent.FastThreadLocalRunnable.run(FastThreadLocalRunnable.java:30)
	at java.lang.Thread.run(Thread.java:750)

Driver stacktrace:

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
