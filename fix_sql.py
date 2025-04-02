#!/usr/bin/env python3
import sys
import re

def fix_postgres_sql(input_file, output_file):
    """PostgreSQL uyumlu olmayan SQL ifadelerini düzeltir"""
    try:
        # Dosyayı satır satır okuyalım
        with open(input_file, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        
        # Çıktı dosyası
        with open(output_file, 'w', encoding='utf-8') as out:
            # Başlık bilgileri
            out.write("-- Auto-generated SQL from MicroLogParser Fix Script\n")
            out.write("-- Her INSERT ifadesi kendi transaction'ı içinde çalışacak\n\n")
            
            # Her INSERT ifadesini kendi transaction'ı içinde işle
            current_statement = ""
            in_transaction = False
            
            for line in lines:
                # Yorum satırlarını olduğu gibi geçir
                if line.startswith("--"):
                    out.write(line)
                    continue
                
                # BEGIN/COMMIT komutlarını atla, bunları kendimiz ekleyeceğiz
                if re.match(r'^\s*BEGIN\s*;?\s*$', line, re.IGNORECASE) or \
                   re.match(r'^\s*COMMIT\s*;?\s*$', line, re.IGNORECASE):
                    continue
                
                # INSERT ifadelerini bul
                if line.strip().startswith("INSERT INTO"):
                    # Önceki ifade varsa bitir
                    if current_statement:
                        out.write("COMMIT;\n\n")
                        in_transaction = False
                    
                    # Yeni bir ifade başlat
                    current_statement = fix_single_statement(line)
                    out.write("BEGIN;\n")
                    in_transaction = True
                    out.write(current_statement)
                    
                    # Eğer ifade noktalı virgülle bitmiyorsa ekle
                    if not current_statement.rstrip().endswith(';'):
                        out.write(';')
                    out.write('\n')
                    
                    # Transaction'ı kapat
                    out.write("COMMIT;\n\n")
                    in_transaction = False
                    current_statement = ""
            
            # Son transaction'ı tamamla
            if in_transaction:
                out.write("COMMIT;\n\n")
        
        print(f"SQL düzeltildi ve {output_file} dosyasına kaydedildi.")
        return True
    except Exception as e:
        print(f"Hata: {str(e)}")
        return False

def fix_single_statement(statement):
    """Tek bir SQL ifadesini düzelt"""
    # Tek tırnakları doğru şekilde kaçır - \' -> ''
    statement = re.sub(r"\\'", "''", statement)
    
    # Satır sonlarında ters eğik çizgi karakterlerini kaldır
    statement = re.sub(r"\\'\);", "');", statement)
    statement = re.sub(r"\\'\s*$", "'", statement)
    
    # Ters eğik çizgileri doğru şekilde kaçır
    statement = re.sub(r"\\\\", "\\\\\\\\", statement)
    
    # Tek tırnak içindeki sorunlu karakterleri düzelt
    statement = fix_quoted_values(statement)
    
    return statement

def fix_quoted_values(text):
    """Tek tırnak içindeki değerlerdeki sorunlu karakterleri temizle ve başındaki/sonundaki boşlukları kaldır"""
    result = ""
    i = 0
    
    # Önce tüm tek tırnak içindeki değerleri belirle
    while i < len(text):
        if text[i] == "'" and (i == 0 or text[i-1] != '\\'):  # Gerçek tek tırnak (kaçırılmamış)
            # Bir değerin başladığını tespit ettik, kapanış tırnağını bul
            start_quote = i
            i += 1  # Açılış tırnağını atla
            value = ""
            
            # Tırnak içindeki değeri al
            while i < len(text) and (text[i] != "'" or (i > 0 and text[i-1] == '\\')):
                if text[i] == '\\' and i+1 < len(text) and text[i+1] == "'":
                    value += text[i]  # Ters eğik çizgiyi al
                    i += 1
                    value += text[i]  # Tek tırnak karakterini al
                else:
                    value += text[i]
                i += 1
                
            # Kapanış tırnağını bulduk mu?
            if i < len(text) and text[i] == "'":
                # Değeri temizle (trim)
                cleaned_value = value.strip()
                
                # Sorunlu karakterleri temizle
                final_value = ""
                for c in cleaned_value:
                    if c == '\r' or c == '\n' or c == '\t':
                        final_value += ' '  # CR, LF ve TAB'ı boşluğa çevir
                    elif c == '\\':
                        final_value += "\\\\"  # Ters eğik çizgi için PostgreSQL kaçışı
                    elif ord(c) < 32 or ord(c) > 126:
                        final_value += "_"  # Basılabilir olmayan karakterleri değiştir
                    else:
                        final_value += c
                
                # Temizlenmiş değeri tek tırnak içine al
                result += "'" + final_value + "'"
                i += 1  # Kapanış tırnağını atla
            else:
                # Kapanış tırnağı bulunamadı, bu durumda orjinal metni koru
                result += "'" + value
        else:
            # Tırnak dışındaki karakterleri olduğu gibi koru
            result += text[i]
            i += 1
    
    return result

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Kullanım: python fix_sql.py <input_sql_file> <output_sql_file>")
        sys.exit(1)
    
    input_file = sys.argv[1] 
    output_file = sys.argv[2]
    
    if fix_postgres_sql(input_file, output_file):
        print("İşlem başarılı!")
    else:
        print("İşlem sırasında hata oluştu!")
        sys.exit(1) 