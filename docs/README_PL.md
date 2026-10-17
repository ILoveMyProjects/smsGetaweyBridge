# smsGetaweyBridge — dokumentacja po polsku

**[English README (domyślna dokumentacja)](../README.md)** · [Instrukcja instalacji PL](INSTALACJA_PL.md) · [Bezpieczeństwo PL](BEZPIECZENSTWO_PL.md) · [Wydania GitHub (EN)](RELEASING.md)

`smsGetaweyBridge` to niestandardowa integracja Home Assistant instalowana przez **HACS**. Łączy się **bezpośrednio z SMS Gateway for Android (Local Server)** na telefonie. Nie wymaga SSH ani Ubuntu Server. Home Assistant i Ubuntu mogą jednocześnie korzystać z tej samej bramki jako **niezależni klienci**.

## Instalacja

1. W HACS dodaj repozytorium `https://github.com/ILoveMyProjects/smsGetaweyBridge` jako **Custom repository → Integration**.
2. Zainstaluj integrację `smsGetaweyBridge` i uruchom ponownie Home Assistant.
3. Wybierz **Ustawienia → Urządzenia i usługi → Dodaj integrację → smsGetaweyBridge**.
4. Podaj **adres/IP**, **port**, **username** i **password** pochodzące z **Local Server** w aplikacji SMS Gateway. Opcjonalnie wybierz HTTPS, jeżeli masz poprawny certyfikat.
5. Kreator sprawdzi dostęp do `/messages` i `/inbox` bez wysyłania testowego SMS-a.

Dalsza konfiguracja i automatyzacje znajdują się w [instrukcji instalacji po polsku](INSTALACJA_PL.md).

## Wysyłanie

```yaml
action: smsgetaweybridge.send_sms
data:
  phone_number: "+48123123123"
  message: "Test z Home Assistant"
```

Numer jest przykładowy. Wysyłka SMS może kosztować zgodnie z taryfą operatora.

## Odbieranie i statusy

Integracja odczytuje nowe SMS-y i statusy z API co **30 sekund** i emituje zdarzenia `smsgetaweybridge_sms_received`, `smsgetaweybridge_sms_status` oraz `smsgetaweybridge_sms_queued`.

Wersja **v1.0.1 nie została jeszcze przetestowana na prawdziwym HA i telefonie**: nie została sprawdzona na działającej instalacji Home Assistant i fizycznym telefonie. Nie gwarantuje dostarczenia zdarzeń dokładnie jeden raz; treść przychodzących SMS-ów może być tylko podglądem. Synchronizacja obsługuje paginację z limitem 10 000 wyników na kategorię. Samo zlecenie wysłania nie oznacza doręczenia.

## Bezpieczeństwo

Nie otwieraj portu bramki na publiczny internet. HTTP Basic Auth bez HTTPS nie szyfruje hasła ani treści; wybierz zaufany LAN/VLAN lub poprawnie skonfigurowane HTTPS. Dane SMS mogą zawierać poufne informacje. Więcej: [Bezpieczeństwo PL](BEZPIECZENSTWO_PL.md).

## Panel SMS Bridge (v1.0.1)

Home Assistant ma trzy zakładki **Overview**, **Templates & Groups** i **Activity & Logs**. Na każdej jest krótka instrukcja. W zakładce **Templates & Groups** można tworzyć, edytować i usuwać grupy odbiorców i szablony. Wybranie szablonu pokazuje osobne pola `$zmiennych`, które należy uzupełnić. `Activity & Logs` wyjaśnia znaczenie statusów SMS i pokazuje zdarzenia bez przechowywania pełnych numerów i treści.

## Szablony w automatyzacjach — bez JSON-a

Najpierw w **SMS Bridge → Templates & Groups** utwórz grupę `ops` z numerami odbiorców oraz szablon `server_alert` o treści `Server $host is $status`.

W **Ustawienia → Automatyzacje → Dodaj akcję** wybierz **smsGetaweyBridge: Send SMS: server_alert**. To **osobna akcja wygenerowana dla tego szablonu**, a nie ogólna `Send saved SMS template (advanced)`.

Opis akcji pokazuje **treść SMS-a**, **nazwę grupy** oraz wymagane zmienne. W zwykłych polach tekstowych wpisz `host = nas01` oraz `status = offline`. Wiadomość `Server nas01 is offline` trafi do numerów w grupie `ops` po uruchomieniu automatyzacji. **Nie wpisujesz JSON-a, treści SMS-a ani numerów ponownie.** Jeśli szablon nie ma zmiennych, nie trzeba uzupełniać żadnych dodatkowych pól.

Jeżeli dodasz lub zmienisz szablon, zamknij i otwórz ponownie edytor automatyzacji, by odświeżyć dostępne akcje.

Dostępna jest również ogólna akcja **Send saved SMS template (advanced)** z wyborem z listy i mapą zmiennych dla zaawansowanych automatyzacji. **Pole `Gateway entry (legacy)` zostało usunięte.** Stare automatyzacje wybierające szablon po samej nazwie albo przekazujące `entry_id` do `send_template` muszą być zaktualizowane. Przy wysyłce bezpośredniej na numer wybór bramki może być nadal konieczny, gdy skonfigurowanych jest kilka telefonów.

Wysłanie SMS-a może kosztować. Brak potwierdzenia odpowiedzi z bramki nie oznacza, że SMS nie został wysłany — nie powtarzaj automatycznie żądania.

## Webhook bez ręcznego wklejania URL

Po połączeniu z lokalnym serwerem bramki integracja **sama próbuje zarejestrować** cztery typy webhooków na telefonie, korzystając z **wewnętrznego adresu HTTPS Home Assistant**. Nie trzeba kopiować adresu ani tworzyć webhooka w Androidzie. Przy braku wewnętrznego HTTPS (lub niezaufanym certyfikacie) webhook nie może działać: panel wskaże `unavailable_local_https` lub `registration_failed`, a odbiór SMS-ów i statusów będzie kontynuowany przez polling co 30 sekund. Integracja nie konfiguruje routera, nie wyłącza weryfikacji TLS i nie korzysta z zewnętrznej chmury.

Oba systemy nadal łączą się niezależnie z telefonem: wysyłki HA są identyfikowane po ID jako `homeassistant`, pozostałe są `external/unknown` — bez przypisywania ich Ubuntu na podstawie domysłów.
