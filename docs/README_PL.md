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

Wersja **v1.0.0 nie została jeszcze przetestowana na prawdziwym HA i telefonie**: nie została sprawdzona na działającej instalacji Home Assistant i fizycznym telefonie. Nie gwarantuje dostarczenia zdarzeń dokładnie jeden raz; treść przychodzących SMS-ów może być tylko podglądem. Synchronizacja obsługuje paginację z limitem 10 000 wyników na kategorię. Samo zlecenie wysłania nie oznacza doręczenia.

## Bezpieczeństwo

Nie otwieraj portu bramki na publiczny internet. HTTP Basic Auth bez HTTPS nie szyfruje hasła ani treści; wybierz zaufany LAN/VLAN lub poprawnie skonfigurowane HTTPS. Dane SMS mogą zawierać poufne informacje. Więcej: [Bezpieczeństwo PL](BEZPIECZENSTWO_PL.md).

## Panel SMS Bridge (v1.0.0)

Home Assistant ma trzy zakładki **Overview**, **Templates & Groups** i **Activity & Logs**. Na każdej jest krótka instrukcja. W zakładce **Templates & Groups** można tworzyć, edytować i usuwać grupy odbiorców i szablony. Wybranie szablonu pokazuje osobne pola `$zmiennych`, które należy uzupełnić. `Activity & Logs` wyjaśnia znaczenie statusów SMS i pokazuje zdarzenia bez przechowywania pełnych numerów i treści.

## Wybór szablonu w automatyzacji (bez zgadywania)

W edytorze automatyzacji wybierz akcję `smsgetaweybridge.send_sms` albo `smsgetaweybridge.send_template`. Pole **Saved template** zawiera listę utworzonych szablonów wraz z nazwą grupy oraz wymaganymi zmiennymi. Zmienne wpisuje się w polu **Variables** jako mapę `nazwa: wartość`.

Każdy zapisany szablon ma również **osobną akcję** w Home Assistant, nazwaną **Send SMS: nazwa_szablonu**, z osobnymi polami dla każdej wymaganej zmiennej. Ta akcja pozwala uzupełniać wartości bez ręcznego JSON-a. Po dodaniu lub zmianie szablonu otwórz edytor automatyzacji ponownie, aby lista i pola się odświeżyły.

Wysłanie SMS-a może kosztować. Brak potwierdzenia odpowiedzi z bramki nie oznacza, że SMS nie został wysłany — nie powtarzaj automatycznie żądania.

## Webhook bez ręcznego wklejania URL

Po połączeniu z lokalnym serwerem bramki integracja **sama próbuje zarejestrować** cztery typy webhooków na telefonie, korzystając z **wewnętrznego adresu HTTPS Home Assistant**. Nie trzeba kopiować adresu ani tworzyć webhooka w Androidzie. Przy braku wewnętrznego HTTPS (lub niezaufanym certyfikacie) webhook nie może działać: panel wskaże `unavailable_local_https` lub `registration_failed`, a odbiór SMS-ów i statusów będzie kontynuowany przez polling co 30 sekund. Integracja nie konfiguruje routera, nie wyłącza weryfikacji TLS i nie korzysta z zewnętrznej chmury.

Oba systemy nadal łączą się niezależnie z telefonem: wysyłki HA są identyfikowane po ID jako `homeassistant`, pozostałe są `external/unknown` — bez przypisywania ich Ubuntu na podstawie domysłów.
