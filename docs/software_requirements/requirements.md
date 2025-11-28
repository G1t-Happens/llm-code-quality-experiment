## 1. Geschäftsziele
Das vorliegende System verfolgt als zentrales geschäftliches Ziel die Bereitstellung eines modernen, sicheren und wartbaren User-Management-Systems als Kernbaustein für digitale Anwendungen und Plattformen. Im Einzelnen werden folgende übergeordnete Geschäftsziele angestrebt:
- **Zentrale Verwaltung von Benutzern und deren persönlichen Daten**: Bereitstellung einer einzigen, verlässlichen Quelle für Identitäten, Kontaktdaten und Adressen, die von beliebigen Frontends und Microservices genutzt werden kan-
- **Sichere, standardkonforme Authentifizierung und Autorisierung**: Einfaches und sicheres Anmelden von Endanwendern und Administratoren mittels JWT-basierter stateless Authentifizierung sowie feingranulare Rechtevergabe (Rollen- und Ownership-basierte Zugriffskontrolle)
- **Wiederverwendbarkeit**: Die Architektur und die generischen Bausteine sollen 1:1 in andere Projekte übernommen werden können

## 2. Randbedingungen (Constraints)
- **(C1) Vertraute Technologien**: Das System soll mit Java 21 und Spring Boot 3.5.x entwickelt werden, da diese im Unternehmen bestens etabliert sind und höchste Vertrautheit sowie langfristige Wartbarkeit gewährleisten.
- **(C2) Stateless JWT-Authentifizierung**: Keine Session-basierte Authentifizierung; JWT mit HS256 und Secret ≥ 256 Bit Länge ist vorgeschrieben.
- **(C3) Generalisierbarkeit**: Die Struktur des Projektes soll geeignet sein, um sie als Vorlage für andere externe Services benutzen zu können.


## 3. Wesentliche funktionale Anforderungen
### Benutzerverwaltung (User Management)
- **USR-001**: Als Administrator möchte ich alle registrierten Benutzer paginiert auflisten können.
- **USR-002**: Als authentifizierter Benutzer oder Administrator möchte ich meine eigenen Benutzerdaten einsehen können.
- **USR-003**: Als Administrator möchte ich einen neuen Benutzer anlegen können (inkl. Passwort-Hashing und Admin-Flag).
- **USR-004**: Als authentifizierter Benutzer oder Administrator möchte ich meine eigenen Daten (Username, E-Mail, Passwort, Admin-Flag) aktualisieren können – wobei nur ein Administrator das Admin-Flag anderer Benutzer setzen darf.
- **USR-005**: Als Administrator möchte ich einen bestehenden Benutzer löschen können.
- **USR-006**: Als beliebiger Client möchte ich mich mit Username + Passwort anmelden und ein gültiges JWT-Token erhalten.
- **USR-007**: Als Administrator möchte ich einen Benutzer anhand seines exakten Usernames suchen können.

### Adressverwaltung (Address Management)
- **ADR-001**: Als authentifizierter Benutzer oder Administrator möchte ich alle eigenen Adressen paginiert auflisten können.
- **ADR-002**: Als authentifizierter Benutzer oder Administrator möchte ich eine einzelne eigene Adresse anhand ihrer ID abrufen können.
- **ADR-003**: Als authentifizierter Benutzer oder Administrator möchte ich eine neue Adresse zu meinem Benutzerkonto hinzufügen können.
- **ADR-004**: Als authentifizierter Benutzer oder Administrator möchte ich eine bestehende eigene Adresse teilweise oder vollständig aktualisieren können (Patch-Semantik).
- **ADR-005**: Als authentifizierter Benutzer oder Administrator möchte ich eine eigene Adresse löschen können.

### Authentifizierung & Autorisierung
- **SEC-001**: Das System muss eine stateless JWT-basierte Authentifizierung (HS256) bereitstellen.
- **SEC-002**: Nur authentifizierte Requests dürfen auf geschützte Endpunkte zugreifen (außer Login und User-Registrierung).
- **SEC-003**: Administratoren haben uneingeschränkten Zugriff auf alle User- und Address-Ressourcen.
- **SEC-004**: Normale Benutzer dürfen ausschließlich auf ihre eigenen Ressourcen (User-Daten und Adressen) zugreifen (Ownership-Prüfung).
- **SEC-005**: Das Setzen des Admin-Flags ist nur für Administratoren erlaubt.
- **SEC-006**: Bei fehlerhaften Logins darf keine Information über die Existenz eines Benutzers preisgegeben werden (Timing-Attack-Schutz).

### Sonstige funktionale Anforderungen
- **API-001**: Alle CRUD-Operationen müssen über eine versionierte, dokumentierte REST-API mit JSON-Payload bereitgestellt werden.
- **API-002**: Es muss eine Validierung aller Eingaben muss.
- **API-003**: Das System muss einheitliche, maschinenlesbare Fehlermeldungen (HTTP-Status + JSON-Body) zurückliefern.


## 4. Wesentliche qualitative Anforderungen
### Sicherheit (Security)
Das System verwaltet personenbezogene Daten und Authentifizierungsdaten → Sicherheit hat höchste Priorität.

| Kategorisierung  |                                                                             |                     |
|------------------|-----------------------------------------------------------------------------|---------------------|
| Szenario-Name    | Schutz vor unberechtigtem Zugriff auf fremde Daten(User & Adresse)          |                     |
| Scenario ID      | Security.01                                                                 |                     |
| Priorität        | Sehr hoch                                                                   |                     |
| **Beschreibung** |                                                                             | **Quantifizierung** |
| Umgebung         | Benutzer A (ID 10) und Benutzer B (ID 20) existieren, beide authentifiziert |                     |
| Stimulus         | Benutzer A ruft GET /users/20/addresses/5 auf                               |                     |
| Antwort          | System antwortet mit 404 Not Found (kein Leak über Existenz)                | ≤ 200 ms            |


### Performanz

| Kategorisierung  |                                                      |                     |
|------------------|------------------------------------------------------|---------------------|
| Szenario-Name    | Schnelle Listenabfrage unter Last                    |                     |
| Scenario ID      | Perf.01                                              |                     |
| Priorität        | Hoch                                                 |                     |
| **Beschreibung** |                                                      | **Quantifizierung** |
| Umgebung         | 100.000 User, 500.000 Adressen                       |                     |
| Stimulus         | 100 gleichzeitige Requests auf /users?page=0&size=20 |                     |
| Antwort          | 95 % der Requests antworten < 500 ms (P95)           |                     |


### Wartbarkeit & Erweiterbarkeit

| Kategorisierung  |                                                        |                     |
|------------------|--------------------------------------------------------|---------------------|
| Szenario-Name    | Hinzufügen einer neuen Entität (z. B. Telefonnummer)   |                     |
| Scenario ID      | Maintainability.01                                     |                     |
| Priorität        | Hoch                                                   |                     |
| **Beschreibung** |                                                        | **Quantifizierung** |
| Umgebung         | Aktueller Codebase                                     |                     |
| Stimulus         | Neuer Entität + CRUD-Endpoint nötig                    |                     |
| Antwort          | Implementierung und Test der kompletten Funktionalität | ≤ 3 Personentage    |


### Portabilität / Umgebungsunabhängigkeit (Deployability & Environment Independence)
Das System muss **zero-touch** in beliebigen Zielumgebungen ohne Code-Änderungen betrieben werden können.

| Kategorisierung  |                                                                                                                                                                             |                                                           |
|------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------|
| Szenario-Name    | Einmal bauen – überall laufen (Zero-Touch-Deployment)                                                                                                                       |                                                           |
| Scenario ID      | Portability.01                                                                                                                                                              |                                                           |
| Priorität        | Sehr hoch                                                                                                                                                                   |                                                           |
| **Beschreibung** |                                                                                                                                                                             | **Quantifizierung**                                       |
| Umgebung         | Das System läuft aktuell produktiv in Kubernetes-Cluster A (AWS EKS) mit PostgreSQL in RDS                                                                                  |                                                           |
| Stimulus         | Aufgrund einer außerordentliche Kündigung des Hostingbetreibers muss das System innerhalb von maximal 6 Stunden auf ein komplett anderes Ausführungssystem umgezogen werden |                                                           |
| Antwort          | Das System startet in allen Umgebungen ohne Code-Änderungen. Nur die externe Konfiguration (Environment-Variablen, Secrets, Datenbank-URL) wird angepasst.                  | Startzeit ≤ 15 Sekunden. Keine manuellen Eingriffe nötig. |