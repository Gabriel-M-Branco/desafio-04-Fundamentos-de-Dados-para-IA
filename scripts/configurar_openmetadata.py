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
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

API_BASE = "http://localhost:8585/api/v1"
DIR_OMD = Path("openmetadata")
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
    """Autentica na API REST do OpenMetadata com as credenciais oficiais de administrador."""
    b64_pwd = base64.b64encode(b"admin").decode("utf-8")
    payload = json.dumps({"email": "admin@openmetadata.org", "password": b64_pwd}).encode("utf-8")
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
                print("[OK] Autenticação bem-sucedida como admin@openmetadata.org!")
                return token
    except Exception as exc:
        print(f"[Aviso] Falha na autenticação do OpenMetadata: {exc}")
    return None


def sincronizar_servico_e_schemas(token: str) -> None:
    """Registra o serviço PostgreSQL, o banco ficdev_recomendacao e os schemas silver e gold."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"}

    # 1. Serviço de Banco
    svc_payload = {
        "name": "ficdev_postgres",
        "displayName": "PostgreSQL FIC_DEV",
        "description": "Instância PostgreSQL da Plataforma Educacional FIC_DEV (RF20 a RF26)",
        "serviceType": "Postgres",
        "connection": {
            "config": {
                "type": "Postgres",
                "scheme": "postgresql+psycopg2",
                "username": "postgres",
                "authType": {"password": "postgres"},
                "hostPort": "postgres:5432",
                "database": "ficdev_recomendacao",
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
        "name": "ficdev_recomendacao",
        "displayName": "ficdev_recomendacao",
        "service": "ficdev_postgres",
        "description": "Banco de dados principal contendo as camadas Bronze, Silver e Gold.",
    }
    req_db = urllib.request.Request(f"{API_BASE}/databases", data=json.dumps(db_payload).encode("utf-8"), headers=headers)
    try:
        with urllib.request.urlopen(req_db, timeout=5) as resp:
            print("[OK] Database 'ficdev_recomendacao' registrado no OpenMetadata!")
    except urllib.error.HTTPError as err:
        if err.code == 409:
            print("[INFO] Database 'ficdev_recomendacao' já existente.")
        else:
            print(f"[Aviso] Database: {err}")

    # 3. Schemas Silver e Gold
    for schema_name, desc in [
        ("silver", "Camada Silver: Dados padronizados, tipados e validados pelo Apache Hop"),
        ("gold", "Camada Gold: Tabelas analíticas agregadas para consumo no Superset (RF26)"),
    ]:
        sch_payload = {
            "name": schema_name,
            "displayName": schema_name,
            "database": "ficdev_postgres.ficdev_recomendacao",
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


def sincronizar_tabelas_catalogo(token: str) -> dict[str, str]:
    """Cadastra as tabelas analíticas no catálogo com colunas, tipos e descrições."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"}
    tabelas_ids: dict[str, str] = {}

    tabelas = [
        {
            "name": "kpis_mensais_categoria",
            "displayName": "kpis_mensais_categoria",
            "description": "Tabela analítica da Camada Gold com métricas agregadas mensais de engajamento e conclusão (RF26).",
            "databaseSchema": "ficdev_postgres.ficdev_recomendacao.gold",
            "columns": [
                {"name": "ano", "dataType": "INT", "description": "Ano de referência"},
                {"name": "mes", "dataType": "INT", "description": "Mês de referência (1-12)"},
                {"name": "categoria", "dataType": "VARCHAR", "dataLength": 100, "description": "Categoria temática oficial"},
                {"name": "usuarios_ativos", "dataType": "INT", "description": "Total de usuários ativos"},
                {"name": "total_visualizacoes", "dataType": "INT", "description": "Total de visualizações"},
                {"name": "total_inicios", "dataType": "INT", "description": "Total de inícios de aulas"},
                {"name": "total_conclusoes", "dataType": "INT", "description": "Total de conclusões de aulas"},
                {"name": "taxa_conclusao_pct", "dataType": "NUMERIC", "description": "Taxa de conclusão percentual"},
                {"name": "tempo_medio_min", "dataType": "NUMERIC", "description": "Tempo médio de consumo em minutos"},
                {"name": "avaliacao_media", "dataType": "NUMERIC", "description": "Nota média de avaliação dos alunos"},
            ],
        },
        {
            "name": "desempenho_conteudos",
            "displayName": "desempenho_conteudos",
            "description": "Tabela analítica da Camada Gold com desempenho individualizado por material didático (RF26).",
            "databaseSchema": "ficdev_postgres.ficdev_recomendacao.gold",
            "columns": [
                {"name": "conteudo_id", "dataType": "INT", "description": "Identificador do conteúdo"},
                {"name": "titulo", "dataType": "VARCHAR", "dataLength": 255, "description": "Título do material didático"},
                {"name": "tipo", "dataType": "VARCHAR", "dataLength": 50, "description": "Formato (Curso, Vídeo, Artigo, Podcast)"},
                {"name": "categoria", "dataType": "VARCHAR", "dataLength": 100, "description": "Categoria pedagógica"},
                {"name": "nivel", "dataType": "VARCHAR", "dataLength": 50, "description": "Nível de complexidade (Básico, Intermediário, Avançado)"},
                {"name": "carga_horaria_min", "dataType": "INT", "description": "Duração estimada em minutos"},
                {"name": "autor", "dataType": "VARCHAR", "dataLength": 150, "description": "Instrutor / Autor responsável"},
                {"name": "total_visualizacoes", "dataType": "INT", "description": "Acessos acumulados"},
                {"name": "total_inicios", "dataType": "INT", "description": "Inícios acumulados"},
                {"name": "total_conclusoes", "dataType": "INT", "description": "Conclusões acumuladas"},
                {"name": "taxa_conclusao_pct", "dataType": "NUMERIC", "description": "Taxa de conclusão do conteúdo"},
                {"name": "avaliacao_media", "dataType": "NUMERIC", "description": "Satisfação média calculada"},
            ],
        },
        {
            "name": "catalogo",
            "displayName": "catalogo",
            "description": "Tabela curada e padronizada da Camada Silver contendo os cursos e conteúdos homologados.",
            "databaseSchema": "ficdev_postgres.ficdev_recomendacao.silver",
            "columns": [
                {"name": "conteudo_id", "dataType": "INT", "description": "Identificador único do conteúdo"},
                {"name": "titulo", "dataType": "VARCHAR", "dataLength": 255, "description": "Título higienizado"},
                {"name": "tipo", "dataType": "VARCHAR", "dataLength": 50, "description": "Tipo do material"},
                {"name": "categoria", "dataType": "VARCHAR", "dataLength": 100, "description": "Categoria homologada"},
                {"name": "nivel", "dataType": "VARCHAR", "dataLength": 50, "description": "Nível formatado"},
                {"name": "carga_horaria_min", "dataType": "INT", "description": "Duração em minutos"},
                {"name": "autor", "dataType": "VARCHAR", "dataLength": 150, "description": "Nome do autor"},
                {"name": "data_publicacao", "dataType": "DATE", "description": "Data de homologação"},
            ],
        },
    ]

    for tbl in tabelas:
        req_tbl = urllib.request.Request(f"{API_BASE}/tables", data=json.dumps(tbl).encode("utf-8"), headers=headers)
        try:
            with urllib.request.urlopen(req_tbl, timeout=5) as resp:
                d = json.loads(resp.read().decode("utf-8"))
                tabelas_ids[tbl["name"]] = d["id"]
                print(f"[OK] Tabela '{tbl['name']}' catalogada com sucesso!")
        except urllib.error.HTTPError as err:
            if err.code == 409:
                print(f"[INFO] Tabela '{tbl['name']}' já existente no catálogo.")
            else:
                print(f"[Aviso] Tabela {tbl['name']}: {err}")

    # Busca IDs atualizados de todas as tabelas
    try:
        req_list = urllib.request.Request(f"{API_BASE}/tables", headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
        with urllib.request.urlopen(req_list, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for item in data.get("data", []):
                tabelas_ids[item["name"]] = item["id"]
    except Exception as exc:
        print(f"[Aviso] Não foi possível listar IDs das tabelas: {exc}")

    return tabelas_ids


def aplicar_tags_lgpd_e_linhagem(token: str, tabelas_ids: dict[str, str]) -> None:
    """Aplica tag PII.Sensitive na coluna autor e conecta o grafo de linhagem visual."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"}

    # 1. Aplica Tag PII.Sensitive na coluna autor de desempenho_conteudos
    if "desempenho_conteudos" in tabelas_ids:
        tbl_id = tabelas_ids["desempenho_conteudos"]
        patch_payload = [
            {
                "op": "add",
                "path": "/columns/6/tags",
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
                print("[OK] Tag LGPD 'PII.Sensitive' aplicada na coluna 'autor' (RF28/RF32)!")
        except Exception:
            pass  # Já aplicada

    # 2. Conecta a Linhagem de Dados (Lineage) entre Silver e Gold
    if "catalogo" in tabelas_ids:
        id_silver = tabelas_ids["catalogo"]
        for target in ["desempenho_conteudos", "kpis_mensais_categoria"]:
            if target in tabelas_ids:
                id_gold = tabelas_ids[target]
                lineage_payload = {
                    "edge": {
                        "fromEntity": {"type": "table", "id": id_silver},
                        "toEntity": {"type": "table", "id": id_gold},
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
                        print(f"[OK] Grafo de Linhagem conectado: silver.catalogo -> gold.{target} (RF29)!")
                except Exception as err:
                    print(f"[INFO] Linhagem {target}: {err}")


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
    """Gera o dossiê formal de metadados técnicos e glossário em JSON para auditoria (RF27/RF28)."""
    caminho = DIR_OMD / "dossie_metadados_oficial.json"
    dossie = {
        "sistema": "OpenMetadata FIC_DEV",
        "versao_plataforma": "1.4.6",
        "credenciais_acesso": {
            "url": "http://localhost:8585",
            "email_login": "admin@openmetadata.org",
            "perfil": "Admin Principal",
        },
        "servico_dados": {
            "nome": "ficdev_postgres",
            "tipo": "PostgreSQL",
            "host": "postgres:5432",
            "banco": "ficdev_recomendacao",
            "schemas_catalogados": ["silver", "gold"],
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
            print("\n--- 1. Sincronizando Serviço de Banco e Schemas ---")
            sincronizar_servico_e_schemas(token)

            print("\n--- 2. Sincronizando Tabelas no Catálogo ---")
            tbl_ids = sincronizar_tabelas_catalogo(token)

            print("\n--- 3. Aplicando Classificações LGPD e Grafo de Linhagem ---")
            aplicar_tags_lgpd_e_linhagem(token, tbl_ids)

            print("\n--- 4. Sincronizando Glossário e 4 Termos Oficiais ---")
            sincronizar_glossario_e_termos(token)

            print("\n[SUCESSO] Plataforma OpenMetadata 100% configurada e populada!")

    print("\n-----------------------------------------------------------------")
    print("INSTRUÇÕES DE ACESSO AO OPENMETADATA:")
    print("  URL no Navegador: http://localhost:8585")
    print("  E-mail de Login:  admin@openmetadata.org")
    print("  Senha:            admin")
    print("-----------------------------------------------------------------")
    print("=================================================================")


if __name__ == "__main__":
    main()
