# smsGetaweyBridge

**Niezależna integracja Home Assistant instalowana przez HACS dla [SMS Gateway for Android](https://github.com/capcom6/android-sms-gateway) — Local Server.**

> [English documentation](docs/README_EN.md) · [Instalacja PL](docs/INSTALACJA_PL.md) · [Bezpieczeństwo PL](docs/BEZPIECZENSTWO_PL.md)

## Co robi

- Łączy **Home Assistant bezpośrednio** z SMS Gateway działającym na telefonie Android.
- Umożliwia wysłanie SMS z akcji `smsgetaweybridge.send_sms`.
- Co 30 sekund pobiera wiadomości odebrane z `GET /inbox` i statusy wysłanych z `GET /messages`.
- Udostępnia zdarzenia: `smsgetaweybridge_sms_received`, `smsgetaweybridge_sms_status`, `smsgetaweybridge_sms_queued`.
- Dodaje prostą diagnostykę: binarny czujnik dostępności, liczba ostatnich odebranych i wysłanych wiadomości oraz najnowszy status.
- Nie używa **SSH**, **Termuxa**, **Magiska**, chmury dostawcy ani pośrednictwa Ubuntu.
- Ubuntu Server może równolegle łączyć się z **tym samym** API telefonu; jego dostęp nie jest zarządzany przez tę integrację.

**Nazwa widoczna w GUI:** `smsGetaweyBridge` (dokładnie taka pisownia). **Wewnętrzna nazwa domeny HA:** `smsgetaweybridge` (zgodnie z regułami nazw integracji HA).

## Schemat

```text
                    [Galaxy S9 / SMS Gateway Local Server]
                          IP telefonu:8080
                            /           \
                    REST API            REST API
                       /                   \
       [Home Assistant / smsGetaweyBridge]  [Ubuntu Server / niezależny SMS Manager]
```

## Wymagania

- Home Assistant obsługujący współczesne custom integrations (zalecana aktualna wersja).
- HACS, jeżeli chcesz instalować przez HACS.
- SMS Gateway for Android z włączonym **Local Server** i uprawnieniami SMS. Dokumentowane endpointy: `/message`, `/messages`, `/inbox`.
- Dostęp sieciowy **z Home Assistant do telefonu** na porcie Local Server (zwykle 8080).
- Lokalny **username/password** pokazany w SMS Gateway.
- Komunikacja pozostaje w sieci prywatnej. Dla HTTP Basic Auth połączenie nie jest szyfrowane — patrz [bezpieczeństwo](docs/BEZPIECZENSTWO_PL.md).

## Instalacja z HACS (własne repozytorium)

1. Utwórz publiczne repozytorium GitHub i wgraj **zawartość** tego archiwum do katalogu głównego repozytorium.
2. **Obowiązkowo przed publikacją:** uruchom `python tools/prepare_github.py --owner TWOJ_LOGIN_GITHUB` (na komputerze z plikami repozytorium). Polecenie wpisuje prawdziwe odnośniki i `codeowners` do manifestu, nie pobiera niczego i nie łączy się z telefonem. Repozytorium musi nazywać się `smsGetaweyBridge`; przy innej nazwie popraw URL ręcznie.
3. W Home Assistant: **HACS → trzy kropki → Custom repositories / Własne repozytoria**; wklej URL repozytorium i wybierz typ **Integration**.
4. Wyszukaj `smsGetaweyBridge`, pobierz i uruchom ponownie Home Assistant.
5. **Ustawienia → Urządzenia i usługi → Dodaj integrację → smsGetaweyBridge**.
6. Podaj **IP / hostname**, **port**, **username**, **password**, w razie potrzeby **HTTPS**.
7. Test konfiguracji odpytuje tylko `/messages` i `/inbox` (nie wysyła testowego SMS).

> Repozytorium nie zostało automatycznie opublikowane na GitHub. Wgranie plików i zgłoszenie do katalogu HACS pozostaje zadaniem właściciela repozytorium. Integrację można od razu dodać w HACS jako własne repozytorium po opublikowaniu i poprawieniu linków.

### Zmiana IP i danych logowania

Na karcie integracji w **Ustawienia → Urządzenia i usługi** wybierz **Skonfiguruj ponownie** (Reconfigure), podaj nowy adres i port lub użytkownika. Zostaw pole hasła puste, jeśli hasło się nie zmieniło. Dane są ponownie sprawdzane przez GET bez wysyłania SMS-a.

### Instalacja ręczna bez HACS

Skopiuj katalog `custom_components/smsgetaweybridge` do `<config>/custom_components/smsgetaweybridge` Home Assistant, uruchom ponownie HA i dodaj integrację z GUI.

## Konfiguracja SMS Gateway na telefonie

1. Zainstaluj SMS Gateway for Android z oficjalnego źródła.
2. Włącz **Local Server** i aktywuj jego działanie w aplikacji.
3. Zanotuj IP, port, **Local Server username i password**; nie udostępniaj hasła publicznie.
4. Zezwól na odczyt/odbiór/wysyłanie SMS zgodnie z wymaganiami aplikacji i wyłącz agresywną optymalizację baterii.
5. **Nie musisz włączać Cloud Server**. Nie przekierowuj portu Local Server na publiczny internet.
6. Jeśli masz zaporę firewall per UID aplikacji, dopuść ruch Home Assistant **do** telefonu; to ruch przychodzący do aplikacji. Jej własny ruch wychodzący można nadal ograniczyć osobno.

## Wysyłanie SMS

W Home Assistant w **Narzędzia deweloperskie → Akcje** wybierz `smsgetaweybridge.send_sms`:

```yaml
action: smsgetaweybridge.send_sms
data:
  phone_number: "+48123123123"
  message: "Test z Home Assistant"
```

Przy kilku skonfigurowanych bramkach podaj dodatkowo `entry_id` konkretnej konfiguracji. Bez `entry_id` działa tylko przy dokładnie jednej bramce.

**Akceptacja żądania przez API ≠ doręczenie SMS.** Zdarzenia statusu pojawiają się po kolejnych odczytach API (jeżeli gateway i operator raportują status).

## Odbieranie SMS i statusy

W Home Assistant automatyzacje mogą reagować na zdarzenia:

| Zdarzenie | Przykładowe dane | Częstotliwość |
| --- | --- | --- |
| `smsgetaweybridge_sms_received` | `sender`, `recipient`, `message`, `message_id`, `received_at`, `sim_number`, `entry_id` | Nowe SMS-y znalezione przy odpytywaniu |
| `smsgetaweybridge_sms_status` | `message_id`, `state`, `changed_at` (czas statusu lub null), `entry_id` | Historia stanów z API, również przejścia pośrednie |
| `smsgetaweybridge_sms_queued` | `message_id`, `phone_number`, `entry_id` | Przyjęcie zlecenia wysyłki przez API |

Przykład [automatyzacji SMS](docs/INSTALACJA_PL.md#automatyzacje).

### Zmiany i ograniczenia v0.1.1

- To **integracja HACS**, a nie add-on Supervisor/App, ani rozbudowany menedżer skrzynki SMS z własnym interfejsem listy wiadomości.
- Odbiór i statusy działają przez **polling co 30 s**; nie ma serwera webhooków. Nie wymaga odbierania HTTPS przez Home Assistant.
- Integracja pobiera **wszystkie strony wyników** (po 250 rekordów, do 10 000 na odczyt): odebrane SMS-y od zapamiętanego czasu (`from`), a wysłane wiadomości z całej dostępnej historii; po przekroczeniu limitu zgłasza błąd zamiast po cichu pomijać starsze SMS-y. Pełne przeglądanie historii wysłanych SMS-ów co 30 s może być kosztowne dla telefonu z dużą skrzynką. Limit jest celowy, nie gwarantuje obsługi dowolnej liczby wiadomości.
- Przy pierwszym uruchomieniu oraz przy **migracji danych z 0.1.0** wykonuje bazowy odczyt bez emitowania historycznych zdarzeń. Z tego powodu nowe wiadomości odebrane podczas samego przejścia z 0.1.0 na 0.1.1 mogą nie zostać wyemitowane. Kolejne odczyty używają trwałego kursora czasowego i ID wiadomości z granicy.
- Sensor liczby SMS pokazuje liczbę rekordów **z ostatniego udanego odczytu** (maksymalnie 10 000), a nie bezwzględną liczbę wiadomości przechowywanych przez operatora.
- Statusy są odtwarzane z mapy `states` jako osobne zdarzenia z czasem `changed_at`. W razie braku historii możliwe są tylko przejścia zaobserwowane w kolejnych odczytach. Zdarzenia mają semantykę **at-least-once** — awaria między emisją a zapisem może spowodować duplikat; deduplikuj po `message_id` albo `(message_id, state, changed_at)`. Przesunięte w przeszłość znaczniki czasu mogą nie zostać wykryte.
- API może zwrócić tylko podgląd treści w `contentPreview`; nie gwarantuje pełnego tekstu długich SMS-ów.
- Nie sprawdzono tej paczki na konkretnym egzemplarzu Galaxy S9 ani uruchomionym Home Assistant. Uruchomienie w produkcji wymaga testów integracyjnych z rzeczywistą bramką.
- Nie ma MMS, kontaktów, dedykowanej skrzynki SMS w dashboardzie ani automatycznego konfigurowania Androida.
- Zwykła karta SIM **nie umożliwia** ustawienia nadawcy `HADevMaster` zamiast numeru telefonu.

## Bezpieczeństwo / prywatność

**SMS-y mogą zawierać dane wrażliwe i kody dostępu.** Treść odebranych SMS jest dostępna w zdarzeniu HA. Nie udostępniaj zdarzeń automatycznie do chmury, niezaufanym integracjom ani publicznych dashboardów. HA Recorder/automatyzacje mogą zachowywać zdarzenia lub je dalej przekazywać. Zadbaj o retencję i dostęp.

Przy `http://IP:8080` login i hasło HTTP Basic Auth są przesyłane w postaci zakodowanej, **niezaszyfrowanej**. Wybierz izolowany LAN/VLAN lub HTTPS z poprawnym certyfikatem; opcja „Use HTTPS” nie wyłącza weryfikacji certyfikatów. W połączeniach nie są wykonywane automatyczne przekierowania HTTP, aby nie ujawnić danych logowania innemu hostowi.

Więcej w [docs/BEZPIECZENSTWO_PL.md](docs/BEZPIECZENSTWO_PL.md).

## Publikacja w GitHub

- Uzupełnij metadane prawdziwego właściciela: `python tools/prepare_github.py --owner TWOJ_LOGIN_GITHUB`, sprawdź linki `documentation`, `issue_tracker` i `codeowners` w `manifest.json`. Bez tego repozytorium **nie jest gotowe do publikacji**.
- Dodaj opis oraz tematy repozytorium, np. `home-assistant`, `hacs`, `sms`, `android`, `smsgateway`.
- Uruchom testy `python -m unittest discover -s tests -v` i `python -m compileall -q custom_components`.
- Stwórz GitHub Release `v0.1.1`. Integracja nie musi być na oficjalnej liście HACS — może działać jako **Custom repository**.
- Jeżeli chcesz zgłosić do domyślnego katalogu HACS, sprawdź dodatkowe wymagania, w tym poprawność manifestu, Hassfest, ikonę marki i odpowiednie działania GitHub Actions.

## Dokumentacja API / inspiracje

- [SMS Gateway for Android](https://github.com/capcom6/android-sms-gateway)
- [Oficjalna dokumentacja API (OpenAPI)](https://capcom6.github.io/android-sms-gateway/)
- [Wymagania HACS dla integracji](https://www.hacs.dev/docs/publish/integration/)
- [Home Assistant: custom integrations](https://developers.home-assistant.io/docs/creating_platform_index/)

Projekt niezależny, niepowiązany z autorami SMS Gateway for Android i Home Assistant.
