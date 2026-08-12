# «La scansione non può essere aperta» — indagine

## Il riscontro del 12 agosto 2026

Primo pacchetto generato, provato dal tecnico sul software di modellazione:

| Passo | Esito |
|---|---|
| 1. Lo ZIP viene accettato in importazione | **sì** |
| 2. Il paziente compare in elenco | **sì**, correttamente |
| 3. Le immagini si aprono | **no** — `Errore - Modellazione: La scansione non può essere aperta!` |

I primi due passi dicono parecchio: l'involucro è a posto — nome
dell'archivio, `manifest.json`, struttura dei due ZIP annidati, nomi dei
file — e il `.his` viene letto e interpretato, altrimenti il paziente non
comparirebbe con i suoi dati. Il punto di rottura è il **caricamento dei
layer**.

## Confronto con i file autentici

Confrontando il pacchetto generato con l'originale, file per file:

| Layer | Esito |
|---|---|
| `.sca` | **identico** per dimensione e header, salvo il fattore di quota (è un dato calcolato) |
| `.ima` | **identico**, stessa osservazione |
| `.his` | terminatori **CRLF** invece di LF, e **a capo finale** che l'originale non ha |
| `.obj` | terminatori CRLF, **manca la riga finale** `# End of file.`, dimensione quasi doppia |
| `.farima` | **manca il chunk `pHYs`** presente nell'originale |
| `.bmp` | mancano i segmenti **EXIF** (`FFE1`) e gli altri metadati |
| ordine nello ZIP | i layer erano raggruppati per piede, negli originali non lo sono |

Che `.sca` e `.ima` risultino byte-compatibili è importante: la mappa quote,
cioè la geometria vera, era già scritta correttamente. Il sospetto si
concentra quindi sui layer accessori e sui dettagli di forma.

Il candidato principale è l'**OBJ**: se il lettore usa `# End of file.` per
riconoscere un file completo — una pratica comune nei formati proprietari —
un OBJ che ne è privo verrebbe scartato come troncato, e la scansione
risulterebbe non apribile pur essendo tutto il resto in ordine.

## Correzioni applicate

Tutte le difformità sono state allineate all'originale: `.his` e `.obj` in
LF, `# End of file.` in coda all'OBJ, mesh più rada (9.117 vertici e 17.730
facce contro 11.249 e 17.872 dell'originale, molto vicina), `pHYs` nel PNG,
EXIF nel JPEG, ordine dei layer come nei pacchetti autentici.

Nota su Pillow: il chunk `pHYs` non si ottiene aggiungendolo a mano ai
metadati — la libreria scarta i chunk che gestisce da sé — ma passando
`dpi` al salvataggio. Il primo tentativo era silenziosamente inefficace, e
se ne è accorto solo il controllo successivo.

## Le due prove successive

Sono stati preparati due pacchetti da provare **in quest'ordine**, perché
insieme dicono da che parte sta il problema:

**CONTROLLO FORMATO (02.02.2000)** — `strumenti/genera_prova_controllo.py`.
I layer sono i **byte originali intatti**: cambiano solo i nomi dei file e il
`.his`. È il controllo: se questo si apre, l'involucro e l'anagrafica sono
fuori discussione e il problema sta nei dati che generiamo. Se non si apre
nemmeno questo, il problema è a monte, nel confezionamento.

**PROVA IMPORT (01.01.2000)** — `strumenti/genera_prova_import.py`, rigenerato
con tutte le correzioni sopra.

| Controllo | Prova | Cosa significa |
|---|---|---|
| si apre | si apre | risolto: era una delle difformità corrette |
| si apre | non si apre | l'involucro va bene, resta qualcosa nei layer generati: si procede sostituendo un layer alla volta con l'originale |
| non si apre | — | il problema è nei nomi dei file o nel `.his`, non nei layer |

Nel terzo caso il sospetto si sposterebbe sulla marca temporale nei nomi o su
un vincolo dell'anagrafica, e servirebbe il programma dell'azienda per
capire quali controlli esegue in lettura.

## Collegamenti

- [[Verifiche aperte]]
- [[Decisioni di design]]
- [[Status componenti]]
