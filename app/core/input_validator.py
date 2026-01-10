"""
Baloise Input Validator
Validiert Schweizer Telefonnummern und E-Mail-Adressen
"""

import re
from dataclasses import dataclass
from typing import Tuple, Optional


@dataclass
class ValidationResult:
    """Ergebnis einer Validierung"""
    valid: bool
    message: str
    corrected_value: Optional[str] = None
    suggestion: Optional[str] = None


class SwissInputValidator:
    """
    Validiert Eingaben nach Schweizer Standards
    """

    # Schweizer Telefonnummer Patterns
    # Mobile: 07x xxx xx xx
    # Festnetz: 0xx xxx xx xx
    # International: +41 xx xxx xx xx
    SWISS_MOBILE_PREFIXES = ['075', '076', '077', '078', '079']
    SWISS_AREA_CODES = [
        '021', '022', '024', '026', '027',  # Westschweiz
        '031', '032', '033', '034', '036',  # Bern/Mittelland
        '041', '043', '044', '052', '055', '056',  # Zürich/Zentralschweiz
        '061', '062', '063',  # Nordwestschweiz
        '071', '081', '091'   # Ostschweiz/Tessin
    ]

    # E-Mail Regex (RFC 5322 vereinfacht)
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )

    # Verdächtige E-Mail Domains (Wegwerf-Mails)
    SUSPICIOUS_DOMAINS = [
        'tempmail', 'throwaway', 'guerrilla', 'mailinator',
        'fakeinbox', 'trashmail', '10minutemail', 'temp-mail'
    ]

    def validate_swiss_phone(self, phone: str) -> ValidationResult:
        """
        Validiert eine Schweizer Telefonnummer

        Gültige Formate:
        - 079 123 45 67
        - 0791234567
        - +41 79 123 45 67
        - +41791234567
        - 044 123 45 67 (Festnetz)

        Returns:
            ValidationResult mit Validierungsergebnis
        """
        if not phone or not phone.strip():
            return ValidationResult(
                valid=False,
                message="Bitte geben Sie eine Telefonnummer ein."
            )

        # Normalisieren: Nur Ziffern und + behalten
        original = phone
        cleaned = re.sub(r'[^\d+]', '', phone)

        # Leere Nummer nach Bereinigung
        if not cleaned or cleaned == '+':
            return ValidationResult(
                valid=False,
                message="Die eingegebene Telefonnummer enthält keine gültigen Ziffern."
            )

        # +41 Format normalisieren
        if cleaned.startswith('+41'):
            cleaned = '0' + cleaned[3:]
        elif cleaned.startswith('0041'):
            cleaned = '0' + cleaned[4:]
        elif cleaned.startswith('41') and len(cleaned) >= 11:
            cleaned = '0' + cleaned[2:]

        # Länge prüfen (Schweizer Nummern haben 10 Ziffern)
        if len(cleaned) != 10:
            return ValidationResult(
                valid=False,
                message=f"Schweizer Telefonnummern haben 10 Ziffern (z.B. 079 123 45 67). "
                        f"Ihre Eingabe hat {len(cleaned)} Ziffern.",
                suggestion="079 123 45 67"
            )

        # Muss mit 0 beginnen
        if not cleaned.startswith('0'):
            return ValidationResult(
                valid=False,
                message="Schweizer Telefonnummern beginnen mit 0 (z.B. 079, 044).",
                suggestion="079 123 45 67"
            )

        # Vorwahl prüfen
        prefix = cleaned[:3]
        is_mobile = prefix in self.SWISS_MOBILE_PREFIXES
        is_landline = prefix in self.SWISS_AREA_CODES

        if not is_mobile and not is_landline:
            return ValidationResult(
                valid=False,
                message=f"Die Vorwahl '{prefix}' ist keine gültige Schweizer Vorwahl. "
                        f"Mobile: 075-079, Festnetz: z.B. 044, 031, 021.",
                suggestion="079 xxx xx xx oder 044 xxx xx xx"
            )

        # Formatierte Ausgabe erstellen
        formatted = f"{cleaned[:3]} {cleaned[3:6]} {cleaned[6:8]} {cleaned[8:10]}"

        return ValidationResult(
            valid=True,
            message="Gültige Schweizer Telefonnummer.",
            corrected_value=formatted
        )

    def validate_email(self, email: str) -> ValidationResult:
        """
        Validiert eine E-Mail-Adresse

        Prüft:
        - Grundformat (xxx@xxx.xx)
        - Keine Wegwerf-Mail-Domains
        - Keine offensichtlichen Tippfehler

        Returns:
            ValidationResult mit Validierungsergebnis
        """
        if not email or not email.strip():
            return ValidationResult(
                valid=False,
                message="Bitte geben Sie eine E-Mail-Adresse ein."
            )

        email = email.strip().lower()

        # Grundformat prüfen
        if not self.EMAIL_PATTERN.match(email):
            # Spezifischere Fehlermeldungen
            if '@' not in email:
                return ValidationResult(
                    valid=False,
                    message="Eine E-Mail-Adresse muss ein @ enthalten (z.B. name@beispiel.ch).",
                    suggestion="ihre.email@beispiel.ch"
                )
            if email.count('@') > 1:
                return ValidationResult(
                    valid=False,
                    message="Eine E-Mail-Adresse darf nur ein @ enthalten.",
                    suggestion="ihre.email@beispiel.ch"
                )

            parts = email.split('@')
            if len(parts) == 2:
                local, domain = parts
                if not local:
                    return ValidationResult(
                        valid=False,
                        message="Vor dem @ fehlt Ihr Name (z.B. max.muster@...).",
                        suggestion="max.muster@beispiel.ch"
                    )
                if '.' not in domain:
                    return ValidationResult(
                        valid=False,
                        message=f"Die Domain '{domain}' ist ungültig. "
                                f"Es fehlt die Endung (z.B. .ch, .com).",
                        suggestion=f"{local}@{domain}.ch"
                    )

            return ValidationResult(
                valid=False,
                message="Das E-Mail-Format ist ungültig. Bitte prüfen Sie Ihre Eingabe.",
                suggestion="vorname.nachname@beispiel.ch"
            )

        # Domain extrahieren
        domain = email.split('@')[1]

        # Wegwerf-Mail-Domains prüfen
        for suspicious in self.SUSPICIOUS_DOMAINS:
            if suspicious in domain:
                return ValidationResult(
                    valid=False,
                    message="Bitte verwenden Sie eine permanente E-Mail-Adresse, "
                            "keine Wegwerf-Mail.",
                    suggestion="ihre.email@gmail.com oder @bluewin.ch"
                )

        # Häufige Tippfehler prüfen
        common_typos = {
            'gmial.com': 'gmail.com',
            'gmal.com': 'gmail.com',
            'gmail.co': 'gmail.com',
            'gamil.com': 'gmail.com',
            'hotmal.com': 'hotmail.com',
            'hotmai.com': 'hotmail.com',
            'outloo.com': 'outlook.com',
            'outlok.com': 'outlook.com',
            'yahooo.com': 'yahoo.com',
            'yaho.com': 'yahoo.com',
            'bluwin.ch': 'bluewin.ch',
            'bluewinn.ch': 'bluewin.ch',
        }

        for typo, correct in common_typos.items():
            if domain == typo:
                corrected = email.replace(typo, correct)
                return ValidationResult(
                    valid=False,
                    message=f"Meinten Sie '{correct}' statt '{typo}'?",
                    suggestion=corrected
                )

        return ValidationResult(
            valid=True,
            message="Gültige E-Mail-Adresse.",
            corrected_value=email
        )

    def validate_plz(self, plz: str) -> ValidationResult:
        """
        Validiert eine Schweizer Postleitzahl

        Returns:
            ValidationResult
        """
        if not plz or not plz.strip():
            return ValidationResult(valid=True, message="OK")  # Optional

        cleaned = re.sub(r'\D', '', plz)

        if len(cleaned) != 4:
            return ValidationResult(
                valid=False,
                message="Schweizer Postleitzahlen haben 4 Ziffern (z.B. 8001).",
                suggestion="8001"
            )

        plz_int = int(cleaned)
        if plz_int < 1000 or plz_int > 9999:
            return ValidationResult(
                valid=False,
                message="Ungültige Postleitzahl. Schweizer PLZ: 1000-9999.",
                suggestion="8001"
            )

        return ValidationResult(
            valid=True,
            message="Gültige Postleitzahl.",
            corrected_value=cleaned
        )


# Singleton-Instanz
swiss_validator = SwissInputValidator()


def generate_validation_response(field_name: str, value: str) -> Tuple[bool, str, Optional[str]]:
    """
    Generiert eine benutzerfreundliche Validierungsantwort

    Args:
        field_name: Name des Feldes (kontakt_telefon, kontakt_email, etc.)
        value: Eingegebener Wert

    Returns:
        Tuple[is_valid, message, corrected_value]
    """
    if field_name == 'kontakt_telefon':
        result = swiss_validator.validate_swiss_phone(value)
    elif field_name == 'kontakt_email':
        result = swiss_validator.validate_email(value)
    elif field_name == 'schadensort_plz':
        result = swiss_validator.validate_plz(value)
    else:
        return True, "", None

    if result.valid:
        return True, "", result.corrected_value
    else:
        msg = f"❌ {result.message}"
        if result.suggestion:
            msg += f"\n💡 Beispiel: {result.suggestion}"
        return False, msg, None


# === TEST ===
if __name__ == "__main__":
    validator = SwissInputValidator()

    print("=== TELEFON TESTS ===")
    test_phones = [
        "079 123 45 67",
        "0791234567",
        "+41 79 123 45 67",
        "044 123 45 67",
        "123456789",  # Ungültig
        "080 123 45 67",  # Ungültige Vorwahl
        "079 123 456",  # Zu kurz
    ]

    for phone in test_phones:
        result = validator.validate_swiss_phone(phone)
        status = "✅" if result.valid else "❌"
        print(f"{status} '{phone}' → {result.message}")
        if result.corrected_value:
            print(f"   Formatiert: {result.corrected_value}")

    print("\n=== EMAIL TESTS ===")
    test_emails = [
        "test@gmail.com",
        "max.muster@bluewin.ch",
        "invalid",
        "test@gmial.com",  # Tippfehler
        "test@@gmail.com",
        "test@tempmail.com",  # Wegwerf
    ]

    for email in test_emails:
        result = validator.validate_email(email)
        status = "✅" if result.valid else "❌"
        print(f"{status} '{email}' → {result.message}")
