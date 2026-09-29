"""Testes para garantir padronização universal do fuso horário America/Cuiaba (UTC-4)."""
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import pytest

from src.config import (
    obter_timezone_projeto,
    agora_projeto,
    agora_iso,
    converter_para_horario_local,
)


def test_timezone_projeto_padrao():
    tz = obter_timezone_projeto()
    assert tz.key == "America/Cuiaba"


def test_agora_projeto_offset():
    dt = agora_projeto()
    assert dt.tzinfo is not None
    # Cuiaba is UTC-4 (offset de -14400 segundos / -4 horas)
    offset = dt.utcoffset()
    assert offset is not None
    assert offset.total_seconds() == -4 * 3600


def test_agora_iso_contem_offset_cuiaba():
    iso_str = agora_iso()
    assert "-04:00" in iso_str or "-0400" in iso_str


def test_converter_para_horario_local_de_utc():
    utc_str = "2026-09-28T23:17:00+00:00"
    dt_local = converter_para_horario_local(utc_str)
    assert dt_local.hour == 19
    assert dt_local.minute == 17
    assert dt_local.tzinfo.key == "America/Cuiaba"


def test_converter_para_horario_local_naive():
    naive_dt = datetime(2026, 9, 28, 19, 17, 0)
    dt_local = converter_para_horario_local(naive_dt)
    assert dt_local.hour == 19
    assert dt_local.minute == 17
    assert dt_local.tzinfo.key == "America/Cuiaba"
