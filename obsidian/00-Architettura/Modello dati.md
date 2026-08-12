# Modello dati

Archivio SQLite in `data/plantari.db`. Tre tabelle.

## `clienti`

| Campo | Tipo | Note |
|---|---|---|
| `id` | INTEGER | chiave primaria |
| `cognome`, `nome` | TEXT | obbligatori |
| `data_nascita` | TEXT | formato `GG.MM.AAAA`, lo stesso che finisce nei file |
| `email`, `telefono`, `note` | TEXT | facoltativi |
| `creato_il`, `modificato_il` | TEXT | ISO 8601 |

Chiave naturale: **cognome + nome + data di nascita**, con vincolo di
unicità. È la stessa terna che identifica il paziente nel `.his` e nei nomi
dei file, quindi due clienti indistinguibili nel formato lo sono anche in
archivio.

## `lavorazioni`

| Campo | Note |
|---|---|
| `cliente_id` | riferimento a `clienti`, con cancellazione a cascata |
| `creata_il` | ISO 8601 |
| `descrizione`, `note` | testo libero |
| `stato` | `bozza` oppure `esportata` |
| `cartella` | dove sono finiti i file generati |
| `ps2d`, `zip_invio` | percorsi dei pacchetti |
| `codice_invio` | i sei caratteri esadecimali in coda al nome dello ZIP |

## `file_lavorazione`

Una riga per ogni file, con `ruolo` che distingue **origine** (il modello
caricato) da **generato** (i layer e i pacchetti prodotti).

Porta anche le misure rilevate in conversione — lunghezza, larghezza,
altezza, numero di vertici e facce — così l'archivio conserva le dimensioni
del pezzo anche senza riaprire il file. `impronta` è uno SHA-256 abbreviato,
utile per accorgersi che lo stesso modello è stato caricato due volte.

## Cartelle su disco

```
data/
├── plantari.db                    archivio
├── originali/                     copia dei modelli caricati
│   └── Cognome_Nome_GG.MM.AAAA/
│       └── AAAAMMGG_HHMMSS_Links.stl
└── archivio/                      pacchetti generati
    └── Cognome_Nome_GG.MM.AAAA/
        └── AAAAMMGG_HHMMSS_lavNNNNN/
            ├── i sei layer per piede
            ├── ....ps2d
            └── Clinica_....zip
```

Una cartella per lavorazione: rigenerare non sovrascrive mai il pacchetto
precedente, e resta traccia di cosa è stato mandato in fresa e quando.

## Aggancio al gestionale esistente

Previsto ma non ancora fatto. `prese misure` ha già la sua anagrafica in
`database.db`: l'idea è leggerla in sola lettura per proporre i clienti già
noti, senza duplicare i dati. Vedi [[Roadmap]].

## Collegamenti

- [[Decisioni di design]]
- [[Status componenti]]
