"""Transformações e PTransforms do Apache Beam para a camada Gold (RF25)."""
from __future__ import annotations

from typing import Any, Iterable
import apache_beam as beam


class ExtrairChaveCategoriaMes(beam.DoFn):
    """Enriquece o evento de interação com a categoria e gera a chave (ano, mes, categoria)."""

    def process(
        self,
        interacao: dict[str, Any],
        mapa_catalogo: dict[int, dict[str, Any]],
    ) -> Iterable[tuple[tuple[int, int, str], dict[str, Any]]]:
        cid = int(interacao.get("conteudo_id", 0))
        conteudo = mapa_catalogo.get(cid, {})
        categoria = conteudo.get("categoria", "Desconhecida")
        ano = int(interacao.get("ano", 2026))
        mes = int(interacao.get("mes", 1))

        chave = (ano, mes, categoria)
        yield (chave, interacao)


class ConsolidarMetricasCategoria(beam.CombineFn):
    """Acumulador para agregação de KPIs por categoria e período."""

    def create_accumulator(self) -> dict[str, Any]:
        return {
            "total_interacoes": 0,
            "usuarios": set(),
            "visualizacoes": 0,
            "inicios": 0,
            "conclusoes": 0,
            "curtidas": 0,
            "tempo_total_min": 0.0,
            "soma_avaliacoes": 0.0,
            "qtd_avaliacoes": 0,
        }

    def add_input(self, acc: dict[str, Any], interacao: dict[str, Any]) -> dict[str, Any]:
        acc["total_interacoes"] += 1
        acc["usuarios"].add(interacao["usuario_id"])

        tipo = interacao.get("tipo_interacao", "")
        if tipo == "visualização":
            acc["visualizacoes"] += 1
        elif tipo == "início":
            acc["inicios"] += 1
        elif tipo == "conclusão":
            acc["conclusoes"] += 1
        elif tipo == "curtida":
            acc["curtidas"] += 1

        tempo = interacao.get("tempo_consumido_min")
        if tempo is not None:
            acc["tempo_total_min"] += float(tempo)

        aval = interacao.get("avaliacao")
        if aval is not None:
            acc["soma_avaliacoes"] += float(aval)
            acc["qtd_avaliacoes"] += 1

        return acc

    def merge_accumulators(self, accumulators: Iterable[dict[str, Any]]) -> dict[str, Any]:
        merged = self.create_accumulator()
        for a in accumulators:
            merged["total_interacoes"] += a["total_interacoes"]
            merged["usuarios"].update(a["usuarios"])
            merged["visualizacoes"] += a["visualizacoes"]
            merged["inicios"] += a["inicios"]
            merged["conclusoes"] += a["conclusoes"]
            merged["curtidas"] += a["curtidas"]
            merged["tempo_total_min"] += a["tempo_total_min"]
            merged["soma_avaliacoes"] += a["soma_avaliacoes"]
            merged["qtd_avaliacoes"] += a["qtd_avaliacoes"]
        return merged

    def extract_output(self, acc: dict[str, Any]) -> dict[str, Any]:
        total_interacoes = acc["total_interacoes"]
        inicios = acc["inicios"]
        conclusoes = acc["conclusoes"]

        taxa_conclusao_pct = round((conclusoes / inicios) * 100.0, 2) if inicios > 0 else 0.0
        tempo_medio_min = round(acc["tempo_total_min"] / total_interacoes, 2) if total_interacoes > 0 else 0.0
        avaliacao_media = round(acc["soma_avaliacoes"] / acc["qtd_avaliacoes"], 2) if acc["qtd_avaliacoes"] > 0 else None

        return {
            "total_interacoes": total_interacoes,
            "usuarios_ativos": len(acc["usuarios"]),
            "total_visualizacoes": acc["visualizacoes"],
            "total_inicios": inicios,
            "total_conclusoes": conclusoes,
            "total_curtidas": acc["curtidas"],
            "taxa_conclusao_pct": taxa_conclusao_pct,
            "tempo_total_consumido_min": round(acc["tempo_total_min"], 2),
            "tempo_medio_min": tempo_medio_min,
            "avaliacao_media": avaliacao_media,
        }


class FormatarRegistroGoldCategoria(beam.DoFn):
    """Formata o par (chave, metricas) para o registro final da camada Gold."""

    def __init__(self, lote_id: str, data_carga: str):
        self.lote_id = lote_id
        self.data_carga = data_carga

    def process(self, elemento: tuple[tuple[int, int, str], dict[str, Any]]) -> Iterable[dict[str, Any]]:
        (ano, mes, categoria), metricas = elemento
        registro = {
            "ano": ano,
            "mes": mes,
            "categoria": categoria,
            **metricas,
            "_data_carga_gold": self.data_carga,
            "_lote_processamento": self.lote_id,
        }
        yield registro
