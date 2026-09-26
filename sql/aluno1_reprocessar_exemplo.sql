-- RF23 - modelo de correção e reprocessamento.
SELECT quarentena_id,entidade,id_registro,regra_violada,payload
FROM quarentena.registros
WHERE reprocessado=FALSE
ORDER BY data_erro,quarentena_id;

-- Exemplo:
-- CALL controle.reenfileirar_quarentena(
--   42,
--   '{"conteudo_id":"1001","titulo":"Conteúdo corrigido","tipo":"Curso",
--     "categoria":"Engenharia de Dados","nivel":"Básico","carga_horaria_min":"60",
--     "data_publicacao":"2026-09-25","descricao":"Registro corrigido","autor":"Equipe FIC_DEV"}'::jsonb,
--   'reprocess-20260925-001'
-- );
-- Depois execute o pipeline Silver da entidade com o novo RUN_ID.

SELECT quarentena_id,reprocessado,data_reprocessamento,novo_id_execucao
FROM quarentena.registros ORDER BY quarentena_id DESC;
