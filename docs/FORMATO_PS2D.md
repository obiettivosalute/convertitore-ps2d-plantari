# Il formato PS2D

Specifica ricostruita analizzando pacchetti autentici prodotti dallo scanner.
Non esiste documentazione ufficiale: quanto segue è il risultato di reverse
engineering, verificato rigenerando i file e confrontandoli con gli originali.

Pacchetto di riferimento usato per la decodifica: un ordine reale di luglio
2026, 1,3 MB, contenente la scansione di entrambi i piedi. Gli esempi
riportati qui sotto usano nomi di fantasia.

---

## 1. Struttura a scatole

Un ordine completo è fatto di tre livelli annidati:

```
Clinica_Nome-Cognome_-GG.MM.AAAA-GG.MM.AAAA-XXXXXX.zip     ZIP di invio
├── manifest.json                                          dati dell'ordine
└── Nome_Cognome_GG.MM.AAAA_AAAAMMGG_HHMMSS.ps2d           anch'esso uno ZIP
    ├── ..._Links_AAAAMMGG_HHMMSS.sca      mappa quote 16 bit   ← la geometria
    ├── ..._Links_....ima                  immagine 8 bit
    ├── ..._Links_....farima               PNG RGBA (colore + maschera)
    ├── ..._Links_....bmp                  in realtà un JPEG grigio
    ├── ..._Links_....obj                  mesh Wavefront in metri
    ├── ..._Links_....his                  metadati testuali
    └── ...Rechts...                       gli stessi sei file per l'altro piede
```

`Links` è il piede **sinistro**, `Rechts` il **destro**: il software che
genera questi file è tedesco. Lo si vede anche nelle chiavi del `.his`
(`KONTRAST`, `HELLIGKEIT`, `GEBDAT`) e nel nome dell'estensione `.farima`,
che sta per *Farbimage*, immagine a colori.

L'estensione `.ps2d` non indica un formato binario proprio: è uno ZIP
regolare, apribile con qualsiasi archiviatore rinominandolo.

---

## 2. Header dei layer binari (`.ima` e `.sca`)

512 byte, poi i pixel grezzi senza padding, in ordine di riga.

| offset | tipo | contenuto |
|---|---|---|
| 0-9 | ascii | `PCIM001\r\n\x1A` (`.ima`) oppure `PCSC001\r\n\x1A` (`.sca`) |
| 10-11 | — | zero |
| 12-15 | uint32 LE | larghezza in pixel |
| 16-19 | uint32 LE | altezza in pixel |
| 20-31 | — | zero |
| 32-35 | float32 | millimetri per pixel sull'asse X (sempre 0,5) |
| 36-39 | float32 | millimetri per pixel sull'asse Y (sempre 0,5) |
| 40-43 | float32 | millimetri per unità di quota |
| 44 | uint8 | `0xFF` nell'`.ima` |
| 44-45 | uint16 | `0xFFFF` nel `.sca` |
| 46-511 | — | zero |

Dati dei due esempi reali:

| | Links | Rechts |
|---|---|---|
| griglia | 340 × 684 px | 342 × 685 px |
| area coperta | 170 × 342 mm | 171 × 342,5 mm |
| mm per unità di quota | 0,000831871 | 0,000724105 |
| fondo scala verticale | 54,52 mm | 47,45 mm |

La griglia **non è di dimensione fissa**: cambia di qualche pixel da una
scansione all'altra. Va sempre letta dall'header, mai data per scontata.

---

## 3. `.sca` — la mappa quote

`uint16` little endian, una quota per cella. È l'unico layer che contiene
la geometria vera; tutto il resto è derivato o accessorio.

**Convenzione del valore**: cresce allontanandosi dal sensore. Il punto più
prominente vale circa 0, e `65535` è riservato allo **sfondo**, cioè alle
celle dove non c'è geometria. Per ottenere l'altezza in millimetri:

```python
altezza_mm = (valore_massimo_valido - valore) * mm_per_unita_z
```

Con fondo scala 54 mm su 16 bit la risoluzione verticale è di circa
0,0008 mm: enormemente più fine di qualunque fresa, quindi la
quantizzazione non è mai il fattore limitante.

---

## 4. Gli altri layer

**`.ima`** — Immagine 8 bit, stessa griglia e stesso header del `.sca`.
Lo sfondo è bianco (255). Non è una riduzione del `.sca`: nei file reali la
correlazione fra i due è debole (0,29 sul piede sinistro, 0,77 sul destro),
quindi si tratta dell'immagine ottica della camera, non della profondità.

**`.farima`** — PNG RGBA con la foto a colori della pianta. Il canale alfa
è la maschera dei pixel validi e coincide con le celle non-sfondo del
`.sca`. Nei file reali il colore medio dell'area opaca è intorno a
(103, 114, 122), cioè pelle in luce fredda.

**`.bmp`** — Malgrado il nome è un **JPEG** in scala di grigi con EXIF, non
un bitmap. Sfondo scuro, correlazione negativa con il `.sca` (−0,70): è una
resa ombreggiata della profondità, buona come anteprima.

**`.obj`** — Mesh Wavefront standard con normali e coordinate UV.
Coordinate **in metri**. Assi: X trasversale, **Y verticale**, Z
longitudinale — attenzione, non è la convenzione Z-up abituale negli STL.
Negli esempi la mesh sta in un riquadro fisso di 141 × 321 mm centrato
sull'origine, con circa 11.000 vertici (passo di campionamento intorno ai
3 mm). Dichiara `mtllib Model.mtl`, ma quel file **non è nel pacchetto**:
la texture va agganciata a mano al `.farima`.

La superficie dell'`.obj` è la stessa del `.sca` con l'asse verticale
invertito e ricentrato: sui file reali la correlazione fra i due è −0,91
(sinistro) e −0,84 (destro), e l'escursione coincide (54,2 mm contro
54,46 mm). Non sono due acquisizioni diverse, sono lo stesso dato.

**`.his`** — Testo ASCII con terminatori CRLF:

```
USERDATA="NAME=Anna","VNAME=Verdi","GEBDAT=04.11.1982"
KONTRAST=1.000000
HELLIGKEIT=0
INVERT=0
3DSCAN=1
```

Attenzione all'inversione: `NAME` contiene il **nome proprio** e `VNAME` il
**cognome**, all'opposto di quanto suggerirebbe il tedesco (*Name* /
*Vorname*).

---

## 5. `manifest.json`

```json
{
  "patient": { "contactEmail": "..." },
  "order": {
    "assets": [{
      "createdAt": "2026-07-01T07:40:45.607Z",
      "deviceSerial": "",
      "caption": "<nome del .ps2d>",
      "type": "PS2D",
      "filename": "<nome del .ps2d>"
    }]
  },
  "archiveFilename": "<nome dello ZIP esterno>",
  "clientDeviceUDID": "<UUID del dispositivo>",
  "submittedAt": "2026-07-01T03:40:45.598Z",
  "practitionerId": 00000,
  "clinic": { "name": "Obiettivo Salute" }
}
```

`practitionerId` e `clientDeviceUDID` identificano il centro e il
dispositivo: sono in `config.py` e vanno cambiati se il pacchetto parte da
una postazione diversa.

---

## 6. Convertire una mesh in mappa quote

Il `.sca` è una rappresentazione **2.5D**: una sola quota per cella. Un
plantare in STL è invece un solido chiuso, con faccia superiore, inferiore
e pareti. Convertirlo significa proiettare: si tiene la faccia utile e si
scarta il resto.

Il procedimento adottato (`src/ps2d/mesh2height.py`):

1. **Unità** — nessun formato di mesh la dichiara. Si deduce dalla
   dimensione maggiore: sotto 1,5 sono metri, sotto 45 centimetri, oltre
   millimetri. Gli OBJ dello scanner sono in metri.
2. **Assi** — l'asse con estensione minima è il verticale, quello massimo
   la lunghezza. Un plantare è molto più lungo che largo e molto più largo
   che alto, quindi la regola non sbaglia.
3. **Infittimento** — la mesh viene suddivisa finché ogni lato è più corto
   di mezzo pixel, così ogni cella riceve dei campioni.
4. **Proiezione in due passaggi** — prima si trova la quota massima di ogni
   cella (individua la faccia superiore), poi si **media** i soli campioni
   che stanno entro un pixel da quel massimo.

Il quarto punto merita una spiegazione, perché è l'errore in cui è facile
cadere. Prendere semplicemente il massimo dei campioni caduti nella cella
produce una **sovrastima sistematica**: su una superficie inclinata il punto
più alto della cella sta sul suo bordo, non al centro, e la mappa quote deve
contenere il valore centrale. Nelle prove questo si vedeva chiaramente —
44.362 celle alzate e nessuna abbassata, con un errore medio di 0,13 mm.
Mediando invece i campioni della sola faccia superiore l'errore medio scende
a 0,02 mm.

### Precisione misurata

| prova | errore medio | errore max |
|---|---|---|
| superficie analitica nota | 0,003 mm | 0,032 mm |
| andata e ritorno su scansione reale, zone regolari | 0,02–0,03 mm | p99,9 = 0,10–0,13 mm |

Sulle **discontinuità** di quota l'errore sale a qualche millimetro, ed è un
limite intrinseco della rappresentazione 2.5D, non un difetto
dell'implementazione: una parete verticale, guardata dall'alto, ricade sulle
celle vicine. Riguarda i bordi del plantare e i gradini, non la superficie
di appoggio.

---

## 7. Cosa resta da verificare

Il generatore produce pacchetti **formalmente conformi** a quanto decodificato:
stessi header, stessa griglia, stessa convenzione delle quote, stessi sei
layer per piede, stessa struttura degli ZIP. Resta da confermare sul campo
**come il software della fresa interpreta il contenuto**: se lo tratta come
geometria finita da lavorare, oppure come scansione di un piede su cui
costruire il plantare secondo le proprie regole. Nel secondo caso il file
verrebbe letto senza errori ma il pezzo uscirebbe diverso da quello atteso.

La verifica richiede una prova reale sulla macchina. Vedi
`obsidian/03-Anomalie/Verifiche aperte.md`.
