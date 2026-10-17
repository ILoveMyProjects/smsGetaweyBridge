# Bezpieczeństwo i granice izolacji

## Sieć

Integracja nie odwołuje się do internetu, używa wyłącznie adresu telefonu z konfiguracji. Brak logiki Cloud Server. `aiohttp` odrzuca przekierowania HTTP (bez przesyłania Basic Auth do obcego hosta). Jeśli ktoś wpisze publiczny host w kreatorze, integracja spróbuje się z nim połączyć — izolację LAN musi egzekwować Twoja sieć/firewall.

Zalecamy:

- Stałą rezerwację adresu w DHCP routera, bez wpisywania adresów na stałe w kodzie.
- Firewall ograniczający **ruch przychodzący** do Local Server telefonu do IP Home Assistant i Ubuntu VM.
- Firewall telefonu ograniczający **wychodzący** internet aplikacji SMS Gateway. Uważaj: nie zablokuj lokalnego połączenia do VM, jeśli używa ona webhooków.
- Brak przekierowania portu 8080 na WAN, brak Cloud Server.
- Dla Basic Auth przez HTTP dane logowania nie są szyfrowane: używaj zaufanego VLAN/LAN albo HTTPS z prawidłowym certyfikatem. Nie wyłączamy sprawdzania certyfikatów.

## SMS i prywatność

Treści odebranych SMS pojawiają się w zdarzeniu `smsgetaweybridge_sms_received`. Nie są przechowywane w zapisie integracji; tylko identyfikatory wiadomości i stany (dane deduplikacji) są zapisywane w magazynie Home Assistant. Dodatkowe automatyzacje i inne komponenty HA mogą jednak treść przechowywać.

Ze względów bezpieczeństwa nie przechowuj ani nie eksportuj kodów OTP; włącz uwierzytelnianie Home Assistant i kontroluj uprawnienia dostępu do jego kopii zapasowych i `.storage` (tam HA przechowuje również hasła integracji).

## Poprawność wysyłania

Odpowiedź `202 Accepted` oznacza zlecenie SMS, nie dostarczenie. Przy przekroczeniu czasu oczekiwania klient **nie powtarza automatycznie POST**, bo duplikat mógłby wysłać drugi SMS. Status z GET `/messages` jest tylko statusem deklarowanym przez bramkę. `Delivered` zależy od potwierdzenia operatora i nie oznacza przeczytania SMS.

## Testy produkcyjne

Sprawdź na własnym sprzęcie i SIM: odczyt, wysyłkę, ponowny restart telefonu, aktualizację aplikacji, zmianę IP i błędne dane logowania. Testy lokalne kodu nie zastępują integracyjnego testu z Home Assistant.

## Historia zdarzeń i ponawianie

Do przechowywania znaczników czasu i identyfikatorów używany jest magazyn `.storage` HA. Treści nie są tam kopiowane, ale HA, automatyzacje i ewentualne logi mogą je zachowywać. Po awarii pomiędzy wyemitowaniem zdarzenia a zapisem znacznika, zdarzenie może zostać zgłoszone ponownie (semantyka **at-least-once**). Dla automatyzacji uruchamiających działania nieodwracalne wymagane jest własne rozpoznawanie duplikatów.

Wysyłanie wykonuje dokładnie jeden POST na żądanie akcji. Przy błędach sieci i HTTP 404/405 nie próbuje automatycznego wysłania przez inne endpointy: to decyzja chroniąca przed podwójnym naliczeniem SMS-a. Płatność lub status wiadomości sprawdź przed ręcznym ponowieniem.
