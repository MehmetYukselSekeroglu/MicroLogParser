from urllib.parse import urlparse, unquote
import re

def is_ip_address(domain):
    """IP adresini kontrol eder"""
    ip_pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
    if ip_pattern.match(domain):
        # Basit bir IPv4 kontrolü
        parts = domain.split('.')
        for part in parts:
            if int(part) > 255:
                return False
        return True
    return False

def get_etc_part(parsed_url):
    """URL'nin query ve fragment kısımlarını birleştirir"""
    etc = ""
    if parsed_url.params:
        etc += f";{parsed_url.params}"
    if parsed_url.query:
        etc += f"?{parsed_url.query}"
    if parsed_url.fragment:
        etc += f"#{parsed_url.fragment}"
    
    return etc if etc else None

def prepare_url(target_url:str) -> dict:
    """
    URL'yi parçalara ayırır ve gerekli bileşenleri döndürür.
    
    Args:
        target_url (str): İşlenecek URL
        
    Returns:
        dict: URL'nin ayrıştırılmış bileşenlerini içeren sözlük
    """
    if not target_url:
        return None
    
    try:
        decoded_url = unquote(target_url)
        parsed_url = urlparse(decoded_url)
        
        if decoded_url.startswith("android://"):
            # Android URL formatını işle
            # Format: android://token@package_name/:credentials
            parts = decoded_url.split("://", 1)
            if len(parts) == 2:
                token_and_rest = parts[1].split("@", 1)
                if len(token_and_rest) == 2:
                    token = token_and_rest[0]
                    package_and_credentials = token_and_rest[1].split("/:", 1)
                    
                    package_name = package_and_credentials[0]
                    credentials = package_and_credentials[1] if len(package_and_credentials) > 1 else ""
                    
                    if str(package_name).startswith("/"):
                        package_name = package_name[1:]
                    
                    if str(package_name).endswith("/"):
                        package_name = package_name[:-1]
                    
                    return {
                        "origin": decoded_url,
                        "protocol": "android",
                        "domain": package_name,
                        "main_domain": package_name,
                        "subdomain": None,
                        "tld": None,
                        "port": None,
                        "path": None,
                        "etc": None,
                        "android_token": token,
                        "android_package": package_name,
                        "android_credentials": credentials
                    }
            
            # Android URL formatına uymuyorsa normal işleme devam et
        
        # Handle domain, port and auth separately
        domain = parsed_url.netloc
        port = None
        
        # Remove auth info if present
        if '@' in domain:
            auth, domain = domain.split('@')
        
        # Handle port
        if ':' in domain:
            domain, port = domain.split(':')
        
        # IP adreslerini kontrol et
        if is_ip_address(domain):
            # IP adresi ise domain olarak kullan, subdomain ve tld yok
            return {
                "origin": decoded_url,
                "protocol": parsed_url.scheme,
                "domain": domain,
                "main_domain": domain,
                "subdomain": None,
                "tld": None,
                "port": port,
                "path": parsed_url.path if parsed_url.path else None,
                "etc": get_etc_part(parsed_url)
            }
        
        # Split domain into parts
        domain_parts = domain.split('.')
        
        # Handle special cases like co.uk and localhost
        if domain == 'localhost':
            tld = None
            main_domain = 'localhost'
            subdomain = None
        elif len(domain_parts) >= 2:
            if domain_parts[-2] in ['co', 'com', 'org', 'net', 'edu', 'gov'] and len(domain_parts) > 2:
                tld = '.'.join(domain_parts[-2:])
                domain_parts = domain_parts[:-2]
            else:
                tld = domain_parts[-1]
                domain_parts = domain_parts[:-1]
            
            # Determine main domain and subdomain
            if domain_parts:
                main_domain = domain_parts[-1]
                subdomain = '.'.join(domain_parts[:-1]) if len(domain_parts) > 1 else None
            else:
                main_domain = None
                subdomain = None
        else:
            main_domain = domain
            subdomain = None
            tld = None
            
        path = parsed_url.path if parsed_url.path else None
        etc = get_etc_part(parsed_url)
        
        return {
            "origin": decoded_url,
            "protocol": parsed_url.scheme,
            "domain": domain,
            "main_domain": main_domain,
            "subdomain": subdomain,
            "tld": tld,
            "port": port,
            "path": path,
            "etc": etc
        }
    except Exception as e:
        return None 