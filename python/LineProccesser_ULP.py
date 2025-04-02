import threading
from UrlParser import prepare_url
from protocol import check_and_add_protocol

# Thread güvenli dosya yazma kilidi
FILE_WRITE_LOCK = threading.Lock()

def write_failed_line(line: str):
    """Başarısız analizlenen satırları bir dosyaya kaydeder"""
    with FILE_WRITE_LOCK:
        with open("failed_lines.txt", "a+", encoding="utf-8") as f:
            f.write(line + "\n")

def proccessLine(currentLine: str) -> tuple:
    """
    URL ve kimlik bilgilerini içeren bir satırı işler.
    Çeşitli format biçimlerini destekler.
    Başarısız olursa None döndürür.
    
    Args:
        currentLine (str): İşlenecek satır
        
    Returns:
        tuple: Ayrıştırılmış URL bileşenlerinin listesi
    """
    try:
        if not currentLine or not isinstance(currentLine, str):
            return None
        
        currentLine = check_and_add_protocol(currentLine)        
        
        if currentLine.lower().startswith("android://"):
            if currentLine.count(" ") == 1:
                split_line = currentLine.strip().split(" ", 1)
                if len(split_line) == 2:
                    _full_url = split_line[0]
                    _usernameAndPassword = split_line[1].split(":")
                    
                    if not _usernameAndPassword:
                        write_failed_line(currentLine)
                        return None
                    
                    _username = _usernameAndPassword[0].strip()
                    _password = ""
                    
                    if len(_usernameAndPassword) > 1:
                        _password = ":".join(_usernameAndPassword[1:]).strip()
                    
                    _parsedUrl = prepare_url(_full_url)
                    if not _parsedUrl:
                        write_failed_line(currentLine)
                        return None
                    
                    return (_parsedUrl["protocol"], 
                            _parsedUrl["main_domain"],
                            _parsedUrl["subdomain"],
                            _parsedUrl["tld"],
                            _parsedUrl["port"],
                            _parsedUrl["path"],
                            _parsedUrl["etc"],
                            _username,
                            _password,
                            _parsedUrl.get("android_token"),
                            _parsedUrl.get("android_package"))
            
            elif currentLine.count(":") == 3:
                split_line = currentLine.strip().split(":")
                if len(split_line) == 4:
                    _full_url = f"{split_line[0]}:{split_line[1]}"
                    _username = split_line[2].strip()
                    _password = split_line[3].strip()
                    
                    _parsedUrl = prepare_url(_full_url)
                    if not _parsedUrl:
                        write_failed_line(currentLine)
                        return None
                    
                    return (_parsedUrl["protocol"], 
                            _parsedUrl["main_domain"],
                            _parsedUrl["subdomain"],
                            _parsedUrl["tld"],
                            _parsedUrl["port"],
                            _parsedUrl["path"],
                            _parsedUrl["etc"],
                            _username,
                            _password,
                            _parsedUrl.get("android_token"),
                            _parsedUrl.get("android_package"))
            elif currentLine.count("|") == 2:
                split_line = currentLine.strip().split("|")
                if len(split_line) == 3:
                    _full_url = split_line[0]
                    _username = split_line[1].strip()
                    _password = split_line[2].strip()
                    
                    _parsedUrl = prepare_url(_full_url)
                    if not _parsedUrl:
                        write_failed_line(currentLine)
                        return None
                    
                    return (_parsedUrl["protocol"], 
                            _parsedUrl["main_domain"],
                            _parsedUrl["subdomain"],
                            _parsedUrl["tld"],
                            _parsedUrl["port"],
                            _parsedUrl["path"],
                            _parsedUrl["etc"],
                            _username,
                            _password,
                            _parsedUrl.get("android_token"),
                            _parsedUrl.get("android_package"))
                    
            elif currentLine.count("::") == 2:
                split_line = currentLine.strip().split("::")
                if len(split_line) == 3:
                    _full_url = split_line[0]
                    _username = split_line[1].strip()
                    _password = split_line[2].strip()
                    
                    _parsedUrl = prepare_url(_full_url)
                    if not _parsedUrl:
                        write_failed_line(currentLine)
                        return None
                    
                    return (_parsedUrl["protocol"], 
                            _parsedUrl["main_domain"],
                            _parsedUrl["subdomain"],
                            _parsedUrl["tld"],
                            _parsedUrl["port"],
                            _parsedUrl["path"],
                            _parsedUrl["etc"],
                            _username,
                            _password,
                            _parsedUrl.get("android_token"),
                            _parsedUrl.get("android_package"))
            else:
                write_failed_line(currentLine)
                return None
        
        # Format: URL username:password
        if currentLine.strip().count(" ") == 1:
            split_line = currentLine.strip().split(" ", 1)
            
            if len(split_line) == 2:        
                _full_url = split_line[0]
                _usernameAndPassword = split_line[1].split(":")
                
                if not _usernameAndPassword:
                    write_failed_line(currentLine)
                    return None
                    
                _username = _usernameAndPassword[0].strip()
                _password = ""

                if len(_usernameAndPassword) > 1:
                    _password = ":".join(_usernameAndPassword[1:]).strip()
                
                _parsedUrl = prepare_url(_full_url)
                if not _parsedUrl:
                    write_failed_line(currentLine)
                    return None

                return (_parsedUrl["protocol"], 
                        _parsedUrl["main_domain"],
                        _parsedUrl["subdomain"],
                        _parsedUrl["tld"],
                        _parsedUrl["port"],
                        _parsedUrl["path"],
                        _parsedUrl["etc"],
                        _username,
                        _password,
                        _parsedUrl.get("android_token"),
                        _parsedUrl.get("android_package"))
        
        # Format: protocol:domain:username:password or protocol:domain:port:username:password
        elif currentLine.count(":") >= 3:
            split_line = currentLine.split(":")              
            
            if len(split_line) < 4:
                write_failed_line(currentLine)
                return None
                
            # Basic format: protocol:domain:username:password
            if len(split_line) == 4:
                _full_url = f"{split_line[0]}:{split_line[1]}"
                _username = split_line[2].strip()
                _password = split_line[3].strip()
                
                _parsedUrl = prepare_url(_full_url)
                if not _parsedUrl:
                    write_failed_line(currentLine)
                    return None
                
                return (_parsedUrl["protocol"], 
                        _parsedUrl["main_domain"],
                        _parsedUrl["subdomain"],
                        _parsedUrl["tld"],
                        _parsedUrl["port"],
                        _parsedUrl["path"],
                        _parsedUrl["etc"],
                        _username,
                        _password,
                        _parsedUrl.get("android_token"),
                        _parsedUrl.get("android_package"))
            
            # Format with port or complex password: protocol:domain:port:username:password...
            elif len(split_line) >= 5:
                _full_url = f"{split_line[0]}:{split_line[1]}"
                _possible_port = split_line[2]
                
                # Check if third element is a port number
                if _possible_port.isdigit():
                    _full_url += f":{_possible_port}"
                    _username = split_line[3].strip()
                    _password = ":".join(split_line[4:]).strip()
                else:
                    # If not a port, it's part of the credential format
                    _username = split_line[2].strip()
                    _password = ":".join(split_line[3:]).strip()
                
                _parsedUrl = prepare_url(_full_url)
                if not _parsedUrl:
                    write_failed_line(currentLine)
                    return None
                
                return (_parsedUrl["protocol"], 
                        _parsedUrl["main_domain"],
                        _parsedUrl["subdomain"],
                        _parsedUrl["tld"],
                        _parsedUrl["port"],
                        _parsedUrl["path"],
                        _parsedUrl["etc"],
                        _username,
                        _password,
                        _parsedUrl.get("android_token"),
                        _parsedUrl.get("android_package"))
        
        # Format: URL|username|password
        elif "|" in currentLine:
            if currentLine.count("|") == 2:
                split_line = currentLine.split("|")  
                if len(split_line) == 3:
                    _full_url = split_line[0]
                    _username = split_line[1].strip()
                    _password = split_line[2].strip()
                    
                    _parsedUrl = prepare_url(_full_url)
                    if not _parsedUrl:
                        write_failed_line(currentLine)
                        return None
                    
                    return (_parsedUrl["protocol"], 
                            _parsedUrl["main_domain"],
                            _parsedUrl["subdomain"],
                            _parsedUrl["tld"],
                            _parsedUrl["port"],
                            _parsedUrl["path"],
                            _parsedUrl["etc"],
                            _username,
                            _password,
                            _parsedUrl.get("android_token"),
                            _parsedUrl.get("android_package"))
        
        # Anlaşılamayan format
        write_failed_line(currentLine)
        return None
    
    except Exception as e:
        write_failed_line(currentLine)
        return None 