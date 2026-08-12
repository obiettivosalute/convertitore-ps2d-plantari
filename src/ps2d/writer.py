"""Generazione del pacchetto PS2D completo a partire dalle mappe quote.

Un .ps2d e' uno ZIP (senza compressione dichiarata particolare) che contiene
sei file per ciascun piede:

    .sca      mappa quote 16 bit          <- la geometria vera
    .ima      immagine 8 bit              <- vista in scala di grigi
    .farima   PNG RGBA                    <- immagine a colori + maschera
    .bmp      JPEG in scala di grigi      <- anteprima ombreggiata
    .obj      mesh Wavefront in metri     <- superficie triangolata
    .his      metadati testuali           <- anagrafica e impostazioni

Il pacchetto di invio e' un secondo ZIP che avvolge il .ps2d insieme a un
manifest.json con i dati dell'ordine.
"""

from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

from config import (CLIENT_DEVICE_UDID, CLINICA_NOME, LATO_DX, LATO_SX,
                    PRACTITIONER_ID, SFONDO_IMA, SFONDO_SCA)

from .formats import scrivi_his, scrivi_ima, scrivi_sca


@dataclass
class DatiPaziente:
    """Anagrafica minima richiesta dal formato."""

    nome: str
    cognome: str
    data_nascita: str          # GG.MM.AAAA
    email: str = ""

    def slug(self) -> str:
        n = self.nome.strip().replace(" ", "-")
        c = self.cognome.strip().replace(" ", "-")
        return f"{n}_{c}_{self.data_nascita}"


# --------------------------------------------------------------- ombreggiatura
def _normali(quote_mm: np.ndarray, mm_per_px: float) -> np.ndarray:
    """Normali di superficie approssimate dal gradiente della mappa quote."""
    gy, gx = np.gradient(quote_mm.astype(np.float64), mm_per_px)
    n = np.dstack([-gx, -gy, np.ones_like(gx)])
    norma = np.linalg.norm(n, axis=2, keepdims=True)
    return n / np.where(norma == 0, 1, norma)


def _ombreggiatura(quote_mm: np.ndarray, maschera: np.ndarray,
                   mm_per_px: float) -> np.ndarray:
    """Illuminazione diffusa, valori 0..1, usata per i layer visivi."""
    n = _normali(quote_mm, mm_per_px)
    luce = np.array([-0.35, -0.45, 0.82])
    luce = luce / np.linalg.norm(luce)
    diff = np.clip(n @ luce, 0.0, 1.0)
    # un po' di rilievo dalla quota stessa, per leggere meglio l'arco
    q = quote_mm.copy()
    if maschera.any():
        qmin, qmax = q[maschera].min(), q[maschera].max()
        if qmax > qmin:
            q = (q - qmin) / (qmax - qmin)
        else:
            q = np.zeros_like(q)
    return np.clip(0.55 * diff + 0.45 * q, 0.0, 1.0) * maschera


# --------------------------------------------------------------- layer visivi
def genera_ima(quote_mm: np.ndarray, maschera: np.ndarray,
               mm_per_px: float) -> np.ndarray:
    """Immagine 8 bit: sfondo bianco come nei file dello scanner."""
    sh = _ombreggiatura(quote_mm, maschera, mm_per_px)
    img = np.full(quote_mm.shape, SFONDO_IMA, dtype=np.uint8)
    img[maschera] = np.clip(40 + sh[maschera] * 180, 0, 254).astype(np.uint8)
    return img


def genera_farima(quote_mm: np.ndarray, maschera: np.ndarray,
                  mm_per_px: float) -> Image.Image:
    """PNG RGBA: il canale alfa e' la maschera dei pixel validi."""
    sh = _ombreggiatura(quote_mm, maschera, mm_per_px)
    base = np.array([182, 168, 158], dtype=np.float64)     # tinta neutra
    rgb = (base[None, None, :] * (0.45 + 0.55 * sh[..., None])).clip(0, 255)
    out = np.zeros((*quote_mm.shape, 4), dtype=np.uint8)
    out[..., :3] = rgb.astype(np.uint8)
    out[..., 3] = np.where(maschera, 255, 0).astype(np.uint8)
    out[~maschera, :3] = 0
    return Image.fromarray(out, mode="RGBA")


def _exif_base(larghezza: int, altezza: int) -> bytes:
    """EXIF minimo con gli stessi campi dei file autentici.

    Negli originali sono presenti: Compression, XResolution, YResolution,
    ResolutionUnit, YCbCrPositioning, PixelXDimension e PixelYDimension.
    """
    exif = Image.Exif()
    exif[0x0128] = 2          # ResolutionUnit: pollici
    exif[0x011A] = 72.0       # XResolution
    exif[0x011B] = 72.0       # YResolution
    exif[0x0112] = 1          # Orientation
    exif[0x0213] = 2          # YCbCrPositioning
    exif[0xA002] = larghezza  # PixelXDimension
    exif[0xA003] = altezza    # PixelYDimension
    return exif.tobytes()


def genera_bmp(quote_mm: np.ndarray, maschera: np.ndarray,
               mm_per_px: float) -> Image.Image:
    """Anteprima JPEG in scala di grigi, sfondo scuro."""
    sh = _ombreggiatura(quote_mm, maschera, mm_per_px)
    img = np.zeros(quote_mm.shape, dtype=np.uint8)
    img[maschera] = np.clip(30 + sh[maschera] * 225, 0, 255).astype(np.uint8)
    return Image.fromarray(img, mode="L")


# --------------------------------------------------------------- mesh OBJ
def genera_obj(quote_mm: np.ndarray, maschera: np.ndarray, mm_per_px: float,
               passo_px: int = 4) -> str:
    """Costruisce la mesh Wavefront dalla mappa quote.

    Coordinate in metri e assi come li scrive lo scanner: X trasversale,
    Y verticale, Z longitudinale, il tutto centrato sull'origine.
    """
    h, w = quote_mm.shape
    ys = np.arange(0, h, passo_px)
    xs = np.arange(0, w, passo_px)
    Q = quote_mm[np.ix_(ys, xs)]
    M = maschera[np.ix_(ys, xs)]

    # coordinate fisiche centrate
    X = (xs - (w - 1) / 2.0) * mm_per_px / 1000.0
    Z = (ys - (h - 1) / 2.0) * mm_per_px / 1000.0
    if M.any():
        centro_q = (Q[M].max() + Q[M].min()) / 2.0
    else:
        centro_q = 0.0
    Y = (Q - centro_q) / 1000.0

    indice = np.full(Q.shape, -1, dtype=np.int64)
    indice[M] = np.arange(int(M.sum()))

    righe: list[str] = ["# Generated.", "mtllib Model.mtl"]
    jj, ii = np.nonzero(M)
    for r, c in zip(jj, ii):
        righe.append(f"v {X[c]:.4f} {Y[r, c]:.4f} {Z[r]:.4f}")

    # normali dal gradiente sulla griglia sottocampionata
    n = _normali(Q, mm_per_px * passo_px)
    for r, c in zip(jj, ii):
        righe.append(f"vn {n[r, c, 0]:.4f} {n[r, c, 2]:.4f} {n[r, c, 1]:.4f}")

    for r, c in zip(jj, ii):
        righe.append(f"vt {c / max(1, Q.shape[1] - 1):.4f} "
                     f"{1.0 - r / max(1, Q.shape[0] - 1):.4f}")

    righe.append("usemtl material0")
    # due triangoli per ogni quadrato con i quattro vertici presenti
    a = indice[:-1, :-1]
    b = indice[:-1, 1:]
    c_ = indice[1:, 1:]
    d = indice[1:, :-1]
    ok = (a >= 0) & (b >= 0) & (c_ >= 0) & (d >= 0)
    for A, B, C, D in zip(a[ok] + 1, b[ok] + 1, c_[ok] + 1, d[ok] + 1):
        righe.append(f"f {A}/{A}/{A} {B}/{B}/{B} {C}/{C}/{C}")
        righe.append(f"f {A}/{A}/{A} {C}/{C}/{C} {D}/{D}/{D}")
    # I file autentici chiudono con questa riga: se il lettore la usa per
    # riconoscere un file completo, ometterla lo farebbe scartare.
    righe.append("# End of file.")
    return "\n".join(righe) + "\n"


# --------------------------------------------------------------- pacchetti
def _nome_base(paziente: DatiPaziente, lato: str, istante: datetime) -> str:
    return f"{paziente.slug()}_{lato}_{istante:%Y%m%d_%H%M%S}"


def scrivi_lato(cartella: Path, paziente: DatiPaziente, lato: str,
                quote_mm: np.ndarray, maschera: np.ndarray, mm_per_px: float,
                mm_per_unita_z: float, valori_sca: np.ndarray,
                istante: datetime, passo_obj: int = 4) -> list[Path]:
    """Scrive i sei file di un piede e restituisce i percorsi.

    Il nome contiene la data di nascita puntata, quindi i percorsi vanno
    composti per concatenazione: with_suffix() taglierebbe tutto a partire
    dall'ultimo punto.
    """
    radice = _nome_base(paziente, lato, istante)

    def percorso(ext: str) -> Path:
        return cartella / f"{radice}.{ext}"

    cartella.mkdir(parents=True, exist_ok=True)
    prodotti: list[Path] = []

    scrivi_sca(percorso("sca"), valori_sca, mm_per_px, mm_per_unita_z)
    prodotti.append(percorso("sca"))

    scrivi_ima(percorso("ima"), genera_ima(quote_mm, maschera, mm_per_px),
               mm_per_px, mm_per_unita_z)
    prodotti.append(percorso("ima"))

    # pHYs e EXIF sono presenti nei file autentici: si replicano per non
    # discostarsi da cio' che il lettore e' abituato a ricevere. Il chunk
    # pHYs si ottiene passando dpi al salvataggio: aggiunto a mano fra i
    # metadati verrebbe scartato, perche' Pillow gestisce da se' i chunk noti.
    genera_farima(quote_mm, maschera, mm_per_px).save(
        percorso("farima"), format="PNG", dpi=(72, 72))
    prodotti.append(percorso("farima"))

    genera_bmp(quote_mm, maschera, mm_per_px).save(
        percorso("bmp"), format="JPEG", quality=88, dpi=(72, 72),
        exif=_exif_base(quote_mm.shape[1], quote_mm.shape[0]))
    prodotti.append(percorso("bmp"))

    # scrittura binaria: l'OBJ autentico usa LF, e su Windows write_text
    # tradurrebbe ogni a capo in CRLF
    percorso("obj").write_bytes(
        genera_obj(quote_mm, maschera, mm_per_px, passo_obj).encode("ascii"))
    prodotti.append(percorso("obj"))

    scrivi_his(percorso("his"), paziente.nome, paziente.cognome,
               paziente.data_nascita)
    prodotti.append(percorso("his"))

    return prodotti


# Ordine con cui i layer compaiono nei pacchetti autentici: non sono
# raggruppati per piede, e l'estensione .ima apre l'archivio. Non e' detto
# che il lettore ci badi, ma somigliare all'originale costa nulla.
ORDINE_LAYER = ["ima", "bmp", "his", "obj", "farima", "sca"]


def _chiave_ordine(percorso: Path) -> tuple:
    ext = percorso.suffix.lstrip(".").lower()
    posizione = ORDINE_LAYER.index(ext) if ext in ORDINE_LAYER else len(ORDINE_LAYER)
    lato = 0 if f"_{LATO_SX}_" in percorso.name else 1
    return (posizione, lato)


def impacchetta_ps2d(destinazione: Path, file_da_includere: list[Path]) -> Path:
    """Crea il .ps2d, che e' uno ZIP con dentro i layer dei due piedi."""
    destinazione.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destinazione, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(file_da_includere, key=_chiave_ordine):
            z.write(f, arcname=f.name)
    return destinazione


def costruisci_manifest(paziente: DatiPaziente, nome_ps2d: str,
                        nome_archivio: str, istante: datetime) -> dict:
    """Manifest dell'ordine, nella stessa forma di quelli ricevuti."""
    ts = istante.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + \
        f"{istante.microsecond // 1000:03d}Z"
    return {
        "patient": {"contactEmail": paziente.email},
        "order": {
            "assets": [
                {
                    "createdAt": ts,
                    "deviceSerial": "",
                    "caption": nome_ps2d,
                    "type": "PS2D",
                    "filename": nome_ps2d,
                }
            ]
        },
        "archiveFilename": nome_archivio,
        "clientDeviceUDID": CLIENT_DEVICE_UDID,
        "submittedAt": ts,
        "practitionerId": PRACTITIONER_ID,
        "clinic": {"name": CLINICA_NOME},
    }


def impacchetta_invio(destinazione: Path, ps2d: Path, paziente: DatiPaziente,
                      istante: datetime) -> Path:
    """Crea lo ZIP di invio con manifest.json accanto al .ps2d."""
    manifest = costruisci_manifest(paziente, ps2d.name, destinazione.name, istante)
    destinazione.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destinazione, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(ps2d, arcname=ps2d.name)
        z.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
    return destinazione


def nome_archivio_invio(paziente: DatiPaziente, istante: datetime,
                        codice: str) -> str:
    """Replica lo schema di denominazione degli archivi ricevuti."""
    n = paziente.nome.strip().replace(" ", "-")
    c = paziente.cognome.strip().replace(" ", "-")
    return (f"{CLINICA_NOME}_{n}-{c}_-{paziente.data_nascita}-"
            f"{istante:%d.%m.%Y}-{codice}.zip")
