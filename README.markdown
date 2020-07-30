# Frugal Message Trasfer Protocol (FMTP)

FMTP dient dem zuverlässigen Austausch von Nachrichten per [HTTP](http://www.ietf.org/rfc/rfc1945.txt)
nach den Prinzipien von [REST](http://www.ics.uci.edu/~fielding/pubs/dissertation/top.htm).
FMTP ist besser als [40 Jahre alte FTP Protocol][rfc114] zum automatisierten Austausch zwischen Unternehmen geeignet. Die Vorteile von FMTP sind:

[rfc114]: http://tools.ietf.org/html/rfc114


* **Sicher**: Vertraulichkeit und Authentizität können durch SSL/TLS sichergestellt werden. Als HTTP-basiertes Protokoll, kann FMTP gut von Firewalls und Proxies verarbeitet werden.
* **Zuverlässig**: Es ist sichergestellt, das nachrichten bei vorrübergehenden Ausfällen von Internet oder Server nicht verloren gehen. Auch werden Dubletten - wichtig in Kufmännischen Systemen - vermieden.
* **Nachvollziehbar**: Zu jeder Nachricht wird eine Empfangsbestätigung erzeugt. An ebiden Enden lässt sich somit feststellen, ob Daten wirklich übertragen wurden.
* **Resourcen schonend**: Als HTTP Basiertes Protokoll kann FMTP mit minimalen Serverresourcen und Bandbreite auskommen. HTTP erlaubt uns Kompression und Conditional-GET einzusetzen, so das selbst über teure und Langsame Satelittenverbindungen FMTP wirtschaftlich möglich ist.
* **Billig**: FMTP ist einfach. Deswegen ist es einfach zu betreiben udn überwachen udn einfach zu implementieren. In einer modernen Programmierumgebung, die HTTP udn ML zur Verfügung stellt sollten Push- und Pull-Clients in einem Manntag zu implementieren sein.
* **Mit Hausmitteln einsetzbar**: Im Zweifel können Sie FMTP nur mit einer Unix-Kommandozeile oder einem Webbrowser bewaffnet einsetzen.
* **Universell**: Ob zum Übertragen von Aufträgen oder zum Ansteuern von Druckern an entfernten Standorten - FMTP ist für eine breite Palette von Einsatzgebieten geeignet.

In diesem Projekt sind diverse Implementierungen von FMTP-Clients eines FMTP-Servers zusammengefasst.


# Das Protokoll

Es gibt zwei Transportmodi, der Sendemodus wird als *push* und der Empfangsmodus als *pull* bezeichnet.
Für den Tansfer einer Nachricht von einem Sender an einem Empfänger wird ein Endpunkt definiert, der mit einer
Queue in einer [MOM](http://de.wikipedia.org/wiki/Message_Oriented_Middleware) vergleichbar ist.
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

#### Kommandozeile

Die Referenzimplementation enthält einen [PUSH-Client](https://github.com/mdornseif/FMTP/tree/master/fmtp-client/push.py).

Der folgende Befehl lädt die Datei *file* mit dem GUID *guid* zum Endpunkt *http://example.com/q* hoch:

    python fmtp-client/push.py -f file -e http://example.com/q -g guid

#### Bibliothek

Das folgende Schnipsel legt eine Nachricht mit dem Inhalt *hello world!* auf dem Endpunkt *http://example.com/q* ab:

   import fmtp_client

   queue = fmtp_client.Queue('http://example.com/q/')
   queue.post_message('myguid', 'text/plain', 'hello world!')

Im obigen Beispiel ist die Queue zur Zeit des Programmierens bekannt (*q*). Ist dies nicht der Fall, kann
folgendes getan werden:

    import fmtp_client

    server = fmtp_client.Server('http://example.com/')

    queue = server[letter.receiver_name]
    queue.post_message(letter.guid, 'text/plain', letter.text)

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

#### Kommandozeile

Die Referenzimplementation enthält einen [PULL-Client](https://github.com/mdornseif/FMTP/tree/master/fmtp-client/pull.py).

Der folgende Befehl lädt alle Nachrichten vom Endpunkt *http://example.com/q* runter:

    python fmtp_client/pull.py -e http://example.com/q

#### Bibliothek

Das folgende Schnipsel ruft alle Nachrichten vom Endpunkt *http://example.com/q* ab, gibt sie aus, und entfernt sie aus der Queue.

    import fmtp_client

    queue = fmtp_client.Queue('http://example.com/q')

    for message in queue:
        print message.content
        message.acknowledge()

## FMTP-Server
### Referenzimplementation

Die Referenzimplementation enthält einen [FMTP-Server](https://github.com/mdornseif/FMTP/tree/master/fmtp-server).
Der Server ist als Anwendung für [Google App Engine](http://code.google.com/intl/de-DE/appengine/) konzipiert.

### Nutzung der Bibliothek

#### Abhängikeiten

Um eine Applikation FMTP-Fähig zu machen, müssen zunächst die Abhängiketen erfüllt werden. z.Z wird benötigt:

* [gaetk](https://github.com/hudora/appengine-toolkit)
* [huTools](https://github.com/hudora/huTools)

#### Veröffentlichung mit Webapp/Google App Engine

Das Rest-Interface wird von zwei Handlern realisiert, die die Nachrichten im google Datastore speichern.

Ein Minimaler FMTP-Server kann so realisiert werden:

    from google.appengine.ext.webapp import util
    from gaetk.webapp2 import WSGIApplication
    from fmtp-server import QueueHandler, MessageHandler


    app = webapp.WSGIApplication([
            # Der QueueHandler implementiert die Nachrichtenübersicht.
            (r'/fmtp/([^/]+)/', QueueHandler),
            # Der MessageHandler implementiert das Erstellen, Holen und Löschen von Nachrichten.
            (r'/fmtp/([^/]+)/(.+)/', MessageHandler),
    ], debug=True)

    if __name__ == '__main__':
        util.run_wsgi_app(app)

Zu beachten ist hier, dass die Pfade der Handler das gleiche Prefix haben müssen (im Beispiel /fmtp), die
relative Anordnung darf nicht geändert werden.
Weiterhin muss der Messagehandler mit einem trailing slash gemountet sein.

#### Anpassungen der Nachrichtenliste

Um die Nachrichtenliste anzupassen, können folgende Änderungen vorgenommen werden:

    class QueueHandler(fmtp_server.QueueHandler):
        # Clients werden gebeten, mindestens alle 10 Sekunden zu aktualisieren
        max_retry_interval = 10000

        # Clients werden gebeten, höchstens 2mal die Sekunde zu aktualisieren
        min_retry_interval = 500

        # Clients maximal 10 Nachrichten gezeigt
        max_messages = 10

Um auf Ereignisse zu reagieren, oder um den Zugriff zu kontrollieren, kann die Methode on_access überschrieben
werden:

    class QueueHandler(fmtp_server.QueueHandler):
        def on_access(self, message_queue_name):
            # Zugriffe werden gelogged
            logging.info('es wurde auf die Queue %r zugegriffen', message_queue_name)

            # Betrachten einer Queue erfordert Authentifikation.
            self.login_required()

#### Anpassungen der Nachrichten

Um das erstellen, löschen und anzeigen von Nachrichten anzupassen, können folgende Änderungen vorgenommern
werden:

    class MessageHandler(fmtp_server.MessageHandler):

        # Nur numerische guids erlauben.
        guid_pattern = '^[0-9]+$'

        def check_message_queue_name(self, message_queue_name):
            # Wir erlabuen nur queues, die mit 'queue_' anfangen.
            return message_queue_name.startswith('queue_')

        def on_access(self, method, message_queue_name, guid, message):
            # Zugriffe werden gelogged
            logging.info('es wurde auf die Nachricht %r zugegriffen', message)

            # Betrachten einer Nachricht erfordert Authentifikation.
            self.login_required()

        def on_created(self, message):
            # das Erstellen von Nachrichten wurd gelogged
            logging.info('Eine neue Nachricht wurde erstellt: %r', message)

        def on_deleted(self, message):
            # das Löschen von Nachrichten wird gelogged
            logging.info('Die Nachricht %r wurde gelöscht.', message)

#### Anpassungen der Administrativen Sicht

Die Administrative Sicht auf queues ist optional (sie ist nicht für einen normalen Betrieb eines FMTP-Servers
erforderlich). Sie bietet eine Übersicht über den Inhalt einer Queue, und eine Schnittstelle zur Garbage 
Collection.

Um die Sicht zu nutzen, muss sie zunächst veröffentlicht werden:

    app = webapp.WSGIApplication([
            (r'/fmtp/admin/([^/]+)/', AdminHandler),
            # ...
    ])

Nun kann per GET auf einen Queue-Name informationen zu dieser Queue abgefragt werden:

    curl -X GET /fmtp/admin/somequeue/

    {
        'success': True,
        'messages': [
                {
                    'queue': 'alpha',
                    'guid': '123123',
                    'is_deleted': False,
                    'created_at': '2011-03-23 00:00:00',
                    'deleted_at': '2011-03-23 00:00:00',
                    'content_type': 'text/plain',
                },
                # ...
        ]
    }

Per DELETE auf einen Queue-Namen kann die Garbage Collection dieser Queue gestartet werden:

    curl -X DELETE /fmtp/admin/somequeue/

    {
        'success': True,
        'deleted': 23,
    }


Um die Sicht anzupassen, können folgende Änderungen vorgenommen werden:

    class AdminHandler(fmtp_server.AdminHandler):

        # wieviele Messages angezeigt werden
        max_messages = 50

        # frist, nach der gelöschte Nachrichten frühestens garbagecollected werden können, in Tagen
        retention_period_days = 7

        def on_access(self):
            # analog zu den anderen Handlern
            self.login_required()
