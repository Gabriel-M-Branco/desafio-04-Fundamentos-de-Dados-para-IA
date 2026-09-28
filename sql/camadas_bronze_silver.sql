-- Desafio Prático 2 — Camadas Bronze, Silver, Quarentena e Controle (RF20 a RF23)
-- Ingestão, validação, workflow, quarentena e recuperação.
BEGIN;
SET timezone TO 'America/Cuiaba';
DO $$ BEGIN
    PERFORM 1 FROM pg_database WHERE datname = 'ficdev_analitico';
    IF FOUND THEN
        ALTER DATABASE ficdev_analitico SET timezone TO 'America/Cuiaba';
    END IF;
END $$;

CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS quarentena;
CREATE SCHEMA IF NOT EXISTS controle;

-- Estruturas mínimas de referência do Desafio 1. IF NOT EXISTS não altera tabelas já existentes.
CREATE TABLE IF NOT EXISTS public.usuarios (usuario_id BIGINT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS public.conteudos (conteudo_id BIGINT PRIMARY KEY);

CREATE TABLE IF NOT EXISTS bronze.catalogo_raw (
  bronze_id BIGSERIAL PRIMARY KEY,
  conteudo_id TEXT, titulo TEXT, tipo TEXT, categoria TEXT, nivel TEXT,
  carga_horaria_min TEXT, data_publicacao TEXT, descricao TEXT, autor TEXT,
  origem TEXT NOT NULL, data_hora_ingestao TIMESTAMP NOT NULL, id_execucao TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS bronze.interacoes_raw (
  bronze_id BIGSERIAL PRIMARY KEY,
  usuario_id TEXT, conteudo_id TEXT, tipo_interacao TEXT, data_hora TEXT,
  tempo_consumido TEXT, percentual_conclusao TEXT, avaliacao_atribuida TEXT,
  origem TEXT NOT NULL, data_hora_ingestao TIMESTAMP NOT NULL, id_execucao TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS bronze.comentarios_raw (
  bronze_id BIGSERIAL PRIMARY KEY,
  usuario_id TEXT, conteudo_id TEXT, avaliacao TEXT, comentario TEXT, tags TEXT, data TEXT,
  origem TEXT NOT NULL, data_hora_ingestao TIMESTAMP NOT NULL, id_execucao TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_bronze_catalogo_run ON bronze.catalogo_raw(id_execucao);
CREATE INDEX IF NOT EXISTS idx_bronze_interacoes_run ON bronze.interacoes_raw(id_execucao);
CREATE INDEX IF NOT EXISTS idx_bronze_comentarios_run ON bronze.comentarios_raw(id_execucao);

CREATE TABLE IF NOT EXISTS silver.catalogo (
  id_execucao TEXT NOT NULL,
  conteudo_id BIGINT NOT NULL, titulo TEXT NOT NULL, tipo VARCHAR(30) NOT NULL,
  categoria TEXT NOT NULL, nivel VARCHAR(30) NOT NULL, carga_horaria_min INTEGER NOT NULL,
  data_publicacao DATE NOT NULL, descricao TEXT NOT NULL, autor TEXT NOT NULL,
  origem TEXT NOT NULL, data_hora_ingestao TIMESTAMP NOT NULL,
  PRIMARY KEY (id_execucao, conteudo_id)
);
CREATE TABLE IF NOT EXISTS silver.interacoes (
  id_execucao TEXT NOT NULL,
  interacao_id BIGINT NOT NULL, usuario_id BIGINT NOT NULL, conteudo_id BIGINT NOT NULL,
  tipo_interacao VARCHAR(30) NOT NULL, data_hora TIMESTAMP NOT NULL,
  tempo_consumido_min NUMERIC(12,2) NOT NULL, percentual_conclusao NUMERIC(5,2) NOT NULL,
  avaliacao NUMERIC(3,1), origem TEXT NOT NULL, data_hora_ingestao TIMESTAMP NOT NULL,
  PRIMARY KEY (id_execucao, interacao_id),
  UNIQUE (id_execucao, usuario_id, conteudo_id, tipo_interacao, data_hora)
);
CREATE TABLE IF NOT EXISTS silver.comentarios (
  id_execucao TEXT NOT NULL,
  comentario_id BIGINT NOT NULL, usuario_id BIGINT NOT NULL, conteudo_id BIGINT NOT NULL,
  avaliacao NUMERIC(3,1) NOT NULL, comentario TEXT NOT NULL, tags TEXT, data DATE NOT NULL,
  origem TEXT NOT NULL, data_hora_ingestao TIMESTAMP NOT NULL,
  PRIMARY KEY (id_execucao, comentario_id),
  UNIQUE (id_execucao, usuario_id, conteudo_id, data, comentario)
);

CREATE TABLE IF NOT EXISTS quarentena.registros (
  quarentena_id BIGSERIAL PRIMARY KEY,
  entidade TEXT NOT NULL, id_registro TEXT, origem TEXT NOT NULL,
  regra_violada TEXT NOT NULL, mensagem_erro TEXT NOT NULL,
  data_erro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  id_execucao TEXT NOT NULL, payload TEXT NOT NULL,
  reprocessado BOOLEAN NOT NULL DEFAULT FALSE,
  data_reprocessamento TIMESTAMP, novo_id_execucao TEXT
);
CREATE INDEX IF NOT EXISTS idx_quarentena_run ON quarentena.registros(id_execucao);
CREATE INDEX IF NOT EXISTS idx_quarentena_pendente ON quarentena.registros(reprocessado, entidade);

CREATE TABLE IF NOT EXISTS controle.execucao_workflow (
  id_execucao TEXT PRIMARY KEY,
  inicio TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  fim TIMESTAMP, duracao_segundos NUMERIC(14,3),
  resultado TEXT NOT NULL, detalhes TEXT
);
CREATE TABLE IF NOT EXISTS controle.execucao_etapa (
  etapa_id BIGSERIAL PRIMARY KEY,
  id_execucao TEXT NOT NULL, etapa TEXT NOT NULL,
  inicio TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  fim TIMESTAMP, duracao_segundos NUMERIC(14,3),
  resultado TEXT NOT NULL, detalhes TEXT,
  UNIQUE (id_execucao, etapa)
);

CREATE OR REPLACE FUNCTION controle.norm_texto(p TEXT)
RETURNS TEXT LANGUAGE sql IMMUTABLE AS $$
  SELECT NULLIF(regexp_replace(trim(COALESCE(p,'')), '[[:space:]]+', ' ', 'g'), '');
$$;

CREATE OR REPLACE FUNCTION controle.try_bigint(p TEXT)
RETURNS BIGINT LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
  IF p IS NULL OR trim(p) = '' THEN RETURN NULL; END IF;
  RETURN trim(p)::BIGINT;
EXCEPTION WHEN OTHERS THEN RETURN NULL;
END; $$;

CREATE OR REPLACE FUNCTION controle.try_numeric(p TEXT)
RETURNS NUMERIC LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
  IF p IS NULL OR trim(p) = '' THEN RETURN NULL; END IF;
  RETURN replace(trim(p), ',', '.')::NUMERIC;
EXCEPTION WHEN OTHERS THEN RETURN NULL;
END; $$;

CREATE OR REPLACE FUNCTION controle.try_date(p TEXT)
RETURNS DATE LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE t TEXT; d DATE;
BEGIN
  t := trim(COALESCE(p,''));
  IF t = '' THEN RETURN NULL; END IF;
  IF t ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN RETURN t::DATE;
  ELSIF t ~ '^[0-9]{2}/[0-9]{2}/[0-9]{4}$' THEN
    d := to_date(t,'DD/MM/YYYY'); IF to_char(d,'DD/MM/YYYY')=t THEN RETURN d; END IF;
  ELSIF t ~ '^[0-9]{4}/[0-9]{2}/[0-9]{2}$' THEN
    d := to_date(t,'YYYY/MM/DD'); IF to_char(d,'YYYY/MM/DD')=t THEN RETURN d; END IF;
  ELSIF t ~ '^[0-9]{2}-[0-9]{2}-[0-9]{4}$' THEN
    d := to_date(t,'DD-MM-YYYY'); IF to_char(d,'DD-MM-YYYY')=t THEN RETURN d; END IF;
  END IF;
  RETURN NULL;
EXCEPTION WHEN OTHERS THEN RETURN NULL;
END; $$;

CREATE OR REPLACE FUNCTION controle.try_timestamp(p TEXT)
RETURNS TIMESTAMP LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE t TEXT;
BEGIN
  t := trim(COALESCE(p,''));
  IF t = '' THEN RETURN NULL; END IF;
  IF t ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN
    RETURN replace(t,'T',' ')::TIMESTAMP;
  ELSIF t ~ '^[0-9]{2}/[0-9]{2}/[0-9]{4} [0-9]{2}:[0-9]{2}$' THEN
    RETURN to_timestamp(t,'DD/MM/YYYY HH24:MI')::TIMESTAMP;
  ELSIF t ~ '^[0-9]{2}/[0-9]{2}/[0-9]{4} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN
    RETURN to_timestamp(t,'DD/MM/YYYY HH24:MI:SS')::TIMESTAMP;
  END IF;
  RETURN NULL;
EXCEPTION WHEN OTHERS THEN RETURN NULL;
END; $$;

CREATE OR REPLACE FUNCTION controle.norm_tipo(p TEXT)
RETURNS TEXT LANGUAGE sql IMMUTABLE AS $$
 SELECT CASE lower(controle.norm_texto(p))
  WHEN 'curso' THEN 'Curso' WHEN 'vídeo' THEN 'Vídeo' WHEN 'video' THEN 'Vídeo'
  WHEN 'artigo' THEN 'Artigo' WHEN 'podcast' THEN 'Podcast'
  ELSE controle.norm_texto(p) END;
$$;
CREATE OR REPLACE FUNCTION controle.norm_nivel(p TEXT)
RETURNS TEXT LANGUAGE sql IMMUTABLE AS $$
 SELECT CASE lower(controle.norm_texto(p))
  WHEN 'básico' THEN 'Básico' WHEN 'basico' THEN 'Básico'
  WHEN 'intermediário' THEN 'Intermediário' WHEN 'intermediario' THEN 'Intermediário'
  WHEN 'avançado' THEN 'Avançado' WHEN 'avancado' THEN 'Avançado'
  ELSE controle.norm_texto(p) END;
$$;
CREATE OR REPLACE FUNCTION controle.norm_interacao(p TEXT)
RETURNS TEXT LANGUAGE sql IMMUTABLE AS $$
 SELECT CASE lower(controle.norm_texto(p))
  WHEN 'visualização' THEN 'visualização' WHEN 'visualizacao' THEN 'visualização'
  WHEN 'início' THEN 'início' WHEN 'inicio' THEN 'início'
  WHEN 'conclusão' THEN 'conclusão' WHEN 'conclusao' THEN 'conclusão'
  WHEN 'curtida' THEN 'curtida'
  WHEN 'avaliação' THEN 'avaliação' WHEN 'avaliacao' THEN 'avaliação'
  WHEN 'compartilhamento' THEN 'compartilhamento'
  ELSE controle.norm_texto(p) END;
$$;
CREATE OR REPLACE FUNCTION controle.norm_tags(p TEXT)
RETURNS TEXT LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE j JSONB; r TEXT;
BEGIN
  IF p IS NULL OR trim(p)='' THEN RETURN '[]'; END IF;
  j := p::JSONB;
  IF jsonb_typeof(j) <> 'array' THEN RETURN p; END IF;
  SELECT COALESCE(jsonb_agg(v ORDER BY v)::TEXT,'[]') INTO r
  FROM (SELECT DISTINCT lower(trim(value)) v FROM jsonb_array_elements_text(j) WHERE trim(value)<>'') t;
  RETURN r;
EXCEPTION WHEN OTHERS THEN RETURN p;
END; $$;

CREATE OR REPLACE VIEW controle.v_catalogo_classificado AS
WITH n AS (
  SELECT b.*,
    controle.try_bigint(b.conteudo_id) conteudo_id_n,
    controle.norm_texto(b.titulo) titulo_n,
    controle.norm_tipo(b.tipo) tipo_n,
    initcap(controle.norm_texto(b.categoria)) categoria_n,
    controle.norm_nivel(b.nivel) nivel_n,
    controle.try_bigint(b.carga_horaria_min) carga_n,
    controle.try_date(b.data_publicacao) data_n,
    controle.norm_texto(b.descricao) descricao_n,
    controle.norm_texto(b.autor) autor_n
  FROM bronze.catalogo_raw b
), r AS (
  SELECT n.*, row_number() OVER(PARTITION BY id_execucao,conteudo_id_n ORDER BY bronze_id) rn FROM n
)
SELECT bronze_id,conteudo_id_n conteudo_id,titulo_n titulo,tipo_n tipo,categoria_n categoria,
  nivel_n nivel,carga_n::INTEGER carga_horaria_min,data_n data_publicacao,
  descricao_n descricao,autor_n autor,origem,data_hora_ingestao,id_execucao,
  COALESCE(conteudo_id,bronze_id::TEXT) id_registro,
  CASE
    WHEN controle.norm_texto(conteudo_id) IS NULL OR titulo_n IS NULL OR controle.norm_texto(tipo) IS NULL
      OR categoria_n IS NULL OR controle.norm_texto(nivel) IS NULL
      OR controle.norm_texto(carga_horaria_min) IS NULL OR controle.norm_texto(data_publicacao) IS NULL
      OR descricao_n IS NULL OR autor_n IS NULL THEN 'INCOMPLETO'
    WHEN conteudo_id_n IS NULL OR conteudo_id_n<=0
      OR tipo_n NOT IN ('Curso','Vídeo','Artigo','Podcast')
      OR nivel_n NOT IN ('Básico','Intermediário','Avançado')
      OR carga_n IS NULL OR carga_n<=0 OR data_n IS NULL THEN 'INVALIDO'
    WHEN rn>1 THEN 'DUPLICADO' ELSE 'VALIDO'
  END status_registro,
  concat_ws(' | ',
    CASE WHEN controle.norm_texto(conteudo_id) IS NULL THEN 'campo obrigatório ausente: conteudo_id' END,
    CASE WHEN titulo_n IS NULL THEN 'campo obrigatório ausente: titulo' END,
    CASE WHEN controle.norm_texto(tipo) IS NULL THEN 'campo obrigatório ausente: tipo' END,
    CASE WHEN categoria_n IS NULL THEN 'campo obrigatório ausente: categoria' END,
    CASE WHEN controle.norm_texto(nivel) IS NULL THEN 'campo obrigatório ausente: nivel' END,
    CASE WHEN controle.norm_texto(carga_horaria_min) IS NULL THEN 'campo obrigatório ausente: carga_horaria_min' END,
    CASE WHEN controle.norm_texto(data_publicacao) IS NULL THEN 'campo obrigatório ausente: data_publicacao' END,
    CASE WHEN descricao_n IS NULL THEN 'campo obrigatório ausente: descricao' END,
    CASE WHEN autor_n IS NULL THEN 'campo obrigatório ausente: autor' END,
    CASE WHEN controle.norm_texto(conteudo_id) IS NOT NULL AND (conteudo_id_n IS NULL OR conteudo_id_n<=0) THEN 'conteudo_id inválido' END,
    CASE WHEN controle.norm_texto(tipo) IS NOT NULL AND tipo_n NOT IN ('Curso','Vídeo','Artigo','Podcast') THEN 'tipo fora do domínio permitido' END,
    CASE WHEN controle.norm_texto(nivel) IS NOT NULL AND nivel_n NOT IN ('Básico','Intermediário','Avançado') THEN 'nível fora do domínio permitido' END,
    CASE WHEN controle.norm_texto(carga_horaria_min) IS NOT NULL AND (carga_n IS NULL OR carga_n<=0) THEN 'carga_horaria_min deve ser positiva' END,
    CASE WHEN controle.norm_texto(data_publicacao) IS NOT NULL AND data_n IS NULL THEN 'data_publicacao inválida' END,
    CASE WHEN rn>1 THEN 'conteudo_id repetido' END
  ) regra_violada,
  concat_ws(' | ',
    CASE WHEN rn>1 THEN 'Duplicidade de chave de negócio' END,
    CASE WHEN conteudo_id_n IS NULL AND controle.norm_texto(conteudo_id) IS NOT NULL THEN 'Falha de conversão/validação de identificador' END,
    CASE WHEN data_n IS NULL AND controle.norm_texto(data_publicacao) IS NOT NULL THEN 'Falha de conversão de data' END,
    CASE WHEN tipo_n NOT IN ('Curso','Vídeo','Artigo','Podcast') THEN 'Domínio de tipo inválido' END,
    CASE WHEN nivel_n NOT IN ('Básico','Intermediário','Avançado') THEN 'Domínio de nível inválido' END
  ) mensagem_erro,
  jsonb_build_object('conteudo_id',conteudo_id,'titulo',titulo,'tipo',tipo,'categoria',categoria,
    'nivel',nivel,'carga_horaria_min',carga_horaria_min,'data_publicacao',data_publicacao,
    'descricao',descricao,'autor',autor)::TEXT payload
FROM r;

CREATE OR REPLACE VIEW controle.v_interacoes_classificadas AS
WITH n AS (
  SELECT b.*,
    controle.try_bigint(b.usuario_id) usuario_id_n,
    controle.try_bigint(b.conteudo_id) conteudo_id_n,
    controle.norm_interacao(b.tipo_interacao) tipo_n,
    controle.try_timestamp(b.data_hora) data_n,
    controle.try_numeric(b.tempo_consumido) tempo_n,
    controle.try_numeric(b.percentual_conclusao) percentual_n,
    controle.try_numeric(b.avaliacao_atribuida) avaliacao_n
  FROM bronze.interacoes_raw b
), r AS (
  SELECT n.*,row_number() OVER(
    PARTITION BY id_execucao,usuario_id_n,conteudo_id_n,tipo_n,data_n ORDER BY bronze_id) rn
  FROM n
), c AS (
  SELECT r.*,
    EXISTS(SELECT 1 FROM public.usuarios u WHERE u.usuario_id=r.usuario_id_n) usuario_existe,
    (EXISTS(SELECT 1 FROM silver.catalogo s WHERE s.conteudo_id=r.conteudo_id_n)
      OR EXISTS(SELECT 1 FROM public.conteudos p WHERE p.conteudo_id=r.conteudo_id_n)) conteudo_existe,
    row_number() OVER(PARTITION BY r.id_execucao ORDER BY r.bronze_id) interacao_id_n
  FROM r
)
SELECT bronze_id,interacao_id_n::BIGINT interacao_id,usuario_id_n usuario_id,conteudo_id_n conteudo_id,
  tipo_n tipo_interacao,data_n data_hora,tempo_n tempo_consumido_min,percentual_n percentual_conclusao,
  avaliacao_n avaliacao,origem,data_hora_ingestao,id_execucao,
  COALESCE(usuario_id||':'||conteudo_id||':'||tipo_interacao||':'||data_hora,bronze_id::TEXT) id_registro,
  CASE
    WHEN controle.norm_texto(usuario_id) IS NULL OR controle.norm_texto(conteudo_id) IS NULL
      OR controle.norm_texto(tipo_interacao) IS NULL OR controle.norm_texto(data_hora) IS NULL
      OR controle.norm_texto(tempo_consumido) IS NULL OR controle.norm_texto(percentual_conclusao) IS NULL
      THEN 'INCOMPLETO'
    WHEN usuario_id_n IS NULL OR usuario_id_n<=0 OR conteudo_id_n IS NULL OR conteudo_id_n<=0
      OR NOT usuario_existe OR NOT conteudo_existe
      OR tipo_n NOT IN ('visualização','início','conclusão','curtida','avaliação','compartilhamento')
      OR data_n IS NULL OR tempo_n IS NULL OR tempo_n<0
      OR percentual_n IS NULL OR percentual_n<0 OR percentual_n>100
      OR (avaliacao_n IS NOT NULL AND (avaliacao_n<1 OR avaliacao_n>5)) THEN 'INVALIDO'
    WHEN rn>1 THEN 'DUPLICADO' ELSE 'VALIDO'
  END status_registro,
  concat_ws(' | ',
    CASE WHEN controle.norm_texto(usuario_id) IS NULL THEN 'campo obrigatório ausente: usuario_id' END,
    CASE WHEN controle.norm_texto(conteudo_id) IS NULL THEN 'campo obrigatório ausente: conteudo_id' END,
    CASE WHEN controle.norm_texto(tipo_interacao) IS NULL THEN 'campo obrigatório ausente: tipo_interacao' END,
    CASE WHEN controle.norm_texto(data_hora) IS NULL THEN 'campo obrigatório ausente: data_hora' END,
    CASE WHEN controle.norm_texto(tempo_consumido) IS NULL THEN 'campo obrigatório ausente: tempo_consumido' END,
    CASE WHEN controle.norm_texto(percentual_conclusao) IS NULL THEN 'campo obrigatório ausente: percentual_conclusao' END,
    CASE WHEN usuario_id_n IS NULL OR usuario_id_n<=0 THEN 'usuario_id inválido' END,
    CASE WHEN conteudo_id_n IS NULL OR conteudo_id_n<=0 THEN 'conteudo_id inválido' END,
    CASE WHEN usuario_id_n IS NOT NULL AND usuario_id_n>0 AND NOT usuario_existe THEN 'referência a usuário inexistente' END,
    CASE WHEN conteudo_id_n IS NOT NULL AND conteudo_id_n>0 AND NOT conteudo_existe THEN 'referência a conteúdo inexistente' END,
    CASE WHEN tipo_n NOT IN ('visualização','início','conclusão','curtida','avaliação','compartilhamento') THEN 'tipo_interacao fora do domínio permitido' END,
    CASE WHEN controle.norm_texto(data_hora) IS NOT NULL AND data_n IS NULL THEN 'data_hora inválida' END,
    CASE WHEN controle.norm_texto(tempo_consumido) IS NOT NULL AND (tempo_n IS NULL OR tempo_n<0) THEN 'tempo_consumido_min inválido' END,
    CASE WHEN controle.norm_texto(percentual_conclusao) IS NOT NULL AND (percentual_n IS NULL OR percentual_n<0 OR percentual_n>100) THEN 'percentual_conclusao deve estar entre 0 e 100' END,
    CASE WHEN avaliacao_n IS NOT NULL AND (avaliacao_n<1 OR avaliacao_n>5) THEN 'avaliação deve estar entre 1 e 5' END,
    CASE WHEN rn>1 THEN 'chave composta da interação repetida' END
  ) regra_violada,
  concat_ws(' | ',
    CASE WHEN rn>1 THEN 'Duplicidade de interação' END,
    CASE WHEN NOT conteudo_existe THEN 'Integridade referencial de conteúdo' END,
    CASE WHEN NOT usuario_existe THEN 'Integridade referencial de usuário' END,
    CASE WHEN data_n IS NULL AND controle.norm_texto(data_hora) IS NOT NULL THEN 'Falha de conversão de data/hora' END,
    CASE WHEN tempo_n IS NULL AND controle.norm_texto(tempo_consumido) IS NOT NULL THEN 'Falha de conversão de tempo' END
  ) mensagem_erro,
  jsonb_build_object('usuario_id',usuario_id,'conteudo_id',conteudo_id,'tipo_interacao',tipo_interacao,
    'data_hora',data_hora,'tempo_consumido',tempo_consumido,'percentual_conclusao',percentual_conclusao,
    'avaliacao_atribuida',avaliacao_atribuida)::TEXT payload
FROM c;

CREATE OR REPLACE VIEW controle.v_comentarios_classificados AS
WITH n AS (
  SELECT b.*,
    controle.try_bigint(b.usuario_id) usuario_id_n,
    controle.try_bigint(b.conteudo_id) conteudo_id_n,
    controle.try_numeric(b.avaliacao) avaliacao_n,
    controle.norm_texto(b.comentario) comentario_n,
    controle.norm_tags(b.tags) tags_n,
    controle.try_date(b.data) data_n
  FROM bronze.comentarios_raw b
), r AS (
  SELECT n.*,row_number() OVER(
    PARTITION BY id_execucao,usuario_id_n,conteudo_id_n,data_n,comentario_n ORDER BY bronze_id) rn
  FROM n
), c AS (
  SELECT r.*,
    EXISTS(SELECT 1 FROM public.usuarios u WHERE u.usuario_id=r.usuario_id_n) usuario_existe,
    (EXISTS(SELECT 1 FROM silver.catalogo s WHERE s.conteudo_id=r.conteudo_id_n)
      OR EXISTS(SELECT 1 FROM public.conteudos p WHERE p.conteudo_id=r.conteudo_id_n)) conteudo_existe,
    row_number() OVER(PARTITION BY r.id_execucao ORDER BY r.bronze_id) comentario_id_n
  FROM r
)
SELECT bronze_id,comentario_id_n::BIGINT comentario_id,usuario_id_n usuario_id,conteudo_id_n conteudo_id,
  avaliacao_n avaliacao,comentario_n comentario,tags_n tags,data_n data,
  origem,data_hora_ingestao,id_execucao,
  COALESCE(usuario_id||':'||conteudo_id||':'||data||':'||comentario,bronze_id::TEXT) id_registro,
  CASE
    WHEN controle.norm_texto(usuario_id) IS NULL OR controle.norm_texto(conteudo_id) IS NULL
      OR controle.norm_texto(avaliacao) IS NULL OR comentario_n IS NULL OR controle.norm_texto(data) IS NULL
      THEN 'INCOMPLETO'
    WHEN usuario_id_n IS NULL OR usuario_id_n<=0 OR conteudo_id_n IS NULL OR conteudo_id_n<=0
      OR NOT usuario_existe OR NOT conteudo_existe
      OR avaliacao_n IS NULL OR avaliacao_n<1 OR avaliacao_n>5 OR data_n IS NULL THEN 'INVALIDO'
    WHEN rn>1 THEN 'DUPLICADO' ELSE 'VALIDO'
  END status_registro,
  concat_ws(' | ',
    CASE WHEN controle.norm_texto(usuario_id) IS NULL THEN 'campo obrigatório ausente: usuario_id' END,
    CASE WHEN controle.norm_texto(conteudo_id) IS NULL THEN 'campo obrigatório ausente: conteudo_id' END,
    CASE WHEN controle.norm_texto(avaliacao) IS NULL THEN 'campo obrigatório ausente: avaliacao' END,
    CASE WHEN comentario_n IS NULL THEN 'campo obrigatório ausente: comentario' END,
    CASE WHEN controle.norm_texto(data) IS NULL THEN 'campo obrigatório ausente: data' END,
    CASE WHEN usuario_id_n IS NULL OR usuario_id_n<=0 THEN 'usuario_id inválido' END,
    CASE WHEN conteudo_id_n IS NULL OR conteudo_id_n<=0 THEN 'conteudo_id inválido' END,
    CASE WHEN usuario_id_n IS NOT NULL AND usuario_id_n>0 AND NOT usuario_existe THEN 'referência a usuário inexistente' END,
    CASE WHEN conteudo_id_n IS NOT NULL AND conteudo_id_n>0 AND NOT conteudo_existe THEN 'referência a conteúdo inexistente' END,
    CASE WHEN avaliacao_n IS NULL OR avaliacao_n<1 OR avaliacao_n>5 THEN 'avaliação deve estar entre 1 e 5' END,
    CASE WHEN controle.norm_texto(data) IS NOT NULL AND data_n IS NULL THEN 'data inválida' END,
    CASE WHEN rn>1 THEN 'chave composta do comentário repetida' END
  ) regra_violada,
  concat_ws(' | ',
    CASE WHEN rn>1 THEN 'Duplicidade de comentário' END,
    CASE WHEN NOT conteudo_existe THEN 'Integridade referencial de conteúdo' END,
    CASE WHEN NOT usuario_existe THEN 'Integridade referencial de usuário' END,
    CASE WHEN data_n IS NULL AND controle.norm_texto(data) IS NOT NULL THEN 'Falha de conversão de data' END
  ) mensagem_erro,
  jsonb_build_object('usuario_id',usuario_id,'conteudo_id',conteudo_id,'avaliacao',avaliacao,
    'comentario',comentario,'tags',tags,'data',data)::TEXT payload
FROM c;

CREATE OR REPLACE PROCEDURE controle.reenfileirar_quarentena(
  p_quarentena_id BIGINT, p_payload_corrigido JSONB, p_novo_run_id TEXT
)
LANGUAGE plpgsql AS $$
DECLARE q quarentena.registros%ROWTYPE;
BEGIN
  SELECT * INTO q FROM quarentena.registros
  WHERE quarentena_id=p_quarentena_id AND reprocessado=FALSE FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'Registro de quarentena % inexistente ou já reprocessado',p_quarentena_id;
  END IF;

  IF q.entidade='catalogo' THEN
    INSERT INTO bronze.catalogo_raw(
      conteudo_id,titulo,tipo,categoria,nivel,carga_horaria_min,data_publicacao,descricao,autor,
      origem,data_hora_ingestao,id_execucao)
    VALUES(
      p_payload_corrigido->>'conteudo_id',p_payload_corrigido->>'titulo',p_payload_corrigido->>'tipo',
      p_payload_corrigido->>'categoria',p_payload_corrigido->>'nivel',p_payload_corrigido->>'carga_horaria_min',
      p_payload_corrigido->>'data_publicacao',p_payload_corrigido->>'descricao',p_payload_corrigido->>'autor',
      'reprocessamento:'||q.origem,CURRENT_TIMESTAMP,p_novo_run_id);
  ELSIF q.entidade='interacoes' THEN
    INSERT INTO bronze.interacoes_raw(
      usuario_id,conteudo_id,tipo_interacao,data_hora,tempo_consumido,percentual_conclusao,
      avaliacao_atribuida,origem,data_hora_ingestao,id_execucao)
    VALUES(
      p_payload_corrigido->>'usuario_id',p_payload_corrigido->>'conteudo_id',
      p_payload_corrigido->>'tipo_interacao',p_payload_corrigido->>'data_hora',
      p_payload_corrigido->>'tempo_consumido',p_payload_corrigido->>'percentual_conclusao',
      p_payload_corrigido->>'avaliacao_atribuida','reprocessamento:'||q.origem,CURRENT_TIMESTAMP,p_novo_run_id);
  ELSIF q.entidade='comentarios' THEN
    INSERT INTO bronze.comentarios_raw(
      usuario_id,conteudo_id,avaliacao,comentario,tags,data,origem,data_hora_ingestao,id_execucao)
    VALUES(
      p_payload_corrigido->>'usuario_id',p_payload_corrigido->>'conteudo_id',
      p_payload_corrigido->>'avaliacao',p_payload_corrigido->>'comentario',
      COALESCE((p_payload_corrigido->'tags')::TEXT,'[]'),p_payload_corrigido->>'data',
      'reprocessamento:'||q.origem,CURRENT_TIMESTAMP,p_novo_run_id);
  ELSE
    RAISE EXCEPTION 'Entidade de quarentena não suportada: %',q.entidade;
  END IF;

  UPDATE quarentena.registros
  SET reprocessado=TRUE,data_reprocessamento=CURRENT_TIMESTAMP,novo_id_execucao=p_novo_run_id
  WHERE quarentena_id=p_quarentena_id;
END; $$;

COMMIT;
