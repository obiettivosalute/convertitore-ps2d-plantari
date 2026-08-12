"""Archivio locale: clienti, lavorazioni e file, su SQLite.

I dati restano sul disco dell'utente: sono dati sanitari e non devono
finire in un repository. Il file .gitignore esclude l'intera cartella data/.
"""

from __future__ import annotations

import hashlib
import shutil
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from config import ARCHIVIO_DIR, DB_PATH, UPLOAD_DIR

SCHEMA = """
CREATE TABLE IF NOT EXISTS clienti (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cognome         TEXT NOT NULL,
    nome            TEXT NOT NULL,
    data_nascita    TEXT NOT NULL,          -- GG.MM.AAAA
    email           TEXT DEFAULT '',
    telefono        TEXT DEFAULT '',
    note            TEXT DEFAULT '',
    creato_il       TEXT NOT NULL,
    modificato_il   TEXT NOT NULL,
    UNIQUE (cognome, nome, data_nascita)
);

CREATE TABLE IF NOT EXISTS lavorazioni (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id      INTEGER NOT NULL REFERENCES clienti(id) ON DELETE CASCADE,
    creata_il       TEXT NOT NULL,
    descrizione     TEXT DEFAULT '',
    note            TEXT DEFAULT '',
    stato           TEXT NOT NULL DEFAULT 'bozza',
    cartella        TEXT DEFAULT '',
    ps2d            TEXT DEFAULT '',
    zip_invio       TEXT DEFAULT '',
    codice_invio    TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS file_lavorazione (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    lavorazione_id  INTEGER NOT NULL REFERENCES lavorazioni(id) ON DELETE CASCADE,
    lato            TEXT NOT NULL,          -- 'Links' | 'Rechts'
    ruolo           TEXT NOT NULL,          -- 'origine' | 'generato'
    percorso        TEXT NOT NULL,
    nome_originale  TEXT DEFAULT '',
    formato         TEXT DEFAULT '',
    byte            INTEGER DEFAULT 0,
    impronta        TEXT DEFAULT '',
    lunghezza_mm    REAL DEFAULT 0,
    larghezza_mm    REAL DEFAULT 0,
    altezza_mm      REAL DEFAULT 0,
    n_vertici       INTEGER DEFAULT 0,
    n_facce         INTEGER DEFAULT 0,
    creato_il       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_lav_cliente ON lavorazioni(cliente_id);
CREATE INDEX IF NOT EXISTS idx_file_lav ON file_lavorazione(lavorazione_id);
CREATE INDEX IF NOT EXISTS idx_clienti_cognome ON clienti(cognome, nome);
"""


@dataclass
class Cliente:
    id: int
    cognome: str
    nome: str
    data_nascita: str
    email: str = ""
    telefono: str = ""
    note: str = ""

    @property
    def etichetta(self) -> str:
        return f"{self.cognome} {self.nome} ({self.data_nascita})"


@dataclass
class Lavorazione:
    id: int
    cliente_id: int
    creata_il: str
    descrizione: str = ""
    note: str = ""
    stato: str = "bozza"
    cartella: str = ""
    ps2d: str = ""
    zip_invio: str = ""
    codice_invio: str = ""


class Archivio:
    """Accesso all'archivio. Una istanza per applicazione."""

    def __init__(self, percorso: Path | None = None):
        self.percorso = Path(percorso or DB_PATH)
        self.percorso.parent.mkdir(parents=True, exist_ok=True)
        with self._connessione() as cx:
            cx.executescript(SCHEMA)

    @contextmanager
    def _connessione(self):
        cx = sqlite3.connect(self.percorso)
        cx.row_factory = sqlite3.Row
        cx.execute("PRAGMA foreign_keys = ON")
        try:
            yield cx
            cx.commit()
        finally:
            cx.close()

    # ------------------------------------------------------------ clienti
    def trova_o_crea_cliente(self, cognome: str, nome: str, data_nascita: str,
                             email: str = "", telefono: str = "") -> Cliente:
        adesso = datetime.now().isoformat(timespec="seconds")
        cognome, nome = cognome.strip(), nome.strip()
        with self._connessione() as cx:
            riga = cx.execute(
                "SELECT * FROM clienti WHERE cognome=? AND nome=? AND data_nascita=?",
                (cognome, nome, data_nascita)).fetchone()
            if riga:
                return self._a_cliente(riga)
            cur = cx.execute(
                "INSERT INTO clienti (cognome, nome, data_nascita, email, telefono,"
                " note, creato_il, modificato_il) VALUES (?,?,?,?,?,'',?,?)",
                (cognome, nome, data_nascita, email, telefono, adesso, adesso))
            return Cliente(cur.lastrowid, cognome, nome, data_nascita, email, telefono)

    def aggiorna_cliente(self, cliente_id: int, **campi) -> None:
        ammessi = {"cognome", "nome", "data_nascita", "email", "telefono", "note"}
        campi = {k: v for k, v in campi.items() if k in ammessi}
        if not campi:
            return
        campi["modificato_il"] = datetime.now().isoformat(timespec="seconds")
        assegnazioni = ", ".join(f"{k}=?" for k in campi)
        with self._connessione() as cx:
            cx.execute(f"UPDATE clienti SET {assegnazioni} WHERE id=?",
                       (*campi.values(), cliente_id))

    def elenca_clienti(self, filtro: str = "") -> list[Cliente]:
        with self._connessione() as cx:
            if filtro:
                like = f"%{filtro.strip()}%"
                righe = cx.execute(
                    "SELECT * FROM clienti WHERE cognome LIKE ? OR nome LIKE ?"
                    " OR data_nascita LIKE ? ORDER BY cognome, nome",
                    (like, like, like)).fetchall()
            else:
                righe = cx.execute(
                    "SELECT * FROM clienti ORDER BY cognome, nome").fetchall()
        return [self._a_cliente(r) for r in righe]

    def cliente(self, cliente_id: int) -> Cliente | None:
        with self._connessione() as cx:
            riga = cx.execute("SELECT * FROM clienti WHERE id=?",
                              (cliente_id,)).fetchone()
        return self._a_cliente(riga) if riga else None

    @staticmethod
    def _a_cliente(r: sqlite3.Row) -> Cliente:
        return Cliente(r["id"], r["cognome"], r["nome"], r["data_nascita"],
                       r["email"] or "", r["telefono"] or "", r["note"] or "")

    # -------------------------------------------------------- lavorazioni
    def crea_lavorazione(self, cliente_id: int, descrizione: str = "",
                         note: str = "") -> Lavorazione:
        adesso = datetime.now().isoformat(timespec="seconds")
        with self._connessione() as cx:
            cur = cx.execute(
                "INSERT INTO lavorazioni (cliente_id, creata_il, descrizione, note)"
                " VALUES (?,?,?,?)", (cliente_id, adesso, descrizione, note))
            return Lavorazione(cur.lastrowid, cliente_id, adesso, descrizione, note)

    def aggiorna_lavorazione(self, lavorazione_id: int, **campi) -> None:
        ammessi = {"descrizione", "note", "stato", "cartella", "ps2d",
                   "zip_invio", "codice_invio"}
        campi = {k: v for k, v in campi.items() if k in ammessi}
        if not campi:
            return
        assegnazioni = ", ".join(f"{k}=?" for k in campi)
        with self._connessione() as cx:
            cx.execute(f"UPDATE lavorazioni SET {assegnazioni} WHERE id=?",
                       (*campi.values(), lavorazione_id))

    def elenca_lavorazioni(self, cliente_id: int | None = None,
                           filtro: str = "") -> list[dict]:
        sql = ("SELECT l.*, c.cognome, c.nome, c.data_nascita FROM lavorazioni l"
               " JOIN clienti c ON c.id = l.cliente_id")
        cond, par = [], []
        if cliente_id is not None:
            cond.append("l.cliente_id = ?")
            par.append(cliente_id)
        if filtro:
            like = f"%{filtro.strip()}%"
            cond.append("(c.cognome LIKE ? OR c.nome LIKE ? OR l.descrizione LIKE ?)")
            par += [like, like, like]
        if cond:
            sql += " WHERE " + " AND ".join(cond)
        sql += " ORDER BY l.creata_il DESC"
        with self._connessione() as cx:
            return [dict(r) for r in cx.execute(sql, par).fetchall()]

    def elimina_lavorazione(self, lavorazione_id: int,
                            cancella_file: bool = False) -> None:
        with self._connessione() as cx:
            riga = cx.execute("SELECT cartella FROM lavorazioni WHERE id=?",
                              (lavorazione_id,)).fetchone()
            cx.execute("DELETE FROM lavorazioni WHERE id=?", (lavorazione_id,))
        if cancella_file and riga and riga["cartella"]:
            cartella = Path(riga["cartella"])
            if cartella.exists() and ARCHIVIO_DIR in cartella.parents:
                shutil.rmtree(cartella, ignore_errors=True)

    # --------------------------------------------------------------- file
    def registra_file(self, lavorazione_id: int, lato: str, ruolo: str,
                      percorso: Path, nome_originale: str = "",
                      misure: dict | None = None) -> int:
        percorso = Path(percorso)
        misure = misure or {}
        with self._connessione() as cx:
            cur = cx.execute(
                "INSERT INTO file_lavorazione (lavorazione_id, lato, ruolo,"
                " percorso, nome_originale, formato, byte, impronta,"
                " lunghezza_mm, larghezza_mm, altezza_mm, n_vertici, n_facce,"
                " creato_il) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (lavorazione_id, lato, ruolo, str(percorso),
                 nome_originale or percorso.name, percorso.suffix.lstrip("."),
                 percorso.stat().st_size if percorso.exists() else 0,
                 impronta_file(percorso) if percorso.exists() else "",
                 misure.get("lunghezza_mm", 0), misure.get("larghezza_mm", 0),
                 misure.get("altezza_mm", 0), misure.get("n_vertici", 0),
                 misure.get("n_facce", 0),
                 datetime.now().isoformat(timespec="seconds")))
            return cur.lastrowid

    def file_di(self, lavorazione_id: int, ruolo: str | None = None) -> list[dict]:
        sql = "SELECT * FROM file_lavorazione WHERE lavorazione_id=?"
        par: list = [lavorazione_id]
        if ruolo:
            sql += " AND ruolo=?"
            par.append(ruolo)
        sql += " ORDER BY lato, ruolo"
        with self._connessione() as cx:
            return [dict(r) for r in cx.execute(sql, par).fetchall()]

    # ------------------------------------------------------------ statistiche
    def riepilogo(self) -> dict:
        with self._connessione() as cx:
            return {
                "clienti": cx.execute("SELECT COUNT(*) c FROM clienti").fetchone()["c"],
                "lavorazioni": cx.execute(
                    "SELECT COUNT(*) c FROM lavorazioni").fetchone()["c"],
                "esportate": cx.execute(
                    "SELECT COUNT(*) c FROM lavorazioni WHERE ps2d <> ''").fetchone()["c"],
            }


def impronta_file(percorso: Path, blocchi: int = 1 << 20) -> str:
    """SHA-256 abbreviato, per riconoscere lo stesso file caricato due volte."""
    h = hashlib.sha256()
    with open(percorso, "rb") as f:
        while (b := f.read(blocchi)):
            h.update(b)
    return h.hexdigest()[:16]


def cartella_lavorazione(cliente: Cliente, lavorazione_id: int,
                         istante: datetime) -> Path:
    """Percorso di archivio: una cartella per lavorazione, sotto il cliente."""
    sicuro = "".join(ch for ch in f"{cliente.cognome}_{cliente.nome}"
                     if ch.isalnum() or ch in "_-")
    cartella = (ARCHIVIO_DIR / f"{sicuro}_{cliente.data_nascita}" /
                f"{istante:%Y%m%d_%H%M%S}_lav{lavorazione_id:05d}")
    cartella.mkdir(parents=True, exist_ok=True)
    return cartella


def archivia_originale(percorso: Path, cliente: Cliente, lato: str) -> Path:
    """Copia il file caricato in archivio, per poterlo riesportare in futuro."""
    sicuro = "".join(ch for ch in f"{cliente.cognome}_{cliente.nome}"
                     if ch.isalnum() or ch in "_-")
    destinazione_dir = UPLOAD_DIR / f"{sicuro}_{cliente.data_nascita}"
    destinazione_dir.mkdir(parents=True, exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    destinazione = destinazione_dir / f"{marca}_{lato}{Path(percorso).suffix.lower()}"
    shutil.copy2(percorso, destinazione)
    return destinazione
