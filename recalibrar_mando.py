"""
recalibrar_mando.py
--------------------
Calcula o ajuste_mando REAL por posição (a partir de 25 rodadas de histórico),
substituindo o valor fixo ±0.28 do modelo atual.

⚠️ Este arquivo é standalone — NÃO tenho acesso ao calcular_conquistado_cedido.py
original (nunca foi enviado nesta conversa). Rode este script, pegue os valores
de DELTA_MANDO_POR_POSICAO impressos, e cole manualmente no lugar do valor fixo
no seu script original.

RESULTADO DO BACKTEST (Rodada 26, dados de 1-25):
- O efeito de mando por posição é estatisticamente real (p<0.001 pra LAT, ZAG,
  MEI, ATA, TEC — só GOL não é significativo, p=0.44).
- MAS o ganho de precisão numa previsão de jogo único é pequeno (~0.1% geral,
  ~1% no TEC) porque o desvio-padrão natural de pontuação (2.5-4.4) é bem maior
  que o efeito de mando (0.3-1.0). Vale corrigir mesmo assim (é dado melhor sem
  custo), mas não é o maior alavancador de precisão do projeto — isso está na
  camada de confronto específico (calcular_confronto.py).

Uso:
    python recalibrar_mando.py
"""
import pandas as pd
from scipy import stats
import argparse

POS_MAP = {1: 'GOL', 2: 'LAT', 3: 'ZAG', 4: 'MEI', 5: 'ATA', 6: 'TEC'}


def calcular_deltas(scouts_path, partidas_path):
    scouts = pd.read_csv(scouts_path)
    partidas = pd.read_csv(partidas_path)
    scouts['pos'] = scouts['posicao_id'].map(POS_MAP)

    casa = partidas[['rodada', 'clube_casa']].rename(columns={'clube_casa': 'clube'})
    casa['mando'] = 'casa'
    fora = partidas[['rodada', 'clube_visitante']].rename(columns={'clube_visitante': 'clube'})
    fora['mando'] = 'fora'
    mando_df = pd.concat([casa, fora])

    scouts = scouts.merge(mando_df, on=['rodada', 'clube'], how='left').dropna(subset=['pontos', 'mando'])

    resultado = {}
    for pos in POS_MAP.values():
        sub = scouts[scouts['pos'] == pos]
        casa_pts = sub[sub['mando'] == 'casa']['pontos']
        fora_pts = sub[sub['mando'] == 'fora']['pontos']
        delta = casa_pts.mean() - fora_pts.mean()
        t, p = stats.ttest_ind(casa_pts, fora_pts)
        resultado[pos] = {
            'delta_casa_menos_fora': round(delta, 3),
            'p_valor': round(p, 4),
            'significativo': p < 0.05,
            'desvio_padrao_geral': round(sub['pontos'].std(), 2),
            'n_casa': len(casa_pts),
            'n_fora': len(fora_pts),
        }
    return resultado


def imprimir_para_colar(resultado):
    print("\n" + "=" * 60)
    print("COLE ISSO NO SEU calcular_conquistado_cedido.py, substituindo")
    print("o valor fixo ±0.28 do ajuste_mando:")
    print("=" * 60)
    print("\nDELTA_MANDO_POR_POSICAO = {")
    for pos, d in resultado.items():
        obs = "" if d['significativo'] else "  # não significativo (p>0.05) — considerar não aplicar"
        print(f"    '{pos}': {d['delta_casa_menos_fora']},{obs}")
    print("}")
    print("\n# Uso: ajuste_mando = DELTA_MANDO_POR_POSICAO[pos] / 2 * (+1 se casa, -1 se fora)")
    print("# (divide por 2 porque o score_cruzado já é uma média geral do jogador;")
    print("#  o delta completo é a DIFERENÇA entre casa e fora, não o ajuste unilateral)")


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--scouts', default='/mnt/user-data/uploads/scouts_rodadas_1_a_25_completo.csv')
    ap.add_argument('--partidas', default='/mnt/user-data/uploads/partidas_1_a_25.csv')
    args = ap.parse_args()

    resultado = calcular_deltas(args.scouts, args.partidas)
    df = pd.DataFrame(resultado).T
    print(df)
    imprimir_para_colar(resultado)
