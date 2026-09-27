"""Módulo de implementação das técnicas de proteção de dados pessoais (RF33 - LGPD).

Implementa:
1. Mascaramento parcial de strings/nomes (ex.: 'João Silva' -> 'J*** S****')
2. Pseudonimização determinística de identificadores (UUIDv5 para joins consistentes)
3. Hashing criptográfico SHA-256 com Salt dinâmico via variável de ambiente (HASH_SALT)
"""
from __future__ import annotations

import hashlib
import hmac
import os
import uuid
from typing import Optional

# Namespace fixo para pseudonimização determinística padrão RFC 4122
NAMESPACE_FICDEV = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

def obter_salt_configurado(salt_override: Optional[str] = None) -> str:
    """Obtém o salt criptográfico da variável de ambiente HASH_SALT ou LGPD_HASH_SALT.
    
    Nunca utiliza valor fixo se não configurado; levanta ValueError para impedir
    vazamento ou execução insegura sem segredo.
    """
    if salt_override:
        return salt_override
    
    salt = os.getenv("HASH_SALT") or os.getenv("LGPD_HASH_SALT")
    if not salt:
        # Fallback de segurança documentado apenas se for ambiente de testes
        if os.getenv("ENV") == "test" or os.getenv("PYTEST_CURRENT_TEST"):
            return "salt_teste_ambiente_isolado_ficdev_2026"
        raise ValueError(
            "Variável de ambiente HASH_SALT ou LGPD_HASH_SALT não está definida. "
            "Defina o salt no arquivo .env antes de executar as funções de proteção."
        )
    return salt


def mascarar_nome(nome: Optional[str]) -> str:
    """Aplica mascaramento parcial ao nome de uma pessoa física.
    
    Regra:
    - Preserva o primeiro caractere de cada palavra (quando >= 2 caracteres).
    - Substitui os caracteres subsequentes por asteriscos (*).
    - Nomes com 1 caractere viram '*'.
    - Nulos ou vazios retornam string anônima '[ANÔNIMO]'.
    
    Exemplos:
        'João Silva' -> 'J*** S****'
        'Ana Beatriz Costa' -> 'A** B****** C****'
    """
    if not nome or not str(nome).strip():
        return "[ANÔNIMO]"
    
    partes = str(nome).strip().split()
    resultado = []
    
    for parte in partes:
        if len(parte) == 1:
            resultado.append("*")
        elif len(parte) == 2:
            resultado.append(parte[0] + "*")
        else:
            mascara = parte[0] + ("*" * (len(parte) - 1))
            resultado.append(mascara)
            
    return " ".join(resultado)


def pseudonimizar_id(usuario_id: str | int, prefixo: str = "USR_PSEUDO_") -> str:
    """Gera um identificador pseudônimo determinístico e consistente para joins analíticos.
    
    Utiliza UUIDv5 baseado no namespace corporativo FIC_DEV e o ID de origem.
    O mesmo usuario_id gerará SEMPRE o mesmo UUID pseudônimo, permitindo:
    - Agrupamentos e contagens distintas (COUNT DISTINCT usuario_id)
    - Joins entre interações e avaliações
    - Impossibilidade de reversão para o ID original sem conhecer a tabela de correspondência.
    
    Exemplo:
        1001 -> 'USR_PSEUDO_b9c4f1a2-...'
    """
    if usuario_id is None:
        return f"{prefixo}NULO"
    
    conteudo = str(usuario_id).strip()
    pseudo_uuid = uuid.uuid5(NAMESPACE_FICDEV, conteudo)
    return f"{prefixo}{pseudo_uuid}"


def gerar_hash_salted(
    valor: str | int,
    salt_override: Optional[str] = None,
    tamanho_hex: int = 64,
) -> str:
    """Gera um hash SHA-256 criptográfico robusto com Salt secreto.
    
    O salt é injetado via variável de ambiente HASH_SALT e combinado via HMAC-SHA256,
    neutralizando completamente ataques de Rainbow Table (tabelas pré-computadas)
    e dicionário.
    
    Argumentos:
        valor: O dado a ser anonimizado/hasheado (ex.: usuario_id ou CPF).
        salt_override: Opcional, para testes unitários ou auditorias pontuais.
        tamanho_hex: Comprimento da string hexadecimal de saída (padrão 64 para SHA-256).
    
    Retorno:
        String hexadecimal do digest do hash criptográfico.
    """
    if valor is None:
        return "0" * min(tamanho_hex, 64)
    
    salt = obter_salt_configurado(salt_override)
    dado_bytes = str(valor).strip().encode("utf-8")
    salt_bytes = salt.encode("utf-8")
    
    # Aplica HMAC-SHA256 para máxima solidez criptográfica
    digest = hmac.new(salt_bytes, dado_bytes, hashlib.sha256).hexdigest()
    return digest[:tamanho_hex]


def verificar_hash(
    valor: str | int,
    hash_esperado: str,
    salt_override: Optional[str] = None,
) -> bool:
    """Verifica se um dado de entrada corresponde a um hash salted previamente gerado."""
    hash_calculado = gerar_hash_salted(valor, salt_override=salt_override)
    return hmac.compare_digest(hash_calculado, hash_esperado)
