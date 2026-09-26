-- RF23 - falha de regra simulada.
-- No psql: \set run_id 'teste-regra-001'
INSERT INTO bronze.catalogo_raw(
  conteudo_id,titulo,tipo,categoria,nivel,carga_horaria_min,data_publicacao,
  descricao,autor,origem,data_hora_ingestao,id_execucao)
VALUES(
  '-99','', 'Ebook','Teste','Especialista','-10','2026-99-99',
  'Registro propositalmente inválido','FIC_DEV','falha_regra.sql',CURRENT_TIMESTAMP,:'run_id');

-- Rode silver_catalogo.hpl com o mesmo RUN_ID e consulte:
SELECT entidade,id_registro,regra_violada,mensagem_erro,id_execucao
FROM quarentena.registros WHERE id_execucao=:'run_id';
