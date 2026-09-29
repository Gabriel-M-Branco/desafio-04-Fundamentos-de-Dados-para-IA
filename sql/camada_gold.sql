-- DDL Oficial da Camada Gold para Consumo Analítico no PostgreSQL (RF26)
-- Integrada ao Apache Beam (RF25), Qualidade de Dados (RF31), SQL Lab e Superset (RF16-18)

SET timezone TO 'America/Cuiaba';
DO $$ BEGIN
    PERFORM 1 FROM pg_database WHERE datname = 'ficdev_analitico';
    IF FOUND THEN
        ALTER DATABASE ficdev_analitico SET timezone TO 'America/Cuiaba';
    END IF;
END $$;

CREATE SCHEMA IF NOT EXISTS gold;

-- 1. Tabela Gold: KPIs Consolidados por Período e Categoria
-- Granularidade: (ano, mes, categoria)
CREATE TABLE IF NOT EXISTS gold.kpis_mensais_categoria (
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    categoria VARCHAR(120) NOT NULL,
    total_interacoes INTEGER NOT NULL CHECK (total_interacoes >= 0),
    usuarios_ativos INTEGER NOT NULL CHECK (usuarios_ativos >= 0),
    total_visualizacoes INTEGER NOT NULL CHECK (total_visualizacoes >= 0),
    total_inicios INTEGER NOT NULL CHECK (total_inicios >= 0),
    total_conclusoes INTEGER NOT NULL CHECK (total_conclusoes >= 0),
    total_curtidas INTEGER NOT NULL CHECK (total_curtidas >= 0),
    taxa_conclusao_pct NUMERIC(5,2) NOT NULL CHECK (taxa_conclusao_pct >= 0),
    tempo_total_consumido_min NUMERIC(12,2) NOT NULL CHECK (tempo_total_consumido_min >= 0),
    tempo_medio_min NUMERIC(10,2) NOT NULL CHECK (tempo_medio_min >= 0),
    avaliacao_media NUMERIC(3,2) CHECK (avaliacao_media IS NULL OR (avaliacao_media >= 1.0 AND avaliacao_media <= 5.0)),
    _data_carga_gold TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    _lote_processamento VARCHAR(100) NOT NULL,
    PRIMARY KEY (ano, mes, categoria)
);

CREATE INDEX IF NOT EXISTS idx_gold_kpis_periodo ON gold.kpis_mensais_categoria(ano, mes);
CREATE INDEX IF NOT EXISTS idx_gold_kpis_categoria ON gold.kpis_mensais_categoria(categoria);

-- 2. Tabela Gold: Desempenho e Engajamento por Conteúdo
-- Granularidade: conteudo_id
CREATE TABLE IF NOT EXISTS gold.desempenho_conteudos (
    conteudo_id BIGINT PRIMARY KEY,
    titulo VARCHAR(255) NOT NULL,
    tipo VARCHAR(30) NOT NULL,
    categoria VARCHAR(120) NOT NULL,
    nivel VARCHAR(30) NOT NULL,
    total_visualizacoes INTEGER NOT NULL DEFAULT 0,
    total_inicios INTEGER NOT NULL DEFAULT 0,
    total_conclusoes INTEGER NOT NULL DEFAULT 0,
    total_curtidas INTEGER NOT NULL DEFAULT 0,
    taxa_conclusao_pct NUMERIC(5,2) NOT NULL DEFAULT 0.0,
    tempo_total_min NUMERIC(12,2) NOT NULL DEFAULT 0.0,
    avaliacao_media NUMERIC(3,2) CHECK (avaliacao_media IS NULL OR (avaliacao_media >= 1.0 AND avaliacao_media <= 5.0)),
    _data_carga_gold TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    _lote_processamento VARCHAR(100) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_gold_conteudos_categoria ON gold.desempenho_conteudos(categoria);

-- 3. Visões Analíticas para o Apache Superset e SQL Lab
CREATE OR REPLACE VIEW gold.vw_kpis_executivos AS
SELECT
    MAKE_DATE(ano, mes, 1) AS data_referencia,
    ano,
    mes,
    categoria,
    total_interacoes,
    usuarios_ativos,
    total_visualizacoes,
    total_inicios,
    total_conclusoes,
    total_curtidas,
    taxa_conclusao_pct,
    tempo_total_consumido_min,
    tempo_medio_min,
    avaliacao_media
FROM gold.kpis_mensais_categoria;

CREATE OR REPLACE VIEW gold.vw_ranking_conteudos_engajamento AS
SELECT
    conteudo_id,
    titulo,
    categoria,
    tipo,
    nivel,
    total_visualizacoes,
    total_conclusoes,
    taxa_conclusao_pct,
    tempo_total_min,
    avaliacao_media,
    DENSE_RANK() OVER (PARTITION BY categoria ORDER BY total_visualizacoes DESC) AS ranking_categoria
FROM gold.desempenho_conteudos;

-- Visões espelho no schema public para garantir compatibilidade com conexões padrão do Superset
CREATE OR REPLACE VIEW public.vw_gold_kpis_mensais_categoria AS
SELECT * FROM gold.vw_kpis_executivos;

CREATE OR REPLACE VIEW public.vw_gold_ranking_conteudos AS
SELECT * FROM gold.vw_ranking_conteudos_engajamento;
