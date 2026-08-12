# Stack tecnologico

## Librerie

| Libreria | A cosa serve |
|---|---|
| **PyQt6** | interfaccia desktop, coerente con il gestionale `prese misure` |
| **numpy** | mappe quote e proiezione, tutto vettorizzato |
| **scipy** | chiusura dei buchi (`ndimage`) e analisi nelle prove |
| **trimesh** | lettura di STL, OBJ, PLY, 3MF, GLB e infittimento della mesh |
| **Pillow** | scrittura dei layer PNG e JPEG |

Nessuna dipendenza da OpenGL: l'anteprima è un'immagine calcolata in numpy e
disegnata come pixmap. Meno cose da installare, nessun problema di driver.

## Perché non un motore 3D vero

L'anteprima serve a controllare orientamento e superficie proiettata, non a
ispezionare la mesh. Una mappa a colori con isoipse ogni 5 mm dice più di un
rendering ombreggiato: si vede subito dove sta l'arco e quanto è alto.

## Organizzazione del codice

```
main.py                 avvio, con --controlla e --ispeziona da riga di comando
config.py               percorsi, dati della clinica, costanti del formato
src/
├── ps2d/
│   ├── formats.py      header PCIM/PCSC, lettura e scrittura dei layer binari
│   ├── mesh2height.py  mesh -> mappa quote (il pezzo delicato)
│   ├── writer.py       generazione dei sei layer e dei due ZIP
│   └── reader.py       lettura e ispezione di pacchetti esistenti
├── db/database.py      archivio SQLite
├── servizio.py         orchestrazione: conversione, archivio, pacchetti
└── gui/                schede PyQt6
tests/
├── test_precisione.py  quanto sbaglia la conversione, in millimetri
├── test_roundtrip.py   rigenera un pacchetto da una scansione reale
└── test_flusso.py      percorso completo senza interfaccia
```

La conversione è separata dall'interfaccia: `src/servizio.py` non importa
nulla di Qt, quindi tutto il percorso è collaudabile da riga di comando e
riutilizzabile in un'eventuale versione batch.

## Threading

Conversione e anteprima girano in `QThread` separati: un STL da qualche
milione di triangoli richiede secondi, e la finestra non deve congelarsi.
I riferimenti a thread e worker vanno tenuti vivi lato Python, altrimenti
Qt li distrugge a metà lavoro.

## Prove

Le prove non sono su `pytest` ma script eseguibili che stampano numeri
leggibili: interessa **di quanto** sbaglia la conversione, non solo se passa.

```
py -3 tests\test_precisione.py <pacchetto.ps2d>
py -3 tests\test_roundtrip.py <cartella_layer> <pacchetto.ps2d>
py -3 tests\test_flusso.py
```

## Collegamenti

- [[Decisioni di design]]
- [[Status componenti]]
