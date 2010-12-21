# Frugal Message Trasfer Protocol (FMTP)

FMTP dient dem zuverlässigen Austausch von Nachrichten per [HTTP](http://www.ietf.org/rfc/rfc1945.txt)
nach den Prinzipien von [REST](http://www.ics.uci.edu/~fielding/pubs/dissertation/top.htm).

Es gibt zwei Transportmodi, der Sendemodus wird als *push* und der Empfangsmodus als *pull* bezeichnet.
Für den Tansfer einer Nachricht von einem Sender an einem Empfänger wird ein Endpunkt definiert, der mit einer Queue in einer [MOM](http://de.wikipedia.org/wiki/Message_Oriented_Middleware) vergleichbar ist.
In den folgenden Beispielen wird der Endpunkt *https://example.com/q* verwendet.

Nachrichten sollten einen eindeutigen Bezeichner haben, der pro Endpunkt nur einmal vorkommen darf.
Wenn das sendende System keine GUIDs erzeugen kann, können auch andere eindeutige Bezeichner verwendet werden, wie z.B. eine Rechungsnummer.
Die verwendeten GUIDs sollten zu dem regulären Ausdruck */[a-zA-Z0-9\_-]+/* passen.

## Daten senden: PUSH
Gesetzt eine Nachricht hat den GUID *guid*, den Inhalt *"content"* und ist vom Typ *application/json*,
dann kann die Nachricht folgendermassen in den Endpunkt https://example.com/q eingespeist werden:

    >>> POST https://example.com/q/guid
    >>> Host: example.com
    >>> Content-Type: application/json
    >>>
    >>> "content"

In der Regel antwortet der Server mit folgenden Nachrichten:

    <<< 201 Created
Die Nachricht wurde auf dem Server unter der GUID *guid* gespeichert.

    <<< 409 Conflict
Es existiert bereits eine Nachricht mit dem gleichen GUID. Die neue Nachricht wird nicht gespeichert.

    <<< 410 Gone
Es existierte bereits eine Nachricht mit dem gleichen GUID, die aber bereits verarbeitet bzw. gelöscht wurde. Die Nachricht wird ebenfalls nicht gespeichert.

### Referenzimplementation
Die Referenzimplementation enthält einen [PUSH-Client](https://github.com/mdornseif/FMTP/tree/master/push_client).

Der folgende Befehl lädt die Datei *file* mit dem GUID *guid* zum Endpunkt *http://example.com/q* hoch:

    python push_client/send_fmtp.py -f file -e http://example.com/q -g guid


## Daten empfangen: PULL
Das Protokoll unterstützt kein Locking.
Das bedeutet, dass entweder nur ein Client lesend auf einen Endpunkt zugreifen darf, oder dass das Locking im Client implementiert werden muss.
Der Empfang gliedert sich in in drei Schritte, die in einer Schleife ausgeführt werden.

1. Abruf einer Liste der bereitstehenden Nachrichten
2. Abruf einer Nachricht
3. Löschen der abgerufenen Nachricht

Die Liste der bereitstehenden Nachrichten kann in verschiedenen Formaten empfangen werden.
Für FMTP müssen die Formate Text, [JSON](http://www.json.org/) und [XML](http://www.w3.org/XML/) unterstützt werden.
Die folgenden Beispiele nutzen das Text-Format.

Durch GET Abruf des Endpunktes bekommt der Empfänger eine Liste mit URLs von Nachrichten.
Die URLs sind durch ‘\n’ (ASCII 10) voneinander getrennt.

    >>> GET https://example.com/q
    >>> Host: example.com
    
    <<< 200 OK
    <<< Content-Type: text/plain
    <<<
    <<< https://example.com/q/guid
    <<< https://example.com/q/otherguid

Aufgrund der Informationen in dieser Liste kann nun eine Nachricht abgerufen werden.

    >>> GET https://example.com/q/guid
    >>> Host: example.com

    <<< 200 OK
    <<< Content-Type: application/json
    <<< 
    <<< 'content'

Der Content-Type ist der gleiche, der von dem Sender mitgegeben wurde.
Wenn der Empfänger die Nachricht erfolgreich übernommen hat - z.B. indem er Sie in eine Datenbank geschrieben hat, muss er die Nachricht auf dem Server löschen.
Das muss mit dem HTTP Befehl DELETE erfolgen.

    >>> DELETE https://example.com/q/guid
    >>> Host: example.com

    <<< 204 No Content

Nun kann erneut durch Aufruf von https://example.com/q geprüft werden, ob neue Nachrichten vorliegen.

### Listenformate
Die Liste der bereitstehenden Nachrichten kann in verschiedenen Formaten abgerufen werden.
Welches Format der Server zurückliefert kann anhand des Accept Headers, der vom Client geschickt wird, gesteuert werden.
Zum einen steht das JSON Format zur Verfügung:

    >>> GET https://example.com/q
    >>> Host: example.com
    >>> Accept: application/json

    <<< 200 OK
    <<< Content-Type: application/json
    <<<    
    <<< {
    <<<  'min_retry_interval': 500,
    <<<  'max_retry_interval': 60000,
    <<<  'messages': [
    <<<   {'url': 'https://example.com/q/guid', 'created_at': '2010-10-13T20:30:40.1234'},
    <<<   {'url': 'https://example.com/q/otherguid', 'created_at': '2010-10-13T20:30:50.6789'},
    <<<  ]
    <<< }

Alternativ kann die Nachrichtenliste als XML abgerufen werden:

    >>> GET https://example.com/q
    >>> Host: example.com
    >>> Accept: application/xml

    <<< 200 OK
    <<< Content-Type: application/xml
    <<<
    <<< <data>
    <<<  <min_retry_interval>500</min_retry_interval>
    <<<  <max_retry_interval>60000</max_retry_interval>
    <<<  <messages>
    <<<   <message>
    <<<    <url>https://example.com/q/guid</url>
    <<<    <created_at>2010-10-13T20:30:40.1234</created_at>
    <<<   </message>
    <<<   <message>
    <<<    <url>https://example.com/q/otherguid</url>
    <<<    <created_at>2010-10-13T20:30:50.6789</created_at>
    <<<   </message>
    <<<  </messages>
    <<< </data>

### Retry-Interval
Ein Empfänger muss immer wieder die Liste der bereitstehenden Nachrichten abrufen.
Die Frage ist, in welchen Intervallen nach neuen Nachrichten gefragt werden soll.
Wird zu häufig gefragt, wird die automatisierte Denial-of-Service Detektion den Client zeitweise sperren und alle Anfragen mit 503 Service Unavailable beantworten.

Deswegen empfiehlt es sich im Client *Exponential Backoff* zu implementieren.
D.h. wenn keine neue Nachrichten gefunden wurden, sollte die Wartezeitbis zur nächsten Anfrage verdoppelt werden.
Der Server liefert mit *min\_retry\_interval* und *max\_retry\_interval* Vorschläge,
wie viele Millisekunden der Client minimal und maximal bis zur nächsten Anfrage warten soll.


### Referenzimplementation
Die Referenzimplementation enthält einen [PULL-Client](https://github.com/mdornseif/FMTP/tree/master/pull_client).

Der folgende Befehl lädt alle Nachrichten vom Endpunkt *http://example.com/q* runter:

    python pull_client/recv_fmtp.py -e http://example.com/q

## FMTP-Server
### Referenzimplementation

Die Referenzimplementation enthält einen [FMTP-Server](https://github.com/mdornseif/FMTP/tree/master/fmtp-server).
Der Server ist als Anwendung für [Google App Engine](http://code.google.com/intl/de-DE/appengine/) konzipiert.
