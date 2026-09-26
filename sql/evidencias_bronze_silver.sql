-- Evidências de Auditoria das Camadas Bronze e Silver
SELECT * FROM controle.execucao_workflow ORDER BY inicio DESC;
SELECT * FROM controle.execucao_etapa ORDER BY etapa_id DESC;

SELECT 'bronze.catalogo_raw' tabela,id_execucao,COUNT(*) linhas FROM bronze.catalogo_raw GROUP BY id_execucao
UNION ALL SELECT 'bronze.interacoes_raw',id_execucao,COUNT(*) FROM bronze.interacoes_raw GROUP BY id_execucao
UNION ALL SELECT 'bronze.comentarios_raw',id_execucao,COUNT(*) FROM bronze.comentarios_raw GROUP BY id_execucao
ORDER BY id_execucao,tabela;

SELECT 'silver.catalogo' tabela,id_execucao,COUNT(*) linhas FROM silver.catalogo GROUP BY id_execucao
UNION ALL SELECT 'silver.interacoes',id_execucao,COUNT(*) FROM silver.interacoes GROUP BY id_execucao
UNION ALL SELECT 'silver.comentarios',id_execucao,COUNT(*) FROM silver.comentarios GROUP BY id_execucao
ORDER BY id_execucao,tabela;

SELECT entidade,regra_violada,COUNT(*) qtd
FROM quarentena.registros GROUP BY entidade,regra_violada ORDER BY qtd DESC;
