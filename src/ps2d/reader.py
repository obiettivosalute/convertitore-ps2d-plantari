"""Lettura e ispezione di pacchetti PS2D esistenti.

Serve a due cose: importare in archivio le scansioni ricevute dallo scanner
e verificare che i pacchetti generati siano conformi a quelli originali.
"""

from __future__ import annotations

import json
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .formats import HEADER_SIZE, LayerHeader, leggi_his


@dataclass
class LatoPS2D:
    """I layer di un singolo piede dentro un pacchetto."""

    lato: str
    file: dict[str, str] = field(default_factory=dict)   # estensione -> nome
    larghezza: int = 0
    altezza: int = 0
    mm_per_px: float = 0.0
    mm_per_unita_z: float = 0.0
    quote_mm: np.ndarray | None = None
    maschera: np.ndarray | None = None

    @property
    def escursione_mm(self) -> float:
        if self.quote_mm is None or self.maschera is None or not self.maschera.any():
            return 0.0
        q = self.quote_mm[self.maschera]
        return float(q.max() - q.min())

    @property
    def area_cm2(self) -> float:
        if self.maschera is None:
            return 0.0
        return float(self.maschera.sum()) * self.mm_per_px ** 2 / 100.0

    def ingombro_mm(self) -> tuple[float, float]:
        if self.maschera is None or not self.maschera.any():
            return (0.0, 0.0)
        ys, xs = np.nonzero(self.maschera)
        return ((ys.max() - ys.min() + 1) * self.mm_per_px,
                (xs.max() - xs.min() + 1) * self.mm_per_px)


@dataclass
class ContenutoPS2D:
    """Riepilogo di quanto trovato in un pacchetto."""

    percorso: Path
    lati: dict[str, LatoPS2D] = field(default_factory=dict)
    anagrafica: dict = field(default_factory=dict)
    manifest: dict | None = None
    inatteso: list[str] = field(default_factory=list)


def _carica_sca(dati: bytes) -> tuple[LayerHeader, np.ndarray, np.ndarray]:
    hdr = LayerHeader.from_bytes(dati[:HEADER_SIZE])
    n = hdr.larghezza * hdr.altezza
    grezzo = np.frombuffer(dati, dtype="<u2", count=n, offset=HEADER_SIZE)
    grezzo = grezzo.reshape(hdr.altezza, hdr.larghezza)
    maschera = grezzo < 0xFFFF
    # riporta a quote crescenti verso l'alto, in mm sopra il punto piu' basso
    quote = np.zeros(grezzo.shape, dtype=np.float32)
    if maschera.any():
        d = grezzo[maschera].astype(np.float64) * hdr.mm_per_unita_z
        quote[maschera] = (d.max() - d).astype(np.float32)
    return hdr, quote, maschera


def leggi_ps2d(percorso: str | Path, carica_geometria: bool = True) -> ContenutoPS2D:
    """Apre un .ps2d (o lo ZIP di invio che lo contiene) e ne riassume il contenuto."""
    percorso = Path(percorso)
    contenuto = ContenutoPS2D(percorso=percorso)

    if not zipfile.is_zipfile(percorso):
        raise ValueError(f"{percorso.name} non e' un pacchetto valido (atteso ZIP)")

    with zipfile.ZipFile(percorso) as z:
        nomi = z.namelist()

        # se e' lo ZIP di invio, scendi di un livello
        interni = [n for n in nomi if n.lower().endswith(".ps2d")]
        if interni:
            if "manifest.json" in nomi:
                contenuto.manifest = json.loads(z.read("manifest.json"))
            with tempfile.TemporaryDirectory() as tmp:
                estratto = Path(tmp) / Path(interni[0]).name
                estratto.write_bytes(z.read(interni[0]))
                interno = leggi_ps2d(estratto, carica_geometria)
            interno.percorso = percorso
            interno.manifest = contenuto.manifest
            return interno

        for nome in nomi:
            p = Path(nome)
            ext = p.suffix.lower()
            lato = "Links" if "_Links_" in p.name else (
                "Rechts" if "_Rechts_" in p.name else "?")
            if lato == "?":
                contenuto.inatteso.append(nome)
                continue
            voce = contenuto.lati.setdefault(lato, LatoPS2D(lato=lato))
            voce.file[ext.lstrip(".")] = p.name

            if ext == ".his" and not contenuto.anagrafica:
                with tempfile.TemporaryDirectory() as tmp:
                    f = Path(tmp) / p.name
                    f.write_bytes(z.read(nome))
                    contenuto.anagrafica = leggi_his(f)

            if ext == ".sca":
                dati = z.read(nome)
                hdr, quote, maschera = _carica_sca(dati)
                voce.larghezza = hdr.larghezza
                voce.altezza = hdr.altezza
                voce.mm_per_px = hdr.mm_per_px_x
                voce.mm_per_unita_z = hdr.mm_per_unita_z
                if carica_geometria:
                    voce.quote_mm = quote
                    voce.maschera = maschera
                else:
                    voce.maschera = maschera

    return contenuto


def descrivi(contenuto: ContenutoPS2D) -> str:
    """Riepilogo leggibile, usato nei log e nella scheda di controllo."""
    righe = [f"Pacchetto: {contenuto.percorso.name}"]
    if contenuto.anagrafica:
        a = contenuto.anagrafica
        righe.append(f"  paziente: {a.get('name','?')} {a.get('vname','?')} "
                     f"({a.get('gebdat','?')})")
    if contenuto.manifest:
        righe.append(f"  clinica : {contenuto.manifest.get('clinic',{}).get('name','?')}")
    for lato, v in sorted(contenuto.lati.items()):
        L, W = v.ingombro_mm()
        righe.append(
            f"  {lato:7s} {v.larghezza}x{v.altezza} px @ {v.mm_per_px} mm  "
            f"ingombro {L:.0f}x{W:.0f} mm  escursione {v.escursione_mm:.1f} mm  "
            f"layer: {','.join(sorted(v.file))}")
    if contenuto.inatteso:
        righe.append(f"  file non riconosciuti: {contenuto.inatteso}")
    return "\n".join(righe)
