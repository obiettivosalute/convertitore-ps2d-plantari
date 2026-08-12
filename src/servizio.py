"""Orchestrazione: dai file caricati al pacchetto pronto per la fresa.

Tiene insieme conversione, archivio e generazione dei pacchetti, in modo che
l'interfaccia grafica debba solo raccogliere i dati e mostrare l'esito.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np

from config import (FRAME_H, FRAME_W, LATO_DX, LATO_SX, MARGINE_MM,
                    PIXEL_MM_X)

from .db import Archivio, Cliente, archivia_originale, cartella_lavorazione
from .ps2d import (DatiPaziente, carica_mesh, controlla_plausibilita, converti,
                   impacchetta_invio, impacchetta_ps2d, nome_archivio_invio,
                   quantizza, scrivi_lato)
from .ps2d.mesh2height import RisultatoConversione
from .ps2d.ritaglio import applica, isola_impronta


@dataclass
class OpzioniConversione:
    """Parametri con cui proiettare le mesh sulla griglia."""

    mm_per_px: float = PIXEL_MM_X
    usa_frame_standard: bool = True
    frame: tuple[int, int] = (FRAME_W, FRAME_H)
    margine_mm: float = MARGINE_MM
    superficie: str = "superiore"
    unita: str = "auto"
    ruota_gradi_sx: float = 0.0
    ruota_gradi_dx: float = 0.0
    specchia_sx: bool = False
    specchia_dx: bool = False
    ritaglia_piano: bool = True
    margine_ritaglio_mm: float = 4.0
    # 4 px = 2 mm: dà una mesh di densità simile a quella dei file autentici
    passo_obj: int = 4
    genera_zip_invio: bool = True


@dataclass
class EsitoLato:
    lato: str
    origine: Path
    risultato: RisultatoConversione | None = None
    valori_sca: np.ndarray | None = None
    mm_per_unita_z: float = 0.0
    avvisi: list[str] = field(default_factory=list)
    errore: str = ""

    @property
    def riuscito(self) -> bool:
        return self.errore == "" and self.risultato is not None


@dataclass
class EsitoLavorazione:
    lavorazione_id: int
    cartella: Path
    ps2d: Path | None = None
    zip_invio: Path | None = None
    lati: dict[str, EsitoLato] = field(default_factory=dict)
    avvisi: list[str] = field(default_factory=list)
    errori: list[str] = field(default_factory=list)

    @property
    def riuscito(self) -> bool:
        return self.ps2d is not None and not self.errori


def prepara_lato(percorso: Path, lato: str, opzioni: OpzioniConversione,
                 avanzamento=None) -> EsitoLato:
    """Carica un file e lo proietta sulla griglia del formato."""
    esito = EsitoLato(lato=lato, origine=Path(percorso))
    try:
        if avanzamento:
            avanzamento(f"{lato}: lettura di {Path(percorso).name}")
        mesh = carica_mesh(percorso)

        if avanzamento:
            avanzamento(f"{lato}: proiezione sulla griglia")
        sinistro = lato == LATO_SX
        risultato = converti(
            mesh,
            mm_per_px=opzioni.mm_per_px,
            frame=opzioni.frame if opzioni.usa_frame_standard else None,
            margine_mm=opzioni.margine_mm,
            superficie=opzioni.superficie,
            unita=opzioni.unita,
            ruota_gradi=(opzioni.ruota_gradi_sx if sinistro
                         else opzioni.ruota_gradi_dx),
            specchia=opzioni.specchia_sx if sinistro else opzioni.specchia_dx,
        )
        if opzioni.ritaglia_piano:
            if avanzamento:
                avanzamento(f"{lato}: ricerca del piano da togliere")
            ritaglio = isola_impronta(
                risultato.quote_mm, risultato.maschera,
                margine_mm=opzioni.margine_ritaglio_mm,
                mm_per_px=opzioni.mm_per_px)
            if ritaglio.applicato:
                risultato.quote_mm = applica(risultato.quote_mm, ritaglio)
                risultato.maschera = ritaglio.maschera
            risultato.avvisi.append(ritaglio.motivo)

        esito.risultato = risultato
        esito.avvisi = list(risultato.avvisi) + controlla_plausibilita(risultato)

        if avanzamento:
            avanzamento(f"{lato}: quantizzazione a 16 bit")
        esito.valori_sca, esito.mm_per_unita_z = quantizza(risultato)
    except Exception as exc:
        esito.errore = str(exc)
    return esito


def esporta(archivio: Archivio, cliente: Cliente,
            file_sx: Path | None, file_dx: Path | None,
            opzioni: OpzioniConversione | None = None,
            descrizione: str = "", note: str = "",
            avanzamento=None) -> EsitoLavorazione:
    """Percorso completo: conversione, archiviazione, pacchetti.

    Accetta anche un solo piede: chi lavora un plantare singolo non deve
    essere costretto a caricare il controlaterale.
    """
    opzioni = opzioni or OpzioniConversione()
    istante = datetime.now()

    lavorazione = archivio.crea_lavorazione(cliente.id, descrizione, note)
    cartella = cartella_lavorazione(cliente, lavorazione.id, istante)
    esito = EsitoLavorazione(lavorazione_id=lavorazione.id, cartella=cartella)

    sorgenti = [(LATO_SX, file_sx), (LATO_DX, file_dx)]
    if not any(p for _, p in sorgenti):
        esito.errori.append("nessun file caricato")
        return esito

    paziente = DatiPaziente(cliente.nome, cliente.cognome,
                            cliente.data_nascita, cliente.email)
    prodotti: list[Path] = []

    for lato, percorso in sorgenti:
        if not percorso:
            continue
        lato_esito = prepara_lato(Path(percorso), lato, opzioni, avanzamento)
        esito.lati[lato] = lato_esito
        if not lato_esito.riuscito:
            esito.errori.append(f"{lato}: {lato_esito.errore}")
            continue
        esito.avvisi += [f"{lato}: {a}" for a in lato_esito.avvisi]

        copia = archivia_originale(Path(percorso), cliente, lato)
        r = lato_esito.risultato
        archivio.registra_file(
            lavorazione.id, lato, "origine", copia, Path(percorso).name,
            {"lunghezza_mm": r.lunghezza_mm, "larghezza_mm": r.larghezza_mm,
             "altezza_mm": r.altezza_mm, "n_vertici": r.n_vertici,
             "n_facce": r.n_facce})

        if avanzamento:
            avanzamento(f"{lato}: scrittura dei sei layer")
        prodotti += scrivi_lato(
            cartella, paziente, lato, r.quote_mm, r.maschera,
            opzioni.mm_per_px, lato_esito.mm_per_unita_z,
            lato_esito.valori_sca, istante, opzioni.passo_obj)

    if not prodotti:
        esito.errori.append("nessun layer generato: conversione fallita")
        return esito

    if avanzamento:
        avanzamento("creazione del pacchetto .ps2d")
    nome_ps2d = f"{paziente.slug()}_{istante:%Y%m%d_%H%M%S}.ps2d"
    esito.ps2d = impacchetta_ps2d(cartella / nome_ps2d, prodotti)

    codice = secrets.token_hex(3).upper()
    if opzioni.genera_zip_invio:
        if avanzamento:
            avanzamento("creazione dell'archivio di invio")
        esito.zip_invio = impacchetta_invio(
            cartella / nome_archivio_invio(paziente, istante, codice),
            esito.ps2d, paziente, istante)

    archivio.aggiorna_lavorazione(
        lavorazione.id, stato="esportata", cartella=str(cartella),
        ps2d=str(esito.ps2d), codice_invio=codice,
        zip_invio=str(esito.zip_invio) if esito.zip_invio else "")

    for p in prodotti:
        lato = LATO_SX if f"_{LATO_SX}_" in p.name else LATO_DX
        archivio.registra_file(lavorazione.id, lato, "generato", p)
    archivio.registra_file(lavorazione.id, "-", "generato", esito.ps2d)
    if esito.zip_invio:
        archivio.registra_file(lavorazione.id, "-", "generato", esito.zip_invio)

    if avanzamento:
        avanzamento("completato")
    return esito


def riesporta(archivio: Archivio, lavorazione_id: int,
              opzioni: OpzioniConversione | None = None,
              avanzamento=None) -> EsitoLavorazione:
    """Rigenera il pacchetto di una lavorazione dai file originali archiviati."""
    righe = archivio.elenca_lavorazioni()
    riga = next((r for r in righe if r["id"] == lavorazione_id), None)
    if riga is None:
        raise ValueError(f"lavorazione {lavorazione_id} inesistente")
    cliente = archivio.cliente(riga["cliente_id"])
    if cliente is None:
        raise ValueError("cliente non trovato")

    origini = archivio.file_di(lavorazione_id, ruolo="origine")
    sx = next((Path(f["percorso"]) for f in origini if f["lato"] == LATO_SX), None)
    dx = next((Path(f["percorso"]) for f in origini if f["lato"] == LATO_DX), None)
    mancanti = [str(p) for p in (sx, dx) if p is not None and not p.exists()]
    if mancanti:
        raise FileNotFoundError("file originali non piu' disponibili: "
                                + ", ".join(mancanti))
    return esporta(archivio, cliente, sx, dx, opzioni,
                   descrizione=f"riesportazione della lavorazione {lavorazione_id}",
                   note=riga.get("note", ""), avanzamento=avanzamento)
