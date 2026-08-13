# Evoluzione: il gestionale come app dentro `prese misure`

Disegno di destinazione, deciso il 13 agosto 2026. Non è ancora stato
scritto codice: questa nota fissa la forma, i vincoli e l'ordine in cui
conviene procedere, così che quando si comincia non si ridiscuta tutto.

## Il gesto che si vuole ottenere

Il tecnico apre l'app sul tablet, sceglie una **scheda paziente già
esistente** in `prese misure`, acquisisce le due scansioni destra e
sinistra, e il sistema fa il resto: costruisce il pacchetto per la fresa,
lo recapita al PC della fresa, e ne conserva traccia nella scheda del
paziente, dove più avanti si potranno rivedere le due scansioni.

Nessun file da cercare, rinominare o caricare a mano.

## Cosa c'è già, e vale più di quanto sembri

**Il motore di conversione è headless.** `src/servizio.py` importa numpy,
`config`, `src/db` e `src/ps2d`: nessuna traccia di Qt, che vive solo in
`src/gui/`. La funzione `esporta(archivio, cliente, sx, dx, opzioni)` è
già chiamabile da una vista Flask senza modifiche. L'interfaccia PyQt6 è
un guscio, non il programma.

**`prese misure` è predisposto per l'innesto.** Ha `create_app()` e
blueprint registrati con prefisso — `/schede`, `/admin`, `/ricontrolli`,
`/clienti-ats`. Un `/scanner` si aggiunge con lo stesso schema. Non è un
adattamento forzato: è il pattern che il progetto usa già.

**Le schede paziente esistono.** Scegliere un nominativo invece di
reinserirlo è la voce «aggancio a `prese misure`» già in [[Roadmap]].

**L'archivio che permane c'è**: SQLite più i file per lavorazione, e
`riesporta()` rigenera un pacchetto a distanza di tempo.

Il grosso del lavoro nuovo è quindi **l'interfaccia web**, non la logica.

## La forma decisa

**Tablet Android.** Revo Scan gira su Android, quindi la scansione dal
tablet è possibile e non solo dal PC.

**PC della fresa sulla stessa rete.** Questo cancella la mail: il
pacchetto si scrive direttamente in una **cartella condivisa** che il PC
della fresa vede. È più semplice, è immediato, e soprattutto non fa
transitare dati sanitari per la posta elettronica — nome, cognome, data di
nascita e conformazione del piede sono dati sanitari, e la mail è il
canale peggiore per muoverli. L'esito della scrittura diventa lo stato
«consegnato» nella lavorazione, che la posta non avrebbe mai dato con
certezza.

**Come arriva l'STL dal tablet al server.** Revo Scan esporta in una
cartella del tablet, che il server non vede. Due modi, in ordine di
preferenza:

1. **sincronizzazione della cartella** (tipo Syncthing) fra tablet e
   server: l'STL compare da solo nella cartella sorvegliata e il gesto
   resta a zero tocchi. È la strada che realizza il sogno per intero
2. **caricamento dal browser**: un tocco su «scegli file» nella pagina
   della lavorazione. Un tocco, non un dramma, e non richiede software in
   più sul tablet

Se si preferisce non installare niente sul tablet, resta la terza via:
**tablet come interfaccia, PC come stazione di scansione.** Si apre la
scheda sul tablet ma si scansiona dal PC, dove la cartella sorvegliata
funziona senza intermediari.

## Le cose che vanno decise prima di scrivere codice

**Quale piede è quale.** Il sistema deve saperlo. La soluzione minima è
che l'interfaccia lo chieda prima di ogni acquisizione — «ora il destro» —
e assegni per ordine di arrivo. Va progettata dentro, non aggiunta dopo.

**Le immagini nella scheda paziente.** Attenzione a un equivoco: la
conversione mesh → mappa quote **butta via la texture**, e il `.farima`
che generiamo non è una foto del piede ma una tinta neutra sintetica,
calcolata dall'ombreggiatura. «Vedere le due immagini a colori dello scan»
oggi non è possibile così com'è.

Due strade. Conservare la texture del POP 4 come allegato della
lavorazione — lavoro in più, e non entra nel PS2D. Oppure mostrare la
**mappa quote a colori**, che il gestionale già disegna in
`src/gui/anteprima.py`: rosso l'appoggio, blu l'arco, isoipse ogni 5 mm.
È quasi gratis ed è clinicamente più utile di una fotografia, perché ci si
leggono l'arco e le zone di carico. Salvo indicazione contraria è questa
la strada.

## Vincoli da rispettare

**`prese misure` è in produzione**, ci si lavora tutti i giorni. L'innesto
deve essere un blueprint isolato: sue rotte, sue tabelle, **nessuna
modifica alle viste esistenti**. Altrimenti un guasto dello scanner
diventa un guasto delle fatture.

**L'anagrafica si legge in sola lettura.** Le schede paziente restano di
`prese misure`; il modulo scanner non le crea e non le modifica.

**I dati restano in sede.** Nessun pacchetto su servizi esterni, nessuna
mail con dati sanitari: cartella condivisa sulla rete locale.

## Ordine in cui conviene procedere

1. **Blueprint `/scanner` che elenca le lavorazioni esistenti** leggendo
   l'anagrafica di `prese misure`. Nessuna acquisizione, solo lettura:
   serve a validare l'innesto senza rischi
2. **Caricamento manuale dei due modelli** e chiamata a `esporta()`. Da
   qui il flusso è già completo, solo con un tocco in più
3. **Cartella sorvegliata**, che sostituisce il caricamento manuale
4. **Consegna alla fresa** sulla cartella condivisa, con stato «consegnato»
5. **Vista della scheda paziente** con le mappe quote dei due piedi
6. Eventuale sincronizzazione dal tablet, se si sceglie quella strada

I primi due passi danno già un sistema usabile. Dal terzo in poi si tolgono
gesti all'operatore.

## Cosa resta com'è

L'interfaccia PyQt6 non va buttata: continua a servire da PC per
l'ispezione dei pacchetti e per i casi fuori flusso. Le due interfacce
condividono lo stesso motore, quindi non divergono.

## Collegamenti

- [[Scelta dello scanner e acquisizione]]
- [[Roadmap]]
- [[Modello dati]]
- [[Status componenti]]
