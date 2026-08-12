# Decisioni di design

## D1 — Il `.sca` è la fonte di verità, non l'`.obj`

**Decisione.** Il generatore costruisce prima la mappa quote e da quella
deriva tutti gli altri layer, `.obj` compreso.

**Perché.** Nei pacchetti autentici i due contengono lo stesso dato: la
correlazione fra la superficie dell'OBJ e la mappa quote è −0,91 sul piede
sinistro e −0,84 sul destro (segno negativo perché l'asse verticale è
invertito), e l'escursione coincide entro tre decimi di millimetro. L'OBJ
però è campionato a 3 mm, la mappa quote a 0,5 mm: partire dall'OBJ
significherebbe buttare via risoluzione.

---

## D2 — Proiezione in due passaggi invece del semplice massimo

**Decisione.** Per ogni cella si individua prima la quota massima, poi si
media fra i campioni che stanno entro un pixel da essa.

**Perché.** Prendere il massimo introduce una sovrastima sistematica: su una
superficie inclinata il punto più alto caduto nella cella si trova sul suo
bordo, mentre la mappa deve contenere il valore al centro. La prova lo ha
mostrato senza ambiguità — 44.362 celle alzate, **zero abbassate**, errore
medio 0,13 mm. Con la media l'errore medio scende a 0,02 mm e la prova su
superficie analitica migliora di sei volte.

**Conseguenza.** Sulle pareti quasi verticali la media taglia leggermente il
bordo (frazioni di millimetro). È il compromesso giusto: la superficie di
appoggio conta, il fianco del plantare no.

---

## D3 — Griglia standard predefinita, ma leggibile dall'header

**Decisione.** Si genera per impostazione predefinita su griglia 340 × 684 a
0,5 mm, con possibilità di adattarla al modello.

**Perché.** I due esempi reali hanno griglie diverse (340 × 684 e 342 × 685):
la dimensione non è fissa nel formato e in lettura va sempre presa
dall'header. In scrittura conviene però restare sul valore più ricorrente,
per somigliare il più possibile ai file che la fresa già digerisce.

---

## D4 — Rilevamento automatico delle unità di misura

**Decisione.** Si deduce l'unità dalla dimensione maggiore del modello: sotto
1,5 metri, sotto 45 centimetri, oltre millimetri. Resta possibile forzarla.

**Perché.** Né STL né OBJ dichiarano l'unità: contengono numeri puri. Gli OBJ
prodotti dallo scanner sono in metri, la maggior parte degli STL in
millimetri. Senza rilevamento il primo file di prova è stato interpretato
come un plantare da 0,3 mm.

---

## D5 — Anche un solo piede è una lavorazione valida

**Decisione.** L'esportazione accetta anche un solo lato.

**Perché.** Capita di rifare un plantare singolo. Obbligare a caricare il
controlaterale costringerebbe a inventare un file.

---

## D5b — Riconoscimento del verso invece di un'impostazione da ricordare

**Decisione.** Sotto ogni anteprima il programma dichiara se la superficie è
orientata nel verso giusto, invece di lasciarlo capire all'operatore.

**Perché.** Chi importa da uno scanner diverso non può sapere in anticipo
come è orientato l'asse verticale, e una mappa rovesciata non è evidente a
colpo d'occhio: sembra semplicemente un altro piede.

**Come.** Le zone di appoggio occupano gran parte dell'area e stanno vicine
al sensore, l'arco è una minoranza che se ne allontana: la distribuzione
delle quote è quindi molto asimmetrica. Sulla scansione di riferimento, 81%
dell'area nella metà alta e asimmetria −1,31; rovesciando l'asse diventano
19% e +1,31. Le soglie (60%/−0,30 e 40%/+0,30) lasciano in mezzo una fascia
di incertezza in cui il programma dichiara di non sapere, invece di tirare a
indovinare — ed è quello che succede sul piede sinistro del pacchetto di
riferimento, dove il piano d'appoggio acquisito falsa la distribuzione.

---

## D5c — Il ritaglio del piano si ferma quando rischia di fare danni

**Decisione.** L'isolamento dell'impronta dal piano circostante non viene
applicato se ciò che resterebbe è più piccolo di 100 cm², o se si butterebbe
via oltre il 70% dell'area acquisita.

**Perché.** Serve per i calchi in schiuma, dove entra tutto il blocco insieme
all'impronta. Ma un plantare già modellato ha spesso una base piatta estesa
che somiglia moltissimo a un piano d'appoggio: senza salvaguardie il ritaglio
teneva solo la gobba dell'arco, buttando via il 78% del modello. Meglio non
intervenire e spiegare perché, che intervenire male.

**Verificato su.** Il pacchetto di riferimento contiene i due casi opposti:
sul piede sinistro il piano viene tolto e la lunghezza torna da 295 a 254 mm,
coerente con il destro (249 mm); sul destro, già pulito, il ritaglio non
interviene.

---

## D6 — I dati dei clienti non lasciano il computer

**Decisione.** SQLite locale sotto `data/`, cartella esclusa dal repository
tramite `.gitignore`.

**Perché.** Nome, cognome, data di nascita e conformazione del piede sono
dati sanitari. Il repository è pubblico e contiene **solo codice**.

---

## D7 — Archiviazione dei modelli originali

**Decisione.** Ogni file caricato viene copiato in `data/originali/` e
registrato con la sua impronta SHA-256.

**Perché.** Rende possibile rigenerare un pacchetto a distanza di tempo —
per esempio se cambiano i parametri di conversione o se il laboratorio
chiede un formato diverso — senza dover ritrovare il file di partenza.

---

## Collegamenti

- [[Modello dati]]
- [[Stack tecnologico]]
- [[Verifiche aperte]]
