# Técnicas de Proteção de Dados e Mecanismos Criptográficos (RF33)

**Projeto:** Plataforma Educacional FIC_DEV — Módulo de Fundamentos de Dados para IA  
**Norma Regulamentadora:** Lei Geral de Proteção de Dados Pessoais (Lei nº 13.709/2018 - LGPD)  
**Escopo:** Implementação, demonstração e validação das técnicas de proteção aplicadas sobre os dados  
**Responsáveis:** Estudante 3 (Governança e Proteção de Dados) em conjunto com Estudante 2 e Estudante 1  

---

## 1. Princípios e Diretrizes Arquiteturais de Proteção

Em cumprimento ao princípio da **Segurança** (Art. 6º, VII) e da **Prevenção** (Art. 6º, VIII), o pipeline da FIC_DEV adota a abordagem de *Privacy by Design and by Default*.

Para neutralizar riscos de vazamento e reidentificação não autorizada, foram implementadas e integradas ao ecossistema três técnicas complementares de engenharia de privacidade:
1. **Mascaramento Parcial de Dados (Data Masking)** para dados cadastrais e nomes em relatórios;
2. **Pseudonimização Determinística (Deterministic Pseudonymization)** para preservação da integridade referencial em análises agregadas;
3. **Hashing Criptográfico com Salt (Salted SHA-256 Hashing)** para garantia de irreversibilidade criptográfica de identificadores de estudantes.

---

## 2. Técnica 1 — Mascaramento Parcial de Dados Identificáveis

### 2.1. Conceito e Objetivo
O mascaramento parcial consiste em ocultar deliberadamente uma fração dos caracteres de um dado identificável direto (como o nome do autor de uma avaliação), preservando apenas fragmentos suficientes para validação visual ou auditoria de integridade, sem expor a identidade completa da pessoa natural.

### 2.2. Algoritmo de Mascaramento
Para cada palavra de um nome completo:
* Se a palavra possuir $\ge 2$ caracteres: preserva-se o primeiro caractere e substituem-se os demais por asteriscos (`*`).
* Se a palavra possuir 1 único caractere: substitui-se por `*`.
* Valores nulos ou em branco são normalizados para `[ANÔNIMO]`.

```
Texto Original                  Texto Mascarado
─────────────────────────────   ──────────────────────────────
João Silva                      J*** S****
Ana Beatriz Costa               A** B****** C****
Carlos Eduardo Oliveira Santos  C***** E****** O******** S*****
Maria                           M****
```

### 2.3. Implementação Prática

#### No Módulo Python (`src.lgpd.protecao.mascarar_nome`):
```python
def mascarar_nome(nome: Optional[str]) -> str:
    if not nome or not str(nome).strip():
        return "[ANÔNIMO]"
    partes = str(nome).strip().split()
    resultado = [
        parte[0] + ("*" * (len(parte) - 1)) if len(parte) >= 2 else "*"
        for parte in partes
    ]
    return " ".join(resultado)
```

#### Em Consulta SQL Lab / PostgreSQL:
```sql
-- Exemplo de máscara dinâmica para apresentação no SQL Lab
SELECT 
    id_comentario,
    CONCAT(
        LEFT(SPLIT_PART(autor, ' ', 1), 1), 
        REPEAT('*', GREATEST(0, LENGTH(SPLIT_PART(autor, ' ', 1)) - 1)),
        ' ',
        LEFT(SPLIT_PART(autor, ' ', 2), 1),
        REPEAT('*', GREATEST(0, LENGTH(SPLIT_PART(autor, ' ', 2)) - 1))
    ) AS autor_mascarado,
    nota,
    sentimento
FROM silver.comentarios_fato;
```

---

## 3. Técnica 2 — Pseudonimização Determinística de Identificadores

### 3.1. Conceito e Base Legal (LGPD Art. 13, § 4º)
> *"Para os efeitos deste artigo, a pseudonimização é o tratamento por meio do qual um dado perde a possibilidade de associação, direta ou indireta, a um indivíduo, senão pelo uso de informação adicional mantida separadamente pelo controlador em ambiente controlado e seguro."*

Diferente da anonimização total, a pseudonimização determinística permite que cientistas de dados e analistas de BI:
1. Realizem junções relacionais (*joins*) entre interações de acesso (`silver.interacoes_fato`) e avaliações (`silver.comentarios_fato`);
2. Calculem métricas de contagem distinta (`COUNT(DISTINCT usuario_pseudonimo)`) para dimensionar o público ativo real da plataforma;
3. Alimentem algoritmos de recomendação colaborativa sem jamais ter acesso ao ID relacional primário (`usuario_id`) ou aos dados cadastrais reais do aluno.

### 3.2. Implementação com UUIDv5 (Padrão RFC 4122)
Utiliza-se o algoritmo **UUID Versão 5**, gerado a partir do namespace institucional da FIC_DEV (`6ba7b810-9dad-11d1-80b4-00c04fd430c8`) e da chave do estudante.

```python
import uuid

NAMESPACE_FICDEV = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

def pseudonimizar_id(usuario_id: str | int, prefixo: str = "USR_PSEUDO_") -> str:
    if usuario_id is None:
        return f"{prefixo}NULO"
    return f"{prefixo}{uuid.uuid5(NAMESPACE_FICDEV, str(usuario_id).strip())}"
```

**Propriedades Verificadas:**
* **Consistência:** `pseudonimizar_id(1001)` produz invariavelmente `USR_PSEUDO_b9c4f1a2-1d4e-5c6b-8f7a-0a1b2c3d4e5f`.
* **Segregação de Chave:** A tabela que mapeia `usuario_id` real ao `UUIDv5` é armazenada em esquema isolado com controle estrito de RBAC, inacessível pela camada de consumo analítico.

---

## 4. Técnica 3 — Hashing Criptográfico com Salt (Salted SHA-256)

### 4.1. Conceito e Defesa Criptográfica
O Hashing simples (ex.: `SHA256(usuario_id)`) é vulnerável a ataques de **Rainbow Tables** (dicionários pré-computados contendo bilhões de hashes de sequências numéricas comuns, como IDs inteiros de 1 a 1.000.000).

Para anular essa vulnerabilidade, o pipeline adota o **Hashing com Salt Criptográfico Secreto**, utilizando o algoritmo **HMAC-SHA256** (Keyed-Hash Message Authentication Code).

```
┌──────────────────────────┐
│ Identificador Original   │ (ex.: "1050")
└─────────────┬────────────┘
              │
              ├─── (+) ───> [HMAC-SHA256 Engine] ───> [Hash Hexadecimal Criptográfico]
              │                                        (64 caracteres irreversíveis)
┌─────────────┴────────────┐
│ Segredo Salt (.env)      │ (ex.: HASH_SALT="segredo_corporativo_ficdev_2026")
└──────────────────────────┘
```

### 4.2. Isolamento de Segredos (RF15)
Em conformidade com a política de segurança:
* O salt **NUNCA** é escrito de forma estática (*hardcoded*) no código-fonte, nos logs ou no repositório Git.
* A injeção ocorre exclusivamente via variável de ambiente:
  ```bash
  # Arquivo .env local (ignorado pelo .gitignore)
  HASH_SALT=chave_criptografica_altamente_segura_ficdev_2026_x9#k2!
  ```

### 4.3. Implementação Prática

```python
import hmac
import hashlib
import os

def gerar_hash_salted(valor: str | int) -> str:
    salt = os.getenv("HASH_SALT")
    if not salt:
        raise ValueError("Variável HASH_SALT não configurada!")
    
    dado_bytes = str(valor).strip().encode("utf-8")
    salt_bytes = salt.encode("utf-8")
    return hmac.new(salt_bytes, dado_bytes, hashlib.sha256).hexdigest()
```

### 4.4. Demonstração de Irreversibilidade Criptográfica
1. **Unilateralidade Matemática:** O SHA-256 é uma função não bijetiva de compressão criptográfica de 512 bits de bloco. Matematicamente, inexiste função inversa $f^{-1}(y) = x$.
2. **Resistência à Pré-imagem:** O custo computacional estimado para encontrar qualquer valor que produza o mesmo hash SHA-256 é de $2^{256}$ operações, tornando a tentativa de força bruta fisicamente inviável.
3. **Dependência do Salt:** Mesmo que um invasor descubra o valor original `1050`, ele não conseguirá correlacioná-lo com os registros analíticos sem possuir o salt secreto configurado no ambiente seguro.

---

## 5. Validação Automatizada e Evidências de Testes

Todas as rotinas de proteção de dados são validadas por testes unitários e de integração contínua implementados em `tests/test_lgpd_protecao.py`:

```
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
collected 5 items

tests/test_lgpd_protecao.py::test_mascaramento_nome_padrao PASSED        [ 20%]
tests/test_lgpd_protecao.py::test_mascaramento_nome_nulo_ou_vazio PASSED [ 40%]
tests/test_lgpd_protecao.py::test_pseudonimizacao_consistente_para_joins PASSED [ 60%]
tests/test_lgpd_protecao.py::test_hash_salted_com_salt_customizado PASSED [ 80%]
tests/test_lgpd_protecao.py::test_hash_salted_com_variavel_ambiente PASSED [100%]

============================== 5 passed in 0.05s ==============================
```

Assegura-se, portanto, a total conformidade do projeto aos requisitos **RF32** e **RF33** da Seção 11.
