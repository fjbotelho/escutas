#!/usr/bin/env python3
"""Importa um CSV exportado pela app "Log de Escutas" para uma base de dados SQLite.

Uso:
    python3 importar_escutas.py escutas_20261019_1255.csv
    python3 importar_escutas.py escutas_20261019_1255.csv --db minha_base.db

A tabela `escutas` é criada se ainda não existir. Registos que já existam
(mesma frequência, data, hora e estação) são ignorados, por isso podes
importar o mesmo ficheiro mais do que uma vez sem duplicar dados.
"""
import argparse
import csv
import sqlite3
import sys

SCHEMA = """
CREATE TABLE IF NOT EXISTS escutas (
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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", help="ficheiro CSV exportado pela app")
    ap.add_argument("--db", default="escutas.db", help="base de dados SQLite (por omissão: escutas.db)")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    con.execute(SCHEMA)

    novos = ignorados = invalidos = 0
    with open(args.csv, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        falta = [c for c in COLS if c not in (reader.fieldnames or [])]
        if falta:
            sys.exit("Cabeçalho inesperado; faltam colunas: " + ", ".join(falta))
        for row in reader:
            try:
                row["freq_hz"] = int(row["freq_hz"])
            except (TypeError, ValueError):
                invalidos += 1
                continue
            existe = con.execute(
                "SELECT 1 FROM escutas WHERE freq_hz=? AND data=? AND hora=? AND estacao=?",
                (row["freq_hz"], row["data"], row["hora"], row["estacao"]),
            ).fetchone()
            if existe:
                ignorados += 1
                continue
            con.execute(
                "INSERT INTO escutas (%s) VALUES (%s)" % (",".join(COLS), ",".join("?" * len(COLS))),
                [row[c] for c in COLS],
            )
            novos += 1
    con.commit()
    con.close()
    print(f"{novos} inseridos, {ignorados} já existiam, {invalidos} inválidos -> {args.db}")


if __name__ == "__main__":
    main()
