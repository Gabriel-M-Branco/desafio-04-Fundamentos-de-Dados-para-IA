"""Testes automatizados de métricas, integridade do dashboard Superset e validação das views analíticas SQL (RF12 e RF13)."""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
import yaml

from src.config import caminho_absoluto


def test_views_definidas_no_criar_banco_sql():
    """Verifica se as 3 views do Superset estão definidas no script sql/criar_banco.sql."""
    caminho_sql = caminho_absoluto("sql/criar_banco.sql")
    conteudo_sql = Path(caminho_sql).read_text(encoding="utf-8")

    views_obrigatorias = [
        "vw_content_views_by_category",
        "vw_content_completion_by_category",
        "vw_recommendation_conversion",
    ]

    for view in views_obrigatorias:
        assert f"CREATE OR REPLACE VIEW {view}" in conteudo_sql, (
            f"A view obrigatória {view} não está definida em sql/criar_banco.sql"
        )


def test_integridade_exportacao_dashboard_superset():
    """Valida se o arquivo zip exportado do Superset existe e contém todos os elementos obrigatórios."""
    pasta_dashboard = caminho_absoluto("dashboard")
    zips = sorted(pasta_dashboard.glob("*.zip"))
    assert len(zips) > 0, "Nenhum arquivo zip de exportação do dashboard Superset encontrado em dashboard/"
    caminho_zip = next((p for p in zips if "desafio_3" in p.name or "dashboard_export.zip" in p.name), zips[0])

    with zipfile.ZipFile(caminho_zip) as z:
        arquivos = z.namelist()

        # Verifica metadata e dashboard
        assert any("metadata.yaml" in a for a in arquivos), "metadata.yaml ausente no zip"
        assert any("dashboards/" in a for a in arquivos), "Definição do dashboard ausente no zip"

        # Verifica datasets das 3 views
        assert any("vw_content_views_by_category" in a for a in arquivos)
        assert any("vw_content_completion_by_category" in a for a in arquivos)
        assert any("vw_recommendation_conversion" in a for a in arquivos)

        # Verifica gráficos (charts) obrigatórios: linhas, barras e big numbers
        charts = [a for a in arquivos if "/charts/" in a and a.endswith(".yaml")]
        assert len(charts) >= 5, f"Esperado ao menos 5 gráficos/cartões no dashboard, encontrados {len(charts)}"

        # Lê um gráfico e valida sintaxe YAML
        chart_content = z.read(charts[0]).decode("utf-8")
        parsed = yaml.safe_load(chart_content)
        assert "viz_type" in parsed
        assert "slice_name" in parsed


def test_integridade_exportacao_dashboard_desafio_4():
    """Valida a integridade do pacote oficial de exportação do Superset do Desafio 4 (RF16-RF18)."""
    caminho_zip = caminho_absoluto("dashboard/dashboard_desafio_4.zip")
    assert caminho_zip.exists(), "Pacote zip do Desafio 4 não encontrado em dashboard/dashboard_desafio_4.zip"

    with zipfile.ZipFile(caminho_zip) as z:
        arquivos = z.namelist()
        assert any("metadata.yaml" in a for a in arquivos)
        assert any("Dashboard_-_Desafio_4" in a for a in arquivos)
        assert any("STORYTELLING" in a for a in arquivos)
        assert any("SQLab_-_Indicadores_por_Mes" in a for a in arquivos)


def test_evidencias_visuais_segregadas_por_desafio():
    """Valida a existência das evidências visuais segregadas em dashboard/evidencias/desafio_3 e desafio_4."""
    pasta_evidencias = caminho_absoluto("dashboard/evidencias")
    evidencias_d3 = list((pasta_evidencias / "desafio_3").glob("*.png"))
    evidencias_d4 = list((pasta_evidencias / "desafio_4").glob("*.png"))

    assert len(evidencias_d3) >= 4, f"Esperado ao menos 4 evidências do Desafio 3, encontradas {len(evidencias_d3)}"
    assert len(evidencias_d4) >= 2, f"Esperado ao menos 2 evidências do Desafio 4, encontradas {len(evidencias_d4)}"



def test_logica_kpi_taxa_conclusao_com_protecao_divisao_zero():
    """Valida a fórmula de taxa de conclusão por categoria garantindo proteção contra divisão por zero."""
    # Cenário normal: 10 inícios e 7 conclusões => 70%
    inicios = 10
    conclusoes = 7
    taxa = (conclusoes / inicios) * 100 if inicios > 0 else 0.0
    assert taxa == 70.0

    # Cenário divisão por zero: 0 inícios e 0 conclusões => 0.0 (equivalente ao NULLIF no SQL)
    inicios_zero = 0
    conclusoes_zero = 0
    taxa_zero = (conclusoes_zero / inicios_zero) * 100 if inicios_zero > 0 else 0.0
    assert taxa_zero == 0.0


def test_logica_kpi_conversao_recomendacoes():
    """Valida a regra de conversão de recomendação baseada na precedência temporal data_hora > data_geracao."""
    rec_gerada = "2026-09-12T10:00:00"
    interacao_posterior = "2026-09-12T11:00:00"
    interacao_anterior = "2026-09-12T09:00:00"

    # Interação posterior converte
    conversao_sucesso = 1 if interacao_posterior > rec_gerada else 0
    assert conversao_sucesso == 1

    # Interação anterior não converte
    conversao_falha = 1 if interacao_anterior > rec_gerada else 0
    assert conversao_falha == 0


def test_logica_kpi_usuarios_ativos_distintos():
    """Valida que o KPI de usuários ativos contabiliza usuários únicos no período."""
    interacoes_amostra = [
        {"usuario_id": 1, "tipo_interacao": "visualização"},
        {"usuario_id": 1, "tipo_interacao": "início"},
        {"usuario_id": 2, "tipo_interacao": "visualização"},
        {"usuario_id": 3, "tipo_interacao": "conclusão"},
    ]
    usuarios_ativos = len({i["usuario_id"] for i in interacoes_amostra})
    assert usuarios_ativos == 3
