"""Lettura e scrittura dei layer binari del formato PS2D.

Struttura dell'header (512 byte) di .ima e .sca, ricavata dai file reali:

    offset  tipo      contenuto
    0-9     ascii     "PCIM001\\r\\n\\x1A"  (.ima)  /  "PCSC001\\r\\n\\x1A"  (.sca)
    10-11   -         zero
    12-15   uint32LE  larghezza in pixel
    16-19   uint32LE  altezza in pixel
    20-31   -         zero
    32-35   float32   millimetri per pixel sull'asse X   (0.5)
    36-39   float32   millimetri per pixel sull'asse Y   (0.5)
    40-43   float32   millimetri per unita' di quota     (fondo scala / 65535)
    44      uint8     valore massimo: 0xFF nell'.ima
    44-45   uint16    valore massimo: 0xFFFF nel .sca
    46-511  -         zero

Seguono i pixel grezzi, row-major, senza padding:
    .ima  -> uint8   (1 byte per pixel)
    .sca  -> uint16LE (2 byte per pixel)

Convenzione delle quote nel .sca: il valore cresce allontanandosi dal
sensore. Il punto piu' prominente vale circa 0, lo sfondo vale 65535.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np

MAGIC_IMA = b"PCIM001\r\n\x1a"
MAGIC_SCA = b"PCSC001\r\n\x1a"
HEADER_SIZE = 512


@dataclass
class LayerHeader:
    """Intestazione di un layer .ima o .sca."""

    magic: bytes
    larghezza: int
    altezza: int
    mm_per_px_x: float
    mm_per_px_y: float
    mm_per_unita_z: float

    @property
    def fondo_scala_mm(self) -> float:
        """Escursione verticale rappresentabile con l'intero range a 16 bit."""
        return self.mm_per_unita_z * 0xFFFF

    def to_bytes(self) -> bytes:
        buf = bytearray(HEADER_SIZE)
        buf[0:10] = self.magic
        struct.pack_into("<I", buf, 12, self.larghezza)
        struct.pack_into("<I", buf, 16, self.altezza)
        struct.pack_into("<f", buf, 32, self.mm_per_px_x)
        struct.pack_into("<f", buf, 36, self.mm_per_px_y)
        struct.pack_into("<f", buf, 40, self.mm_per_unita_z)
        if self.magic == MAGIC_SCA:
            struct.pack_into("<H", buf, 44, 0xFFFF)
        else:
            buf[44] = 0xFF
        return bytes(buf)

    @classmethod
    def from_bytes(cls, raw: bytes) -> "LayerHeader":
        if len(raw) < HEADER_SIZE:
            raise ValueError("header troncato: servono 512 byte")
        magic = raw[0:10]
        if magic not in (MAGIC_IMA, MAGIC_SCA):
            raise ValueError(f"firma non riconosciuta: {magic!r}")
        larghezza, altezza = struct.unpack_from("<II", raw, 12)
        mx, my, mz = struct.unpack_from("<fff", raw, 32)
        return cls(magic, larghezza, altezza, mx, my, mz)


def scrivi_sca(path: Path, quote: np.ndarray, mm_per_px: float,
               mm_per_unita_z: float) -> None:
    """Scrive la mappa quote a 16 bit.

    `quote` deve essere gia' quantizzata in uint16 secondo la convenzione
    del formato (0 = piu' vicino al sensore, 65535 = sfondo).
    """
    if quote.dtype != np.uint16:
        raise TypeError("la mappa quote deve essere uint16")
    h, w = quote.shape
    hdr = LayerHeader(MAGIC_SCA, w, h, mm_per_px, mm_per_px, mm_per_unita_z)
    with open(path, "wb") as f:
        f.write(hdr.to_bytes())
        f.write(quote.astype("<u2").tobytes())


def scrivi_ima(path: Path, immagine: np.ndarray, mm_per_px: float,
               mm_per_unita_z: float) -> None:
    """Scrive l'immagine 8 bit in scala di grigi."""
    if immagine.dtype != np.uint8:
        raise TypeError("l'immagine deve essere uint8")
    h, w = immagine.shape
    hdr = LayerHeader(MAGIC_IMA, w, h, mm_per_px, mm_per_px, mm_per_unita_z)
    with open(path, "wb") as f:
        f.write(hdr.to_bytes())
        f.write(immagine.tobytes())


def leggi_layer(path: Path) -> tuple[LayerHeader, np.ndarray]:
    """Legge un .ima o .sca e restituisce header e matrice dei pixel."""
    raw = Path(path).read_bytes()
    hdr = LayerHeader.from_bytes(raw)
    n = hdr.larghezza * hdr.altezza
    if hdr.magic == MAGIC_SCA:
        dati = np.frombuffer(raw, dtype="<u2", count=n, offset=HEADER_SIZE)
    else:
        dati = np.frombuffer(raw, dtype=np.uint8, count=n, offset=HEADER_SIZE)
    return hdr, dati.reshape(hdr.altezza, hdr.larghezza)


def scrivi_his(path: Path, nome: str, cognome: str, data_nascita: str,
               contrasto: float = 1.0, luminosita: int = 0,
               invert: int = 0, scan3d: int = 1) -> None:
    """Scrive il file di metadati testuali.

    Attenzione alla convenzione dello scanner: NAME contiene il nome
    proprio e VNAME il cognome, all'inverso di quanto suggerirebbe il
    tedesco. `data_nascita` va nel formato GG.MM.AAAA.
    """
    testo = (
        f'USERDATA="NAME={nome}","VNAME={cognome}","GEBDAT={data_nascita}"\n'
        f"KONTRAST={contrasto:.6f}\n"
        f"HELLIGKEIT={luminosita}\n"
        f"INVERT={invert}\n"
        f"3DSCAN={scan3d}\n"
    )
    Path(path).write_text(testo, encoding="ascii", newline="\r\n")


def leggi_his(path: Path) -> dict:
    """Legge il file di metadati e restituisce un dizionario."""
    out: dict = {}
    for riga in Path(path).read_text(encoding="ascii", errors="replace").splitlines():
        if not riga.strip():
            continue
        chiave, _, valore = riga.partition("=")
        if chiave == "USERDATA":
            for campo in valore.split('","'):
                campo = campo.strip('"')
                k, _, v = campo.partition("=")
                out[k.lower()] = v
        else:
            out[chiave.lower()] = valore
    return out
