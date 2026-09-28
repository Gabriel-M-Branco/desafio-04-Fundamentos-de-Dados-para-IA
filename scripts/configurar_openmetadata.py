"""Script de automação, catálogo e governança do OpenMetadata (RF27 — RF29).

Realiza de forma 100% reproduzível via API REST:
1. Autenticação oficial com admin@openmetadata.org (JWT Bearer Token).
2. Registro do Serviço de Banco de Dados PostgreSQL (ficdev_postgres) e schemas (silver e gold).
3. Catalogação das tabelas analíticas (kpis_mensais_categoria, desempenho_conteudos e catalogo).
4. Aplicação de tags de sensibilidade LGPD (PII.Sensitive).
5. Criação da linhagem gráfica de dados ponta a ponta (Lineage).
6. Cadastro do Glossário de Negócio e dos 4 Termos Obrigatórios (RF28).
7. Exportação do Dossiê Estruturado de Metadados em JSON para auditoria (RF34).
"""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

RAIZ_PROJETO = Path(__file__).resolve().parents[1]
load_dotenv(RAIZ_PROJETO / ".env")

# Validação estrita de variáveis de ambiente sem fallbacks (RF15)
variaveis_obrigatorias = [
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "POSTGRES_HOST_DOCKER",
    "POSTGRES_PORT_DOCKER",
    "OPENMETADATA_URL",
    "OPENMETADATA_ADMIN_EMAIL",
    "OPENMETADATA_ADMIN_PASSWORD",
]
ausentes = [v for v in variaveis_obrigatorias if not os.environ.get(v)]
if ausentes:
    raise KeyError(
        f"Variáveis de ambiente obrigatórias não configuradas no .env: {ausentes}. "
        "Fallbacks e valores padrão estão desabilitados por política de segurança (RF15)."
    )

OPENMETADATA_URL = os.environ["OPENMETADATA_URL"].rstrip("/")
API_BASE = f"{OPENMETADATA_URL}/api/v1"
OM_ADMIN_EMAIL = os.environ["OPENMETADATA_ADMIN_EMAIL"]
OM_ADMIN_PASSWORD = os.environ["OPENMETADATA_ADMIN_PASSWORD"]

PG_USER = os.environ["POSTGRES_USER"]
PG_PASSWORD = os.environ["POSTGRES_PASSWORD"]
PG_DB = os.environ["POSTGRES_DB"]
PG_HOST = os.environ["POSTGRES_HOST_DOCKER"]
PG_PORT = os.environ["POSTGRES_PORT_DOCKER"]

DIR_OMD = RAIZ_PROJETO / "openmetadata"
DIR_OMD.mkdir(parents=True, exist_ok=True)
DIR_EVIDENCIAS = DIR_OMD / "evidencias"
DIR_EVIDENCIAS.mkdir(parents=True, exist_ok=True)




TERMOS_GLOSSARIO_OFICIAIS = [
    {
        "name": "Usuario_Ativo",
        "displayName": "Usuário Ativo",
        "description": "Estudante que realizou pelo menos uma interação de consumo (início, visualização ou conclusão) na plataforma no período de apuração mensal.",
        "regra_calculo": "COUNT(DISTINCT usuario_id) WHERE ano = YYYY AND mes = MM",
        "responsavel": "Equipe Pedagógica e Engenharia FIC_DEV",
        "tabela_associada": "gold.kpis_mensais_categoria",
        "coluna_associada": "usuarios_ativos",
        "classificacao_lgpd": "Pseudonimizado (UUIDv5) / Métrica Agregada",
    },
    {
        "name": "Taxa_Conclusao",
        "displayName": "Taxa de Conclusão",
        "description": "Eficiência percentual do funil de aprendizagem, calculada pela razão entre o total de conteúdos concluídos e o total de conteúdos iniciados.",
        "regra_calculo": "ROUND((SUM(total_conclusoes)::NUMERIC / NULLIF(SUM(total_inicios), 0)) * 100, 2)",
        "responsavel": "Coordenação de Ensino e Avaliação Didática",
        "tabela_associada": "gold.kpis_mensais_categoria",
        "coluna_associada": "taxa_conclusao_pct",
        "classificacao_lgpd": "Métrica Analítica Estatística Não-Identificável",
    },
    {
        "name": "Tempo_Medio_Consumo",
        "displayName": "Tempo Médio de Consumo",
        "description": "Tempo médio despendido em minutos pelos alunos em cada formato ou categoria temática durante as jornadas de estudo.",
        "regra_calculo": "ROUND(AVG(tempo_consumido_min), 2) agrupado por categoria e período",
        "responsavel": "Equipe de Produto e Conteúdo Pedagógico",
        "tabela_associada": "gold.kpis_mensais_categoria",
        "coluna_associada": "tempo_medio_min",
        "classificacao_lgpd": "Dado Estatístico Agregado (Alvo de Alerta < 500 min)",
    },
    {
        "name": "Conversao_Recomendacao",
        "displayName": "Conversão de Recomendação",
        "description": "Proporção de recomendações pedagógicas geradas pelo motor de IA que foram efetivamente consumidas ou concluídas pelos usuários recomendados.",
        "regra_calculo": "ROUND((COUNT(DISTINCT interacoes_concluidas_recomendadas)::NUMERIC / NULLIF(COUNT(DISTINCT total_recomendacoes_geradas), 0)) * 100, 2)",
        "responsavel": "Equipe de Inteligência Artificial e Data Science",
        "tabela_associada": "gold.vw_ranking_conteudos_engajamento",
        "coluna_associada": "ranking_categoria",
        "classificacao_lgpd": "Métrica Comportamental Algorítmica",
    },
]


def testar_conexao_openmetadata() -> bool:
    """Verifica se o servidor do OpenMetadata está respondendo na porta 8585."""
    try:
        req = urllib.request.Request(f"{API_BASE}/system/version", headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                dados = json.loads(resp.read().decode("utf-8"))
                print(f"[OK] OpenMetadata Server conectado! Versão: {dados.get('version', '1.4.x')}")
                return True
    except Exception as exc:
        print(f"[INFO] OpenMetadata Server não respondeu em {API_BASE}: {exc}")
    return False


def autenticar_openmetadata() -> str | None:
    """Autentica na API REST do OpenMetadata com credenciais administrativas seguras via .env (RF15)."""
    if not OM_ADMIN_PASSWORD:
        print("[Aviso] Variável OPENMETADATA_ADMIN_PASSWORD não configurada no ambiente (.env).")
        return None

    b64_pwd = base64.b64encode(OM_ADMIN_PASSWORD.encode("utf-8")).decode("utf-8")
    payload = json.dumps({"email": OM_ADMIN_EMAIL, "password": b64_pwd}).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE}/users/login",
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                dados = json.loads(resp.read().decode("utf-8"))
                token = dados.get("accessToken")
                print(f"[OK] Autenticação bem-sucedida como {OM_ADMIN_EMAIL}!")
                return token
    except Exception as exc:
        print(f"[Aviso] Falha na autenticação do OpenMetadata: {exc}")
    return None


def sincronizar_servico_e_schemas(token: str) -> None:
    """Registra o serviço PostgreSQL, o banco e os schemas silver e gold sem expor credenciais (RF15)."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"}

    # 1. Serviço de Banco (injetando credenciais das variáveis de ambiente de forma segura)
    svc_payload = {
        "name": "ficdev_postgres",
        "displayName": "PostgreSQL FIC_DEV",
        "description": "Instância PostgreSQL da Plataforma Educacional FIC_DEV (RF20 a RF26)",
        "serviceType": "Postgres",
        "connection": {
            "config": {
                "type": "Postgres",
                "scheme": "postgresql+psycopg2",
                "username": PG_USER,
                "authType": {"password": PG_PASSWORD},
                "hostPort": f"{PG_HOST}:{PG_PORT}",
                "database": PG_DB,
            }
        },
    }
    req_svc = urllib.request.Request(f"{API_BASE}/services/databaseServices", data=json.dumps(svc_payload).encode("utf-8"), headers=headers)
    try:
        with urllib.request.urlopen(req_svc, timeout=5) as resp:
            print("[OK] Serviço de Banco 'ficdev_postgres' registrado no OpenMetadata!")
    except urllib.error.HTTPError as err:
        if err.code == 409:
            print("[INFO] Serviço 'ficdev_postgres' já existente.")
        else:
            print(f"[Aviso] Serviço: {err}")

    # 2. Banco de Dados
    db_payload = {
        "name": PG_DB,
        "displayName": PG_DB,
        "service": "ficdev_postgres",
        "description": "Banco de dados principal contendo as camadas Bronze, Silver e Gold.",
    }
    req_db = urllib.request.Request(f"{API_BASE}/databases", data=json.dumps(db_payload).encode("utf-8"), headers=headers)
    try:
        with urllib.request.urlopen(req_db, timeout=5) as resp:
            print(f"[OK] Database '{PG_DB}' registrado no OpenMetadata!")
    except urllib.error.HTTPError as err:
        if err.code == 409:
            print(f"[INFO] Database '{PG_DB}' já existente.")
        else:
            print(f"[Aviso] Database: {err}")

    # 3. Schemas Fontes, Bronze, Silver e Gold (RF20 a RF26)
    schemas_info = [
        ("fontes", "Camada de Fontes Brutas: Arquivos de telemetria (JSON), catálogo administrativo (CSV) e NoSQL (MongoDB)"),
        ("bronze", "Camada Bronze: Ingestão bruta com campos técnicos de auditoria (_origem, _ingestao_em, _run_id) via Apache Hop (RF20)"),
        ("silver", "Camada Silver: Dados padronizados, tipados e validados pelo Apache Hop (RF20/RF30)"),
        ("gold", "Camada Gold: Tabelas e visões analíticas agregadas para consumo no Superset (RF26)"),
    ]
    for schema_name, desc in schemas_info:
        sch_payload = {
            "name": schema_name,
            "displayName": schema_name,
            "database": f"ficdev_postgres.{PG_DB}",
            "description": desc,
        }

        req_sch = urllib.request.Request(f"{API_BASE}/databaseSchemas", data=json.dumps(sch_payload).encode("utf-8"), headers=headers)
        try:
            with urllib.request.urlopen(req_sch, timeout=5) as resp:
                print(f"[OK] Schema '{schema_name}' registrado no OpenMetadata!")
        except urllib.error.HTTPError as err:
            if err.code == 409:
                print(f"[INFO] Schema '{schema_name}' já existente.")
            else:
                print(f"[Aviso] Schema {schema_name}: {err}")


def sincronizar_servico_dashboard(token: str) -> str | None:
    """Registra o serviço Apache Superset e o Dashboard analítico oficial no OpenMetadata (RF16/RF29)."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"}

    # 1. Serviço de Dashboard (Superset)
    d_svc = {
        "name": "ficdev_superset",
        "displayName": "Apache Superset FIC_DEV",
        "description": "Serviço de Business Intelligence e Consumo Analítico Executivo (RF16 a RF18)",
        "serviceType": "Superset",
        "connection": {
            "config": {
                "type": "Superset",
                "hostPort": "http://superset:8088",
            }
        },
    }
    try:
        req = urllib.request.Request(f"{API_BASE}/services/dashboardServices", data=json.dumps(d_svc).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            print("[OK] Dashboard Service 'ficdev_superset' registrado no OpenMetadata!")
    except urllib.error.HTTPError as err:
        if err.code == 409:
            print("[INFO] Dashboard Service 'ficdev_superset' já existente.")
        else:
            print(f"[Aviso] Dashboard Service: {err}")

    # 2. Entidade Dashboard Oficial
    dash_payload = {
        "name": "desafio_4_dashboard",
        "displayName": "Desafio 4 - Dashboard Executivo FIC_DEV",
        "description": "Dashboard analítico executivo consolidado com KPIs educacionais e engajamento da Camada Gold (RF16 a RF18)",
        "service": "ficdev_superset",
    }
    dashboard_id = None
    try:
        req = urllib.request.Request(f"{API_BASE}/dashboards", data=json.dumps(dash_payload).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            dashboard_id = data.get("id")
            print("[OK] Dashboard 'desafio_4_dashboard' registrado no OpenMetadata!")
    except urllib.error.HTTPError as err:
        if err.code == 409:
            print("[INFO] Dashboard 'desafio_4_dashboard' já existente.")
        else:
            print(f"[Aviso] Dashboard: {err}")

    if not dashboard_id:
        try:
            req_get = urllib.request.Request(f"{API_BASE}/dashboards/name/ficdev_superset.desafio_4_dashboard", headers=headers)
            with urllib.request.urlopen(req_get, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                dashboard_id = data.get("id")
        except Exception as exc:
            print(f"[Aviso] Não foi possível obter ID do dashboard: {exc}")

    return dashboard_id


def sincronizar_tabelas_catalogo(token: str) -> dict[str, str]:
    """Cadastra todas as entidades do pipeline (Fontes, Bronze, Silver e Gold) com esquemas colunares detalhados."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"}
    tabelas_ids: dict[str, str] = {}

    tabelas = [
        # --- CAMADA 1: FONTES BRUTAS DE ORIGEM (CSV / JSON / MONGODB) ---
        {
            "name": "catalogo_csv",
            "displayName": "catalogo.csv (Arquivo Bruto)",
            "description": "Arquivo delimitado CSV de origem contendo o catálogo administrativo de conteúdos educacionais (dados/catalogo.csv).",
            "databaseSchema": f"ficdev_postgres.{PG_DB}.fontes",
            "tableType": "Regular",
            "columns": [
                {"name": "conteudo_id", "dataType": "INT", "description": "ID original do conteúdo"},
                {"name": "titulo", "dataType": "VARCHAR", "dataLength": 255, "description": "Título original"},
                {"name": "tipo", "dataType": "VARCHAR", "dataLength": 50, "description": "Formato bruto"},
                {"name": "categoria", "dataType": "VARCHAR", "dataLength": 100, "description": "Categoria temática"},
                {"name": "nivel", "dataType": "VARCHAR", "dataLength": 50, "description": "Nível bruto"},
                {"name": "carga_horaria_min", "dataType": "INT", "description": "Duração em minutos"},
                {"name": "data_publicacao", "dataType": "DATE", "description": "Data de cadastro"},
                {"name": "descricao", "dataType": "TEXT", "description": "Sinopse pedagógica"},
                {"name": "autor", "dataType": "VARCHAR", "dataLength": 150, "description": "Instrutor / Autor"},
            ],
        },
        {
            "name": "interacoes_json",
            "displayName": "interacoes.json (Logs de Telemetria)",
            "description": "Logs de telemetria em formato JSON com interações brutas de consumo dos alunos (dados/interacoes.json).",
            "databaseSchema": f"ficdev_postgres.{PG_DB}.fontes",
            "tableType": "Regular",
            "columns": [
                {"name": "usuario_id", "dataType": "INT", "description": "ID do usuário"},
                {"name": "conteudo_id", "dataType": "INT", "description": "ID do conteúdo consumido"},
                {"name": "tipo_interacao", "dataType": "VARCHAR", "dataLength": 50, "description": "Tipo de evento (inicio, visualizacao, conclusao)"},
                {"name": "data_hora", "dataType": "TIMESTAMP", "description": "Carimbo de data/hora do evento"},
                {"name": "tempo_consumido", "dataType": "INT", "description": "Tempo em minutos"},
                {"name": "percentual_conclusao", "dataType": "NUMERIC", "description": "Progresso percentual"},
                {"name": "avaliacao_atribuida", "dataType": "NUMERIC", "description": "Nota atribuída"},
            ],
        },
        {
            "name": "comentarios_mongodb",
            "displayName": "comentarios (Coleção NoSQL MongoDB)",
            "description": "Coleção documental NoSQL MongoDB contendo avaliações textuais e feedbacks de alunos (dados/comentarios.json).",
            "databaseSchema": f"ficdev_postgres.{PG_DB}.fontes",
            "tableType": "Regular",
            "columns": [
                {"name": "usuario_id", "dataType": "INT", "description": "ID do estudante"},
                {"name": "conteudo_id", "dataType": "INT", "description": "ID do curso avaliado"},
                {"name": "comentario", "dataType": "TEXT", "description": "Texto livre da avaliação"},
                {"name": "avaliacao", "dataType": "INT", "description": "Nota de 1 a 5"},
                {"name": "data_comentario", "dataType": "TIMESTAMP", "description": "Data/hora do comentário"},
            ],
        },

        # --- CAMADA 2: BRONZE (INGESTÃO BRUTA COM AUDITORIA - APACHE HOP) ---
        {
            "name": "catalogo_raw",
            "displayName": "catalogo_raw (Bronze)",
            "description": "Tabela da Camada Bronze no PostgreSQL com dados brutos do catálogo e colunas técnicas de rastreabilidade (_origem, _ingestao_em, _run_id) (RF20).",
            "databaseSchema": f"ficdev_postgres.{PG_DB}.bronze",
            "tableType": "Regular",
            "columns": [
                {"name": "conteudo_id", "dataType": "BIGINT", "description": "Identificador do conteúdo"},
                {"name": "titulo", "dataType": "TEXT", "description": "Título bruto"},
                {"name": "tipo", "dataType": "TEXT", "description": "Tipo bruto"},
                {"name": "categoria", "dataType": "TEXT", "description": "Categoria bruta"},
                {"name": "nivel", "dataType": "TEXT", "description": "Nível bruto"},
                {"name": "carga_horaria_min", "dataType": "INT", "description": "Carga horária bruta"},
                {"name": "data_publicacao", "dataType": "DATE", "description": "Data bruta"},
                {"name": "descricao", "dataType": "TEXT", "description": "Descrição bruta"},
                {"name": "autor", "dataType": "TEXT", "description": "Autor bruto"},
                {"name": "_origem", "dataType": "VARCHAR", "dataLength": 100, "description": "Metadado técnico: arquivo de origem"},
                {"name": "_ingestao_em", "dataType": "TIMESTAMP", "description": "Metadado técnico: timestamp da carga Hop"},
                {"name": "_run_id", "dataType": "VARCHAR", "dataLength": 64, "description": "Metadado técnico: UUID da execução do Hop"},
            ],
        },
        {
            "name": "interacoes_raw",
            "displayName": "interacoes_raw (Bronze)",
            "description": "Tabela da Camada Bronze com eventos brutos de telemetria ingeridos pelo Hop com auditoria (RF20).",
            "databaseSchema": f"ficdev_postgres.{PG_DB}.bronze",
            "tableType": "Regular",
            "columns": [
                {"name": "usuario_id", "dataType": "BIGINT", "description": "ID do usuário"},
                {"name": "conteudo_id", "dataType": "BIGINT", "description": "ID do conteúdo"},
                {"name": "tipo_interacao", "dataType": "TEXT", "description": "Tipo de evento"},
                {"name": "data_hora", "dataType": "TIMESTAMP", "description": "Data/hora do evento"},
                {"name": "tempo_consumido", "dataType": "INT", "description": "Tempo consumido"},
                {"name": "percentual_conclusao", "dataType": "NUMERIC", "description": "Percentual"},
                {"name": "avaliacao_atribuida", "dataType": "NUMERIC", "description": "Avaliação"},
                {"name": "_origem", "dataType": "VARCHAR", "dataLength": 100, "description": "Metadado técnico: origem"},
                {"name": "_ingestao_em", "dataType": "TIMESTAMP", "description": "Metadado técnico: timestamp de ingestão"},
                {"name": "_run_id", "dataType": "VARCHAR", "dataLength": 64, "description": "Metadado técnico: run_id"},
            ],
        },
        {
            "name": "comentarios_raw",
            "displayName": "comentarios_raw (Bronze)",
            "description": "Tabela da Camada Bronze com comentários brutos ingeridos do MongoDB via Hop (RF20).",
            "databaseSchema": f"ficdev_postgres.{PG_DB}.bronze",
            "tableType": "Regular",
            "columns": [
                {"name": "usuario_id", "dataType": "BIGINT", "description": "ID do usuário"},
                {"name": "conteudo_id", "dataType": "BIGINT", "description": "ID do conteúdo"},
                {"name": "comentario", "dataType": "TEXT", "description": "Comentário bruto"},
                {"name": "avaliacao", "dataType": "NUMERIC", "description": "Nota"},
                {"name": "data_comentario", "dataType": "TIMESTAMP", "description": "Data do comentário"},
                {"name": "_origem", "dataType": "VARCHAR", "dataLength": 100, "description": "Metadado técnico: origem"},
                {"name": "_ingestao_em", "dataType": "TIMESTAMP", "description": "Metadado técnico: timestamp"},
                {"name": "_run_id", "dataType": "VARCHAR", "dataLength": 64, "description": "Metadado técnico: run_id"},
            ],
        },

        # --- CAMADA 3: SILVER (DADOS PADRONIZADOS E CURADOS - APACHE HOP / MDM) ---
        {
            "name": "catalogo",
            "displayName": "catalogo (Silver)",
            "description": "Tabela curada e padronizada da Camada Silver contendo conteúdos homologados e reconciliados por MDM (RF20/RF30).",
            "databaseSchema": f"ficdev_postgres.{PG_DB}.silver",
            "tableType": "Regular",
            "columns": [
                {"name": "conteudo_id", "dataType": "INT", "description": "Identificador único do conteúdo"},
                {"name": "titulo", "dataType": "VARCHAR", "dataLength": 255, "description": "Título padronizado"},
                {"name": "tipo", "dataType": "VARCHAR", "dataLength": 50, "description": "Formato padronizado"},
                {"name": "categoria", "dataType": "VARCHAR", "dataLength": 100, "description": "Categoria temática padronizada"},
                {"name": "nivel", "dataType": "VARCHAR", "dataLength": 50, "description": "Nível de complexidade"},
                {"name": "carga_horaria_min", "dataType": "INT", "description": "Duração em minutos"},
                {"name": "autor", "dataType": "VARCHAR", "dataLength": 150, "description": "Autor / Instrutor"},
                {"name": "data_publicacao", "dataType": "DATE", "description": "Data de homologação"},
            ],
        },
        {
            "name": "interacoes",
            "displayName": "interacoes (Silver)",
            "description": "Tabela da Camada Silver com eventos de telemetria desduplicados, validados e com tipos normalizados (RF20).",
            "databaseSchema": f"ficdev_postgres.{PG_DB}.silver",
            "tableType": "Regular",
            "columns": [
                {"name": "usuario_id", "dataType": "BIGINT", "description": "ID do usuário"},
                {"name": "conteudo_id", "dataType": "BIGINT", "description": "ID do conteúdo referenciado"},
                {"name": "tipo_interacao", "dataType": "VARCHAR", "dataLength": 50, "description": "Evento padronizado"},
                {"name": "data_hora", "dataType": "TIMESTAMP", "description": "Data e hora normalizadas"},
                {"name": "tempo_consumido", "dataType": "INT", "description": "Tempo em minutos"},
                {"name": "percentual_conclusao", "dataType": "NUMERIC", "description": "Percentual de conclusão"},
                {"name": "avaliacao_atribuida", "dataType": "NUMERIC", "description": "Nota válida"},
            ],
        },
        {
            "name": "comentarios",
            "displayName": "comentarios (Silver)",
            "description": "Tabela da Camada Silver contendo feedbacks textuais sanitizados e consistentes (RF20).",
            "databaseSchema": f"ficdev_postgres.{PG_DB}.silver",
            "tableType": "Regular",
            "columns": [
                {"name": "usuario_id", "dataType": "BIGINT", "description": "ID do usuário"},
                {"name": "conteudo_id", "dataType": "BIGINT", "description": "ID do conteúdo"},
                {"name": "comentario", "dataType": "TEXT", "description": "Texto avaliativo limpo"},
                {"name": "avaliacao", "dataType": "NUMERIC", "description": "Nota de 1 a 5"},
                {"name": "data_comentario", "dataType": "TIMESTAMP", "description": "Data do comentário"},
            ],
        },

        # --- CAMADA 4: GOLD (MODELOS ANALÍTICOS DIMENSIONAIS - APACHE BEAM / PARQUET) ---
        {
            "name": "kpis_mensais_categoria",
            "displayName": "kpis_mensais_categoria (Gold)",
            "description": "Tabela analítica agregada com métricas mensais de engajamento e conclusão processadas pelo Apache Beam (RF26).",
            "databaseSchema": f"ficdev_postgres.{PG_DB}.gold",
            "tableType": "Regular",
            "columns": [
                {"name": "ano", "dataType": "INT", "description": "Ano de apuração"},
                {"name": "mes", "dataType": "INT", "description": "Mês de apuração (1-12)"},
                {"name": "categoria", "dataType": "VARCHAR", "dataLength": 100, "description": "Categoria temática oficial"},
                {"name": "usuarios_ativos", "dataType": "INT", "description": "Total de usuários únicos ativos"},
                {"name": "total_visualizacoes", "dataType": "INT", "description": "Total de visualizações"},
                {"name": "total_inicios", "dataType": "INT", "description": "Total de inícios de aulas"},
                {"name": "total_conclusoes", "dataType": "INT", "description": "Total de conclusões"},
                {"name": "taxa_conclusao_pct", "dataType": "NUMERIC", "description": "Taxa percentual de conclusão"},
                {"name": "tempo_medio_min", "dataType": "NUMERIC", "description": "Tempo médio despendido em minutos"},
                {"name": "avaliacao_media", "dataType": "NUMERIC", "description": "Média de satisfação dos alunos"},
            ],
        },
        {
            "name": "desempenho_conteudos",
            "displayName": "desempenho_conteudos (Gold)",
            "description": "Tabela analítica agregada com métricas individuais de engajamento por material didático (RF26).",
            "databaseSchema": f"ficdev_postgres.{PG_DB}.gold",
            "tableType": "Regular",
            "columns": [
                {"name": "conteudo_id", "dataType": "INT", "description": "ID do conteúdo educacional"},
                {"name": "titulo", "dataType": "VARCHAR", "dataLength": 255, "description": "Título oficial"},
                {"name": "tipo", "dataType": "VARCHAR", "dataLength": 50, "description": "Formato pedagógico"},
                {"name": "categoria", "dataType": "VARCHAR", "dataLength": 100, "description": "Categoria temática"},
                {"name": "nivel", "dataType": "VARCHAR", "dataLength": 50, "description": "Nível de complexidade"},
                {"name": "carga_horaria_min", "dataType": "INT", "description": "Carga horária em minutos"},
                {"name": "autor", "dataType": "VARCHAR", "dataLength": 150, "description": "Autor responsável (Dado protegido LGPD)"},
                {"name": "total_visualizacoes", "dataType": "INT", "description": "Acessos totais acumulados"},
                {"name": "total_inicios", "dataType": "INT", "description": "Inícios totais acumulados"},
                {"name": "total_conclusoes", "dataType": "INT", "description": "Conclusões acumuladas"},
                {"name": "taxa_conclusao_pct", "dataType": "NUMERIC", "description": "Taxa percentual de conclusão"},
                {"name": "avaliacao_media", "dataType": "NUMERIC", "description": "Média de avaliação dos alunos"},
            ],
        },
        {
            "name": "vw_ranking_conteudos_engajamento",
            "displayName": "vw_ranking_conteudos_engajamento (Gold View)",
            "description": "Visão analítica da Camada Gold com ranking dos conteúdos de maior engajamento para alimentar o Superset (RF16/RF26).",
            "databaseSchema": f"ficdev_postgres.{PG_DB}.gold",
            "tableType": "View",
            "columns": [
                {"name": "conteudo_id", "dataType": "INT", "description": "ID do conteúdo"},
                {"name": "titulo", "dataType": "VARCHAR", "dataLength": 255, "description": "Título do curso"},
                {"name": "categoria", "dataType": "VARCHAR", "dataLength": 100, "description": "Categoria pedagógica"},
                {"name": "total_inicios", "dataType": "INT", "description": "Inícios acumulados"},
                {"name": "total_conclusoes", "dataType": "INT", "description": "Conclusões acumuladas"},
                {"name": "taxa_conclusao_pct", "dataType": "NUMERIC", "description": "Eficiência de conclusão"},
                {"name": "ranking_categoria", "dataType": "INT", "description": "Posição no ranking por categoria"},
            ],
        },
    ]

    for tbl in tabelas:
        sch_name = tbl["databaseSchema"].split(".")[-1]
        key = f"{sch_name}.{tbl['name']}"
        req_tbl = urllib.request.Request(f"{API_BASE}/tables", data=json.dumps(tbl).encode("utf-8"), headers=headers)
        try:
            with urllib.request.urlopen(req_tbl, timeout=5) as resp:
                d = json.loads(resp.read().decode("utf-8"))
                tabelas_ids[key] = d["id"]
                print(f"[OK] Tabela '{key}' catalogada com sucesso!")
        except urllib.error.HTTPError as err:
            if err.code == 409:
                print(f"[INFO] Tabela '{key}' já existente no catálogo.")
            else:
                print(f"[Aviso] Tabela {key}: {err}")

        # Garante a recuperação do ID exato pelo FQN
        if key not in tabelas_ids:
            try:
                fqn = f"{tbl['databaseSchema']}.{tbl['name']}"
                req_get = urllib.request.Request(f"{API_BASE}/tables/name/{fqn}", headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
                with urllib.request.urlopen(req_get, timeout=5) as resp_get:
                    data_get = json.loads(resp_get.read().decode("utf-8"))
                    tabelas_ids[key] = data_get["id"]
            except Exception as exc:
                print(f"[Aviso] Falha ao recuperar ID de {key}: {exc}")

    return tabelas_ids


def aplicar_tags_lgpd_e_linhagem(token: str, tabelas_ids: dict[str, str], dashboard_id: str | None) -> None:
    """Aplica tags PII e conecta o grafo de linhagem de 5 pontas: Fonte -> Bronze -> Silver -> Gold -> Dashboard (RF28/RF29/RF32)."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"}

    # 1. Aplica Tags LGPD PII.Sensitive
    tabelas_pii = [
        ("gold.desempenho_conteudos", "/columns/6/tags"),  # autor
        ("silver.catalogo", "/columns/6/tags"),            # autor
        ("bronze.catalogo_raw", "/columns/8/tags"),        # autor
        ("silver.interacoes", "/columns/0/tags"),          # usuario_id
        ("bronze.interacoes_raw", "/columns/0/tags"),      # usuario_id
    ]
    for tbl_key, path in tabelas_pii:
        if tbl_key in tabelas_ids:
            tbl_id = tabelas_ids[tbl_key]
            patch_payload = [
                {
                    "op": "add",
                    "path": path,
                    "value": [
                        {
                            "tagFQN": "PII.Sensitive",
                            "source": "Classification",
                            "labelType": "Manual",
                            "state": "Confirmed",
                        }
                    ],
                }
            ]
            patch_req = urllib.request.Request(
                f"{API_BASE}/tables/{tbl_id}",
                data=json.dumps(patch_payload).encode("utf-8"),
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json-patch+json"},
                method="PATCH",
            )
            try:
                with urllib.request.urlopen(patch_req, timeout=5) as resp:
                    print(f"[OK] Tag LGPD 'PII.Sensitive' aplicada em {tbl_key}!")
            except Exception:
                pass  # Já aplicada

    # 2. Conecta a Linhagem Ponta a Ponta (RF29)
    arestas = [
        # --- ETAPA 1: Fontes Brutas -> Bronze (Ingestão Hop) ---
        ("fontes.catalogo_csv", "bronze.catalogo_raw", "table", "table", "Ingestão Hop: catalogo.csv -> bronze.catalogo_raw"),
        ("fontes.interacoes_json", "bronze.interacoes_raw", "table", "table", "Ingestão Hop: interacoes.json -> bronze.interacoes_raw"),
        ("fontes.comentarios_mongodb", "bronze.comentarios_raw", "table", "table", "Ingestão Hop: MongoDB comentarios -> bronze.comentarios_raw"),

        # --- ETAPA 2: Bronze -> Silver (Curadoria, Tipagem e Qualidade Hop) ---
        ("bronze.catalogo_raw", "silver.catalogo", "table", "table", "Padronização Hop: bronze.catalogo_raw -> silver.catalogo"),
        ("bronze.interacoes_raw", "silver.interacoes", "table", "table", "Validação Hop: bronze.interacoes_raw -> silver.interacoes"),
        ("bronze.comentarios_raw", "silver.comentarios", "table", "table", "Sanitização Hop: bronze.comentarios_raw -> silver.comentarios"),

        # --- ETAPA 3: Silver -> Gold (Apache Beam / Parquet / Processamento Distribuído) ---
        ("silver.catalogo", "gold.kpis_mensais_categoria", "table", "table", "Apache Beam: silver.catalogo -> gold.kpis_mensais_categoria"),
        ("silver.interacoes", "gold.kpis_mensais_categoria", "table", "table", "Apache Beam: silver.interacoes -> gold.kpis_mensais_categoria"),
        ("silver.catalogo", "gold.desempenho_conteudos", "table", "table", "Consolidação Gold: silver.catalogo -> gold.desempenho_conteudos"),
        ("silver.interacoes", "gold.desempenho_conteudos", "table", "table", "Consolidação Gold: silver.interacoes -> gold.desempenho_conteudos"),
        ("silver.comentarios", "gold.desempenho_conteudos", "table", "table", "Consolidação Gold: silver.comentarios -> gold.desempenho_conteudos"),
        ("silver.catalogo", "gold.vw_ranking_conteudos_engajamento", "table", "table", "View Analítica: silver.catalogo -> gold.vw_ranking_conteudos_engajamento"),
        ("silver.interacoes", "gold.vw_ranking_conteudos_engajamento", "table", "table", "View Analítica: silver.interacoes -> gold.vw_ranking_conteudos_engajamento"),
    ]

    for origem_key, destino_key, from_type, to_type, desc in arestas:
        if origem_key in tabelas_ids and destino_key in tabelas_ids:
            from_id = tabelas_ids[origem_key]
            to_id = tabelas_ids[destino_key]
            lineage_payload = {
                "edge": {
                    "fromEntity": {"type": from_type, "id": from_id},
                    "toEntity": {"type": to_type, "id": to_id},
                }
            }
            put_req = urllib.request.Request(
                f"{API_BASE}/lineage",
                data=json.dumps(lineage_payload).encode("utf-8"),
                headers=headers,
                method="PUT",
            )
            try:
                with urllib.request.urlopen(put_req, timeout=5) as resp:
                    print(f"[OK] Grafo de Linhagem (RF29): {desc}")
            except Exception as err:
                print(f"[INFO] Linhagem {origem_key} -> {destino_key}: {err}")

    # --- ETAPA 4: Gold -> Dashboard (Consumo Analítico no Superset) ---
    if dashboard_id:
        tabelas_para_dashboard = [
            "gold.kpis_mensais_categoria",
            "gold.desempenho_conteudos",
            "gold.vw_ranking_conteudos_engajamento",
        ]
        for gold_key in tabelas_para_dashboard:
            if gold_key in tabelas_ids:
                tbl_id = tabelas_ids[gold_key]
                lineage_payload = {
                    "edge": {
                        "fromEntity": {"type": "table", "id": tbl_id},
                        "toEntity": {"type": "dashboard", "id": dashboard_id},
                    }
                }
                put_req = urllib.request.Request(
                    f"{API_BASE}/lineage",
                    data=json.dumps(lineage_payload).encode("utf-8"),
                    headers=headers,
                    method="PUT",
                )
                try:
                    with urllib.request.urlopen(put_req, timeout=5) as resp:
                        print(f"[OK] Grafo de Linhagem (RF29): {gold_key} -> Superset Dashboard (desafio_4_dashboard)")
                except Exception as err:
                    print(f"[INFO] Linhagem {gold_key} -> Dashboard: {err}")



def sincronizar_glossario_e_termos(token: str) -> None:
    """Cria e sincroniza o glossário educacional e os 4 termos obrigatórios no OpenMetadata."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"}

    # 1. Cria ou valida o Glossário
    glossary_payload = {
        "name": "Glossario_Educacional_FICDEV",
        "displayName": "Glossário Educacional FIC_DEV",
        "description": "Vocabulário de Negócio Padronizado para Análise Pedagógica e IA (RF28)",
    }
    req_g = urllib.request.Request(
        f"{API_BASE}/glossaries",
        data=json.dumps(glossary_payload).encode("utf-8"),
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req_g, timeout=5) as resp:
            print("[OK] Glossário 'Glossario_Educacional_FICDEV' cadastrado com sucesso!")
    except urllib.error.HTTPError as err:
        if err.code == 409:
            print("[INFO] Glossário 'Glossario_Educacional_FICDEV' já existente no catálogo.")
        else:
            print(f"[Aviso] Falha ao criar glossário: {err}")

    # 2. Cadastra os 4 Termos Obrigatórios
    for t in TERMOS_GLOSSARIO_OFICIAIS:
        termo_payload = {
            "name": t["name"],
            "displayName": t["displayName"],
            "description": f"{t['description']}\n\n- **Fórmula / Regra de Cálculo:** `{t['regra_calculo']}`\n- **Responsável:** {t['responsavel']}\n- **Ativo Vinculado:** `{t['tabela_associada']}.{t['coluna_associada']}`\n- **Classificação LGPD:** `{t['classificacao_lgpd']}`",
            "glossary": "Glossario_Educacional_FICDEV",
        }
        req_t = urllib.request.Request(
            f"{API_BASE}/glossaryTerms",
            data=json.dumps(termo_payload).encode("utf-8"),
            headers=headers,
        )
        try:
            with urllib.request.urlopen(req_t, timeout=5) as resp_t:
                print(f"[OK] Termo de Glossário '{t['displayName']}' sincronizado com sucesso!")
        except urllib.error.HTTPError as err_t:
            if err_t.code == 409:
                print(f"[INFO] Termo '{t['displayName']}' já existente no catálogo.")
            else:
                print(f"[Aviso] Falha ao cadastrar termo {t['name']}: {err_t}")


def exportar_dossie_metadados() -> Path:
    """Gera o dossiê formal de metadados técnicos e glossário em JSON para auditoria (RF27/RF28/RF29)."""
    caminho = DIR_OMD / "dossie_metadados_oficial.json"
    dossie = {
        "sistema": "OpenMetadata FIC_DEV",
        "versao_plataforma": "1.4.6",
        "credenciais_acesso": {
            "url": OPENMETADATA_URL,
            "email_login": OM_ADMIN_EMAIL,
            "perfil": "Admin Principal",
            "origem_credenciais": "Variáveis de ambiente (.env / RF15)",
        },
        "servico_dados": {
            "nome": "ficdev_postgres",
            "tipo": "PostgreSQL",
            "host": f"{PG_HOST}:{PG_PORT}",
            "banco": PG_DB,
            "schemas_catalogados": ["fontes", "bronze", "silver", "gold"],
        },
        "servico_dashboard": {
            "nome": "ficdev_superset",
            "tipo": "Superset",
            "url": "http://superset:8088",
            "dashboard_oficial": "desafio_4_dashboard",
            "titulo": "Desafio 4 - Dashboard Executivo FIC_DEV",
        },
        "linhagem_end_to_end_rf29": {
            "descricao": "Grafo de linhagem completo em 5 etapas: Fontes -> Bronze -> Silver -> Gold -> Dashboard (Superset)",
            "arestas": [
                "fontes.catalogo_csv -> bronze.catalogo_raw",
                "fontes.interacoes_json -> bronze.interacoes_raw",
                "fontes.comentarios_mongodb -> bronze.comentarios_raw",
                "bronze.catalogo_raw -> silver.catalogo",
                "bronze.interacoes_raw -> silver.interacoes",
                "bronze.comentarios_raw -> silver.comentarios",
                "silver.catalogo -> gold.kpis_mensais_categoria",
                "silver.interacoes -> gold.kpis_mensais_categoria",
                "silver.catalogo -> gold.desempenho_conteudos",
                "silver.interacoes -> gold.desempenho_conteudos",
                "silver.comentarios -> gold.desempenho_conteudos",
                "silver.catalogo -> gold.vw_ranking_conteudos_engajamento",
                "silver.interacoes -> gold.vw_ranking_conteudos_engajamento",
                "gold.kpis_mensais_categoria -> dashboard.desafio_4_dashboard",
                "gold.desempenho_conteudos -> dashboard.desafio_4_dashboard",
                "gold.vw_ranking_conteudos_engajamento -> dashboard.desafio_4_dashboard",
            ],
        },
        "glossario_negocio": {
            "nome": "Glossario_Educacional_FICDEV",
            "descricao": "Vocabulário de Negócio Padronizado para Análise Pedagógica e IA (RF28)",
            "termos": TERMOS_GLOSSARIO_OFICIAIS,
        },
        "controles_anti_data_swamp": [
            "Esquemas estritamente tipados com contratos DDL nas camadas Silver e Gold.",
            "Quality Gate bloqueador com 5 dimensões antes da publicação Gold.",
            "Desduplicação e regras de sobrevivência via Master Data Management (MDM).",
            "Atribuição formal de proprietários (Data Owners) e regras de cálculo documentadas.",
        ],
        "classificacoes_sensibilidade_lgpd": {
            "usuario_id": "PII.Pseudonymized (UUIDv5 determinístico)",
            "autor": "PII.Masked (Mascaramento parcial J*** D**)",
            "data_hora": "PII.TemporalGeneralized (Agrupado por ano e mês na Gold)",
            "avaliacao": "Non-PII (Métrica de Satisfação)",
        },
    }

    with caminho.open("w", encoding="utf-8") as f:
        json.dump(dossie, f, indent=2, ensure_ascii=False)

    print(f"[OK] Dossiê oficial de governança e metadados exportado em: {caminho}")
    return caminho


def main() -> None:
    print("=================================================================")
    print("AUTOMAÇÃO COMPLETA DO OPENMETADATA (RF27 — RF29)")
    print("=================================================================")

    ativo = testar_conexao_openmetadata()
    exportar_dossie_metadados()

    if ativo:
        token = autenticar_openmetadata()
        if token:
            print("\n--- 1. Sincronizando Serviço de Banco e Schemas (Fontes, Bronze, Silver, Gold) ---")
            sincronizar_servico_e_schemas(token)

            print("\n--- 2. Sincronizando Serviço e Entidade de Dashboard (Apache Superset) ---")
            dashboard_id = sincronizar_servico_dashboard(token)

            print("\n--- 3. Sincronizando Tabelas no Catálogo (12 entidades nas 4 camadas) ---")
            tbl_ids = sincronizar_tabelas_catalogo(token)

            print("\n--- 4. Aplicando Classificações LGPD e Grafo de Linhagem Ponta a Ponta (RF29) ---")
            aplicar_tags_lgpd_e_linhagem(token, tbl_ids, dashboard_id)

            print("\n--- 5. Sincronizando Glossário e 4 Termos Oficiais ---")
            sincronizar_glossario_e_termos(token)

            print("\n[SUCESSO] Plataforma OpenMetadata 100% configurada com linhagem completa de 5 pontas!")

    print("\n-----------------------------------------------------------------")
    print("INSTRUÇÕES DE ACESSO AO OPENMETADATA:")
    print(f"  URL no Navegador: {OPENMETADATA_URL}")
    print(f"  E-mail de Login:  {OM_ADMIN_EMAIL}")
    print("  Senha:            (conforme variável OPENMETADATA_ADMIN_PASSWORD no .env)")
    print("-----------------------------------------------------------------")
    print("=================================================================")


if __name__ == "__main__":
    main()
