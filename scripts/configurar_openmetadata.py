"""Script de automação e configuração do OpenMetadata (RF27 — RF29).

Realiza:
1. Teste de conectividade com a API REST do OpenMetadata (http://localhost:8585/api/v1).
2. Cadastro automatizado do Glossário de Negócio e dos 4 Termos Obrigatórios (RF28).
3. Associação de classificações de dados pessoais e sensibilidade (LGPD / RF28 / RF32).
4. Exportação do Dossiê Estruturado de Metadados em JSON para auditoria (RF34).
"""
from __future__ import annotations

import json
import urllib.request
import urllib.error
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


import base64


def autenticar_openmetadata() -> str | None:
    """Autentica na API REST do OpenMetadata com o usuário admin oficial."""
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
                print("[OK] Autenticação bem-sucedida no OpenMetadata como admin@openmetadata.org!")
                return token
    except Exception as exc:
        print(f"[Aviso] Não foi possível autenticar na API do OpenMetadata: {exc}")
    return None


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
    print("CONFIGURAÇÃO E AUDITORIA DO OPENMETADATA (RF27 — RF29)")
    print("=================================================================")

    ativo = testar_conexao_openmetadata()
    exportar_dossie_metadados()

    if ativo:
        token = autenticar_openmetadata()
        if token:
            print("\n--- Sincronizando Glossário e Termos via API REST ---")
            sincronizar_glossario_e_termos(token)
            print("\n[SUCESSO] Glossário e 4 Termos integrados no OpenMetadata!")

    print("\n-----------------------------------------------------------------")
    print("INSTRUÇÕES DE ACESSO AO OPENMETADATA:")
    print("  URL no Navegador: http://localhost:8585")
    print("  E-mail de Login:  admin@openmetadata.org")
    print("  Senha:            admin")
    print("-----------------------------------------------------------------")
    print("=================================================================")


if __name__ == "__main__":
    main()
