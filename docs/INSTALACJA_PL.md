# Instalacja i konfiguracja — smsGetaweyBridge

## 1. Telefon

Użyj **SMS Gateway for Android → Local Server**. Zapisz `host`, `port`, `username` oraz `password`.

Ustawienia typowej instalacji Galaxy S9:

| Ustawienie | Przykład, nie stała wartość |
|---|---|
| IP telefonu | `192.168.1.186` — DHCP może je zmienić |
| Port | `8080` |
| Login | Z panelu Local Server |
| Hasło | Z panelu Local Server |
| Cloud Server | Wyłączony |

Zalecana rezerwacja DHCP dla telefonu. **Nie wpisujemy IP na sztywno w skryptach instalacyjnych**: konfigurację można zmienić przez **Skonfiguruj ponownie** na karcie integracji (v1.0.1).

## 2. Home Assistant

Zobacz instrukcję HACS w [README](../README.md#install-using-hacs-custom-repository).

W formularzu podaj dane ręcznie. Program nie próbuje używać SSH, Termuxa ani roota i nie korzysta z chmury. Testuje HTTP API — bez wysyłania płatnego SMS.

## 3. Pierwsza weryfikacja

Po skonfigurowaniu w **Ustawienia → Urządzenia i usługi** sprawdź encje:

- `Gateway online` — po udanym odczycie „on”; w razie błędu „off".
- `Recent inbox SMS` — liczba rekordów zwróconych w ostatniej pełnej synchronizacji (maksymalnie 10 000).
- `Recent outgoing SMS` — liczba rekordów z ostatniej pełnej synchronizacji (maksymalnie 10 000).
- `Latest outgoing status` — stan ostatniej wysłanej wiadomości widocznej w API.

Nazwy entity_id mogą być zmienione przez Home Assistant; nie polegaj na przykładach stałych identyfikatorów.

## 4. Wysyłanie SMS

Przetestuj wyłącznie na **własnym numerze** i sprawdź opłaty operatora.

```yaml
action: smsgetaweybridge.send_sms
data:
  phone_number: "+48123123123"
  message: "Test z HA"
```

## 5. Automatyzacje

Zdarzenie nowego SMS (w automatyzacjach można odczytać jego dane):

```yaml
alias: "SMS Gateway - informacja o odebraniu"
triggers:
  - trigger: event
    event_type: smsgetaweybridge_sms_received
actions:
  - action: persistent_notification.create
    data:
      title: "Nowy SMS"
      message: "SMS od {{ trigger.event.data.sender }}"
mode: queued
```

Treści wiadomości nie podajemy w powyższym powiadomieniu celowo, dla prywatności. Jeżeli świadomie chcesz jej użyć: `{{ trigger.event.data.message }}`.

Powiadomienie o zmianie statusu:

```yaml
alias: "SMS Gateway - status"
triggers:
  - trigger: event
    event_type: smsgetaweybridge_sms_status
actions:
  - action: persistent_notification.create
    data:
      title: "Status SMS"
      message: "ID {{ trigger.event.data.message_id }}: {{ trigger.event.data.state }}"
mode: queued
```

## 6. Współpraca z Ubuntu SMS Manager

Ubuntu Server i HA są **równoległymi klientami telefonu**. W aplikacji SMS Gateway obie usługi używają istniejącego Local Server. GET `/inbox` i GET `/messages` nie usuwają wiadomości. Wysłane przez Ubuntu wiadomości mogą także pojawić się w statusach widocznych przez Home Assistant. Integracja nie zna, który system zlecił dany SMS.

## 7. Wersja 0.1.1 — synchronizacja i aktualizacja

Po uaktualnieniu z 0.1.0 integracja jednorazowo wyznacza nowe kursory z istniejącej historii. Nie wysyła starszych zdarzeń do automatyzacji (może pominąć wiadomości odebrane w trakcie samej migracji). Później odczytuje stronicowaną skrzynkę `/inbox` od zapamiętanego czasu i wszystkie strony `/messages`. Po przerwie nadrabia nowe SMS-y i zmiany statusów, o ile pozostały na telefonie i mają poprawne znaczniki czasu.

Zdarzenia mają semantykę **at-least-once**: w razie przerwania HA między emisją zdarzenia a zapisem stanu to samo zdarzenie może pojawić się ponownie. W automatyzacjach wymagających dokładnie jednego wykonania stosuj deduplikację po `message_id` lub `(message_id, state, changed_at)`. Bramka musi nadal przechowywać starsze wiadomości i ich historię statusów; usuniętych danych nie da się odzyskać.

Jeśli na telefonie jest ponad 10 000 rekordów danej kategorii, integracja zgłosi błąd zamiast pomijać część. Pełne odczyty co 30 sekund mogą obciążać starsze telefony.

## 8. Diagnostyka

- `Cannot connect`: Local Server wyłączony, zły IP/port, firewall lub niedostępne `/inbox` albo `/messages`.
- `Invalid auth`: sprawdź login i hasło Local Server, nie Cloud Server.
- `Invalid response`: API zwróciło inny format niż udokumentowane listy JSON.
- `Gateway online` = off: nie oznacza uszkodzenia telefonu, tylko brak udanego odczytu API.
- Nowe SMS nie pojawiają się: sprawdź uprawnienia odbioru/odczytu SMS w Androidzie i dostępność `/inbox`, zasięg SIM, baterię.
- Przy pierwszym uruchomieniu historyczne SMS-y są oznaczane jako już znane. To zachowanie zamierzone.

**Nie publikuj logów z hasłami, numerami ani treściami wiadomości.**


## 8. Nowy panel SMS Bridge v1.0.1

Po aktualizacji integracji i restarcie HA w bocznym menu dostępny jest panel **SMS Bridge**. W **Templates** dodaj grupę odbiorców (numery w formacie `+48123123123`), następnie szablon tekstu, np. `ALERT: $device offline`, a potem wybierz w automatyzacji osobną akcję **Send SMS: nazwa_szablonu** z prostymi polami zmiennych. **Logs** wyświetla lokalny dziennik bez treści SMS. **Overview** pozwala opcjonalnie skonfigurować callback HTTPS: potrzebny jest lokalny adres HTTPS i certyfikat zaufany przez telefon. Nie używaj publicznego internetu ani chmury.


## 9. Nowości 1.0.0: formularze automatyzacji i webhook automatyczny

W edytorze automatyzacji dostępne są `send_sms` i `send_template` z listą zapisanych szablonów. Wybór pokazuje nazwę grupy oraz listę wymaganych `$zmiennych`. Dodatkowo każdy szablon ma własną akcję z osobnymi polami tekstowymi tych zmiennych (najwygodniejsze rozwiązanie). Panel **SMS Bridge → Templates & Groups** pozwala edytować istniejące grupy i szablony oraz wyjaśnia składnię zmiennych.

Po podaniu loginu i hasła Local Server bramka otrzyma automatyczną próbę rejestracji webhooków. Warunkiem jest skonfigurowany **wewnętrzny URL HTTPS** HA i certyfikat zaufany przez Android. Żadnych adresów webhooków się nie wkleja. Przy braku takiej konfiguracji status pokaże `unavailable_local_https`; polling nadal działa. **Nie** zmieniaj ustawień HTTPS bramki ani zapory w celu obchodzenia zabezpieczeń.

## Wygodne automatyzacje v1.0.1 (bez JSON-a)

W panelu **SMS Bridge → Templates & Groups** utwórz grupę z numerami i szablon, np. `server_alert` z treścią `Server $host is $status`. W edytorze automatyzacji wybierz osobną akcję **Send SMS: server_alert**. Zobaczysz podgląd zapisanej treści, grupę oraz osobne pola `host` i `status`. Uzupełnij zwykłe wartości, bez JSON-a, bez ponownego wpisywania numerów. Inne akcje to opcje zaawansowane. **Gateway entry (legacy) usunięto**; stary zapis `send_template` z `entry_id` lub samym kluczem szablonu wymaga aktualizacji.
