# Metodologia Cartola FC — Fathur FC

> Versão atualizada após Rodada 26 (01/09/2026), incorporando validação crítica dos parâmetros com dados reais das 25 rodadas já disputadas.

## Contexto estratégico

Fathur FC está atrás do líder da liga com ~14 rodadas restantes. A estratégia é **recuperação agressiva de pontos**: aceita-se maior variância e concentração de clube (Flamengo/Palmeiras) como trade-off consciente, não como falha de análise.

## As 6 camadas de análise

1. **Modelo estatístico próprio** (Python/pandas): `conquistado × cedido`, pesos 0.6/0.4, janela móvel de 5 rodadas, mínimo 3 jogos, ajuste por mando de campo por posição. Coluna: `score_final`.
2. **TCC (Treinando Campeões de Cartola)** — conteúdo premium, transcrições ao vivo e sugestões de time.
3. **cartodados** — fonte estatística independente para validação cruzada.
4. **Notícias de repórteres + prévias oficiais de escalação dos clubes.**
5. **Odds de casas de apostas + dados de escalação colaborativa (crowd-sourced).**
6. **Camada de ajuste cruzado via IA externa (DeepSeek)** — modelo `score_ajustado`/`score_oportunidade`, que recalcula o score aplicando força relativa de time/adversário e um fator de consistência por perfil. Tratada como uma **segunda opinião de modelo**, não como substituta do `score_final`. Ver ressalva abaixo.

**Regra de decisão**: pelo menos 2 fontes independentes precisam concordar antes de fechar uma posição. Picks de fonte única são sinalizados explicitamente, não escondidos. Na prática, `score_final` × `score_ajustado` já cumprem esse papel de checagem cruzada automática a cada rodada (ver Spearman abaixo).

### ⚠️ O que NÃO conta como segunda fonte — caso Ignácio (Rodada 26)

Erro real cometido nesta rodada: o Ignácio foi recomendado num comparativo com base em `score_confronto` (camada 7, interna) sem sinalizar que essa era a **única** fonte por trás do pick. `score_final`, `score_ajustado` e `score_confronto` são todos derivados do **mesmo pipeline interno** (scouts + partidas próprios) — usar dois desses três pra "confirmar" um jogador é o modelo concordando consigo mesmo, não uma checagem cruzada de verdade. A TCC nunca citou o Ignácio em nenhuma fonte (nem live, nem PDF) — isso só ficou claro quando o usuário perguntou diretamente, e deveria ter sido sinalizado antes, no momento do comparativo original.

**Regra explícita a partir de agora**: contam como fonte independente pra fechar uma posição — TCC (live/PDF/semáforo), xG real (tabelas da TCC), odds reais, notícia de escalação/imprensa. `score_final`, `score_ajustado` e `score_confronto` juntos = **1 fonte só** (o próprio modelo), não importa quantos desses três concordem entre si. Isso já foi implementado no código: `calcular_confronto.py` agora retorna `fonte_unica: True` e `validado_externamente: False` por padrão em toda saída — o campo só deve virar `True` manualmente, depois de cruzar com algo de fora do pipeline.

**Hierarquia de confiabilidade de fontes**: GE/Globo Esporte e canais oficiais dos clubes > cartodados/TCC > repórteres de escalação (Diego Firmino tem histórico de imprecisão, tratar com ceticismo) > `score_ajustado` (camada 6) > campo `status` do `mercado_atletas.csv` isoladamente (já teve erros confirmados — sempre cruzar com notícia real).

### ⚠️ Ressalva sobre a Camada 6 (odds mockadas)

O documento gerado pelo DeepSeek (`CARTOLA_ANALISADOR_EXTREMO_MD.txt`) inclui uma tabela de "Fator Poder" baseada em odds de apostas — mas o próprio script do documento declara essas odds como **`ODDS_MOCKADOS`, um placeholder** ("substituir por API em produção"), não dados reais de casa de apostas. Ou seja:
- A coluna `score_ajustado`/`score_oportunidade` do CSV (`ranking_oportunidade_rodada_26_ajustado.csv`) é **utilizável** como segunda opinião de modelo — ela é calculada e consistente, mesmo que a metodologia exata de "força de time/adversário" não esteja 100% documentada.
- Já a tabela específica de "Fator Poder" com % de vitória/over gols do texto do DeepSeek **não deve ser tratada como sinal real** até que odds de verdade (The Odds API, FootyStats etc. — ver Integrações Futuras) sejam plugadas.
- Antes de aceitar qualquer output de IA externa (DeepSeek ou outra) como camada válida, checar se os dados de entrada são reais ou mockados — isso já pegou um erro nesta rodada.

## Fórmula do modelo (estado atual)

```
score_cruzado = 0.6 * conquistado_ponderado + 0.4 * cedido_pelo_adversario
score_final = score_cruzado + ajuste_mando
```
- `conquistado_ponderado`: média de pontos do jogador nas últimas 5 rodadas, com decaimento temporal (pesos 0.2 → 1.0, rodada mais recente pesa mais).
- `cedido_pelo_adversario`: quanto o adversário-alvo cede à posição, na mesma janela.
- `ajuste_mando`: bônus/penalidade fixo por jogar em casa/fora.
- Mínimo de 3 jogos na janela para o atleta entrar no ranking.

---

## ⚠️ VALIDAÇÃO CRÍTICA DOS PARÂMETROS (Parte 2 — dados reais, Rodada 26)

Rodei os números do `cruzamento_rodada_26_v2.csv` (326 atletas) para testar se os parâmetros atuais fazem o que deveriam fazer. Três achados importantes:

### 1. `ajuste_mando` está praticamente sem efeito prático

- Range real: **-0.284 a +0.284** (média ≈ 0, desvio-padrão 0.168) — num score que varia de 0.99 a 10.65.
- Correlação entre `score_cruzado` (sem mando) e `score_final` (com mando): **0.9946**. Isso significa que o ajuste de mando explica menos de 1% da variação do score final — ele existe na fórmula, mas não move o ranking na prática.
- **Diagnóstico**: o fator de mando está subdimensionado. Se a intenção é que jogar em casa realmente pese na decisão (e o pedido de priorizar mandantes confirma que sim), o ajuste precisa ter magnitude maior, calibrada com dados reais de home/away das 25 rodadas já disputadas (você tem esse histórico completo em `partidas_1_a_25.csv` + `scouts_rodadas_1_a_25_completo.csv`).
- **Ação recomendada**: calcular, por posição, a diferença real de pontuação média em casa vs. fora nas 25 rodadas (não um valor fixo arbitrário), e aplicar esse delta como multiplicador, não como somatório de ±0.28.

### 2. O modelo não penaliza volatilidade — na prática, prefere "Explosivo"

- Correlação entre `desvio_padrao` e `score_final`: **+0.53** (positiva e considerável). Ou seja, jogadores mais instáveis tendem a ter score final mais alto, porque picos pontuais de pontuação puxam a média ponderada para cima.
- Na otimização da Parte 1, 8 dos 12 titulares da escalação agressiva têm perfil "Explosivo" — não porque eu busquei isso, mas porque o próprio `score_final` já embute esse viés.
- **Diagnóstico**: não há problema em aceitar risco (é a estratégia consciente do Fathur FC), mas hoje o modelo não permite *escolher* o nível de risco — ele empurra para o perfil explosivo por padrão, escondido dentro do score.
- **Ação recomendada**: separar o score em dois números — `score_teto` (atual, sem penalização) e `score_piso` = `score_final − k×desvio_padrao` (k sugerido: 0.4–0.6, testável). Escalação conservadora usa `score_piso`; agressiva usa `score_teto`. Isso já foi simulado manualmente na Parte 1 desta rodada e funcionou bem como separação de escalações.

### 3. A normalização "0-10" não é uma normalização de fato

- Distribuição real do `score_final`: mínimo 0.99, máximo 10.65, mediana **3.85**, mas fortemente assimétrica à direita.
- Por posição, a mediana varia muito: TEC = 5.62, LAT = 4.75, ZAG = 3.87, MEI = 3.45, ATA = 3.35, GOL = 3.83.
- **Isso quer dizer que um "score 5" de técnico não é comparável a um "score 5" de atacante** — técnicos estão sistematicamente mais altos na escala. Isso pode distorcer decisões de custo-benefício entre posições diferentes se comparadas diretamente.
- **Ação recomendada**: normalizar por posição (z-score ou min-max dentro de cada posição), não globalmente. Manter um `score_bruto` (atual) para referência, mas adicionar `score_normalizado_pos` para comparações justas entre setores.

### 4. Janela de 5 rodadas / mínimo 3 jogos

- Na Rodada 26, a distribuição de `jogos_disputados` no ranking é: 3 jogos (109 atletas), 4 jogos (122), 5 jogos (95). Ou seja, **quase 1/3 da base está tomando decisão com apenas 3 jogos de amostra** — estatisticamente frágil, principalmente para jogadores "Explosivo" onde 1 grande atuação isolada já infla a média.
- Agora que você tem 25 rodadas de histórico completo, a janela de 5 pode ser testada contra alternativas maiores (8-10 rodadas) via backtest real, não só teoricamente.
- **Ação recomendada**: manter janela de 5 como "forma recente" mas criar uma segunda métrica de janela 10 como "baseline de temporada", e usar a divergência entre as duas como sinal extra (jogador em alta vs. jogador regressando à média).

---

## Novas features sugeridas

- **Cruzamento xG conquistado × XGA cedido (nova camada, validada na Rodada 26)**: em vez de só cruzar pontos de scout (`conquistado × cedido`), cruzar xG do time (mando específico) contra o XGA que o adversário cede no mesmo contexto de mando. Fórmula proposta:
  ```
  fator_xG = xG_conquistado_time * (XGA_media_liga / XGA_cedido_adversario)
  ```
  Fator > 1 = ataque mais forte que a defesa que vai enfrentar (ex.: Rodada 26, Flamengo fora 1.92 xG vs Remo casa XGA 1.50 → jogo favorável, confirmado pelo resultado real). Fator < 1 = defesa do adversário mais sólida que o volume de xG sugere isoladamente (ex.: Fluminense casa 1.97 xG vs Vasco fora XGA 0.98, o melhor XGA-fora do campeonato → volume ofensivo bom no papel, mas esbarra na defesa visitante mais eficiente da rodada). Aplicar principalmente em MEI/ATA, onde xG se relaciona mais diretamente com pontuação real (gol/assistência/finalização). Para ZAG/GOL/LAT, o equivalente é o XGA do próprio time (proxy de chance de SG).
- **Sequência de jogos (fixture congestion)**: nº de dias desde o último jogo, jogos em 3 competições simultâneas (desgaste) — dá pra derivar de `partidas_1_a_25.csv` cruzando datas.
- **Fator clássico/derbi — corrigido (Rodada 26)**: a hipótese original (fonte DeepSeek) era clássico = +10% no score. O caso Fluminense x Vasco mostrou que isso está errado na direção: o jogo teve o maior xG casa da rodada de um lado e o melhor XGA fora da rodada do outro — ou seja, clássico não aumenta o valor esperado, aumenta a **incerteza**. Proposta corrigida: clássico ajusta o desvio-padrão, não o score:
  ```
  desvio_padrao_ajustado = desvio_padrao_base * fator_classico   (fator_classico ≈ 1.15–1.25, a calibrar com mais rodadas)
  score_final permanece inalterado
  ```
  Na prática, isso deveria se traduzir em **cautela de concentração** (não capitanear, não empilhar excesso de peças de um clássico), não em preferência extra — alinhado com a leitura qualitativa que a própria TCC deu para este jogo.
- **Sequência de mando**: 3 jogos em casa seguidos vs. alternado — afeta ritmo do time.
- **Head-to-head**: histórico do jogador especificamente contra aquele adversário nas últimas temporadas (não só "cedido médio" do adversário a todos).
- **Flag de status automatizada**: cruzar `status` do mercado com uma fonte de notícias estruturada (ver Integrações Futuras) em vez de checagem manual a cada rodada.

## Ajustes de parâmetros — resumo de prioridade

| Parâmetro | Situação atual | Problema identificado | Ajuste sugerido |
|---|---|---|---|
| `ajuste_mando` | ±0.284 fixo | Correlação 0.99 com score sem mando = efeito quase nulo | Calibrar com delta real casa/fora por posição via histórico |
| Penalização de volatilidade | Nenhuma | Correlação +0.53 entre desvio e score = viés pró-explosivo oculto | Criar `score_piso` = score − k×desvio_padrao |
| Normalização | "0-10" nominal | Mediana varia de 3.35 (ATA) a 5.62 (TEC); comparação entre posições distorcida | Normalizar por posição, não globalmente |
| Janela temporal | 5 rodadas, mín. 3 jogos | 1/3 da base decide com só 3 jogos de amostra | Manter janela curta + adicionar janela longa (10) como baseline |
| Curva de decaimento | Linear 0.2→1.0 | Não testada contra alternativa exponencial | Backtestar exponencial (ex: peso = 0.7^(n-rodada)) contra a linear atual usando as 25 rodadas históricas |

## Métricas de performance / validação pós-rodada

Para cada rodada, comparar:
1. **Erro médio absoluto (MAE)**: `|pontos_reais − score_final_previsto|` por jogador escalado.
2. **Taxa de acerto de capitão**: capitão escolhido estava no top-3 real de pontuação da rodada entre os titulares? (sim/não, acumulado ao longo da temporada)
3. **Correlação de Spearman** entre ranking previsto e ranking real de pontuação da rodada (mede se a *ordem* está certa, não só o valor absoluto).
4. **Calibração do mando**: pontos médios reais de jogadores em casa vs. fora, comparado ao `ajuste_mando` usado — feedback direto para recalibrar o parâmetro acima.

Um dashboard simples (ver `TEMPLATE_POS_RODADA.md`) já cobre isso rodada a rodada.

## Validação empírica da Camada 6 — Rodada 26

- Correlação de Spearman entre `score_final` e `score_ajustado`: **0.84** — concordância forte, mas não total; divergências valem investigação pontual (ex: técnico Marcão subiu no ajustado por capturar melhor o efeito casa+adversário fraco que o `ajuste_mando` original subestima — achado nº1 desta metodologia confirmado na prática).
- `score_ajustado` é sistematicamente **mais baixo** que `score_final` (diferença média de -1,33), ou seja, a camada 6 pune mais forte do que gratifica — bom contrapeso para o viés pró-"Explosivo" identificado no achado nº2.
- **Lição operacional**: mercado (`mercado_atletas.csv`) pode perder jogadores entre uma exportação e outra (ex: Allan/PAL sumiu do arquivo entre duas versões da mesma rodada) — sempre re-cruzar contra a versão mais recente do mercado antes de fechar, mesmo que o ranking pareça igual.
- Ganho estimado ao usar a escalação combinada (`score_final` + `score_ajustado` normalizados, média) vs. uma escalação por intuição/ancoragem: **+~10 pontos de score projetado** na Rodada 26, principalmente por evitar jogadores caros e inconsistentes (Arrascaeta, Matheus Bidu) que os dois modelos já sinalizavam como "evitar".

## Camada 5 (odds) — ativada com dado real a partir da Rodada 26

A TCC passou a fornecer, junto do conteúdo semanal, uma tabela de probabilidades por time (vitória, SG, 2+ gols) com fonte declarada em cotações reais de bolsas esportivas — isso substitui, na prática, o buraco que tínhamos identificado (a camada de odds do DeepSeek era mockada). A partir de agora, ao fechar qualquer rodada:
- Cruzar `preco_num`/`score_final`/`score_ajustado` dos titulares contra essa tabela de probabilidade do time.
- Qualquer titular cujo clube tenha probabilidade de vitória sensivelmente abaixo dos demais (ex: Rodada 26 — Acevedo/BAH com 26% contra 47%+ do resto do elenco) deve ser reavaliado, mesmo que o score interno o favoreça.
- **Caso real (Rodada 26)**: Acevedo (BAH, score interno ok) foi trocado por Martinelli (FLU, mais barato e com o time em 54% de vitória/50% de 2 gols) depois desse cruzamento — ganho de saldo + redução de risco por concentração no time mais provável de pontuar bem na rodada.

## Camada de confronto específico — implementada e testada (Rodada 26)

Script: `calcular_confronto.py`. Resolve a "cegueira" do `score_final` (média de forma, cega ao adversário específico) cruzando conquistado do jogador × cedido do adversário em 3 categorias de scout (finalização, participação em gol, falta sofrida), últimos 3 jogos por mando — mesma lógica que a TCC usa nos cards de indicação.

**Validação real**: rodando contra a base completa de Rodada 26, o top 10 de maior divergência (`score_confronto` alto com `score_final` mediano) trouxe 3 nomes que a TCC já tinha destacado manualmente em lives anteriores sem qualquer dica prévia — Garro (COR x CHA), Matheus Pereira (CRU x CAP) e Carbonero (INT x SAN). Confirma que a lógica geral está certa.

**Limite conhecido**: o caso que motivou a criação do script (Arrascaeta x Remo, indicado como Unanimidade pela TCC) não apareceu como divergência forte nessa primeira versão — a categoria "finalização" (FT+FD+FF+G somados) provavelmente dilui o sinal que a TCC pega separando métricas (ela trata "FF+FT" e "chute a gol" como eixos distintos). Próximo passo: separar as categorias como a TCC faz, e rodar toda rodada comparando contra os selos dela (Confiança A/B, Unanimidade) como métrica de validação — mesma lógica do log de divergência que já usamos pra outras fontes.

## Automação da pipeline — plano até a Rodada 38

A partir da Rodada 26, o projeto ganhou 5 peças que rodam em sequência (`pipeline_semanal.py` orquestra todas):

1. `coleta_dados_cartola.py` (Colab, manual — API exige autenticação)
2. `coletar_fontes_gratuitas.py` (automático — tenta xG via FBref; odds e notícia ficam como stub documentado, ver ressalva abaixo)
3. `calcular_conquistado_cedido.py` + `calcular_confronto.py` (automáticos)
4. Conteúdo da TCC (**continua manual** — não tem API, e a leitura de jogo/bastidor dela é trabalho humano que não dá pra scraping)
5. `validar_rodada.py` (automático, pós-rodada — grava linha em `log_aproximacao_rodadas.csv`)

**GitHub Actions** (`.github/workflows/rodada.yml`) automatiza a etapa pré-rodada toda sexta-feira, sem precisar rodar nada manualmente — mas o número da rodada no workflow precisa ser atualizado toda semana até isso virar automático de verdade (calculado pela data).

### Ressalva sobre as fontes gratuitas

`coletar_fontes_gratuitas.py` tem 3 funções: `buscar_xg_fbref` (funcional, mas não testada em produção — rede bloqueada no ambiente onde foi escrita), e `buscar_odds_publicas`/`buscar_noticias_escalacao` (stubs propositais — scraping direto de site de odds/notícia quebra com frequência e alguns bloqueiam bot; a alternativa mais estável enquanto não se decide uma fonte fixa é pedir a busca manual ao Claude dentro da conversa, como já vem sendo feito). Isso significa: **por enquanto, odds e notícia continuam vindo da TCC ou de busca manual — só o xG tem chance real de ficar 100% automático**.

### Meta explícita: aproximar da qualidade da TCC até a Rodada 38

Ficam ~12 rodadas pra testar e calibrar. A cada rodada:
- Rodar `validar_rodada.py` com o resultado real → grava MAE, Spearman, acerto de capitão e desempenho dos riscos de Dúvida assumidos em `log_aproximacao_rodadas.csv`.
- Comparar picks nossos vs. picks da TCC vs. resultado real — já fizemos isso manualmente nesta rodada (Ignácio, Garro/Matheus Pereira, Léo Pereira) e vale continuar registrando como "placar de acerto por fonte", conforme já estava no plano da Parte 2.
- Se a tendência do MAE cair e o Spearman subir consistentemente ao longo das rodadas, é sinal de que a metodologia própria está de fato se aproximando da qualidade da TCC — decisão de cancelar ou não a assinatura pode ser tomada com esse dado na mão, em vez de no feeling.

### Recalibração do `ajuste_mando` — feita, com achado honesto (backtest real, 25 rodadas)

Script: `recalibrar_mando.py`. Substitui o valor fixo ±0.28 por delta real por posição:

| Posição | Delta real (casa − fora) | Significativo? |
|---|---|---|
| TEC | +1.06 | Sim (p<0.001) |
| ZAG | +0.81 | Sim (p<0.001) |
| LAT | +0.88 | Sim (p<0.001) |
| ATA | +0.68 | Sim (p<0.001) |
| MEI | +0.49 | Sim (p<0.001) |
| GOL | +0.27 | **Não** (p=0.44) — considerar não aplicar mando pra goleiro |

**Achado importante**: o efeito é estatisticamente real (o valor fixo de fato subestimava ZAG, LAT e TEC em até 4x), mas o ganho de precisão numa previsão de jogo único é pequeno (~0.1% de MAE geral, ~1% no TEC) — porque o desvio-padrão natural de pontuação por jogo (2.5 a 4.4) é bem maior que o próprio efeito de mando (0.3 a 1.0). **Vale corrigir (é dado melhor sem custo), mas essa não é a maior alavanca de precisão do projeto.** Isso está registrado pra não repetir a expectativa errada da próxima vez — a camada que realmente move a agulha (diferenças de 3-5 pontos, não 0.3) é o confronto específico (`calcular_confronto.py`).

### Score_teto / score_piso — implementado (Rodada 26)

Script: `calcular_teto_piso.py`. Resolve o viés pró-"Explosivo" (achado original: `desvio_padrao` correlacionava +0.53 com `score_final`, empurrando pra volatilidade sem escolha). Agora:

```
score_teto = score_final                          (escalação agressiva)
score_piso = score_final − k × desvio_padrao       (escalação conservadora, k=0.6 por padrão)
```

**`k` calibrado com backtest real** (25 rodadas, ~6000 observações), não no chute: k=0.6 protege em 65% dos jogos (a pontuação real ficou igual ou acima do piso projetado), custando em média -1,93 pts de projeção. k mais alto = mais seguro, mais pessimista — não existe valor "certo", é escolha de apetite de risco. Tabela completa de k no script.

**Validação de comportamento** (Rodada 26): Marcão (baixa volatilidade) perde só 0,44 pts do teto pro piso; Hulk (Explosivo) perde 3,77 pts — a separação funciona como esperado, discriminando risco real por jogador, não só por posição.

### Normalização por posição — implementada (Rodada 26)

Script: `calcular_normalizacao_posicao.py`. Resolve o achado original (mediana de score_final variava de 3,35 em ATA a 5,62 em TEC — "score 5" não era comparável entre posições). Baseline calculado com 25 rodadas de histórico (não só a rodada atual, pra não oscilar):

| Posição | Média histórica | Desvio |
|---|---|---|
| GOL | 4,08 | 1,74 |
| LAT | 4,46 | 2,08 |
| ZAG | 3,20 | 1,50 |
| MEI | 3,06 | 2,10 |
| ATA | 3,81 | 2,52 |
| TEC | 4,99 | 1,32 |

`score_normalizado_pos = (score_final − média_hist_pos) / desvio_hist_pos` (z-score).

**Validação prática (Rodada 26)**: Ignácio (ZAG, score bruto 6,79) normaliza pra +2,40 desvios — quase no mesmo patamar relativo do Hulk (ATA, score bruto 10,65 → +2,72), mesmo o score bruto do Hulk sendo 57% maior. Confirma que comparações de custo-benefício entre posições diferentes (ex: "top 5 custo-benefício" feito no início da rodada) estavam sistematicamente injustas com posições de baseline mais baixo (ZAG, MEI). Usar `score_normalizado_pos` a partir de agora pra qualquer ranking que misture posições.

**Etapa 1 da metodologia — status final**: chave de junção segura ✅, recalibração de mando ✅ (impacto pequeno, ~0,3 pts), score_teto/score_piso ✅ (impacto grande, 1,9-3,8 pts), normalização por posição ✅ (impacto médio, corrige comparação injusta entre posições). As 4 falhas críticas originais estão endereçadas.

## Integrações futuras

- **API de notícias em tempo real** (lesão/suspensão): reduz dependência do campo `status` manual e de checagem humana no GE.
- **Dados de odds**: já mapeado como camada 5; formalizar como coluna estruturada no CSV de cruzamento em vez de consulta manual.
- **Rankings de especialistas**: agregar 2-3 rankings públicos (ge.globo, cartola.globo "cartoletas") como camada de consenso adicional.
- **Dados históricos de temporadas anteriores**: importar do Project separado de API do Cartola — prioridade alta, já sinalizada como próximo passo.
