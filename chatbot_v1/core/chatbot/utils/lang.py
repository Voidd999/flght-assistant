from .redis_client import get_language_config

# Use get_language_config() instead of LANGUAGE_CONFIG
language_config = None

def normalize_language_code(lang_code: str) -> str:
    """
    Normalize language code to supported format.
    Args:
        lang_code: Input language code (e.g., 'en-GB', 'ar-SA', 'fr-CA')
    Returns:
        Normalized language code (e.g., 'en-US', 'ar', 'fr')
    """
    if not lang_code:
        return 'en-US'
        
    lang_code = lang_code.lower().strip()
    
    global language_config
    if language_config is None:
        language_config = get_language_config()
    
    # Check if it's already a main language code
    if lang_code in language_config:
        return language_config[lang_code]['code']
    
    # Check variants
    for main_lang, config in language_config.items():
        if lang_code in config['variants'] or lang_code.startswith(main_lang + '-'):
            return config['code']
    
    # Extract primary language code for unknown variants
    primary_lang = lang_code.split('-')[0]
    if primary_lang in language_config:
        return language_config[primary_lang]['code']
    
    return 'en-US'  # Default fallback
