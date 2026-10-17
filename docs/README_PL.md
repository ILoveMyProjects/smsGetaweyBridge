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

Wersja **v0.1.1 jest testowa**: nie została sprawdzona na działającej instalacji Home Assistant i fizycznym telefonie. Nie gwarantuje dostarczenia zdarzeń dokładnie jeden raz; treść przychodzących SMS-ów może być tylko podglądem. Synchronizacja obsługuje paginację z limitem 10 000 wyników na kategorię. Samo zlecenie wysłania nie oznacza doręczenia.

## Bezpieczeństwo

Nie otwieraj portu bramki na publiczny internet. HTTP Basic Auth bez HTTPS nie szyfruje hasła ani treści; wybierz zaufany LAN/VLAN lub poprawnie skonfigurowane HTTPS. Dane SMS mogą zawierać poufne informacje. Więcej: [Bezpieczeństwo PL](BEZPIECZENSTWO_PL.md).
