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

# A cosa serve ciascun layer, per l'elenco dell'ispezione. Le descrizioni
# vengono da docs/FORMATO_PS2D.md: due estensioni mentono sul contenuto,
# e vale la pena che si legga.
TIPI_LAYER = {
    "sca": "mappa quote 16 bit - la geometria",
    "ima": "immagine 8 bit della camera",
    "farima": "PNG RGBA a colori, alfa = maschera",
    "bmp": "malgrado il nome e' un JPEG grigio",
    "obj": "mesh Wavefront, in metri",
    "his": "anagrafica e impostazioni",
    "ps2d": "pacchetto interno",
    "json": "manifest dell'invio",
    "mtl": "materiali della mesh",
}


@dataclass
class FilePacchetto:
    """Una voce dell'archivio, con il contenitore da cui proviene."""

    nome: str
    dimensione: int
    compressa: int
    contenitore: str          # "zip di invio" oppure "ps2d"
    lato: str = "-"
    tipo: str = ""

    @property
    def estensione(self) -> str:
        return Path(self.nome).suffix.lstrip(".").lower()


@dataclass
class LatoPS2D:
    """I layer di un singolo piede dentro un pacchetto."""

    lato: str
    file: dict[str, str] = field(default_factory=dict)   # estensione -> nome
    larghezza: int = 0
    altezza: int = 0
    mm_per_px: float = 0.0
    mm_per_px_y: float = 0.0
    mm_per_unita_z: float = 0.0
    firma: str = ""
    anagrafica: dict = field(default_factory=dict)
    quote_mm: np.ndarray | None = None
    maschera: np.ndarray | None = None

    @property
    def fondo_scala_mm(self) -> float:
        """Escursione rappresentabile con l'intero range a 16 bit."""
        return self.mm_per_unita_z * 0xFFFF

    @property
    def pixel_validi(self) -> int:
        return 0 if self.maschera is None else int(self.maschera.sum())

    @property
    def copertura_pct(self) -> float:
        """Quanta parte del fotogramma porta dati, in percentuale.

        Su una scansione di piede un valore alto segnala che nel campo e'
        finito anche il piano d'appoggio: vedi la verifica V4 nel vault.
        """
        celle = self.larghezza * self.altezza
        return 0.0 if not celle else 100.0 * self.pixel_validi / celle

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
    dimensione: int = 0
    elenco_file: list[FilePacchetto] = field(default_factory=list)
    ps2d_interno: str | None = None


def _elenca(z: zipfile.ZipFile, contenitore: str) -> list[FilePacchetto]:
    """Inventario di un archivio: nome, peso e a cosa serve ogni file."""
    voci: list[FilePacchetto] = []
    for info in z.infolist():
        if info.is_dir():
            continue
        nome = Path(info.filename).name
        ext = Path(nome).suffix.lstrip(".").lower()
        lato = "Links" if "_Links_" in nome else (
            "Rechts" if "_Rechts_" in nome else "-")
        voci.append(FilePacchetto(
            nome=info.filename, dimensione=info.file_size,
            compressa=info.compress_size, contenitore=contenitore,
            lato=lato, tipo=TIPI_LAYER.get(ext, "")))
    return voci


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
    contenuto.dimensione = percorso.stat().st_size

    if not zipfile.is_zipfile(percorso):
        raise ValueError(f"{percorso.name} non e' un pacchetto valido (atteso ZIP)")

    with zipfile.ZipFile(percorso) as z:
        nomi = z.namelist()

        # se e' lo ZIP di invio, scendi di un livello
        interni = [n for n in nomi if n.lower().endswith(".ps2d")]
        if interni:
            esterni = _elenca(z, "zip di invio")
            if "manifest.json" in nomi:
                contenuto.manifest = json.loads(z.read("manifest.json"))
            with tempfile.TemporaryDirectory() as tmp:
                estratto = Path(tmp) / Path(interni[0]).name
                estratto.write_bytes(z.read(interni[0]))
                interno = leggi_ps2d(estratto, carica_geometria)
            interno.percorso = percorso
            interno.dimensione = contenuto.dimensione
            interno.manifest = contenuto.manifest
            interno.ps2d_interno = Path(interni[0]).name
            # l'involucro davanti, poi quello che contiene
            interno.elenco_file = esterni + interno.elenco_file
            return interno

        contenuto.elenco_file = _elenca(z, "ps2d")
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

            if ext == ".his":
                # ogni piede porta il suo .his: si leggono entrambi, cosi'
                # l'ispezione puo' mostrare se divergono. Il primo vale
                # come anagrafica del pacchetto.
                with tempfile.TemporaryDirectory() as tmp:
                    f = Path(tmp) / p.name
                    f.write_bytes(z.read(nome))
                    voce.anagrafica = leggi_his(f)
                if not contenuto.anagrafica:
                    contenuto.anagrafica = dict(voce.anagrafica)

            if ext == ".sca":
                dati = z.read(nome)
                hdr, quote, maschera = _carica_sca(dati)
                voce.larghezza = hdr.larghezza
                voce.altezza = hdr.altezza
                voce.mm_per_px = hdr.mm_per_px_x
                voce.mm_per_px_y = hdr.mm_per_px_y
                voce.mm_per_unita_z = hdr.mm_per_unita_z
                voce.firma = hdr.magic.decode("ascii", "replace").strip("\r\n\x1a")
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


def _byte(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _coda(testo: str, larghezza: int) -> str:
    """Accorcia dall'inizio, non dalla fine.

    I nomi dei layer condividono un prefisso lungo e si distinguono per la
    coda — lato, marca temporale, estensione. Tagliare a destra butterebbe
    via proprio quello che serve leggere.
    """
    if len(testo) <= larghezza:
        return testo
    return "..." + testo[-(larghezza - 3):]


def osservazioni(contenuto: ContenutoPS2D) -> list[str]:
    """Cose che vale la pena far notare a chi guarda il pacchetto.

    Non sono errori: sono le difformita' che, guardando i pacchetti a mano,
    si e' imparato a cercare per prime.
    """
    note: list[str] = []
    lati = contenuto.lati

    griglie = {(v.larghezza, v.altezza) for v in lati.values()}
    if len(griglie) > 1:
        detta = "  ".join(f"{k}: {v.larghezza}x{v.altezza}"
                          for k, v in sorted(lati.items()))
        note.append(f"le due griglie non coincidono ({detta}). Negli originali "
                    "succede: la griglia non e' fissa, si legge dall'header")

    for lato, v in sorted(lati.items()):
        if v.copertura_pct > 50.0:
            note.append(f"{lato}: il {v.copertura_pct:.0f}% del fotogramma porta "
                        "dati. Su una scansione di piede e' il segno che nel "
                        "campo e' finito anche il piano d'appoggio")

    attesi = {"sca", "ima", "farima", "obj", "his", "bmp"}
    for lato, v in sorted(lati.items()):
        mancanti = attesi - set(v.file)
        if mancanti:
            note.append(f"{lato}: layer mancanti - {', '.join(sorted(mancanti))}")

    ana = [v.anagrafica for v in lati.values() if v.anagrafica]
    if len(ana) > 1 and any(a != ana[0] for a in ana[1:]):
        note.append("i due .his non sono identici: l'anagrafica dei due piedi "
                    "diverge")

    if contenuto.inatteso:
        note.append(f"{len(contenuto.inatteso)} file non attribuibili a un piede")

    if contenuto.ps2d_interno is None:
        note.append("nessun .ps2d annidato: questo e' un pacchetto nudo, non "
                    "l'archivio di invio con il manifest")

    return note


def report(contenuto: ContenutoPS2D) -> str:
    """Resoconto completo di un pacchetto, da leggere o da salvare.

    A differenza di descrivi(), che sta in cinque righe, qui esce tutto
    quello che il lettore ha raccolto: serve per confrontare a freddo un
    pacchetto generato con uno autentico, senza rileggerli a schermo.
    """
    r: list[str] = []
    r.append("PACCHETTO")
    r.append(f"  file        {contenuto.percorso.name}")
    r.append(f"  percorso    {contenuto.percorso.parent}")
    r.append(f"  dimensione  {_byte(contenuto.dimensione)} byte")
    if contenuto.ps2d_interno:
        r.append(f"  ps2d interno  {contenuto.ps2d_interno}")
    r.append(f"  piedi       {len(contenuto.lati)}    "
             f"file  {len(contenuto.elenco_file)}")

    if contenuto.anagrafica:
        r.append("")
        r.append("ANAGRAFICA (.his)")
        for k, v in contenuto.anagrafica.items():
            r.append(f"  {k:<12s}{v}")
        # NAME e VNAME sono invertiti rispetto al tedesco: vale la pena
        # dirlo qui, perche' e' la prima cosa che confonde chi confronta.
        r.append("  (NAME e' il nome proprio, VNAME il cognome)")

    if contenuto.manifest:
        r.append("")
        r.append("MANIFEST")
        for riga in json.dumps(contenuto.manifest, indent=2,
                               ensure_ascii=False).splitlines():
            r.append(f"  {riga}")

    for lato, v in sorted(contenuto.lati.items()):
        lung, larg = v.ingombro_mm()
        r.append("")
        r.append(f"{lato.upper()}")
        r.append(f"  firma            {v.firma}")
        r.append(f"  griglia          {v.larghezza} x {v.altezza} px")
        r.append(f"  passo            {v.mm_per_px} x {v.mm_per_px_y} mm/px")
        r.append(f"  mm per unita' z  {v.mm_per_unita_z:.8f}")
        r.append(f"  fondo scala      {v.fondo_scala_mm:.1f} mm")
        r.append(f"  pixel validi     {_byte(v.pixel_validi)}"
                 f"  ({v.copertura_pct:.1f}% del fotogramma)")
        r.append(f"  area utile       {v.area_cm2:.1f} cm2")
        r.append(f"  ingombro         {lung:.0f} x {larg:.0f} mm")
        r.append(f"  escursione       {v.escursione_mm:.1f} mm")
        if v.anagrafica and v.anagrafica != contenuto.anagrafica:
            r.append("  ATTENZIONE: il .his di questo piede differisce da quello del pacchetto")
        r.append("  layer:")
        for ext in sorted(v.file):
            r.append(f"    .{ext:<8s} {v.file[ext]}")

    if contenuto.elenco_file:
        r.append("")
        r.append("FILE")
        r.append(f"  {'nome':<52s}{'contenitore':<14s}{'lato':<8s}"
                 f"{'byte':>12s}  tipo")
        for f in contenuto.elenco_file:
            r.append(f"  {_coda(f.nome, 51):<52s}{f.contenitore:<14s}"
                     f"{f.lato:<8s}{_byte(f.dimensione):>12s}  {f.tipo}")

    if contenuto.inatteso:
        r.append("")
        r.append("NON RICONOSCIUTI")
        for n in contenuto.inatteso:
            r.append(f"  {n}")

    note = osservazioni(contenuto)
    if note:
        r.append("")
        r.append("OSSERVAZIONI")
        for n in note:
            r.append(f"  - {n}")

    return "\n".join(r)


def report_dati(contenuto: ContenutoPS2D) -> dict:
    """Lo stesso resoconto in forma di dizionario, per l'export in JSON."""
    return {
        "pacchetto": {
            "file": contenuto.percorso.name,
            "percorso": str(contenuto.percorso.parent),
            "dimensione_byte": contenuto.dimensione,
            "ps2d_interno": contenuto.ps2d_interno,
        },
        "anagrafica": contenuto.anagrafica,
        "manifest": contenuto.manifest,
        "lati": {
            lato: {
                "firma": v.firma,
                "larghezza_px": v.larghezza,
                "altezza_px": v.altezza,
                "mm_per_px_x": v.mm_per_px,
                "mm_per_px_y": v.mm_per_px_y,
                "mm_per_unita_z": v.mm_per_unita_z,
                "fondo_scala_mm": round(v.fondo_scala_mm, 3),
                "pixel_validi": v.pixel_validi,
                "copertura_pct": round(v.copertura_pct, 2),
                "area_cm2": round(v.area_cm2, 2),
                "ingombro_mm": [round(x, 1) for x in v.ingombro_mm()],
                "escursione_mm": round(v.escursione_mm, 2),
                "anagrafica": v.anagrafica,
                "layer": v.file,
            }
            for lato, v in sorted(contenuto.lati.items())
        },
        "file": [
            {"nome": f.nome, "contenitore": f.contenitore, "lato": f.lato,
             "dimensione_byte": f.dimensione, "compressa_byte": f.compressa,
             "tipo": f.tipo}
            for f in contenuto.elenco_file
        ],
        "non_riconosciuti": contenuto.inatteso,
        "osservazioni": osservazioni(contenuto),
    }
