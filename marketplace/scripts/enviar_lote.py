#!/usr/bin/env python3
"""Envia um CSV de casos ao webhook do triador e grava o resultado em resultados/.

Cada caso vira um POST separado. Não há nova tentativa automática: uma falha
vira linha de erro no resultado e o script segue para o próximo caso.

Uso:
    python3 scripts/enviar_lote.py casos/arquivo.csv [--pausa 2] [--timeout 180]
    python3 scripts/enviar_lote.py casos/arquivo.csv --ids id1,id2
"""

import argparse
import csv
import http.client
import itertools
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import date
from pathlib import Path

URL_WEBHOOK = "http://localhost:5678/webhook/review-atendimento-lote"
PASTA_RESULTADOS = Path(__file__).resolve().parent.parent / "resultados"
TIMEOUT_MINIMO_S = 120

COLUNAS_ENTRADA = [
    "id", "lote", "tipo", "nota", "texto", "nome_cliente", "id_pedido",
    "categoria_gabarito", "prioridade_gabarito", "time_gabarito", "assinado_por",
]
CAMPOS_ENVIADOS = ["tipo", "nota", "texto", "nome_cliente", "id_pedido"]
CAMPOS_OBRIGATORIOS_RESPOSTA = ["categoria_ia", "prioridade", "time"]
COLUNAS_RESULTADO = [
    "id", "lote", "tipo", "nota", "texto", "nome_cliente", "id_pedido", "assinado_por",
    "categoria_gabarito", "categoria_ia", "acerto_categoria",
    "prioridade_gabarito", "prioridade_ia", "acerto_prioridade",
    "time_gabarito", "time_ia", "acerto_time",
    "justificativa_prioridade", "resumo", "resposta_sugerida",
    "status_http", "tempo_total_s", "tempo_processamento_s",
    "versao_prompt", "modelo", "situacao", "erro",
]


def recusar(mensagem):
    sys.exit(f"RECUSADO: {mensagem}")


def ler_casos(caminho):
    try:
        # utf-8-sig aceita o BOM que planilhas costumam colocar no início do arquivo.
        with open(caminho, encoding="utf-8-sig", newline="") as arquivo:
            leitor = csv.DictReader(arquivo)
            faltando = [c for c in COLUNAS_ENTRADA if c not in (leitor.fieldnames or [])]
            if faltando:
                recusar(f"colunas ausentes no CSV: {', '.join(faltando)}")
            casos = []
            for linha in leitor:
                if None in linha:
                    recusar(f"linha {leitor.line_num} tem mais colunas que o cabeçalho")
                caso = {c: linha[c] or "" for c in COLUNAS_ENTRADA}
                caso["_linha"] = leitor.line_num
                casos.append(caso)
    except (OSError, UnicodeDecodeError, csv.Error) as erro:
        recusar(f"não consegui ler {caminho}: {erro}")
    return casos


def rotulo(caso):
    return caso["id"].strip() or f"linha {caso['_linha']}"


def validar(casos):
    """Valida o arquivo inteiro, mesmo com --ids, e devolve o nome do lote."""
    if not casos:
        recusar("o CSV não tem casos")

    sem_assinatura = [rotulo(c) for c in casos if not c["assinado_por"].strip()]
    if sem_assinatura:
        recusar(f"{len(sem_assinatura)} linha(s) sem assinado_por: {', '.join(sem_assinatura)}")

    sem_id = [f"linha {c['_linha']}" for c in casos if not c["id"].strip()]
    if sem_id:
        recusar(f"linha(s) sem id: {', '.join(sem_id)}")

    repetidos = [i for i, n in Counter(c["id"].strip() for c in casos).items() if n > 1]
    if repetidos:
        recusar(f"id(s) repetido(s): {', '.join(repetidos)}")

    # O nome do arquivo de resultado leva o lote, então ele precisa ser único.
    lotes = sorted({c["lote"].strip() for c in casos})
    if len(lotes) != 1 or not lotes[0]:
        recusar(f"o CSV precisa ter exatamente um lote preenchido, encontrei: {lotes}")
    return lotes[0]


def selecionar(casos, ids):
    if ids is None:
        return casos
    pedidos = {i.strip() for i in ids.split(",") if i.strip()}
    if not pedidos:
        recusar("--ids não traz nenhum id")
    desconhecidos = sorted(pedidos - {c["id"].strip() for c in casos})
    if desconhecidos:
        recusar(f"id(s) que não existem no CSV: {', '.join(desconhecidos)}")
    return [c for c in casos if c["id"].strip() in pedidos]


def enviar(abridor, caso, timeout):
    """Faz um único POST e devolve (status_http, corpo, erro_de_rede, tempo_total_s)."""
    corpo = json.dumps({c: caso[c] for c in CAMPOS_ENVIADOS}, ensure_ascii=False).encode("utf-8")
    pedido = urllib.request.Request(
        URL_WEBHOOK, data=corpo, method="POST", headers={"Content-Type": "application/json"}
    )
    status, texto, erro_rede = "", "", ""
    inicio = time.perf_counter()
    try:
        try:
            with abridor.open(pedido, timeout=timeout) as resposta:
                status = resposta.status
                texto = resposta.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as erro:
            status = erro.code
            texto = erro.read().decode("utf-8", "replace")
    except (OSError, http.client.HTTPException) as erro:
        if isinstance(erro, socket.timeout) or isinstance(getattr(erro, "reason", None), socket.timeout):
            # O n8n continua processando depois que o cliente desiste.
            erro_rede = f"timeout após {timeout:g} s; o n8n pode ter gravado a linha na planilha"
        else:
            erro_rede = f"falha de conexão: {erro}"
    return status, texto, erro_rede, round(time.perf_counter() - inicio, 3)


def interpretar(status, texto, erro_rede):
    """Devolve (dados_da_resposta, mensagem_de_erro)."""
    if erro_rede:
        return None, erro_rede
    if status != 200:
        return None, f"HTTP {status}: {texto[:500]}"
    try:
        dados = json.loads(texto)
    except ValueError:
        return None, f"HTTP 200 com corpo que não é JSON: {texto[:500]}"
    if not isinstance(dados, dict) or any(c not in dados for c in CAMPOS_OBRIGATORIOS_RESPOSTA):
        return None, f"HTTP 200 sem os campos esperados: {texto[:500]}"
    return dados, ""


def normalizar(valor):
    return str(valor).strip().casefold()


def acerto(gabarito, valor_ia):
    if not gabarito.strip():
        return ""
    return "sim" if normalizar(gabarito) == normalizar(valor_ia) else "não"


def montar_linha(caso, status, texto, erro_rede, tempo_total):
    dados, erro = interpretar(status, texto, erro_rede)
    linha = {c: caso[c] for c in COLUNAS_RESULTADO if c in caso}
    linha.update(status_http=status, tempo_total_s=tempo_total, erro=erro)
    linha["situacao"] = "ok" if dados is not None else "erro"
    if dados is None:
        return linha  # sem resposta da IA, os acertos ficam vazios

    linha.update(
        categoria_ia=dados["categoria_ia"],
        prioridade_ia=dados["prioridade"],
        time_ia=dados["time"],
        justificativa_prioridade=dados.get("justificativa_prioridade", ""),
        resumo=dados.get("resumo", ""),
        resposta_sugerida=dados.get("resposta_sugerida", ""),
        tempo_processamento_s=dados.get("tempo_processamento_s", ""),
        versao_prompt=dados.get("versao_prompt", ""),
        modelo=dados.get("modelo", ""),
        acerto_categoria=acerto(caso["categoria_gabarito"], dados["categoria_ia"]),
        acerto_prioridade=acerto(caso["prioridade_gabarito"], dados["prioridade"]),
        acerto_time=acerto(caso["time_gabarito"], dados["time"]),
    )
    return linha


def criar_resultado(lote):
    """Cria o arquivo sem nunca sobrescrever um resultado anterior."""
    PASTA_RESULTADOS.mkdir(parents=True, exist_ok=True)
    nome_lote = re.sub(r"[^\w.-]+", "_", lote)
    base = f"resultado-{nome_lote}-{date.today().isoformat()}"
    for n in itertools.count(1):
        caminho = PASTA_RESULTADOS / (f"{base}.csv" if n == 1 else f"{base}-{n}.csv")
        try:
            return caminho, open(caminho, "x", encoding="utf-8", newline="")
        except FileExistsError:
            continue


def gravar_no_disco(arquivo):
    arquivo.flush()
    os.fsync(arquivo.fileno())


def ler_argumentos():
    parser = argparse.ArgumentParser(description="Envia um CSV de casos ao webhook do triador.")
    parser.add_argument("csv", help="caminho do CSV de casos")
    parser.add_argument("--pausa", type=float, default=2.0, help="segundos entre envios (padrão: 2)")
    parser.add_argument("--timeout", type=float, default=180.0, help="segundos por requisição (padrão: 180, mínimo: 120)")
    parser.add_argument("--ids", help="envia só estes ids, separados por vírgula")
    args = parser.parse_args()
    if args.timeout < TIMEOUT_MINIMO_S:
        parser.error(f"--timeout precisa ser de pelo menos {TIMEOUT_MINIMO_S} s")
    if args.pausa < 0:
        parser.error("--pausa não pode ser negativa")
    return args


def main():
    args = ler_argumentos()
    casos = ler_casos(args.csv)
    lote = validar(casos)
    selecionados = selecionar(casos, args.ids)

    # Sem proxy: o webhook é local e variáveis http_proxy do ambiente não devem interferir.
    abridor = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    caminho, arquivo = criar_resultado(lote)
    print(f"Lote {lote}: {len(selecionados)} de {len(casos)} caso(s). Resultado em {caminho}")

    linhas = []
    with arquivo:
        escritor = csv.DictWriter(arquivo, COLUNAS_RESULTADO)
        escritor.writeheader()
        gravar_no_disco(arquivo)
        for i, caso in enumerate(selecionados, 1):
            if i > 1:
                time.sleep(args.pausa)
            linha = montar_linha(caso, *enviar(abridor, caso, args.timeout))
            escritor.writerow(linha)
            gravar_no_disco(arquivo)
            linhas.append(linha)
            print(f"[{i}/{len(selecionados)}] {rotulo(caso)}: {linha['situacao']} "
                  f"HTTP {linha['status_http'] or '-'} em {linha['tempo_total_s']} s", flush=True)

    falhas = [l["id"].strip() for l in linhas if l["situacao"] == "erro"]
    print(f"\nConcluído: {len(linhas) - len(falhas)} ok, {len(falhas)} com erro.")
    for coluna in ("acerto_categoria", "acerto_prioridade", "acerto_time"):
        comparadas = [l for l in linhas if l.get(coluna)]
        sim = sum(l[coluna] == "sim" for l in comparadas)
        print(f"{coluna}: {sim}/{len(comparadas)}")
    if falhas:
        print(f"Ids com erro (use em --ids): {','.join(falhas)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
