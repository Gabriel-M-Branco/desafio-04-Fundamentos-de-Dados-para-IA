# Contrato de Integração do Pipeline e Orquestração (RF15)

O ecossistema integra as entregas dos 3 estudantes através de interfaces padronizadas e contratos de dados estritos.

## 1. Encadeamento Oficial do Pipeline

A esteira executa a seguinte sequência estrita de dependências:

1. **Carga Base, IA e Embeddings (RF02-RF10):** DDL base, carga PostgreSQL/MongoDB, geração e persistência de embeddings vetoriais com pgvector e recomendações pedagógicas.
2. **Ingestão Bronze e Silver no Apache Hop (RF20-RF23, RF26):** Execução do workflow mestre `workflow_principal.hwf` (`carga_bronze_silver.hwf`), validação de regras de borda, isolamento de registros anômalos na Quarentena (`quarentena.registros`), geração das tabelas limpas `silver.*` e provisionamento das estruturas `gold.*`.
3. **Qualidade de Dados e Quality Gate (RF31):** Avaliação das 5 dimensões corporativas (Completude, Validade, Unicidade, Consistência e Integridade Referencial). Uma falha crítica bloqueia a publicação da camada Gold.
4. **Particionamento Colunar Parquet Hive (RF24):** Exportação dos dados validados da Silver para Parquet particionado (`dados/parquet/interacoes/particionado/ano=YYYY/mes=MM/`) e execução de benchmark comparativo com CSV e JSON.
5. **Privacidade e Proteção de Dados (RF32/RF33):** Demonstração das rotinas de mascaramento, pseudonimização determinística e hashing com salt.
6. **Processamento Analítico com Apache Beam (RF25):** Agregação analítica distribuída via DirectRunner (e diagnóstico de ambiente Spark), gravando o artefato `dados/parquet/gold/kpis_mensais_categoria.parquet`.
7. **Publicação da Camada Gold no PostgreSQL (RF26):** Sincronização analítica nas tabelas `gold.kpis_mensais_categoria`, `gold.desempenho_conteudos` e visões executivas.
8. **Governança de Dados Mestres — MDM (RF30):** Matching, survivorship e geração de Golden Record para reconciliação cadastral.
9. **Governança, Catálogo e Linhagem no OpenMetadata (RF27-RF29):** Catalogação via API REST de 12 entidades nas 4 camadas, 4 termos de glossário e grafo de linhagem de 5 pontas.
10. **Sincronização Analítica no Apache Superset (RF16-RF18):** Importação de dashboards executivos e conexão com schema Gold.
11. **Suíte de Testes Automatizados (RF34):** Execução da suíte de 103 testes no pytest.

---

## 2. Modalidades de Execução Homologadas

O projeto oferece suporte a duas formas oficiais de execução:

### Modalidade A: Orquestrador Unificado em Comando Único (Recomendada)
- **Universal / Multiplataforma (Windows, Linux e macOS via Python):**
  ```bash
  python scripts/executar_fluxo_completo.py
  # Opcional (sem rodar o pytest ao final):
  python scripts/executar_fluxo_completo.py --sem-testes
  ```
- **Windows (PowerShell Nativo):**
  ```powershell
  .\scripts\executar_fluxo_completo.ps1
  # Opcional:
  .\scripts\executar_fluxo_completo.ps1 -SemTestes
  ```
- **Linux e macOS (Bash / Zsh Nativo):**
  ```bash
  chmod +x scripts/executar_fluxo_completo.sh
  ./scripts/executar_fluxo_completo.sh
  # Opcional:
  ./scripts/executar_fluxo_completo.sh --sem-testes
  ```

*Garantias Multiplataforma (Windows, macOS e Linux):*
- **Agnóstico ao Sistema Operacional:** O código utiliza `pathlib.Path` e encodings `UTF-8` padronizados, eliminando problemas com separadores de diretório (`/` vs `\`) ou formatos de quebra de linha (`CRLF` vs `LF`).
- **Resolução Automática do Interpretador:** Detecta o executável do ambiente virtual ativo (`sys.executable`), funcionando perfeitamente tanto com `.venv\Scripts\python.exe` (Windows) quanto com `.venv/bin/python` (Linux/macOS).
- **Conteinerização Padronizada:** A chamada `docker exec hop-web ...` roda o script shell diretamente dentro do contêiner Linux do Apache Hop, sendo 100% idêntica e agnóstica ao sistema host.
- **Validação de Código de Saída:** Cada etapa é monitorada via `subprocess.run(..., check=True)`, abortando imediatamente caso qualquer etapa retorne código de erro diferente de zero.
- **Compatibilidade com Volumes Limpos:** Funciona mesmo após reset total da infraestrutura (`docker compose down -v && docker compose up -d`).

### Modalidade B: Execução Modular por Etapas (Inspeção e Auditoria)
Permite auditar e depurar cada camada isoladamente:
```bash
# 1. Carga base e IA
python -m src.main

# 2. Apache Hop (Headless via Docker)
docker exec hop-web /usr/local/tomcat/webapps/ROOT/hop-run.sh --environment desafio4-dev --project desafio4 --file /files/workflows/workflow_principal.hwf --runconfig local --level BASIC

# 3. Pipeline analítico, Parquet, Qualidade, LGPD e Beam
python -m src.executar_etapas --etapa todas

# 4. Dados Mestres (MDM)
python scripts/demonstrar_dados_mestres.py

# 5. OpenMetadata (Catálogo, Glossário e Linhagem)
python scripts/configurar_openmetadata.py

# 6. Sincronização Apache Superset
python dashboard/sync_database.py

# 7. Testes Automatizados
python -m pytest tests/
```

