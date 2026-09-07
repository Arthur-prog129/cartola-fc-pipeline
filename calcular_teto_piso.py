"""
calcular_teto_piso.py
-----------------------
Separa o score em dois números — resolve o viés pró-"Explosivo" identificado
na Rodada 26 (score_final sozinho empurrava pra jogadores voláteis sem dar
escolha de risco pro usuário).

    score_teto = score_final (sem penalidade) → escalação agressiva
    score_piso = score_final - k * desvio_padrao → escalação conservadora

CALIBRAÇÃO DO k (backtest real, 25 rodadas, ~6000 observações jogador-rodada):
    k=0.4 → piso protege em 57% dos jogos, custa -1.29 pts de projeção
    k=0.6 → piso protege em 65% dos jogos, custa -1.93 pts   ← padrão
    k=0.8 → piso protege em 75% dos jogos, custa -2.57 pts
    k=1.0 → piso protege em 82% dos jogos, custa -3.22 pts

"Protege" = % de vezes que a pontuação real ficou IGUAL OU ACIMA do piso
projetado. Não existe k "certo" — é uma escolha de quanto risco você aceita.
k mais alto = mais seguro, mas também mais pessimista (subestima mais vezes).

Uso:
    python calcular_teto_piso.py --input cruzamento_rodada_XX.csv --k 0.6
"""
import pandas as pd
import argparse


def calcular(df, k=0.6):
    """df precisa ter as colunas: score_final, desvio_padrao (já existem no
    cruzamento_rodada_XX.csv que o pipeline já gera)."""
    df = df.copy()
    df['score_teto'] = df['score_final']
    df['score_piso'] = (df['score_final'] - k * df['desvio_padrao']).clip(lower=0)
    df['k_usado'] = k
    return df


def calibrar_k(scouts_path, ks=(0.4, 0.6, 0.8, 1.0)):
    """Recalcula a tabela de calibração acima, caso queira testar outros k
    ou revalidar quando tiver mais rodadas de histórico (ex: rodar de novo
    na Rodada 38 com dados 1-37, pra ver se a calibração muda)."""
    scouts = pd.read_csv(scouts_path).sort_values(['atleta_id', 'rodada'])
    linhas = []
    for atleta_id, grupo in scouts.groupby('atleta_id'):
        grupo = grupo.sort_values('rodada').reset_index(drop=True)
        for i in range(len(grupo)):
            hist = grupo.iloc[max(0, i - 5):i]
            if len(hist) < 3:
                continue
            linhas.append({
                'media': hist['pontos'].mean(),
                'desvio': hist['pontos'].std(),
                'real': grupo.iloc[i]['pontos'],
            })
    df = pd.DataFrame(linhas).dropna(subset=['desvio'])

    print(f"Calibração rodada com {len(df)} observações jogador-rodada")
    for k in ks:
        piso = df['media'] - k * df['desvio']
        protecao = (df['real'] >= piso).mean()
        custo = (k * df['desvio']).mean()
        print(f"k={k:.1f} | protege {protecao*100:.1f}% | custo médio -{custo:.2f} pts")


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='comando')

    p_calc = sub.add_parser('calcular', help='Aplica score_teto/score_piso num CSV de rodada')
    p_calc.add_argument('--input', required=True)
    p_calc.add_argument('--k', type=float, default=0.6)
    p_calc.add_argument('--output', default=None)

    p_cal = sub.add_parser('calibrar', help='Recalcula a tabela de calibração do k')
    p_cal.add_argument('--scouts', default='/mnt/user-data/uploads/scouts_rodadas_1_a_25_completo.csv')

    args = ap.parse_args()

    if args.comando == 'calibrar':
        calibrar_k(args.scouts)
    elif args.comando == 'calcular':
        df = pd.read_csv(args.input)
        resultado = calcular(df, k=args.k)
        saida = args.output or args.input.replace('.csv', '_teto_piso.csv')
        resultado.to_csv(saida, index=False)
        print(f"Salvo em {saida} (k={args.k})")
        print(resultado[['apelido', 'clube', 'score_teto', 'score_piso']].sort_values(
            'score_piso', ascending=False).head(15).to_string(index=False))
    else:
        ap.print_help()
