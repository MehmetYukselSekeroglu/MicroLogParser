import re

def check_and_add_protocol(url: str) -> str:
    """
    URL'ye eksik protokol bilgisini ekler.
    
    Args:
        url (str): Kontrol edilecek URL
        
    Returns:
        str: Protokolü eklenmiş URL
    """
    # URL boş ise None döndür
    if not url:
        return None
    
    # URL zaten protokol içeriyorsa aynen döndür
    if re.match(r'^[a-z]+://', url.lower()):
        return url
    
    # android:// formatı kontrolü
    if url.startswith('android@'):
        return 'android://' + url[8:]
    
    # Diğer protokoller için varsayılan olarak http:// ekle
    return 'http://' + url 