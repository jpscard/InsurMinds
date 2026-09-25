"""Armazenamento estruturado em SQLite.

Modelo híbrido:
- Colunas relacionais para os campos consultados com frequência (seguradora,
  vigência, LMG, prêmio) e tabelas filhas para coberturas e exclusões, o que
  permite consultas SQL diretas (ex.: "apólices com LMG acima de R$ 10 mi").
- Uma coluna JSON com o `ApoliceDO` completo, que preserva todos os detalhes
  e permite evoluir o esquema sem migrações a cada novo campo.
- Tabela de páginas com o texto original, usada pelo Agente de Consulta.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from ..schema import ApoliceDO

_DDL = """
CREATE TABLE IF NOT EXISTS apolices (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    arquivo          TEXT NOT NULL,
    sha256           TEXT NOT NULL UNIQUE,
    seguradora       TEXT,
    numero_apolice   TEXT,
    tomador          TEXT,
    vigencia_inicio  TEXT,
    vigencia_fim     TEXT,
    lmg              REAL,
    premio           REAL,
    moeda            TEXT,
    provedor_llm     TEXT,
    triagem_json     TEXT,
    alertas_json     TEXT,
    dados_json       TEXT NOT NULL,
    criado_em        TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS coberturas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    apolice_id  INTEGER NOT NULL REFERENCES apolices(id) ON DELETE CASCADE,
    nome        TEXT NOT NULL,
    categoria   TEXT,
    limite      REAL,
    franquia    REAL,
    descricao   TEXT
);
CREATE TABLE IF NOT EXISTS exclusoes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    apolice_id  INTEGER NOT NULL REFERENCES apolices(id) ON DELETE CASCADE,
    titulo      TEXT NOT NULL,
    categoria   TEXT,
    descricao   TEXT
);
CREATE TABLE IF NOT EXISTS paginas (
    apolice_id  INTEGER NOT NULL REFERENCES apolices(id) ON DELETE CASCADE,
    numero      INTEGER NOT NULL,
    metodo      TEXT,
    texto       TEXT,
    PRIMARY KEY (apolice_id, numero)
);
CREATE TABLE IF NOT EXISTS comparacoes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    apolice_ids  TEXT NOT NULL,
    analise_json TEXT NOT NULL,
    provedor_llm TEXT,
    criado_em    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_cob_apolice ON coberturas(apolice_id);
CREATE INDEX IF NOT EXISTS ix_exc_apolice ON exclusoes(apolice_id);
"""


class Repository:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        with self._conn() as c:
            c.executescript(_DDL)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------ escrita
    def find_by_hash(self, sha256: str) -> int | None:
        with self._conn() as c:
            row = c.execute("SELECT id FROM apolices WHERE sha256 = ?", (sha256,)).fetchone()
            return row["id"] if row else None

    def save(self, arquivo: str, sha256: str, ap: ApoliceDO, pages: list[tuple[int, str, str]],
             triagem: dict, alertas: list[dict], provedor: str) -> int:
        """Grava (ou substitui, se o mesmo arquivo já existir) uma apólice processada."""
        idt = ap.identificacao
        lmg = ap.limite_maximo_garantia
        pr = ap.premio_total
        with self._conn() as c:
            c.execute("DELETE FROM apolices WHERE sha256 = ?", (sha256,))
            cur = c.execute(
                """INSERT INTO apolices (arquivo, sha256, seguradora, numero_apolice, tomador,
                   vigencia_inicio, vigencia_fim, lmg, premio, moeda, provedor_llm,
                   triagem_json, alertas_json, dados_json, criado_em)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (arquivo, sha256, idt.seguradora, idt.numero_apolice, idt.tomador,
                 idt.vigencia_inicio, idt.vigencia_fim, lmg.valor if lmg else None,
                 pr.valor if pr else None, lmg.moeda if lmg else None, provedor,
                 json.dumps(triagem, ensure_ascii=False), json.dumps(alertas, ensure_ascii=False),
                 ap.model_dump_json(), datetime.now().isoformat(timespec="seconds")),
            )
            aid = cur.lastrowid
            c.executemany(
                "INSERT INTO coberturas (apolice_id, nome, categoria, limite, franquia, descricao) VALUES (?,?,?,?,?,?)",
                [(aid, cb.nome, cb.categoria, cb.limite.valor if cb.limite else None,
                  cb.franquia.valor if cb.franquia else None, cb.descricao) for cb in ap.coberturas],
            )
            c.executemany(
                "INSERT INTO exclusoes (apolice_id, titulo, categoria, descricao) VALUES (?,?,?,?)",
                [(aid, e.titulo, e.categoria, e.descricao) for e in ap.exclusoes],
            )
            c.executemany("INSERT INTO paginas (apolice_id, numero, metodo, texto) VALUES (?,?,?,?)",
                          [(aid, n, m, t) for n, m, t in pages])
            return aid

    def update_data(self, apolice_id: int, ap: ApoliceDO) -> None:
        """Salva correções manuais feitas pelo usuário na interface (human-in-the-loop)."""
        pages = [(p["numero"], p["metodo"], p["texto"]) for p in self.pages(apolice_id)]
        row = self.get_row(apolice_id)
        self.save(row["arquivo"], row["sha256"], ap, pages, json.loads(row["triagem_json"] or "{}"),
                  json.loads(row["alertas_json"] or "[]"), row["provedor_llm"])

    def delete(self, apolice_id: int) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM apolices WHERE id = ?", (apolice_id,))

    def save_comparison(self, ids: list[int], analise: dict, provedor: str) -> int:
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO comparacoes (apolice_ids, analise_json, provedor_llm, criado_em) VALUES (?,?,?,?)",
                (json.dumps(ids), json.dumps(analise, ensure_ascii=False), provedor,
                 datetime.now().isoformat(timespec="seconds")),
            )
            return cur.lastrowid

    # ------------------------------------------------------------------ leitura
    def list(self) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                """SELECT a.id, a.arquivo, a.seguradora, a.numero_apolice, a.tomador, a.vigencia_inicio,
                          a.vigencia_fim, a.lmg, a.premio, a.moeda, a.provedor_llm, a.criado_em,
                          (SELECT COUNT(*) FROM coberturas WHERE apolice_id = a.id) AS n_coberturas,
                          (SELECT COUNT(*) FROM exclusoes  WHERE apolice_id = a.id) AS n_exclusoes
                   FROM apolices a ORDER BY a.id DESC"""
            ).fetchall()
            return [dict(r) for r in rows]

    def get_row(self, apolice_id: int) -> dict:
        with self._conn() as c:
            row = c.execute("SELECT * FROM apolices WHERE id = ?", (apolice_id,)).fetchone()
            if not row:
                raise KeyError(f"Apólice {apolice_id} não encontrada")
            return dict(row)

    def get(self, apolice_id: int) -> ApoliceDO:
        return ApoliceDO.model_validate_json(self.get_row(apolice_id)["dados_json"])

    def pages(self, apolice_id: int) -> list[dict]:
        with self._conn() as c:
            return [dict(r) for r in c.execute(
                "SELECT numero, metodo, texto FROM paginas WHERE apolice_id = ? ORDER BY numero",
                (apolice_id,))]

    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        """Consulta SQL somente leitura (usada na aba de consultas estruturadas)."""
        if not sql.strip().lower().startswith(("select", "with")):
            raise ValueError("Apenas consultas SELECT são permitidas")
        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()
