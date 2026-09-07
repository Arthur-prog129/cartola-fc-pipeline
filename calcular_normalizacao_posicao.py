"""
calcular_normalizacao_posicao.py
-----------------------------------
Resolve o problema da "normalização 0-10" que não normalizava nada de verdade
(achado original: mediana de score_final variava de 3.35 em ATA a 5.62 em TEC
— um "score 5" de técnico e de atacante não eram comparáveis).

Cria score_normalizado_pos via z-score, usando como referência a distribuição
HISTÓRICA de 25 rodadas por posição (não a distribuição só da rodada atual,
que teria amostra pequena e oscilaria rodada a rodada).

BASELINE HISTÓRICO CALCULADO (25 rodadas, ~6000 obs jogador-rodada):
    pos   média  desvio  mediana
    GOL   4.08   1.74    4.15
    LAT   4.46   2.08    4.36
    ZAG   3.20   1.50    3.20
    MEI   3.06   2.10    2.62
    TEC   4.99   1.32    4.92
    ATA   3.81   2.52    3.48

Fórmula: score_normalizado_pos = (score_final − média_hist_pos) / desvio_hist_pos

Um jogador com score_normalizado_pos = +1.0 está 1 desvio-padrão ACIMA da média
histórica da própria posição — comparável entre posições diferentes, ao
contrário do score_final bruto.

Uso:
    python calcular_normalizacao_posicao.py --input cruzamento_rodada_XX.csv
"""
import pandas as pd
import argparse

# Baseline fixo, calculado uma vez com scouts_rodadas_1_a_25_completo.csv.
# Recalcular (função recalcular_baseline abaixo) quando tiver mais rodadas —
# sugestão: revisar na Rodada 38, com a temporada mais completa.
BASELINE_POR_POSICAO = {
    'GOL': {'media': 4.080, 'desvio': 1.744},
    'LAT': {'media': 4.457, 'desvio': 2.076},
    'ZAG': {'media': 3.201, 'desvio': 1.498},
    'MEI': {'media': 3.055, 'desvio': 2.100},
    'ATA': {'media': 3.812, 'desvio': 2.519},
    'TEC': {'media': 4.986, 'desvio': 1.324},
}


def normalizar(df):
    df = df.copy()
    def z(row):
        b = BASELINE_POR_POSICAO.get(row['pos'])
        if b is None or pd.isna(row['score_final']):
            return None
        return round((row['score_final'] - b['media']) / b['desvio'], 3)
    df['score_normalizado_pos'] = df.apply(z, axis=1)
    return df


def recalcular_baseline(scouts_path, janela=5, minimo_jogos=3):
    """Recalcula o baseline com dado mais recente (rodar de novo na Rodada 38,
    por exemplo, pra ver se a distribuição por posição mudou ao longo da
    temporada)."""
    POS_MAP = {1: 'GOL', 2: 'LAT', 3: 'ZAG', 4: 'MEI', 5: 'ATA', 6: 'TEC'}
    scouts = pd.read_csv(scouts_path)
    scouts['pos'] = scouts['posicao_id'].map(POS_MAP)
    scouts = scouts.sort_values(['atleta_id', 'rodada'])

    linhas = []
    for atleta_id, grupo in scouts.groupby('atleta_id'):
        grupo = grupo.sort_values('rodada').reset_index(drop=True)
        for i in range(len(grupo)):
            hist = grupo.iloc[max(0, i - janela):i]
            if len(hist) < minimo_jogos:
                continue
            linhas.append({'pos': grupo.iloc[i]['pos'], 'score_equivalente': hist['pontos'].mean()})

    df = pd.DataFrame(linhas)
    novo_baseline = df.groupby('pos')['score_equivalente'].agg(['mean', 'std']).round(3)
    print("Novo baseline calculado — atualize BASELINE_POR_POSICAO no topo do arquivo:")
    print(novo_baseline)
    return novo_baseline


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='comando')

    p_norm = sub.add_parser('normalizar')
    p_norm.add_argument('--input', required=True)
    p_norm.add_argument('--output', default=None)

    p_recalc = sub.add_parser('recalcular_baseline')
    p_recalc.add_argument('--scouts', default='/mnt/user-data/uploads/scouts_rodadas_1_a_25_completo.csv')

    args = ap.parse_args()

    if args.comando == 'recalcular_baseline':
        recalcular_baseline(args.scouts)
    elif args.comando == 'normalizar':
        df = pd.read_csv(args.input)
        resultado = normalizar(df)
        saida = args.output or args.input.replace('.csv', '_normalizado.csv')
        resultado.to_csv(saida, index=False)
        print(f"Salvo em {saida}")
        print("\nTop 5 por posição (score_normalizado_pos):")
        for pos in BASELINE_POR_POSICAO:
            top = resultado[resultado['pos'] == pos].sort_values(
                'score_normalizado_pos', ascending=False).head(5)
            if len(top):
                print(f"\n{pos}:")
                print(top[['apelido', 'clube', 'score_final', 'score_normalizado_pos']].to_string(index=False))
    else:
        ap.print_help()
