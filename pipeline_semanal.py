"""
pipeline_semanal.py
--------------------
Orquestra o fluxo da rodada numa sequência só. Não substitui os scripts
individuais — só chama eles na ordem certa e para nos pontos que ainda
precisam de você.

Fluxo por rodada:
  1. [MANUAL — Colab] coleta_dados_cartola.py → gera CSVs de scouts/mercado/partidas
  2. [AUTOMÁTICO] coletar_fontes_gratuitas.py → tenta puxar xG/odds públicos
  3. [MANUAL — você] Conteúdo da TCC (live/PDF) → colar na conversa com Claude,
     ou salvar em texto/CSV estruturado se quiser alimentar isso aqui depois
  4. [AUTOMÁTICO] calcular_conquistado_cedido.py → score_final por jogador
  5. [AUTOMÁTICO] calcular_confronto.py → score_confronto (camada de matchup)
  6. [MANUAL — decisão] Você fecha o time, com ajuda do Claude cruzando tudo
  7. [AUTOMÁTICO, pós-rodada] validar_rodada.py → MAE, Spearman, acerto de capitão,
     e agora também grava uma linha em log_aproximacao_rodadas.csv

Marcado [AUTOMÁTICO] = roda sozinho, sem sua decisão no meio.
Marcado [MANUAL] = precisa de você (decisão, leitura de jogo, ou rodar o Colab
à parte porque a API do Cartola exige o ambiente do Colab autenticado).

Uso:
    python pipeline_semanal.py --rodada 27 --etapa coleta
    python pipeline_semanal.py --rodada 27 --etapa pos_rodada --resultado_real caminho.csv
"""
import argparse
import subprocess
import sys
import os

PASTA = os.path.dirname(os.path.abspath(__file__))


def rodar(script, args_extra=None):
    cmd = [sys.executable, os.path.join(PASTA, script)] + (args_extra or [])
    print(f"\n>>> Rodando {script} {' '.join(args_extra or [])}")
    resultado = subprocess.run(cmd, capture_output=True, text=True)
    print(resultado.stdout)
    if resultado.returncode != 0:
        print(f"⚠️  {script} terminou com erro:\n{resultado.stderr}")
    return resultado.returncode == 0


def etapa_pre_rodada(rodada):
    print(f"=== PRÉ-RODADA {rodada} ===")
    print("1. Buscando dados oficiais (mercado + partidas) direto da API do Cartola...")
    rodar('coleta_dados_cartola.py', ['--modo', 'pre_rodada', '--rodada', str(rodada)])
    print("2. Tentando puxar fontes gratuitas extras (xG público)...")
    ok = rodar('coletar_fontes_gratuitas.py')
    if not ok:
        print("   → Falhou ou não configurado. Seguir com dado manual/TCC pra essa rodada.")
    print("3. [MANUAL] Cole o conteúdo da TCC (live/PDF) na conversa com o Claude "
          "quando sair, pra cruzar junto com o resto.")
    print(f"4. Rodando calcular_confronto.py pra rodada {rodada}...")
    rodar('calcular_confronto.py', ['--rodada_alvo', str(rodada)])
    print("\nPré-rodada pronta pra você (e o Claude) decidirem a escalação final.")


def etapa_pos_rodada(rodada, resultado_real_path=None):
    print(f"=== PÓS-RODADA {rodada} ===")
    if resultado_real_path is None:
        print("Buscando resultado oficial direto da API do Cartola (rodada precisa estar fechada)...")
        rodar('coleta_dados_cartola.py', ['--modo', 'pos_rodada', '--rodada', str(rodada)])
        resultado_real_path = f"scouts_rodada_{rodada}.csv"
    ok = rodar('validar_rodada.py', ['--resultado_real', resultado_real_path, '--rodada', str(rodada)])
    if ok:
        print(f"Validação da rodada {rodada} concluída. "
              "Ver log_aproximacao_rodadas.csv pra acompanhar a evolução até a rodada 38.")
    else:
        print("Validação falhou — checar se o CSV de resultado real está no formato certo "
              "(colunas: apelido, clube, pontos).")


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--rodada', type=int, required=True)
    ap.add_argument('--etapa', choices=['pre_rodada', 'pos_rodada'], required=True)
    ap.add_argument('--resultado_real', default=None,
                     help='Opcional pra --etapa pos_rodada: se não passar, busca da API oficial')
    args = ap.parse_args()

    if args.etapa == 'pre_rodada':
        etapa_pre_rodada(args.rodada)
    else:
        etapa_pos_rodada(args.rodada, args.resultado_real)
