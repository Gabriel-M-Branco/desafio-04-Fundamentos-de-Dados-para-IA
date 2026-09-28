**SQLab - Visualizações por Categoria**

SELECT 
    -- Creates a date corresponding to the 1st day of each month
    MAKE_DATE(ano, mes, 1) AS data_mes,
    categoria,
    SUM(total_visualizacoes) AS total_visualizacoes
FROM gold.kpis_mensais_categoria
GROUP BY MAKE_DATE(ano, mes, 1), categoria
ORDER BY data_mes ASC;

**SQLab - Análise de Eficiência e Evasão por Categoria**

-- Finalidade: Avaliar o desempenho acumulado e a eficiência do funil de consumo por categoria na Camada Gold.
-- Campos Calculados: 
--   1. taxa_eficiencia_funil_pct: Percentual de conclusões em relação aos inícios do conteúdo.
--   2. classificacao_engajamento: Categoria condicional baseada na taxa de conclusão (Baixo, Médio, Alto).
SELECT 
    k.categoria,
    SUM(k.total_visualizacoes) AS total_visualizacoes,
    SUM(k.total_inicios) AS total_inicios,
    SUM(k.total_conclusoes) AS total_conclusoes,
    -- Expressão Condicional + Agregação:
    ROUND(
        (SUM(k.total_conclusoes)::NUMERIC / NULLIF(SUM(k.total_inicios), 0)) * 100, 2
    ) AS taxa_eficiencia_funil_pct,
    AVG(k.avaliacao_media) AS avaliacao_media_acumulada,
    -- Expressão Condicional:
    CASE 
        WHEN (SUM(k.total_conclusoes)::NUMERIC / NULLIF(SUM(k.total_inicios), 0)) >= 0.70 THEN 'Alto Engajamento'
        WHEN (SUM(k.total_conclusoes)::NUMERIC / NULLIF(SUM(k.total_inicios), 0)) BETWEEN 0.40 AND 0.69 THEN 'Médio Engajamento'
        ELSE 'Risco de Evasão'
    END AS classificacao_engajamento
FROM gold.kpis_mensais_categoria k
-- Função de Data (Filtro do último ano):
WHERE MAKE_DATE(k.ano, k.mes, 1) >= DATE_TRUNC('year', CURRENT_DATE - INTERVAL '1 year')
GROUP BY k.categoria
ORDER BY total_inicios DESC;

**STORYTELLING - Distribuição de visualizações por tipo de conteúdo**

SELECT
    tipo,
    SUM(total_visualizacoes) AS total
FROM gold.desempenho_conteudos
WHERE total_visualizacoes > 0
GROUP BY tipo
ORDER BY total DESC;

**STORYTELLING - Retenção por Tipo**

-- Finalidade: Avaliar o impacto dos diferentes formatos de conteúdo
-- (Vídeo, Curso, Artigo, Podcast) na retenção global,
-- comparando com os KPIs mensais acumulados na Camada Gold.
--
-- Campos Calculados:
--   1. taxa_conversao_inicio_conclusao_pct: Eficiência acumulada de
--      conversão dos conteúdos por tipo.
--   2. nivel_impacto_engajamento: Classificação condicional de relevância
--      baseada na taxa de conversão e média de avaliações.
--   3. dias_desde_ultima_carga: Dias decorridos desde o lote de carga Gold
--      até a data atual.

SELECT 
    dc.tipo AS tipo_conteudo,
    COUNT(dc.conteudo_id) AS total_conteudos_ofertados,
    SUM(dc.total_visualizacoes) AS total_visualizacoes,
    SUM(dc.total_inicios) AS total_inicios,
    SUM(dc.total_conclusoes) AS total_conclusoes,

    -- Agregação + Expressão Condicional:
    ROUND(
        (SUM(dc.total_conclusoes)::NUMERIC / NULLIF(SUM(dc.total_inicios), 0)) * 100,
        2
    ) AS taxa_conversao_inicio_conclusao_pct,

    AVG(dc.avaliacao_media) AS avaliacao_media_formato,

    -- Expressão Condicional (CASE WHEN):
    CASE 
        WHEN (SUM(dc.total_conclusoes)::NUMERIC / NULLIF(SUM(dc.total_inicios), 0)) >= 0.60 
             AND AVG(dc.avaliacao_media) >= 4.0 
            THEN 'Alta Retenção e Satisfação'

        WHEN (SUM(dc.total_conclusoes)::NUMERIC / NULLIF(SUM(dc.total_inicios), 0)) < 0.40 
            THEN 'Gargalo de Evasão'

        ELSE 'Desempenho Moderado'
    END AS nivel_impacto_engajamento,

    -- Função de Data:
    EXTRACT(
        DAY FROM (CURRENT_DATE - MAX(dc._data_carga_gold))
    ) AS dias_desde_ultima_carga

FROM gold.desempenho_conteudos dc

-- Junção entre tabelas da camada Gold:
INNER JOIN (
    SELECT 
        categoria,
        SUM(total_interacoes) AS interacoes_categoria
    FROM gold.kpis_mensais_categoria
    WHERE MAKE_DATE(ano, mes, 1) >= (CURRENT_DATE - INTERVAL '12 months')
    GROUP BY categoria
) kmc 
    ON dc.categoria = kmc.categoria

-- Agrupamento apenas por tipo de conteúdo:
GROUP BY dc.tipo

ORDER BY total_visualizacoes DESC;

**STORYTELLING - Desempenho de cada Tipo**

SELECT 
    tipo, 
    SUM(total_conclusoes) * 100.0 / NULLIF(SUM(total_inicios), 0) AS taxa_conclusao_pct, 
    AVG(avaliacao_media) AS nota_media,
    SUM(total_visualizacoes) AS volume
FROM gold.desempenho_conteudos 
GROUP BY tipo;