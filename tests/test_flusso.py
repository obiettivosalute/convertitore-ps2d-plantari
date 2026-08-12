"""Prova il flusso completo senza interfaccia: cliente, conversione, pacchetti.

Usa un archivio temporaneo, cosi' non tocca i dati reali.
"""

from __future__ import annotations

import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import trimesh

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))

from src.db import Archivio
from src.ps2d import leggi_ps2d
from src.servizio import OpzioniConversione, esporta


def plantare_finto(destinazione: Path, lunghezza=265.0, larghezza=95.0,
                   specchia=False) -> Path:
    """Costruisce un solido a forma di plantare e lo salva in STL."""
    passo = 1.0
    xs = np.arange(0, larghezza + passo, passo)
    ys = np.arange(0, lunghezza + passo, passo)
    X, Y = np.meshgrid(xs, ys)

    # contorno arrotondato
    mezza = larghezza / 2
    raggio = mezza * (1.0 - 0.35 * ((Y - lunghezza * 0.55) / (lunghezza * 0.6)) ** 2)
    dentro = np.abs(X - mezza) <= raggio

    # sopra: sostegno dell'arco sul lato mediale, tallone incavato
    lato = (X - mezza) if not specchia else (mezza - X)
    sopra = (14.0 * np.exp(-(((lato + 20) / 20.0) ** 2 + ((Y - 100) / 45.0) ** 2))
             + 4.0 * np.exp(-((Y - 30) / 28.0) ** 2)
             + 3.0)
    sotto = np.zeros_like(sopra)

    V, F = [], []
    indice_sopra = np.full(X.shape, -1, dtype=np.int64)
    indice_sotto = np.full(X.shape, -1, dtype=np.int64)
    n = 0
    for j in range(X.shape[0]):
        for i in range(X.shape[1]):
            if not dentro[j, i]:
                continue
            V.append((X[j, i], Y[j, i], sopra[j, i])); indice_sopra[j, i] = n; n += 1
            V.append((X[j, i], Y[j, i], sotto[j, i])); indice_sotto[j, i] = n; n += 1

    for j in range(X.shape[0] - 1):
        for i in range(X.shape[1] - 1):
            quadrato = [(j, i), (j, i + 1), (j + 1, i + 1), (j + 1, i)]
            if not all(dentro[a, b] for a, b in quadrato):
                continue
            a, b, c, d = (indice_sopra[p] for p in quadrato)
            F += [(a, b, c), (a, c, d)]
            a2, b2, c2, d2 = (indice_sotto[p] for p in quadrato)
            F += [(a2, c2, b2), (a2, d2, c2)]

    # pareti laterali lungo il contorno
    for j in range(X.shape[0] - 1):
        for i in range(X.shape[1] - 1):
            if not dentro[j, i]:
                continue
            for (jj, ii) in ((j, i + 1), (j + 1, i)):
                if dentro[jj, ii]:
                    continue
                a, b = indice_sopra[j, i], indice_sotto[j, i]
                F += [(a, b, a)]           # degenere: verra' scartato
    mesh = trimesh.Trimesh(vertices=np.array(V), faces=np.array(F), process=True)
    mesh.export(destinazione)
    return destinazione


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        sx = plantare_finto(tmp / "sinistro.stl", specchia=False)
        dx = plantare_finto(tmp / "destro.stl", specchia=True)
        print(f"modelli di prova: {sx.stat().st_size:,} e {dx.stat().st_size:,} byte")

        archivio = Archivio(tmp / "prova.db")
        cliente = archivio.trova_o_crea_cliente("Rossi", "Mario", "15.03.1975",
                                                "mario@example.com", "3331234567")
        print(f"cliente creato: {cliente.etichetta}")

        passi: list[str] = []
        # I modelli di prova sono plantari, quindi serve la faccia superiore:
        # per le scansioni di piede si usa invece quella inferiore, la pianta.
        # Il ritaglio resta acceso di proposito: un plantare ha una base
        # piatta estesa che somiglia a un piano d'appoggio, e qui si verifica
        # che le salvaguardie impediscano di scambiarla per tale.
        esito = esporta(archivio, cliente, sx, dx,
                        OpzioniConversione(genera_zip_invio=True,
                                           superficie="superiore",
                                           ritaglia_piano=True),
                        descrizione="prova automatica",
                        avanzamento=passi.append)

        print(f"\npassi: {len(passi)}")
        for p in passi:
            print(f"   {p}")
        print(f"\nriuscito: {esito.riuscito}")
        for e in esito.errori:
            print(f"  ERRORE {e}")
        for a in esito.avvisi:
            print(f"  avviso {a}")
        if not esito.riuscito:
            return 1

        with zipfile.ZipFile(esito.ps2d) as z:
            nomi = sorted(z.namelist())
        print(f"\ncontenuto del .ps2d ({len(nomi)} file):")
        for nome in nomi:
            print(f"   {nome}")
        atteso = 12
        if len(nomi) != atteso:
            print(f"  ATTESI {atteso} file, trovati {len(nomi)}")
            return 1

        letto = leggi_ps2d(esito.zip_invio)
        print("\nrilettura del pacchetto di invio:")
        print(f"   anagrafica: {letto.anagrafica}")
        print(f"   clinica   : {letto.manifest['clinic']['name']}")
        for lato, v in sorted(letto.lati.items()):
            L, W = v.ingombro_mm()
            print(f"   {lato:7s} {v.larghezza}x{v.altezza} px  "
                  f"ingombro {L:.0f}x{W:.0f} mm  rilievo {v.escursione_mm:.1f} mm")

        controlli = [
            (letto.anagrafica.get("name") == "Mario", "nome nel .his"),
            (letto.anagrafica.get("vname") == "Rossi", "cognome nel .his"),
            (letto.anagrafica.get("gebdat") == "15.03.1975", "data di nascita"),
            (set(letto.lati) == {"Links", "Rechts"}, "presenza dei due piedi"),
            (all(v.larghezza == 340 and v.altezza == 684
                 for v in letto.lati.values()), "griglia standard"),
            (all(14.0 < v.escursione_mm < 26.0
                 for v in letto.lati.values()), "rilievo plausibile"),
            (not any("tolto il piano" in a for a in esito.avvisi),
             "la base piatta del plantare non viene scambiata per un piano"),
        ]
        print()
        ok = True
        for esatto, cosa in controlli:
            print(f"   {'OK  ' if esatto else 'NO  '} {cosa}")
            ok = ok and esatto

        righe = archivio.elenca_lavorazioni()
        file_registrati = archivio.file_di(righe[0]["id"])
        print(f"\narchivio: {len(righe)} lavorazioni, "
              f"{len(file_registrati)} file registrati")
        print(f"riepilogo: {archivio.riepilogo()}")
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
