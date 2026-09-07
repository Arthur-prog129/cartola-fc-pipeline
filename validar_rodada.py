"""
validar_rodada.py
------------------
Fecha o loop de validação da metodologia (Parte 2 — métricas de performance).

Uso:
    1. Rode o coleta_dados_cartola.py (Colab) depois que a rodada fechar, pra gerar
       o CSV oficial de pontos+scouts da rodada (mesmo formato de
       scouts_rodadas_1_a_25_completo.csv, mas só com a rodada nova).
    2. python validar_rodada.py --resultado_real caminho/rodada_26_real.csv

O script cruza o resultado real contra:
    - Nossa projeção interna (score_final) — todos os titulares e reservas do time
    - O status de risco assumido (Dúvida) — pra ver se compensou
    - A escolha de capitão
    - MAE, correlação de Spearman (ordem prevista vs ordem real) pro nosso elenco

Isso alimenta a métrica de performance da metodologia (Parte 2): "Como validar o
modelo após cada rodada? Como comparar com resultados reais?"
"""
import pandas as pd
import numpy as np
from scipy.stats import spearmanr
import argparse
import os
from datetime import datetime

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log_aproximacao_rodadas.csv')

# ============================================================================
# 🔧 EDITAR ISSO A CADA RODADA (os 2 únicos pontos deste arquivo que mudam):
#    1. TIME_R26 → renomeie e atualize com o time e as projeções da rodada nova
#    2. CAPITAO  → o nome do capitão daquela rodada
# O resto do arquivo (funções, lógica de comparação) não precisa mexer nunca.
# ============================================================================

# Time fechado da Rodada 26 (Fathur FC) — projeção registrada no momento do fechamento
# atleta_id é a CHAVE PRIMÁRIA de junção (nunca usar só apelido — já pegamos nomes
# duplicados reais nesse próprio time: Gustavo Henrique, Matheuzinho e Renê têm
# homônimos em outros clubes na base do Cartola).
TIME_R26 = [
    # atleta_id, apelido,           pos,  status,     score_final_previsto, titular
    (104084, 'Carlos Miguel',    'GOL', 'Provável', 7.70,  True),
    (83528,  'Léo Pereira',      'ZAG', 'Provável', 3.78,  True),
    (78248,  'Gustavo Henrique', 'ZAG', 'Provável', 4.24,  True),   # COR (não confundir c/ o do SAN, id 141776)
    (101727, 'Matheuzinho',      'LAT', 'Provável', 5.08,  True),   # COR (não confundir c/ o do VIT, id 90703)
    (78445,  'Renê',             'LAT', 'Provável', 6.22,  True),   # FLU (não confundir c/ o do VIT, id 130209)
    (87863,  'Arrascaeta',       'MEI', 'Provável', 4.12,  True),
    (105436, 'Carrascal',        'MEI', 'Dúvida',   7.81,  True),
    (117632, 'Garro',            'MEI', 'Provável', 3.86,  True),
    (94583,  'Pedro',            'ATA', 'Provável', 6.14,  True),   # CAPITÃO
    (113103, 'Flaco López',      'ATA', 'Provável', 7.94,  True),
    (98873,  'Samuel Lino',      'ATA', 'Provável', 9.02,  True),
    (None,   'L. Jardim',        'TEC', 'Provável', None,  True),   # técnico, sem atleta_id de jogador
    (91101,  'Ronaldo',          'GOL', 'Provável', 3.74,  False),
    (106313, 'Domingos Duarte',  'ZAG', 'Provável', 4.22,  False),
    (101319, 'Guga',             'LAT', 'Provável', None,  False),
    (105647, 'Maurício',         'MEI', 'Dúvida',   6.54,  False),
    (39148,  'Hulk',             'ATA', 'Provável', 9.77,  False),  # reserva de luxo
]
CAPITAO = 'Pedro'
CAPITAO_ID = 94583


def carregar_projecao():
    df = pd.DataFrame(TIME_R26, columns=['atleta_id', 'apelido', 'pos', 'status', 'score_previsto', 'titular'])
    return df


def gravar_log(rodada, mae, spearman_rho, acertou_capitao, n_duvidas_assumidas, duvidas_media):
    """Acrescenta uma linha no histórico — é isso que permite ver a evolução
    real da metodologia rodada a rodada até a 38, em vez de só comparar
    pontualmente. Roda toda vez que validar_rodada.py roda; nunca sobrescreve
    linha de rodada já gravada (atualiza se já existir)."""
    linha = pd.DataFrame([{
        'rodada': rodada,
        'data_validacao': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'mae': round(mae, 2) if mae is not None else None,
        'spearman_rho': round(spearman_rho, 2) if spearman_rho is not None else None,
        'capitao_acertou': acertou_capitao,
        'n_duvidas_assumidas': n_duvidas_assumidas,
        'media_pontos_duvidas': round(duvidas_media, 2) if duvidas_media is not None else None,
    }])
    if os.path.exists(LOG_PATH):
        log = pd.read_csv(LOG_PATH)
        log = log[log['rodada'] != rodada]  # remove duplicata se já validou essa rodada antes
        log = pd.concat([log, linha], ignore_index=True).sort_values('rodada')
    else:
        log = linha
    log.to_csv(LOG_PATH, index=False)
    print(f"\n📊 Log atualizado: {LOG_PATH}")
    if len(log) >= 2:
        print("Tendência do MAE nas últimas rodadas validadas:")
        print(log[['rodada', 'mae', 'spearman_rho', 'capitao_acertou']].tail(5).to_string(index=False))


def validar(resultado_real_path, rodada):
    real = pd.read_csv(resultado_real_path)
    proj = carregar_projecao()

    # CHAVE DE JUNÇÃO SEGURA: atleta_id primeiro (nunca falha por homônimo).
    # Fallback pra apelido+clube só existe pra compatibilidade com CSVs manuais
    # antigos que não tinham atleta_id (ex: o resultado de teste que usamos
    # antes desta correção) — mas fallback por apelido sozinho NUNCA é usado,
    # porque foi exatamente isso que causou risco de erro com nomes duplicados
    # (Gustavo Henrique, Matheuzinho, Renê — todos têm homônimo em outro clube).
    if 'atleta_id' in real.columns:
        merged = proj.merge(real[['atleta_id', 'clube', 'pontos']], on='atleta_id', how='left',
                             suffixes=('', '_real'))
        modo_juncao = 'atleta_id (seguro)'
    else:
        print("⚠️  AVISO: resultado_real não tem coluna 'atleta_id' — usando fallback "
              "apelido+clube (mais seguro que apelido sozinho, mas ainda pode falhar "
              "se o CSV grafar o clube diferente do nosso). Prefira sempre exportar "
              "com atleta_id quando possível (coleta_dados_cartola.py já faz isso).")
        merged = proj.merge(real[['apelido', 'clube', 'pontos']], on='apelido', how='left')
        modo_juncao = 'apelido+clube (fallback)'

    print(f"[chave de junção usada: {modo_juncao}]")

    print("=" * 70)
    print(f"RESULTADO REAL x PROJEÇÃO — RODADA {rodada} — FATHUR FC")
    print("=" * 70)
    merged['erro_abs'] = (merged['pontos'] - merged['score_previsto']).abs()
    print(merged[['apelido', 'pos', 'status', 'score_previsto', 'pontos', 'erro_abs']]
          .to_string(index=False))

    titulares = merged[merged['titular']]
    com_projecao = titulares.dropna(subset=['score_previsto', 'pontos'])

    mae = com_projecao['erro_abs'].mean()
    print(f"\nMAE (titulares com projeção): {mae:.2f} pontos")

    rho = None
    if len(com_projecao) >= 3:
        rho, p = spearmanr(com_projecao['score_previsto'], com_projecao['pontos'])
        print(f"Correlação de Spearman (ordem prevista x ordem real): {rho:.2f} (p={p:.3f})")

    # Acerto de capitão: o capitão estava no top-3 real entre os titulares?
    top3_real = titulares.sort_values('pontos', ascending=False).head(3)['apelido'].tolist()
    acertou_capitao = CAPITAO in top3_real
    print(f"\nCapitão ({CAPITAO}) estava no top-3 real dos titulares? {'SIM' if acertou_capitao else 'NÃO'}")
    print(f"Top-3 real: {top3_real}")

    # Risco de Dúvida: compensou?
    duvidas = merged[merged['status'] == 'Dúvida']
    print("\n--- Jogadores com risco de Dúvida assumido ---")
    print(duvidas[['apelido', 'pontos']].to_string(index=False))
    duvidas_media = duvidas['pontos'].mean() if len(duvidas) else None

    gravar_log(rodada, mae, rho, acertou_capitao, len(duvidas), duvidas_media)

    return merged


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--resultado_real', required=True,
                     help='CSV com colunas: apelido, clube, pontos (da rodada real)')
    ap.add_argument('--rodada', type=int, required=True,
                     help='Número da rodada (precisa bater com o TIME_R26 hardcoded acima — '
                          'ver aviso na docstring do módulo)')
    args = ap.parse_args()

    if args.rodada != 26:
        print("⚠️  ATENÇÃO: TIME_R26 no topo do arquivo está fixo pra Rodada 26.")
        print("   Pra validar outra rodada, atualize essa lista manualmente com o time e as")
        print("   projeções daquela rodada específica antes de rodar — senão a comparação")
        print("   vai usar o time errado. Melhoria futura: carregar de um CSV por rodada")
        print("   em vez de hardcoded (ver TODO no código).")

    validar(args.resultado_real, args.rodada)
