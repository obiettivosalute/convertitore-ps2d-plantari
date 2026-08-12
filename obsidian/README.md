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

## Punti fermi

- Il formato PS2D è stato ricostruito per reverse engineering: la specifica
  completa sta in `docs/FORMATO_PS2D.md`.
- La geometria vive nel layer `.sca`, una mappa quote a 16 bit su griglia da
  0,5 mm. Tutto il resto è derivato.
- L'archivio clienti resta **sul computer**: sono dati sanitari e la cartella
  `data/` è esclusa dal repository.
- Resta da confermare sul campo come il software della fresa interpreti i
  pacchetti generati. Vedi [[Verifiche aperte]].

## Collegamenti

- [[Decisioni di design]]
- [[Modello dati]]
- [[Stack tecnologico]]
- [[Status componenti]]
- [[Verifiche aperte]]
- [[Roadmap]]
