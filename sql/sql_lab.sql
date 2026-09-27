-- =============================================================================
-- CONSULTAS ANALÍTICAS DO SQL LAB E DATASETS VIRTUAIS (RF17)
-- Plataforma Educacional FIC_DEV - Desafio Prático 2
-- Integrado à Camada Gold (RF26) e Dashboards do Apache Superset (RF16-RF18)
-- =============================================================================
-- Este arquivo consolida as consultas virtuais modeladas no SQL Lab para alimentar
-- os gráficos do Storytelling Executivo e os painéis de monitoramento do Superset.
--
-- Requisitos técnicos atendidos:
--   [x] Junção (JOIN) entre tabelas/visões da camada Gold
--   [x] Agregação com GROUP BY, SUM, AVG, COUNT, ROUND
--   [x] Expressão condicional com CASE WHEN
--   [x] Funções de data (MAKE_DATE, DATE_TRUNC, EXTRACT, INTERVAL)
--   [x] Documentação da finalidade e campos calculados
--   [x] Reprodutibilidade a partir do schema gold no PostgreSQL
-- =============================================================================


-- -----------------------------------------------------------------------------
-- CONSULTA 1: STORYTELLING - Retenção e Eficiência por Tipo de Conteúdo
-- Utilizada em: Gráfico de Barras Agrupadas do Storytelling (Passo 2 - Evidência)
-- -----------------------------------------------------------------------------
-- Finalidade:
--   Avaliar o impacto dos diferentes formatos de conteúdo (Curso, Vídeo, Artigo,
--   Podcast) na retenção e conclusão global dos alunos, cruzando o desempenho
--   individual dos materiais com os KPIs mensais acumulados na camada Gold.
--
-- Campos Calculados:
--   1. taxa_conversao_inicio_conclusao_pct: Percentual acumulado de conclusões
--      em relação aos inícios por formato (eficiência do funil).
--   2. nivel_impacto_engajamento: Classificação condicional de relevância baseada
--      na combinação de taxa de conclusão e satisfação média (avaliação).
--   3. dias_desde_ultima_carga: Dias decorridos desde a data da última carga Gold.
-- -----------------------------------------------------------------------------
SELECT 
    dc.tipo AS tipo_conteudo,
    COUNT(dc.conteudo_id) AS total_conteudos_ofertados,
    SUM(dc.total_visualizacoes) AS total_visualizacoes,
    SUM(dc.total_inicios) AS total_inicios,
    SUM(dc.total_conclusoes) AS total_conclusoes,

    -- 1. Agregação + Expressão Aritmética (Taxa de Conversão):
    ROUND(
        (SUM(dc.total_conclusoes)::NUMERIC / NULLIF(SUM(dc.total_inicios), 0)) * 100,
        2
    ) AS taxa_conversao_inicio_conclusao_pct,

    ROUND(AVG(dc.avaliacao_media), 2) AS avaliacao_media_formato,

    -- 2. Expressão Condicional (CASE WHEN):
    CASE 
        WHEN (SUM(dc.total_conclusoes)::NUMERIC / NULLIF(SUM(dc.total_inicios), 0)) >= 0.60 
             AND AVG(dc.avaliacao_media) >= 4.0 
            THEN 'Alta Retenção e Satisfação'

        WHEN (SUM(dc.total_conclusoes)::NUMERIC / NULLIF(SUM(dc.total_inicios), 0)) < 0.40 
            THEN 'Gargalo de Evasão'

        ELSE 'Desempenho Moderado'
    END AS nivel_impacto_engajamento,

    -- 3. Função de Data (Cálculo de intervalo em dias):
    EXTRACT(
        DAY FROM (CURRENT_DATE - MAX(dc._data_carga_gold))
    ) AS dias_desde_ultima_carga

FROM gold.desempenho_conteudos dc

-- 4. Junção (JOIN) entre tabelas da camada Gold:
INNER JOIN (
    SELECT 
        categoria,
        SUM(total_interacoes) AS interacoes_categoria
    FROM gold.kpis_mensais_categoria
    WHERE MAKE_DATE(ano, mes, 1) >= (CURRENT_DATE - INTERVAL '12 months')
    GROUP BY categoria
) kmc 
    ON dc.categoria = kmc.categoria

-- Agrupamento por tipo de conteúdo:
GROUP BY dc.tipo
ORDER BY total_visualizacoes DESC;



-- -----------------------------------------------------------------------------
-- CONSULTA 2: SQLab - Evolução Temporal dos Indicadores e Status de Qualidade
-- Utilizada em: Painel de Indicadores Mensais e Séries Temporais do Superset
-- -----------------------------------------------------------------------------
-- Finalidade:
--   Acompanhar a evolução temporal mensal dos principais indicadores da plataforma
--   (usuários ativos, taxa de conclusão média e tempo médio de consumo) segmentados
--   por área temática, avaliando o cumprimento da meta de qualidade pedagógica.
--
-- Campos Calculados:
--   1. data_referencia: Converte os campos numéricos de ano e mês em uma data formal.
--   2. status_qualidade_mes: Classifica o mês conforme a nota média das avaliações
--      atribuídas pelos alunos (meta de qualidade >= 4.0).
-- -----------------------------------------------------------------------------
SELECT 
    -- 1. Função de Data (Gera o primeiro dia de cada mês):
    MAKE_DATE(k.ano, k.mes, 1) AS data_referencia,
    k.categoria,
    SUM(k.usuarios_ativos) AS usuarios_ativos,
    ROUND(AVG(k.taxa_conclusao_pct), 2) AS taxa_conclusao_media_pct,
    ROUND(AVG(k.tempo_medio_min), 2) AS tempo_medio_consumo_min,
    ROUND(AVG(k.avaliacao_media), 2) AS avaliacao_media_mes,

    -- 2. Expressão Condicional (CASE WHEN):
    CASE 
        WHEN AVG(k.avaliacao_media) >= 4.0 THEN 'Meta de Qualidade Atingida'
        WHEN AVG(k.avaliacao_media) IS NULL THEN 'Sem Avaliações Registradas'
        ELSE 'Abaixo da Meta de Qualidade'
    END AS status_qualidade_mes

FROM gold.kpis_mensais_categoria k
GROUP BY k.ano, k.mes, k.categoria
HAVING MAKE_DATE(k.ano, k.mes, 1) >= (CURRENT_DATE - INTERVAL '12 months')
ORDER BY data_referencia DESC, k.categoria;



-- -----------------------------------------------------------------------------
-- CONSULTA 3: SQLab - Eficiência do Funil e Diagnóstico de Evasão por Categoria
-- Utilizada em: Gráfico de Barras Empilhadas de Eficiência do Funil
-- -----------------------------------------------------------------------------
-- Finalidade:
--   Mapear a perda de alunos ao longo do funil de consumo (Inícios vs Conclusões)
--   em cada categoria de conhecimento, identificando temas críticos com risco de evasão.
--
-- Campos Calculados:
--   1. taxa_eficiencia_funil_pct: Percentual acumulado de finalização de cursos.
--   2. classificacao_engajamento: Diagnóstico categórico do engajamento estudantil.
-- -----------------------------------------------------------------------------
SELECT 
    k.categoria,
    SUM(k.total_visualizacoes) AS total_visualizacoes,
    SUM(k.total_inicios) AS total_inicios,
    SUM(k.total_conclusoes) AS total_conclusoes,

    -- 1. Cálculo de Eficiência Percentual:
    ROUND(
        (SUM(k.total_conclusoes)::NUMERIC / NULLIF(SUM(k.total_inicios), 0)) * 100, 
        2
    ) AS taxa_eficiencia_funil_pct,

    ROUND(AVG(k.avaliacao_media), 2) AS avaliacao_media_acumulada,

    -- 2. Expressão Condicional (CASE WHEN):
    CASE 
        WHEN (SUM(k.total_conclusoes)::NUMERIC / NULLIF(SUM(k.total_inicios), 0)) >= 0.70 THEN 'Alto Engajamento'
        WHEN (SUM(k.total_conclusoes)::NUMERIC / NULLIF(SUM(k.total_inicios), 0)) BETWEEN 0.40 AND 0.69 THEN 'Médio Engajamento'
        ELSE 'Risco de Evasão'
    END AS classificacao_engajamento

FROM gold.kpis_mensais_categoria k

-- 3. Função de Data (Janela anual):
WHERE MAKE_DATE(k.ano, k.mes, 1) >= DATE_TRUNC('year', CURRENT_DATE - INTERVAL '1 year')
GROUP BY k.categoria
ORDER BY total_inicios DESC;



-- -----------------------------------------------------------------------------
-- CONSULTA 4: Observador do Alerta Crítico (Superset Alerts & Reports - RF18)
-- Utilizada em: Regra automatizada de disparo de alerta por email
-- -----------------------------------------------------------------------------
-- Finalidade:
--   Monitorar ativamente se o tempo médio de consumo por categoria no mês mais
--   recente caiu abaixo do limite de tolerância operacional (< 500 minutos).
--   Se a consulta retornar qualquer linha (NOT NULL), o Superset dispara o alerta.
-- -----------------------------------------------------------------------------
SELECT 
    ano,
    mes,
    categoria,
    ROUND(AVG(tempo_total_consumido_min), 2) AS media_tempo_consumido_min
FROM gold.kpis_mensais_categoria 
WHERE (ano, mes) = (
    SELECT ano, mes 
    FROM gold.kpis_mensais_categoria 
    ORDER BY ano DESC, mes DESC 
    LIMIT 1
)
GROUP BY ano, mes, categoria
HAVING AVG(tempo_total_consumido_min) < 500;
