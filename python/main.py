import argparse
import sys
import os
import time 
import concurrent.futures
import threading
import queue
import io

from LineProccesser_ULP import proccessLine

# Thread güvenli yazma işlemleri için
file_write_lock = threading.Lock()
output_queue = queue.Queue(maxsize=200000)  # Daha büyük bir kuyruk kapasitesi
sql_counter = 0
total_line_count = 0
BATCH_SIZE = 5000  # Her seferde kaç satır SQL yazılacak
progress_lock = threading.Lock()

def write_sql_to_file(sql_file, statements):
    """Thread güvenli bir şekilde SQL ifadelerini dosyaya yazar"""
    with file_write_lock:
        with open(sql_file, "a", encoding="utf-8") as f:
            f.write("\n".join(statements) + "\n")

def sql_writer_thread(output_file):
    """Kuyruktan SQL ifadelerini alıp dosyaya yazan thread"""
    global sql_counter
    statements_batch = []
    last_write_time = time.time()
    
    while True:
        try:
            statement = output_queue.get(timeout=1)
            if statement == "DONE":
                # Son kalan ifadeleri de yaz
                if statements_batch:
                    write_sql_to_file(output_file, statements_batch)
                    with progress_lock:
                        print(f"Son kayıtlar yazıldı: {sql_counter} SQL kaydı oluşturuldu.")
                break
                
            statements_batch.append(statement)
            
            with progress_lock:
                sql_counter += 1
            
            # Belirli sayıda ifade biriktiğinde veya belirli bir süre geçtiğinde toplu şekilde yaz
            current_time = time.time()
            if len(statements_batch) >= BATCH_SIZE or (current_time - last_write_time > 5 and statements_batch):
                write_sql_to_file(output_file, statements_batch)
                statements_batch = []
                last_write_time = current_time
                
                with progress_lock:
                    elapsed = current_time - start_time
                    speed = sql_counter / elapsed if elapsed > 0 else 0
                    processed_percent = (total_line_count > 0) and (sql_counter / total_line_count * 100) or 0
                    print(f"İlerleme: {sql_counter:,} / {total_line_count:,} kayıt (%{processed_percent:.2f}), Hız: {speed:.2f} kayıt/sn")
                
        except queue.Empty:
            # Kuyruk boşsa ve bekleyen ifadeler varsa, onları yaz
            current_time = time.time()
            if statements_batch and (current_time - last_write_time > 1):
                write_sql_to_file(output_file, statements_batch)
                statements_batch = []
                last_write_time = current_time
                
                with progress_lock:
                    print(f"Beklemede: {sql_counter:,} kayıt işlendi, kuyrukta {output_queue.qsize():,} kayıt var")

def format_sql_value(value):
    """SQL değerlerini güvenli bir şekilde formatlama"""
    if value is None:
        return "NULL"
    if isinstance(value, int):
        return str(value)
    
    # SQL injection'ı engellemek için tırnak işaretlerini escape et
    return f"'{str(value).replace(chr(0), '').replace(chr(92), '\\\\').replace(chr(39), chr(92)+chr(39))}'"

def process_line(line: str):
    """Bir satırı işleyip SQL sorgusu oluşturur"""
    try:
        line = line.strip()
        if not line:
            return
        
        processed_line = proccessLine(line)
        
        if not processed_line:
            return

        # SQL ifadesi oluşturma
        sql_values = {}
        
        protocol = processed_line[0]
        sql_values["protocol"] = protocol
        
        if protocol == "android":
            # Android için özel alan değerleri
            sql_values["android_token"] = processed_line[9]  # android_token
            sql_values["android_package"] = processed_line[10]  # android_package
            sql_values["domain"] = None
            sql_values["subdomain"] = None
            sql_values["tld"] = None
            sql_values["port"] = None
            sql_values["path"] = None
            sql_values["path_etc"] = None
        else:
            # Normal URL formatı için
            sql_values["android_token"] = None
            sql_values["android_package"] = None
            sql_values["domain"] = processed_line[1]  # main_domain
            sql_values["subdomain"] = processed_line[2]  # subdomain
            sql_values["tld"] = processed_line[3]  # tld
            sql_values["port"] = processed_line[4]  # port
            sql_values["path"] = processed_line[5]  # path
            sql_values["path_etc"] = processed_line[6]  # etc
            
        # Path içindeki query ve fragment ayırma
        query = None
        fragment = None
        
        if processed_line[6] and isinstance(processed_line[6], str):
            etc = processed_line[6]
            if '?' in etc:
                query_part = etc.split('?', 1)[1]
                if '#' in query_part:
                    query, fragment = query_part.split('#', 1)
                else:
                    query = query_part
            elif '#' in etc:
                fragment = etc.split('#', 1)[1]
        
        sql_values["query"] = query
        sql_values["fragment"] = fragment
        
        # Kimlik bilgileri
        sql_values["username"] = processed_line[7]  # username
        sql_values["password"] = processed_line[8]  # password
        
        # SQL ifadesini oluştur
        columns = ", ".join(sql_values.keys())
        values = ", ".join(format_sql_value(v) for v in sql_values.values())
        
        sql_statement = f"INSERT INTO log ({columns}) VALUES ({values});"
        
        # Kuyrukta işlenmek üzere SQL ifadesini ekle
        output_queue.put(sql_statement)

    except Exception as err:
        print(f"Error processing line: {err}")
        return

def count_lines(file_path):
    """Dosyadaki satır sayısını hızlı bir şekilde hesaplar"""
    try:
        with open(file_path, 'rb') as f:
            bufgen = io.DEFAULT_BUFFER_SIZE
            buf_count = 0
            
            for buf in iter(lambda: f.raw.read(bufgen), b''):
                buf_count += buf.count(b'\n')
                
            return buf_count
    except Exception as e:
        print(f"Satır sayımı sırasında hata: {e}")
        return 0

def main():
    global start_time, total_line_count
    
    parser = argparse.ArgumentParser(description='Process URL logs and convert to SQL.')
    parser.add_argument('--input', type=str, help='The file containing the URLs to process', required=True)
    parser.add_argument('--output', type=str, help='The file to write the SQL output to', required=True)
    parser.add_argument('--threads', type=int, help='Number of worker threads (default: 100)', default=100)
    parser.add_argument('--batch-size', type=int, help='Batch size for SQL inserts (default: 5000)', default=5000)
    args = parser.parse_args()

    input_log_file = args.input
    output_sql_file = args.output
    worker_threads = args.threads
    global BATCH_SIZE
    BATCH_SIZE = args.batch_size

    if not os.path.exists(input_log_file):
        print(f"Input file {input_log_file} does not exist")
        sys.exit(1)
    
    # Satır sayımı
    print("Giriş dosyasındaki satır sayısı hesaplanıyor...")
    total_line_count = count_lines(input_log_file)
    print(f"Toplam {total_line_count:,} satır işlenecek")
    
    # SQL başlangıç kodu
    with open(output_sql_file, "w", encoding="utf-8") as f:
        f.write("-- Auto-generated SQL from MicroLogParser\n")
        f.write("-- Generated at: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n\n")
        f.write("BEGIN;\n\n")
    
    # SQL yazma thread'ini başlat
    writer_thread = threading.Thread(target=sql_writer_thread, args=(output_sql_file,))
    writer_thread.daemon = True
    writer_thread.start()
    
    print(f"İşlem başlatılıyor: {worker_threads} thread ile çalışılacak")
    start_time = time.time()
    
    # İşlem thread'lerini başlat
    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_threads) as executor:
        try:
            with open(input_log_file, "r", encoding="utf-8", errors='ignore') as f:
                for line in f:
                    executor.submit(process_line, line)
        except KeyboardInterrupt:
            print("\nİşlem kullanıcı tarafından durduruldu.")
            executor.shutdown(wait=False)
    
    # Tüm satırlar işlendi, SQL yazma thread'ine bitirme sinyali gönder
    output_queue.put("DONE")
    writer_thread.join()
    
    # SQL dosyasını kapat
    with open(output_sql_file, "a", encoding="utf-8") as f:
        f.write("\nCOMMIT;\n")
    
    elapsed_time = time.time() - start_time
    print(f"\nİşlem tamamlandı: {total_line_count:,} satır okundu, {sql_counter:,} SQL kaydı oluşturuldu.")
    print(f"Toplam süre: {elapsed_time:.2f} saniye")
    print(f"İşleme hızı: {sql_counter/elapsed_time:.2f} kayıt/saniye")

if __name__ == "__main__":
    start_time = 0
    try:
        main()
    except KeyboardInterrupt:
        print("\nİşlem kullanıcı tarafından durduruldu.")
        sys.exit(0)


