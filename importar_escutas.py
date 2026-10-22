#!/usr/bin/env python3
"""Importa um CSV de escutas (exportado pela app "Log de Escutas") para SQLite.

Uso:
    python3 importar_escutas.py log_final.csv
    python3 importar_escutas.py log_final.csv --db minha_base.db

A tabela `logs` é criada se ainda não existir. Registos que já existam
(mesma frequência, data, hora e estação) são ignorados, por isso podes
importar o mesmo ficheiro mais do que uma vez sem duplicar dados.

O script aceita ficheiros guardados por outros programas (Excel, LibreOffice,
Bloco de Notas): deteta sozinho a codificação (UTF-8, Windows-1252 ou Latin-1)
e o separador (vírgula, ponto e vírgula ou tabulação). Se precisares, podes
forçar com --encoding e --sep.
"""
import argparse
import csv
import io
import sqlite3
import sys

SCHEMA = """
CREATE TABLE IF NOT EXISTS logs (
    freq_hz INTEGER NOT NULL,
    local   TEXT,
    radio   TEXT,
    antena  TEXT,
    data    TEXT,
    hora    TEXT,
    modo    TEXT,
    sinal   TEXT,
    estacao TEXT,
    sinfo   TEXT,
    lingua  TEXT,
    observ  TEXT
)
"""
COLS = ["freq_hz", "local", "radio", "antena", "data", "hora",
        "modo", "sinal", "estacao", "sinfo", "lingua", "observ"]
ENCODINGS = ["utf-8-sig", "cp1252", "latin-1"]   # latin-1 aceita qualquer byte


def ler_texto(caminho, forcar):
    raw = open(caminho, "rb").read()
    for enc in ([forcar] if forcar else ENCODINGS):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    sys.exit("Não consegui ler o ficheiro com a codificação %r." % forcar)


def detetar_separador(texto, forcar):
    if forcar:
        return "\t" if forcar.lower() in ("tab", "\\t") else forcar
    cabecalho = texto.lstrip("﻿").splitlines()[0] if texto.strip() else ""
    return max([",", ";", "\t"], key=cabecalho.count)


def inteiro(valor):
    """Converte freq_hz; aceita '6070000', '6070000.0' e '6,07E+06' (Excel)."""
    v = (valor or "").strip().replace(" ", "")
    try:
        return int(v)
    except ValueError:
        return int(round(float(v.replace(",", "."))))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", help="ficheiro CSV de escutas")
    ap.add_argument("--db", default="radio.db", help="base de dados SQLite (por omissão: radio.db)")
    ap.add_argument("--encoding", help="forçar a codificação (ex.: cp1252)")
    ap.add_argument("--sep", help="forçar o separador (ex.: ';' ou 'tab')")
    args = ap.parse_args()

    texto, enc = ler_texto(args.csv, args.encoding)
    sep = detetar_separador(texto, args.sep)
    print("Codificação: %s | separador: %r" % (enc, sep))
    if enc != "utf-8-sig":
        print("Aviso: o ficheiro não está em UTF-8. Foi convertido ao importar; "
              "para evitar isto, guarda-o como 'CSV UTF-8'.")

    reader = csv.DictReader(io.StringIO(texto, newline=""), delimiter=sep)
    reader.fieldnames = [(h or "").strip().lstrip("﻿") for h in (reader.fieldnames or [])]
    falta = [c for c in COLS if c not in reader.fieldnames]
    if falta:
        sys.exit("Cabeçalho inesperado; faltam colunas: " + ", ".join(falta) +
                 "\nColunas encontradas: " + ", ".join(reader.fieldnames))

    con = sqlite3.connect(args.db)
    con.execute(SCHEMA)
    novos = ignorados = invalidos = 0
    for n, row in enumerate(reader, start=2):
        if not any((row.get(c) or "").strip() for c in COLS):
            continue                                    # linha vazia
        try:
            row["freq_hz"] = inteiro(row["freq_hz"])
        except (TypeError, ValueError):
            print("  linha %d ignorada: freq_hz inválido (%r)" % (n, row.get("freq_hz")))
            invalidos += 1
            continue
        for c in COLS[1:]:
            row[c] = (row.get(c) or "").strip()
        # o Excel/LibreOffice apagam zeros à esquerda: 0930 -> 930, 0005 -> 5
        if row["hora"].isdigit():
            row["hora"] = row["hora"].zfill(4)
        if row["data"].isdigit():
            row["data"] = row["data"].zfill(8)
        existe = con.execute(
            "SELECT 1 FROM logs WHERE freq_hz=? AND data=? AND hora=? AND estacao=?",
            (row["freq_hz"], row["data"], row["hora"], row["estacao"]),
        ).fetchone()
        if existe:
            ignorados += 1
            continue
        con.execute(
            "INSERT INTO logs (%s) VALUES (%s)" % (",".join(COLS), ",".join("?" * len(COLS))),
            [row[c] for c in COLS],
        )
        novos += 1
    con.commit()
    con.close()
    print("%d inseridos, %d já existiam, %d inválidos -> %s" % (novos, ignorados, invalidos, args.db))


if __name__ == "__main__":
    main()
