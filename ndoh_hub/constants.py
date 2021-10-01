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
JEMBI_LANGUAGES = ["zu", "xh", "af", "en", "nso", "tn", "st", "ts", "ss", "ve", "nr"]
# Since WhatsApp doesn't support most of South Africa's official languages, we create
# a mapping to languages that we don't use for missing languages
WHATSAPP_LANGUAGE_MAP = {
    "zul_ZA": "en",
    "xho_ZA": "en",
    "afr_ZA": "af",
    "eng_ZA": "en",
    "nso_ZA": "en",
    "tsn_ZA": "en",
    "sot_ZA": "en",
    "tso_ZA": "en",
    "ssw_ZA": "en",
    "ven_ZA": "en",
    "nbl_ZA": "en",
}

HCS_STUDY_A_TARGETS = {
    "ZA-LP": {"total": 2275, "percentage": 13},
    "ZA-NW": {"total": 1050, "percentage": 6},
    "ZA-NL": {"total": 2975, "percentage": 17},
    "ZA-EC": {"total": 1575, "percentage": 9},
    "ZA-MP": {"total": 1050, "percentage": 6},
    "ZA-WC": {"total": 2450, "percentage": 14},
    "ZA-FS": {"total": 1050, "percentage": 6},
    "ZA-NC": {"total": 175, "percentage": 1},
    "ZA-GT": {"total": 4900, "percentage": 28},
}
