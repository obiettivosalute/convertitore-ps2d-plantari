# Status componenti

Aggiornato al 13 agosto 2026.

> **Prova di import superata: il formato è validato.** Un pacchetto scritto
> interamente da noi viene importato, apre entrambi i piedi con
> l'orientamento corretto e arriva alla modellazione. Il guasto era il
> `.farima`, capovolto e con il `pHYs` sbagliato. Vedi
> [[Import rifiutato - indagine]]. Da qui in avanti il progetto dipende
> dallo scanner, non più dal software della fresa.

| Componente | File | Stato | Note |
|---|---|---|---|
| Header e layer binari | `src/ps2d/formats.py` | **fatto** | firma, griglia, fattori di scala, `.his` |
| Mesh → mappa quote | `src/ps2d/mesh2height.py` | **fatto** | proiezione in due passaggi, errore 0,02 mm |
| Generazione pacchetti | `src/ps2d/writer.py` | **fatto** | sei layer, `.ps2d`, ZIP con manifest |
| Lettura pacchetti | `src/ps2d/reader.py` | **fatto** | apre sia `.ps2d` sia ZIP di invio; inventario, report e osservazioni automatiche |
| Ispezione di un pacchetto | `src/gui/ispezione.py` | **fatto** | sei schede, anteprime delle mappe quote, export del report in txt e json |
| Archivio SQLite | `src/db/database.py` | **fatto** | clienti, lavorazioni, file |
| Orchestrazione | `src/servizio.py` | **fatto** | indipendente da Qt |
| Interfaccia | `src/gui/` | **fatto** | tre schede, conversione in thread separato |
| Prove | `tests/` | **fatto** | precisione, round-trip, flusso |
| Riconoscimento del verso | `src/ps2d/mesh2height.py` | **fatto** | criterio sull'asimmetria delle quote |
| Ritaglio del piano | `src/ps2d/ritaglio.py` | **fatto** | con salvaguardie contro i falsi allarmi |
| Strumento di prova import | `strumenti/genera_prova_import.py` | **fatto** | rigenera un pacchetto da una scansione autentica |
| Strumento di controllo | `strumenti/genera_prova_controllo.py` | **fatto** | originale con la sola anagrafica cambiata, per isolare il guasto |
| Strumento pacchetti ibridi | `strumenti/genera_prove_ibride.py` | **fatto** | un layer sostituito per volta; `--solo` e `--giro` per i cicli successivi |
| Documentazione formato | `docs/FORMATO_PS2D.md` | **fatto** | specifica completa, con le due convenzioni del `.farima` |
| Prova di import | — | **superata** | il pacchetto generato si apre e arriva alla modellazione |
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

## Cosa il lettore della fresa non guarda

Il pacchetto generato si apre pur restando diverso dall'originale su
parecchi fronti: mesh più rada (4.920 vertici contro 10.963 sul destro),
`.ima` e `.bmp` risintetizzati invece che ripresi dalla camera, JPEG senza
i segmenti `APP13` e `DRI`, file in ordine diverso dentro lo ZIP, fattore
di quota ricalcolato. Nessuna di queste cose conta. Contava solo il verso
del `.farima` e la scala dichiarata nel suo `pHYs`.

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
