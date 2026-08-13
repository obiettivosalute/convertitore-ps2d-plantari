# Gestionale Plantari — vault di progetto

Vault Obsidian del progetto **scanner 3d per fresa - convertitore stl**.
Raccoglie decisioni, avanzamento e questioni aperte.

## Cosa fa il progetto

Un gestionale desktop che prende i modelli 3D dei plantari destro e sinistro
(STL, OBJ, PLY), li converte nel formato **PS2D** letto dal software della
fresa e tiene l'archivio dei clienti e delle lavorazioni, così che ogni
pacchetto sia rigenerabile in futuro.

## Struttura del vault

| Cartella | Contenuto |
|---|---|
| `00-Architettura` | Decisioni di design, modello dati, stack |
| `01-Progressioni` | Diario delle sessioni di lavoro |
| `02-Aggiornamenti` | Stato dei componenti |
| `03-Anomalie` | Problemi noti e verifiche ancora aperte |
| `04-Roadmap` | Cosa manca e in che ordine |

## A che punto siamo — 13 agosto 2026

**Il formato è validato.** Un pacchetto scritto interamente da noi viene
importato dal software di modellazione, apre entrambi i piedi con
l'orientamento corretto e arriva alla pagina di modellazione. Il gestionale
è completo, collaudato e accettato dalla fresa.

Il guasto delle prime due prove era il `.farima`: va scritto **capovolto**
rispetto al `.sca`, e il suo chunk `pHYs` deve dichiarare la scala vera
della griglia. È stato isolato generando una serie di pacchetti ibridi, uno
per layer, e chiedendo al software quale rifiutasse. Il racconto sta in
[[Import rifiutato - indagine]].

Da qui in avanti il progetto **dipende dallo scanner**, che non è ancora
stato acquistato. Alla ripresa non c'è nessuna domanda in sospeso: si
sceglie da [[Roadmap]].

## Punti fermi

- Il formato PS2D è stato ricostruito per reverse engineering: la specifica
  completa sta in `docs/FORMATO_PS2D.md`. Il registro dei formati di
  paro360 ne ha poi confermato firme ed estensioni.
- La geometria vive nel layer `.sca`, una mappa quote a 16 bit su griglia da
  0,5 mm. Tutto il resto è derivato.
- **Il verso delle righe non è uniforme fra i layer**: il `.farima` va
  capovolto rispetto al `.sca`, l'`.ima` no. È la trappola che è costata
  due giri di prove.
- Al lettore della fresa non importano mesh più rada, immagini
  risintetizzate, ordine dei file nello ZIP né fattore di quota
  ricalcolato: si è verificato sul campo che li accetta tutti.
- L'archivio clienti resta **sul computer**: sono dati sanitari e la cartella
  `data/` è esclusa dal repository.

## Collegamenti

- [[Decisioni di design]]
- [[Modello dati]]
- [[Stack tecnologico]]
- [[Status componenti]]
- [[Verifiche aperte]]
- [[Roadmap]]
