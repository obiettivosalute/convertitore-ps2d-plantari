# Status componenti

Aggiornato al 12 agosto 2026.

> **In attesa di riscontro**: il pacchetto di prova è stato consegnato al
> tecnico il 12 agosto. Finché non si sa se il software di modellazione lo
> importa, tutto il resto resta in sospeso — vedi [[Verifiche aperte]] per
> cosa farsi riferire.

| Componente | File | Stato | Note |
|---|---|---|---|
| Header e layer binari | `src/ps2d/formats.py` | **fatto** | firma, griglia, fattori di scala, `.his` |
| Mesh → mappa quote | `src/ps2d/mesh2height.py` | **fatto** | proiezione in due passaggi, errore 0,02 mm |
| Generazione pacchetti | `src/ps2d/writer.py` | **fatto** | sei layer, `.ps2d`, ZIP con manifest |
| Lettura pacchetti | `src/ps2d/reader.py` | **fatto** | apre sia `.ps2d` sia ZIP di invio |
| Archivio SQLite | `src/db/database.py` | **fatto** | clienti, lavorazioni, file |
| Orchestrazione | `src/servizio.py` | **fatto** | indipendente da Qt |
| Interfaccia | `src/gui/` | **fatto** | tre schede, conversione in thread separato |
| Prove | `tests/` | **fatto** | precisione, round-trip, flusso |
| Riconoscimento del verso | `src/ps2d/mesh2height.py` | **fatto** | criterio sull'asimmetria delle quote |
| Ritaglio del piano | `src/ps2d/ritaglio.py` | **fatto** | con salvaguardie contro i falsi allarmi |
| Strumento di prova import | `strumenti/genera_prova_import.py` | **fatto** | rigenera un pacchetto da una scansione autentica |
| Documentazione formato | `docs/FORMATO_PS2D.md` | **fatto** | specifica completa |
| Prova di import | — | **consegnata** | in attesa del riscontro del tecnico |
| Taratura su calco vero | — | **da fare** | soglie del ritaglio e orientamento dello scanner |
| Acquisizione diretta (fase 2) | — | **da fare** | dipende dallo scanner, non ancora acquistato |
| Aggancio a `prese misure` | — | **da fare** | anagrafica in sola lettura |

## Dettaglio delle prove

```
superficie analitica       errore medio 0,003 mm   max 0,032 mm
andata e ritorno reale     r = 0,999   errore 0,02–0,03 mm (zone regolari)
round-trip da OBJ scanner  r = 0,966   (OBJ campionato a 3 mm)
flusso completo            12 file, anagrafica e griglia verificate
```

## Comportamento noto e accettato

Sulle **discontinuità di quota** l'errore di proiezione sale a qualche
millimetro. È il limite della rappresentazione 2.5D — una parete verticale
vista dall'alto ricade sulle celle vicine — e riguarda i bordi del plantare,
non la superficie d'appoggio. Nelle zone regolari, che sono l'80-84% della
superficie, l'errore resta sotto i tre centesimi di millimetro.

## Collegamenti

- [[Verifiche aperte]]
- [[Roadmap]]
- [[Stack tecnologico]]
