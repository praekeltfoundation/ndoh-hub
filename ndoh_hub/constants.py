ID_TYPES = ["sa_id", "passport", "none"]
PASSPORT_ORIGINS = [
    "na",
    "bw",
    "mz",
    "sz",
    "ls",
    "cu",
    "zw",
    "mw",
    "ng",
    "cd",
    "so",
    "other",
]
LANGUAGES = [
    "zul_ZA",  # isiZulu
    "xho_ZA",  # isiXhosa
    "afr_ZA",  # Afrikaans
    "eng_ZA",  # English
    "nso_ZA",  # Sesotho sa Leboa / Pedi
    "tsn_ZA",  # Setswana
    "sot_ZA",  # Sesotho
    "tso_ZA",  # Xitsonga
    "ssw_ZA",  # siSwati
    "ven_ZA",  # Tshivenda
    "nbl_ZA",  # isiNdebele
]
# Since WhatsApp doesn't support most of South Africa's official languages, we create
# a mapping to languages that we don't use for missing languages
WHATSAPP_LANGUAGE_MAP = {
    "zul_ZA": "uz",
    "xho_ZA": "th",
    "afr_ZA": "af",
    "eng_ZA": "en",
    "nso_ZA": "sl",
    "tsn_ZA": "bn",
    "sot_ZA": "ta",
    "tso_ZA": "sv",
    "ssw_ZA": "sw",
    "ven_ZA": "vi",
    "nbl_ZA": "nb",
}
