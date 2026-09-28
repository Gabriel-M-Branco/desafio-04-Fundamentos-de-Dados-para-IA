# Cenários de Teste e Demonstração de Casos de Borda (Dados Brutos)

Este diretório contém bases de dados sintéticas isoladas para demonstrar **todas as possibilidades e regras do pipeline**, incluindo:
1. Caminho feliz (dados válidos e íntegros);
2. As 5 dimensões do Motor de Qualidade de Dados (RF31: Q01 a Q05);
3. O isolamento de falhas na Quarentena do Apache Hop (RF22);
4. O bloqueio da Camada Gold pelo Quality Gate (RF31);
5. As técnicas de proteção e conformidade da LGPD (RF32 e RF33).

---

## Arquivos Disponíveis

| Arquivo | Origem Simulada | Descrição |
| :--- | :--- | :--- |
| [`catalogo_cenarios.csv`](catalogo_cenarios.csv) | CSV Educacional | Catálogo com exemplos válidos, violações de completude (título nulo), validade (carga horária negativa), unicidade (chave duplicada) e nomes para mascaramento. |
| [`interacoes_cenarios.json`](interacoes_cenarios.json) | Logs de Telemetria | Eventos de acesso com notas inválidas, conclusões inconsistentes, IDs nulos, chaves duplicadas e IDs órfãos. |
| [`comentarios_cenarios.json`](comentarios_cenarios.json) | Coleção MongoDB | Avaliações com notas fora da escala ([1.0, 5.0]), IDs órfãos e textos livres para validação da minimização na LGPD. |

---

## Mapeamento Detalhado dos Cenários e Regras

### 1. Motor de Qualidade de Dados (RF31)

| Dimensão | Regra | Cenário Demonstrado no Dataset | Arquivo / Registro | Comportamento Esperado do Pipeline |
| :--- | :--- | :--- | :--- | :--- |
| **Completude** | `Q01_COMPLETUDE` | `usuario_id = null` em evento de interação | `interacoes_cenarios.json` (ID 103) | **Severidade CRÍTICA:** Quality Gate bloqueia publicação na Gold (`FalhaQualidadeDadosCriticaError`). |
| **Completude** | `Q01_COMPLETUDE` | `titulo` vazio/nulo no catálogo | `catalogo_cenarios.csv` (ID 3) | **Severidade CRÍTICA:** Rejeição na ingestão e desvio para `quarentena.registros`. |
| **Validade** | `Q02_VALIDADE` | Nota `7.5` (fora do domínio permitido `[1.0, 5.0]`) | `interacoes_cenarios.json` (ID 104) | **Severidade CRÍTICA:** Isolamento imediato em quarentena com `regra_violada = NOTA_FORA_FAIXA`. |
| **Validade** | `Q02_VALIDADE` | Percentual de conclusão `150%` (fora de `[0.0, 100.0]`) | `interacoes_cenarios.json` (ID 105) | **Severidade CRÍTICA:** Rejeição de regra de domínio numérico. |
| **Validade** | `Q02_VALIDADE` | Carga horária negativa `-120 min` | `catalogo_cenarios.csv` (ID 4) | Rejeição por validação de intervalo numérico. |
| **Unicidade** | `Q03_UNICIDADE` | `interacao_id = 101` duplicado propositalmente | `interacoes_cenarios.json` (ID 101 repetido) | **Severidade CRÍTICA:** Violação de chave primária; impede corrupção de contagens na Silver. |
| **Unicidade** | `Q03_UNICIDADE` | `conteudo_id = 1` repetido no catálogo | `catalogo_cenarios.csv` (ID 1 repetido) | Violação de PK no catálogo educacional. |
| **Consistência** | `Q04_CONSISTENCIA` | `tipo_interacao = "conclusão"`, mas com `percentual_conclusao = 25.0%` | `interacoes_cenarios.json` (ID 106) | **Severidade AVISO:** Registra alerta de incoerência lógica no histórico de auditoria (`historico_qualidade.json`). |
| **Integridade Referencial** | `Q05_INTEGRIDADE_REFERENCIAL` | `conteudo_id = 99999` (não existe em `catalogo`) | `interacoes_cenarios.json` (ID 107) | **Severidade CRÍTICA:** Rejeição por chave estrangeira órfã; registro enviado para quarentena. |

---

### 2. Demonstração de Proteção de Dados (LGPD - RF32 e RF33)

| Técnica LGPD | Dado de Entrada no Dataset | Processamento Aplicado | Resultado Gerado |
| :--- | :--- | :--- | :--- |
| **Mascaramento Parcial** | Autor: `"Gabriel Moreira Branco"` (`catalogo_cenarios.csv`) | `src.lgpd.protecao.mascarar_nome()` | `"G****** M****** B*****"` |
| **Mascaramento Parcial** | Autor: `"Ana Beatriz Costa"` (`catalogo_cenarios.csv`) | `src.lgpd.protecao.mascarar_nome()` | `"A** B****** C****"` |
| **Pseudonimização Determinística** | Usuário ID: `1002` (`interacoes_cenarios.json`) | `src.lgpd.protecao.pseudonimizar_id(1002)` | `"USR_PSEUDO_b7e8d697-7c70-5b5f-a3c3-6316bf494ecf"` (Consistente para `JOINs`) |
| **Hashing Irreversível com Salt** | Usuário ID: `1002` com salt corporativo do `.env` | `src.lgpd.protecao.gerar_hash_salted(1002)` | Hash SHA-256 de 64 caracteres imune a *Rainbow Tables*. |
| **Minimização Radical** | Comentário qualitativo com relato livre | Regra de carga Medalhão | O texto é preservado apenas na Silver; na Gold sobe apenas a média estatística (`avaliacao_media`). |

---

## Como Validar Esses Cenários

Você pode inspecionar diretamente os arquivos ou executar o script de teste de cenários:
```bash
python -m pytest tests/test_cenarios_brutos.py
```
