# MKIK AI HACKATHON

## Belső tudástár, amit kérdezni lehet

Feladatleírás résztvevőknek · A rendszer használói kamarai munkatársak

## 1. A helyzet

A kamara munkatársai nap mint nap ugyanazokba a kérdésekbe futnak bele. Milyen eljárásrend szerint kell kezelni ezt a beérkező megkeresést? Ki hagyhat jóvá egy adott értékhatár feletti tételt? Milyen határidővel kell válaszolni? Melyik nyomtatvány az érvényes, és hova kell iktatni?

A válaszok léteznek. Ott vannak az ügyrendben, az eljárásrendekben, a belső szabályzatokban, a vezetői utasításokban és a körlevelekben. Csak éppen húsz dokumentumban szétszórva, és jó részük egyszerűbb a tapasztalt kollégától megkérdezni, mint kikeresni.

Ez két kollégát is megállít. A kérdezőt, amíg vár, és a tapasztalt munkatársat, akinek a napja részben azzal telik, hogy olyan kérdésre válaszol, amit már valaki leírt. Új belépőnél ez hetekig tart, és a fluktuációval újraindul.

Egy általános célú chatbot erre nem megoldás. A belső kérdésre kapott téves válasz nem áll meg a kamara falain belül: a munkatárs továbbadja a tagnak, az ügyfélnek, a hatóságnak — a kamara nevében. Amit a munkatárs jóhiszeműen kimond, azon a kamara számonkérhető. Ezért itt a magabiztosan előadott téves válasz többe kerül, mint a meg nem válaszolt kérdés.

## 2. A feladat

Építs olyan rendszert, amely a kamara előre betáplált belső dokumentumaiból válaszol a munkatársak magyar nyelvű kérdéseire, és minden válaszát visszavezeti a forrásra.

Amit tudnia kell

Magyarul feltehető kérdés, magyar válasz — abban a szaknyelvben, amit a dokumentumok használnak.

Minden érdemi állítás mellett ott a forrás: melyik dokumentum, melyik oldal, és mi a szó szerinti részlet, amire épül.

A forrás egy mozdulattal ellenőrizhető. A munkatársnak nem kell hinnie a rendszernek — meg tudja nézni, mielőtt továbbadja a választ.

Ha a kérdésre nincs fedezet a dokumentumokban, a rendszer ezt mondja meg. A „nem tudom” itt helyes válasz, a kitalált válasz nem.

A dokumentumállomány cserélhető és bővíthető anélkül, hogy fejlesztőt kellene hívni. A belső szabályzatok változnak, egy elavult válasz rosszabb, mint a semmi.

Ennyi a belépő. Ettől még nem nyer senki — a döntés a következő fejezetben leírt három szemponton fog eldőlni.

## 3. Három szempont, amit nem lehet megkerülni

A kamara nem demót vásárol, hanem rendszert, amit évekig üzemeltetni kell. Egy szépen működő bemutató önmagában kevés, ha ezekre a kérdésekre nincs válasz.

### 3.1 Bővíthetőség

A vezetőség kérni fog olyan funkciókat, amik ma nincsenek ezen a listán. Belső rendszernél tapasztalatból ezek jönnek elsőként:

jogosultságkezelés — nem minden munkatárs láthat minden belső anyagot; a HR-, pénzügyi és vezetői dokumentumok külön körbe tartoznak,

kimutatás arról, mit kérdeznek a legtöbben, és főleg mire nem talál választ a rendszer — ez megmutatja, hol hiányos a belső szabályozás,

szervezeti egységenként vagy területi kamaránként külön dokumentumkészlet,

tartalom átvétele a meglévő belső rendszerekből — iktatóból, intranetről, megosztott meghajtóról —, nem kézi feltöltéssel,

a válasz beillesztése a napi munkafolyamatba, ne külön megnyitandó felület legyen.

Nem az a kérdés, hogy ezek elkészültek-e a hackathonon. Nem is várjuk. Az a kérdés, hogy meg tudod-e mutatni, hova épülnek be, és nagyságrendileg mekkora munka. Egy megoldás, amit minden új kéréshez elölről kell írni, nem opció.

### 3.2 Skálázhatóság

A demó néhány tucat dokumentummal fut. A valóságban ez több száz, idővel több ezer belső dokumentum: ügyrend, eljárásrendek, szabályzatok, vezetői utasítások, körlevelek — több szervezeti egység és több területi kamara anyagával, munkaidőben párhuzamosan használva.

Mutasd meg, mi történik, ha a mennyiség tízszereződik: mi lassul, mi drágul, mit kell kicserélni, és mi az, ami változatlanul marad. Megalapozott becslés is elfogadható — az a fontos, hogy tudd, hol a határ, és mi van mögötte.

### 3.3 Ár

Egy megoldásról, aminek nem ismerjük a költségét, nem lehet dönteni. Add meg:

mennyibe kerül egyetlen kérdés megválaszolása,

mennyibe kerül a havi üzemeltetés — belső rendszernél ez jól becsülhető: munkatársak száma szorozva a napi kérdésszámmal,

mennyibe kerül a dokumentumállomány betöltése és rendszeres frissítése,

hol lehet a költségen faragni, és annak mi az ára minőségben.

A pontos szám kevésbé érdekes, mint az, hogy tudod, mitől függ. Aki azt mondja, hogy „olcsó”, az nem számolta ki.

## 4. Pluszpont: a saját ötleteid

Ez a dokumentum azt rögzíti, mit várunk el. Attól még nem lesz jó a megoldás, hogy megfelel neki.

Külön pontot ad a zsűri annak, aki olyan funkcióval áll elő, ami nincs benne ebben a kiírásban, de a kamara valóban használni tudná. Nem díszítésre gondolunk, hanem olyasmire, amitől egy munkatárs napi munkája kézzelfoghatóan könnyebb lesz.

A jó ötletek ritkán az asztalnál születnek. A kamara vezetői ott lesznek a helyszínen — kérdezd meg őket. Mit kérdeznek tőlük a leggyakrabban? Miről tudják, hogy a munkatársak nem találják meg? Hol akad meg ma a munka? Tizenöt perc beszélgetés többet ér, mint két óra ötletelés.

Amit ilyenkor értékelünk

Megkerested-e a jelenlévő vezetőket, és be tudsz-e számolni arról, mit mondtak.

Az ötlet valódi, tőlük jövő igényre válaszol-e — vagy csak jól hangzik.

Beépítetted-e, akár egyszerű formában. A működő fél funkció többet ér a szépen leírt egésznél.

Elmondod-e a pitchben, honnan jött az ötlet és kivel egyeztetted.

Ez a rész nem kötelező. Aki viszont él vele, kettős előnnyel indul: a megoldása arra válaszol, amire tényleg szükség van, és ezt a zsűriben ülő vezető fel is fogja ismerni.

## 5. Amit le kell adni

Működő demó, amit élőben ki lehet próbálni — a zsűri saját kérdéseivel is.

Pitch: 5 perc előadás, utána kérdések.

## 6. A pitch

A pitch nem a technológiáról szól. Arról szól, hogy miért a te rendszeredet érdemes választani. A zsűriben ülő döntéshozót nem az érdekli, mi van a motorháztető alatt, hanem hogy mit nyer vele, mibe kerül, és mi történik két év múlva.

Amire térj ki

Milyen problémát oldasz meg, kinek, és mi ma a helyzet enélkül.

Élő bemutató: tegyél fel egy valódi kérdést, és mutasd meg, hogyan ellenőrizhető a válasz.

Tegyél fel egy olyan kérdést is, amire a dokumentumok nem adnak választ. Az a mondat, hogy „erre nincs fedezet”, többet ér a zsűri szemében, mint tíz sikeres kérdés.

A három szempont — bővíthetőség, skálázhatóság, ár — konkrét számokkal.

Ha van saját ötleted: honnan jött, kivel egyeztetted, és mit építettél be belőle.

Mi az, amit a te megoldásod tud, és a többi nem.

Amit kerülj el

Funkciólista felolvasása. A zsűri nem jegyzetel, hanem dönt.

A használt technológia vagy modell nevének emlegetése érv helyett. Attól, hogy valami korszerű, még nem lesz jó.

Előre begyakorolt, kockázatmentes kérdésen futó demó. Ez látszik, és rontja a bizalmat.

## 7. Értékelés

A zsűri az alábbi súlyozás szerint pontoz.

A súlyozásból jól látszik: a működő demó a pontok kevesebb mint harmadát hozza. A többi arról szól, hogy a megoldás elbírja-e a valóságot.

A pluszpont a száz százalékon felül jár, és önmagában is fordíthat egy szoros versenyen. Nem jár automatikusan attól, hogy valaki hozzátesz egy funkciót — akkor jár, ha az igény a kamarától jött, és be is épült.

## 8. Keretek

A technológia szabadon választható.

A szervezők biztosítanak mintaanyagot. Saját dokumentumot is hozhatsz, ha nyilvános.

Külső, fizetős szolgáltatás használható, de a költségét be kell számolni az árba.

Bizalmas vagy személyes adatot tartalmazó dokumentum nem használható.