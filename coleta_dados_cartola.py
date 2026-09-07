"""
coleta_dados_cartola.py
-------------------------
Puxa dados direto da API pública do Cartola FC — os 3 endpoints usados aqui
NÃO exigem login/autenticação (são os mesmos que o site oficial usa por trás
dos panos pra mostrar mercado, jogos e pontuação).

⚠️ Isso é API não-documentada oficialmente (a Globo não publica um manual),
mantida pela comunidade de desenvolvedores de Cartola. Ela pode mudar sem
aviso — se algum dia parar de funcionar, o fallback é voltar pro processo
manual (Colab) que você já usava.

Endpoints usados:
  - https://api.cartola.globo.com/atletas/mercado
      → status, preço, clube de TODOS os atletas (rodada atual, sempre "ao vivo")
  - https://api.cartola.globo.com/partidas/{rodada}
      → jogos (mandante/visitante, data/hora) de uma rodada específica
  - https://api.cartola.globo.com/atletas/pontuados/{rodada}
      → pontos + scouts de todos os atletas numa rodada JÁ FECHADA

Uso:
    python coleta_dados_cartola.py --modo pre_rodada --rodada 27
    python coleta_dados_cartola.py --modo pos_rodada --rodada 26
"""
import requests
import pandas as pd
import argparse
import time
import sys

BASE_URL = "https://api.cartola.globo.com"
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; FathurFC-pipeline/1.0)'}


def buscar_mercado():
    """Status/preço/clube de todos os atletas — sempre reflete o momento atual."""
    r = requests.get(f"{BASE_URL}/atletas/mercado", headers=HEADERS, timeout=20)
    r.raise_for_status()
    dados = r.json()

    clubes = {int(k): v['abreviacao'] for k, v in dados['clubes'].items()}
    posicoes = {int(k): v['abreviacao'].upper() for k, v in dados['posicoes'].items()}
    status_map = {int(k): v['nome'] for k, v in dados['status'].items()}

    linhas = []
    for atleta in dados['atletas']:
        linhas.append({
            'atleta_id': atleta['atleta_id'],
            'apelido': atleta['apelido'],
            'clube': clubes.get(atleta['clube_id'], '???'),
            'posicao': posicoes.get(atleta['posicao_id'], '???'),
            'status': status_map.get(atleta['status_id'], '???'),
            'preco_num': atleta['preco_num'],
            'variacao_num': atleta['variacao_num'],
            'media_num': atleta['media_num'],
            'jogos_num': atleta['jogos_num'],
        })
    return pd.DataFrame(linhas)


def buscar_partidas(rodada):
    """Jogos de uma rodada específica (mandante x visitante, data/hora)."""
    r = requests.get(f"{BASE_URL}/partidas/{rodada}", headers=HEADERS, timeout=20)
    r.raise_for_status()
    dados = r.json()

    clubes = {int(k): v['abreviacao'] for k, v in dados['clubes'].items()}
    linhas = []
    for p in dados['partidas']:
        linhas.append({
            'rodada': rodada,
            'clube_casa': clubes.get(p['clube_casa_id'], '???'),
            'placar_casa': p.get('placar_oficial_mandante'),
            'placar_visitante': p.get('placar_oficial_visitante'),
            'clube_visitante': clubes.get(p['clube_visitante_id'], '???'),
            'data_hora': p.get('partida_data'),
        })
    return pd.DataFrame(linhas)


def buscar_pontuados(rodada):
    """Pontos + scouts de todos os atletas numa rodada JÁ FECHADA.
    Só retorna dado real depois que todos os jogos daquela rodada terminaram."""
    r = requests.get(f"{BASE_URL}/atletas/pontuados/{rodada}", headers=HEADERS, timeout=20)
    r.raise_for_status()
    dados = r.json()

    if not dados.get('atletas'):
        print(f"⚠️  Rodada {rodada} ainda sem pontuação fechada (ou não existe).")
        return None

    clubes = {int(k): v['abreviacao'] for k, v in dados['clubes'].items()}
    posicoes = {int(k): v['abreviacao'].upper() for k, v in dados['posicoes'].items()}

    linhas = []
    for atleta_id, info in dados['atletas'].items():
        scout = info.get('scout') or {}
        linhas.append({
            'rodada': rodada,
            'atleta_id': int(atleta_id),
            'apelido': info['apelido'],
            'clube': clubes.get(info['clube_id'], '???'),
            'posicao_id': info['posicao_id'],
            'pontos': info['pontuacao'],
            'G': scout.get('G', 0), 'A': scout.get('A', 0), 'FT': scout.get('FT', 0),
            'FD': scout.get('FD', 0), 'FF': scout.get('FF', 0), 'FS': scout.get('FS', 0),
            'PS': scout.get('PS', 0), 'PC': scout.get('PC', 0), 'DP': scout.get('DP', 0),
            'GS': scout.get('GS', 0), 'SG': scout.get('SG', 0), 'DS': scout.get('DS', 0),
            'CA': scout.get('CA', 0), 'CV': scout.get('CV', 0), 'GC': scout.get('GC', 0),
            'CN': scout.get('CN', 0), 'DE': scout.get('DE', 0), 'PP': scout.get('PP', 0),
            'I': scout.get('I', 0),
        })
    return pd.DataFrame(linhas)


def rodar_pre_rodada(rodada):
    print(f"=== Coletando dados PRÉ-RODADA {rodada} ===")
    print("Buscando mercado (status/preço)...")
    mercado = buscar_mercado()
    nome_mercado = f"mercado_atletas_rodada{rodada}.csv"
    mercado.to_csv(nome_mercado, index=False)
    print(f"  → {len(mercado)} atletas salvos em {nome_mercado}")

    time.sleep(1)
    print(f"Buscando partidas da rodada {rodada}...")
    try:
        partidas = buscar_partidas(rodada)
        nome_partidas = f"partidas_rodada_{rodada}.csv"
        partidas.to_csv(nome_partidas, index=False)
        print(f"  → {len(partidas)} jogos salvos em {nome_partidas}")
    except Exception as e:
        print(f"  ⚠️  Falha ao buscar partidas: {e}")


def rodar_pos_rodada(rodada, arquivo_scouts_historico=None):
    print(f"=== Coletando dados PÓS-RODADA {rodada} ===")
    pontuados = buscar_pontuados(rodada)
    if pontuados is None:
        sys.exit(1)

    nome_arquivo = f"scouts_rodada_{rodada}.csv"
    pontuados.to_csv(nome_arquivo, index=False)
    print(f"  → {len(pontuados)} atletas pontuados salvos em {nome_arquivo}")

    if arquivo_scouts_historico:
        print(f"Anexando ao histórico ({arquivo_scouts_historico})...")
        historico = pd.read_csv(arquivo_scouts_historico)
        historico = historico[historico['rodada'] != rodada]  # evita duplicar se já rodou antes
        atualizado = pd.concat([historico, pontuados], ignore_index=True).sort_values(['rodada', 'atleta_id'])
        atualizado.to_csv(arquivo_scouts_historico, index=False)
        print(f"  → Histórico atualizado: {len(atualizado)} linhas, rodadas "
              f"{atualizado['rodada'].min()} a {atualizado['rodada'].max()}")


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--modo', choices=['pre_rodada', 'pos_rodada'], required=True)
    ap.add_argument('--rodada', type=int, required=True,
                     help='⚠️ MUDA ISSO TODA RODADA — é o único número que precisa editar aqui')
    ap.add_argument('--historico', default='scouts_rodadas_1_a_25_completo.csv',
                     help='Arquivo histórico pra anexar o resultado (só usado em pos_rodada)')
    args = ap.parse_args()

    if args.modo == 'pre_rodada':
        rodar_pre_rodada(args.rodada)
    else:
        rodar_pos_rodada(args.rodada, args.historico)
