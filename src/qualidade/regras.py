"""Definição formal das regras e dimensões de qualidade de dados (RF31)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable


class Severidade(str, Enum):
    CRITICA = "CRITICA"
    AVISO = "AVISO"


class AcaoFalha(str, Enum):
    BLOQUEAR_GOLD = "BLOQUEAR_PUBLICACAO_GOLD"
    ALERTA_AUDITORIA = "REGISTRAR_ALERTA_AUDITORIA"


@dataclass(frozen=True)
class RegraQualidade:
    id_regra: str
    nome: str
    dimensao: str  # Completude, Validade, Unicidade, Consistência, Integridade Referencial
    descricao: str
    campo_ou_conjunto: str
    limite_aceitavel_descricao: str
    severidade: Severidade
    acao_em_falha: AcaoFalha


REGRAS_QUALIDADE: dict[str, RegraQualidade] = {
    "Q01_COMPLETUDE": RegraQualidade(
        id_regra="Q01_COMPLETUDE",
        nome="Completude de Campos Obrigatórios",
        dimensao="Completude",
        descricao="Verifica ausência de valores nulos em chaves e atributos mandatórios de interações e catálogo.",
        campo_ou_conjunto="interacoes(interacao_id, usuario_id, conteudo_id, tipo_interacao, data_hora)",
        limite_aceitavel_descricao="0% de valores nulos ou vazios",
        severidade=Severidade.CRITICA,
        acao_em_falha=AcaoFalha.BLOQUEAR_GOLD,
    ),
    "Q02_VALIDADE": RegraQualidade(
        id_regra="Q02_VALIDADE",
        nome="Validade de Domínios e Escalas Numéricas",
        dimensao="Validade",
        descricao="Garante que avaliações estejam em [1.0, 5.0], conclusão em [0.0, 100.0] e tipo_interacao pertença ao vocabulário controlado.",
        campo_ou_conjunto="interacoes(avaliacao, percentual_conclusao, tempo_consumido_min, tipo_interacao)",
        limite_aceitavel_descricao="100% de conformidade com os domínios válidos",
        severidade=Severidade.CRITICA,
        acao_em_falha=AcaoFalha.BLOQUEAR_GOLD,
    ),
    "Q03_UNICIDADE": RegraQualidade(
        id_regra="Q03_UNICIDADE",
        nome="Unicidade de Identificadores Primários",
        dimensao="Unicidade",
        descricao="Assegura que interacao_id seja único em interações e conteudo_id seja único no catálogo.",
        campo_ou_conjunto="interacoes(interacao_id) e catalogo(conteudo_id)",
        limite_aceitavel_descricao="0% de registros com chaves duplicadas",
        severidade=Severidade.CRITICA,
        acao_em_falha=AcaoFalha.BLOQUEAR_GOLD,
    ),
    "Q04_CONSISTENCIA": RegraQualidade(
        id_regra="Q04_CONSISTENCIA",
        nome="Consistência Lógica de Eventos de Conclusão",
        dimensao="Consistência",
        descricao="Verifica se eventos com tipo_interacao 'conclusão' possuem percentual_conclusao igual a 100%.",
        campo_ou_conjunto="interacoes(tipo_interacao, percentual_conclusao)",
        limite_aceitavel_descricao="Tolerância de inconsistência <= 1.0%",
        severidade=Severidade.AVISO,
        acao_em_falha=AcaoFalha.ALERTA_AUDITORIA,
    ),
    "Q05_INTEGRIDADE_REFERENCIAL": RegraQualidade(
        id_regra="Q05_INTEGRIDADE_REFERENCIAL",
        nome="Integridade Referencial entre Interações e Catálogo",
        dimensao="Integridade Referencial",
        descricao="Garante que todo conteudo_id referenciado nas interações exista previamente no catálogo de conteúdos.",
        campo_ou_conjunto="interacoes(conteudo_id) -> catalogo(conteudo_id)",
        limite_aceitavel_descricao="0% de registros órfãos",
        severidade=Severidade.CRITICA,
        acao_em_falha=AcaoFalha.BLOQUEAR_GOLD,
    ),
}
