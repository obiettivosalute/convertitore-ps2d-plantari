# Scelta dello scanner e modo di acquisire

Valutazione del 13 agosto 2026, nata dall'ipotesi di comprare un
**Revopoint POP 4** e di far partire la scansione da dentro il gestionale,
su tablet, come si fa con l'app di `prese misure`.

## La domanda vera

L'obiettivo dichiarato è tornare al gesto di prima: aprire la lavorazione,
premere un riquadro, acquisire, e ritrovarsi la scansione registrata senza
passare da file da cercare e caricare a mano.

La domanda che decide tutto non è quale scanner sia più preciso, ma
**se il gestionale possa comandarlo**. La risposta cambia il progetto:
se sì, l'acquisizione vive dentro la nostra finestra; se no, vive nel
software del produttore e noi possiamo solo raccogliere quel che esce.

## Il Revopoint POP 4

Scanner palmare ibrido: laser blu multistrato, luce strutturata a
infrarossi, VCSEL. 286 g più impugnatura-batteria da 5500 mAh, circa
quattro ore in wireless. Dichiara fino a 0,03 mm in modalità laser. Sul
mercato europeo sta intorno ai 950 €.

**Quello che va benissimo.** Esporta in PLY, OBJ, STL e 3MF, tutti formati
che il convertitore legge già: da quel lato il lavoro è zero. E lo si
userebbe su **calchi in schiuma**, non su piedi vivi — il calco sta fermo,
è opaco, ha geometria netta, e sparisce buona parte della difficoltà dello
scanning palmare.

**Quello che non si può fare.** Il POP 4 si collega solo in Wi-Fi e parla
solo con Revo Scan, il software di Revopoint. Non è una camera che
un'applicazione possa aprire.

Un SDK esiste, a pagamento, in C++ e Python, ma il forum ufficiale dice due
cose che lo escludono: *«The SDK doesn't support scanning directly»* — si
leggono i dati e si impostano i parametri, non si comanda una scansione — e
l'elenco dei modelli compatibili (POP 2, POP 3, RANGE, MINI, INSPIRE,
RANGE 2, MINI 2, POP 3 Plus) **non comprende il POP 4**, con nota esplicita
che la licenza non copre i modelli futuri.

Prima di comprare conviene comunque scrivere a `customer@revopoint3d.com` e
chiedere tre cose secche: il POP 4 è coperto dall'SDK, l'SDK permette di
**avviare** una scansione, esiste supporto Android. Sono domande gratis che
chiudono la questione in un senso o nell'altro.

## Le tre famiglie, e cosa costano davvero

Cercando alternative si scopre che il mercato si divide in tre, e che su
Amazon esiste solo la prima.

**Scanner chiavi in mano** — Revopoint, Creality, 3DMakerpro, Einstar.
Scansionano benissimo, costano fra 400 e 1500 €, e l'acquisizione è chiusa
dentro il software del produttore. Nessuno di questi si comanda dal nostro
gestionale.

**Camere di profondità** — Intel RealSense D4xx, Orbbec Femto. Dai 300 ai
600 €, si trovano su Amazon, e hanno SDK **aperti e gratuiti** (Python e
C++, Orbbec anche Android): il controllo della cattura è totale, si avvia e
si ferma da codice nostro. Ma non sono scanner: danno fotogrammi di
profondità, e trasformarli in una superficie pulita e metricamente corretta
è esattamente il lavoro che manca. Non si compra un componente, si apre un
progetto.

**Scanner professionali con SDK** — Polyga, Shining3D serie 2X. Hanno
entrambe le cose: qualità di scansione e API programmabili (Polyga in
C++/C#/riga di comando, inclusa con lo scanner; Shining3D via un servizio
che dialoga in ZMQ). Ma il Polyga H3 parte da 9.990 dollari, e nessuno dei
due si compra su Amazon.

**Quindi: il prodotto che si cerca — palmare, da Amazon, sotto i mille
euro, comandabile dal nostro software — non esiste.** Si sceglie fra
comprare la qualità e rinunciare al controllo, o comprare il controllo e
costruire la qualità.

## L'escamotage, che vale il 90%

Rinunciando a comandare lo scanner, il gesto dell'operatore si può comunque
ridurre quasi a quello desiderato:

1. il gestionale diventa una web app, come `prese misure`, servita dal PC;
   il tablet la apre nel browser
2. si apre la lavorazione e si preme «Acquisisci»: parte Revo Scan
3. si scansiona e si esporta in STL nella cartella di esportazione
4. **il gestionale sorveglia quella cartella**: appena compare un file
   nuovo lo associa alla lavorazione aperta, converte e genera il pacchetto

L'operatore non tocca mai un file. L'unico passaggio irriducibile è che
l'acquisizione avviene dentro Revo Scan.

Va detto chiaro che il punto 1 è la parte di lavoro più grossa e **non
dipende dallo scanner**: l'interfaccia attuale è PyQt6, un'applicazione
desktop che su un tablet non gira. `prese misure` si apre sul tablet perché
è Flask. Rifare l'interfaccia come web app è un progetto a sé, che va
deciso per conto suo.

## Un'idea che vale la pena tenere da parte

C'è un dettaglio del nostro caso che rende la seconda famiglia meno assurda
di quanto sembri: **il formato di destinazione è 2.5D**, una mappa quote su
griglia da 0,5 mm, non una mesh chiusa. Una camera di profondità montata
fissa sopra un calco fermo produce esattamente quello — una mappa di
profondità dall'alto — senza bisogno di fusione, allineamento o
ricostruzione della mesh, che è la parte difficile.

Non è però una raccomandazione, per due motivi onesti. Il primo è la
precisione: la D405 dichiara ±1,4% a 20 cm, cioè quasi tre millimetri, e
per inquadrare un piede intero servirebbe stare più lontano, dove l'errore
cresce. Mediare molti fotogrammi su un oggetto fermo abbatte il rumore
casuale ma non l'errore sistematico. Il secondo è che resta comunque
software da scrivere e da tarare, mentre un POP 4 quel lavoro lo fa già.

Va tenuta da parte come idea, non presa come piano.

## Cosa si consiglia

Per la situazione attuale — convertitore funzionante, lavorazione su calchi
in schiuma, un operatore — **lo scanner chiavi in mano più la sorveglianza
della cartella** è la scelta giusta. Costruire uno scanner da una camera di
profondità sarebbe mesi di lavoro per rifare quello che un dispositivo da
950 € fa già bene.

Il POP 4 va bene. Solo, si compra un ottimo scanner, non un componente
integrabile.

## Collegamenti

- [[Roadmap]]
- [[Verifiche aperte]]
- [[Stack tecnologico]]
- [[2026-08-13 - Sessione 4, il formato e chiuso]]
