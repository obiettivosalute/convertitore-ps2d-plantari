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

È anche un miglioramento rispetto a **come si lavorava prima**: con il
vecchio sistema si scansionava dal tablet con il programma del fornitore e
il file finiva alla fresa **via mail**. La cartella condivisa toglie quel
passaggio e con esso l'unico punto in cui i dati uscivano dalla rete
aziendale. Da qui in avanti **tutto resta dentro l'azienda, niente esce**:
è un vincolo del progetto, non una preferenza.

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

## Le decisioni prese

**Le immagini nella scheda paziente: mappa quote a colori.** Va sciolto un
equivoco che sta a monte: la conversione mesh → mappa quote **butta via la
texture**, e il `.farima` che generiamo non è una foto del piede ma una
tinta neutra sintetica, calcolata dall'ombreggiatura. Una fotografia a
colori dello scan, oggi, non esiste nel nostro pacchetto.

Si mostra quindi la **mappa quote a colori**, quella che il gestionale già
disegna in `src/gui/anteprima.py`: rosso l'appoggio, blu l'arco, isoipse
ogni 5 mm. È quasi gratis ed è clinicamente più utile di una fotografia,
perché ci si leggono l'arco e le zone di carico.

**Come arriva l'STL al server: si vagliano entrambe le strade sul campo.**
Sincronizzazione della cartella o caricamento dal browser, la scelta si fa
quando si arriva al punto 3, con lo scanner in mano.

**Quale piede è quale: lo si chiede, ma lo si verifica.** L'interfaccia lo
chiede prima di ogni acquisizione — «ora il destro» — e assegna per ordine
di arrivo, ma il sistema **controlla la geometria** e avvisa se non torna.
Vedi la sezione seguente.

## Riconoscere destro e sinistro: da fare

Da non confondere con quello che c'è già. `valuta_verso()` in
`src/ps2d/mesh2height.py` giudica il verso **verticale** — se la pianta
guarda il sensore o se è rovesciata — dalla distribuzione delle quote:
sulla scansione di riferimento l'81% dell'area sta nella metà alta, con
asimmetria −1,31, e rovesciando l'asse i valori si invertono con ampio
margine. Non dice nulla su quale piede sia.

Distinguere destro da sinistro è un'altra misura, e si può fare: **l'arco
sta sul lato mediale**, quindi la mappa quote è asimmetrica rispetto
all'asse longitudinale, e da che parte cade la zona bassa dice qual è il
piede. È lo stesso genere di criterio già usato per il verso, applicato
all'altro asse.

**Attenzione a cosa deve significare «il sistema sistema».** Se l'operatore
ha detto «destro» e la geometria dice sinistro, la correzione giusta è
**scambiare l'etichetta**, non specchiare la geometria: specchiarla
produrrebbe un plantare per il piede sbagliato, che è un danno vero, non un
fastidio. E se **entrambe** le scansioni risultassero lo stesso piede, il
sistema non deve indovinare: si ferma e chiede, perché o si è scansionato
due volte lo stesso piede o il criterio ha sbagliato.

Per lo stesso motivo il controllo **propone** e non corregge in silenzio:
su un prodotto che finisce sotto il piede di una persona, un riconoscimento
che sbaglia da solo è peggio dell'errore che previene. L'operatore conferma
con un tocco.

## Vincoli da rispettare

**`prese misure` è in produzione**, ci si lavora tutti i giorni. L'innesto
arriva per ultimo (fase B) e deve essere un blueprint isolato: sue rotte,
sue tabelle, **nessuna modifica alle viste esistenti**. Altrimenti un
guasto dello scanner diventa un guasto delle fatture.

**L'anagrafica si legge in sola lettura.** Le schede paziente restano di
`prese misure`; il modulo scanner non le crea e non le modifica.

**I dati restano in sede.** Nessun pacchetto su servizi esterni, nessuna
mail con dati sanitari: cartella condivisa sulla rete locale.

## Due tempi: prima autonomo, poi innestato

Deciso il 13 agosto 2026, ed è la scelta che tiene al riparo la
produzione. **Non si parte innestando.** Si costruisce prima la versione
web come applicazione **a sé stante**, la si prova sul campo con lo
scanner vero, e solo quando funziona la si innesta in `prese misure`.

Tre motivi. Il primo è che si sbaglia molto, all'inizio, e sbagliare su un
programma isolato non costa niente mentre sbagliare dentro `prese misure`
ferma il lavoro di tutti. Il secondo è che così le due strade restano
percorribili in parallelo: chi lavora allo scanner non aspetta chi lavora
alle fatture. Il terzo è che l'innesto, fatto alla fine su codice già
collaudato, si riduce a registrare un blueprint e a cambiare da dove si
prende l'anagrafica — un giorno di lavoro invece di un rischio continuo.

Perché questo funzioni, una regola sola: **il modulo non deve mai dare per
scontato di essere dentro `prese misure`**. L'anagrafica si prende da
un'interfaccia sottile, che nella versione autonoma legge dall'archivio
locale e nella versione innestata legge da quella di `prese misure`. Se
questa separazione si rispetta dal primo giorno, l'innesto è indolore; se
si perde, va riscritto tutto.

## Ordine in cui conviene procedere

**Fase A — applicazione autonoma**

1. **Interfaccia web che elenca clienti e lavorazioni** dall'archivio
   locale, sola lettura. Serve a mettere in piedi il guscio Flask sopra il
   motore che c'è già
2. **Caricamento manuale dei due modelli** e chiamata a `esporta()`. Da
   qui il flusso è già completo, solo con un tocco in più
3. **Cartella sorvegliata**, che sostituisce il caricamento manuale. Qui
   si decide fra sincronizzazione dal tablet e caricamento dal browser
4. **Consegna alla fresa** sulla cartella condivisa, con stato «consegnato»
5. **Scheda con le mappe quote a colori** dei due piedi
6. **Riconoscimento di destro e sinistro** come controllo, con proposta di
   scambio all'operatore

**Fase B — innesto in `prese misure`**

7. Blueprint `/scanner` isolato, e l'interfaccia dell'anagrafica che passa
   a leggere le schede paziente di `prese misure` in sola lettura

I primi due passi danno già un sistema usabile. Dal terzo in poi si tolgono
gesti all'operatore. Il settimo non aggiunge funzioni: cambia solo dove
vive il modulo e da dove prende i nomi.

## Cosa resta com'è

L'interfaccia PyQt6 non va buttata: continua a servire da PC per
l'ispezione dei pacchetti e per i casi fuori flusso. Le due interfacce
condividono lo stesso motore, quindi non divergono.

## Collegamenti

- [[Scelta dello scanner e acquisizione]]
- [[Roadmap]]
- [[Modello dati]]
- [[Status componenti]]
