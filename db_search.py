#!/usr/bin/env python3
import os
import sys
import psycopg2
import psycopg2.extras
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import datetime
import configparser
import json
from typing import Dict, List, Tuple, Any, Optional

# ========================
# Veritabanı Bağlantı Sınıfı
# ========================
class DatabaseConnection:
    def __init__(self, config_file='db_config.ini'):
        self.conn = None
        self.cursor = None
        self.config_file = config_file
        self.load_config()
        
    def load_config(self):
        """Yapılandırma dosyasından veritabanı bağlantı bilgilerini yükle"""
        config = configparser.ConfigParser()
        
        # Varsayılan yapılandırma
        self.db_config = {
            'host': os.environ.get('PGHOST', '127.0.0.1'),
            'port': os.environ.get('PGPORT', '5432'),
            'database': os.environ.get('PGDATABASE', 'micrologparser'),
            'user': os.environ.get('PGUSER', 'postgres'),
            'password': os.environ.get('PGPASSWORD', '')
        }
        
        if os.path.exists(self.config_file):
            config.read(self.config_file)
            if 'PostgreSQL' in config:
                for key in self.db_config:
                    if key in config['PostgreSQL']:
                        self.db_config[key] = config['PostgreSQL'][key]
        else:
            # Yapılandırma dosyası yoksa oluştur
            config['PostgreSQL'] = self.db_config
            with open(self.config_file, 'w') as f:
                config.write(f)
    
    def save_config(self):
        """Veritabanı bağlantı bilgilerini yapılandırma dosyasına kaydet"""
        config = configparser.ConfigParser()
        config['PostgreSQL'] = self.db_config
        with open(self.config_file, 'w') as f:
            config.write(f)
    
    def connect(self):
        """Veritabanına bağlan"""
        try:
            self.conn = psycopg2.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                database=self.db_config['database'],
                user=self.db_config['user'],
                password=self.db_config['password']
            )
            self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            return True
        except Exception as e:
            print(f"Veritabanı bağlantı hatası: {e}")
            return False
    
    def close(self):
        """Veritabanı bağlantısını kapat"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def execute_query(self, query, params=None):
        """Sorguyu çalıştır ve sonuçları döndür"""
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Sorgu hatası: {e}")
            return []
    
    def execute_query_with_headers(self, query, params=None):
        """Sorguyu çalıştır ve sütun başlıkları ile sonuçları döndür"""
        try:
            self.cursor.execute(query, params)
            results = self.cursor.fetchall()
            headers = [desc[0] for desc in self.cursor.description]
            return headers, results
        except Exception as e:
            print(f"Sorgu hatası: {e}")
            return [], []
    
    def get_table_columns(self, table_name):
        """Tablodaki sütunları döndür"""
        query = """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
        """
        return self.execute_query(query, (table_name,))
    
    def get_table_rows_count(self, table_name):
        """Tablodaki satır sayısını döndür"""
        query = f"SELECT COUNT(*) FROM {table_name}"
        result = self.execute_query(query)
        return result[0][0] if result else 0
    
    def get_table_size(self, table_name):
        """Tablo boyutunu döndür"""
        query = """
        SELECT pg_size_pretty(pg_total_relation_size(%s))
        """
        result = self.execute_query(query, (table_name,))
        return result[0][0] if result else "0 bytes"
    
    def get_database_stats(self):
        """Veritabanı istatistiklerini döndür"""
        stats = {}
        
        # Toplam tablo sayısı
        query = """
        SELECT COUNT(*) FROM information_schema.tables 
        WHERE table_schema = 'public'
        """
        result = self.execute_query(query)
        stats['total_tables'] = result[0][0] if result else 0
        
        # Veritabanı boyutu
        query = """
        SELECT pg_size_pretty(pg_database_size(current_database()))
        """
        result = self.execute_query(query)
        stats['database_size'] = result[0][0] if result else "0 bytes"
        
        # Son istatistik toplama zamanı
        query = """
        SELECT now()
        """
        result = self.execute_query(query)
        stats['stats_time'] = result[0][0] if result else datetime.datetime.now()
        
        return stats

# ========================
# Arama Motoru Sınıfı
# ========================
class SearchEngine:
    def __init__(self, db_connection, table_name='log'):
        self.db = db_connection
        self.table_name = table_name
        self.search_fields = self._get_fields()
    
    def _get_fields(self):
        """Tablo alanlarını al ve arama için kullanılabilir alanları belirle"""
        columns = self.db.get_table_columns(self.table_name)
        fields = []
        for col in columns:
            column_name = col[0]
            data_type = col[1]
            
            # BIGSERIAL ve TIMESTAMP alanlarını arama için kullanma
            if column_name == 'id' or data_type == 'timestamp with time zone':
                continue
                
            fields.append({
                'name': column_name,
                'type': data_type,
                'is_text': data_type in ('character varying', 'text', 'varchar', 'char')
            })
        
        return fields
    
    def build_search_query(self, search_params):
        """Arama parametrelerine göre SQL sorgusu oluştur"""
        conditions = []
        params = []
        
        for field in search_params:
            field_name = field['name']
            field_value = field['value']
            operator = field['operator']
            
            if not field_value and operator not in ('IS NULL', 'IS NOT NULL'):
                continue
                
            if operator == 'LIKE':
                conditions.append(f"{field_name} ILIKE %s")
                params.append(f"%{field_value}%")
            elif operator == '=':
                conditions.append(f"{field_name} = %s")
                params.append(field_value)
            elif operator == '!=':
                conditions.append(f"{field_name} != %s")
                params.append(field_value)
            elif operator == '>':
                conditions.append(f"{field_name} > %s")
                params.append(field_value)
            elif operator == '<':
                conditions.append(f"{field_name} < %s")
                params.append(field_value)
            elif operator == 'IS NULL':
                conditions.append(f"{field_name} IS NULL")
            elif operator == 'IS NOT NULL':
                conditions.append(f"{field_name} IS NOT NULL")
            elif operator == 'STARTS WITH':
                conditions.append(f"{field_name} ILIKE %s")
                params.append(f"{field_value}%")
            elif operator == 'ENDS WITH':
                conditions.append(f"{field_name} ILIKE %s")
                params.append(f"%{field_value}")
            elif operator == 'IN':
                # Virgülle ayrılmış değerler listesi
                values = [v.strip() for v in field_value.split(',')]
                placeholders = ', '.join(['%s'] * len(values))
                conditions.append(f"{field_name} IN ({placeholders})")
                params.extend(values)
            elif operator == 'NOT IN':
                # Virgülle ayrılmış değerler listesi
                values = [v.strip() for v in field_value.split(',')]
                placeholders = ', '.join(['%s'] * len(values))
                conditions.append(f"{field_name} NOT IN ({placeholders})")
                params.extend(values)
            elif operator == 'DOMAIN+TLD':
                # domain ve tld alanlarını birlikte ara
                conditions.append(f"(domain = %s AND tld = %s)")
                domain_parts = field_value.split('.')
                if len(domain_parts) >= 2:
                    domain = domain_parts[0]
                    tld = '.'.join(domain_parts[1:])
                    params.append(domain)
                    params.append(tld)
                else:
                    # Tek parça ise sadece domain üzerinde ara
                    conditions.pop()  # Son eklenen koşulu kaldır
                    conditions.append(f"domain = %s")
                    params.append(field_value)
        
        query = f"SELECT * FROM {self.table_name}"
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY id DESC"  # Sonuç sayısını sınırla
        
        return query, params
    
    def search(self, search_params):
        """Veritabanında arama yap"""
        query, params = self.build_search_query(search_params)
        headers, results = self.db.execute_query_with_headers(query, params)
        
        return {
            'headers': headers,
            'results': results,
            'count': len(results),
            'query': query,
            'params': params
        }
    
    def get_distinct_values(self, field_name, limit=100):
        """Belirli bir alan için benzersiz değerleri al"""
        query = f"""
        SELECT DISTINCT {field_name} FROM {self.table_name}
        WHERE {field_name} IS NOT NULL
        ORDER BY {field_name}
        LIMIT %s
        """
        result = self.db.execute_query(query, (limit,))
        return [row[0] for row in result]
    
    def get_domain_tld_combinations(self, limit=100):
        """En çok kullanılan domain ve tld kombinasyonlarını al"""
        query = """
        SELECT domain, tld, COUNT(*) as count 
        FROM log 
        WHERE domain IS NOT NULL AND tld IS NOT NULL
        GROUP BY domain, tld 
        ORDER BY count DESC
        LIMIT %s
        """
        result = self.db.execute_query(query, (limit,))
        return result
    
    def get_tld_stats(self, limit=20):
        """En çok kullanılan TLD'leri istatistikleriyle birlikte al"""
        query = """
        SELECT tld, COUNT(*) as count 
        FROM log 
        WHERE tld IS NOT NULL
        GROUP BY tld 
        ORDER BY count DESC
        LIMIT %s
        """
        result = self.db.execute_query(query, (limit,))
        return result
    
    def get_tld_growth(self, days=30, top_n=10):
        """Belirli bir dönem içinde en hızlı büyüyen TLD'leri al"""
        query = """
        WITH recent_counts AS (
            SELECT tld, COUNT(*) as recent_count
            FROM log
            WHERE created_at >= NOW() - INTERVAL %s DAY
            AND tld IS NOT NULL
            GROUP BY tld
        ),
        old_counts AS (
            SELECT tld, COUNT(*) as old_count
            FROM log
            WHERE created_at < NOW() - INTERVAL %s DAY
            AND tld IS NOT NULL
            GROUP BY tld
        )
        SELECT r.tld, r.recent_count, COALESCE(o.old_count, 0) as old_count,
               r.recent_count - COALESCE(o.old_count, 0) as growth
        FROM recent_counts r
        LEFT JOIN old_counts o ON r.tld = o.tld
        ORDER BY growth DESC
        LIMIT %s
        """
        result = self.db.execute_query(query, (days, days, top_n))
        return result
    
    def get_domain_stats_by_tld(self, tld, limit=20):
        """Belirli bir TLD için en popüler domainleri al"""
        query = """
        SELECT domain, COUNT(*) as count
        FROM log
        WHERE tld = %s
        GROUP BY domain
        ORDER BY count DESC
        LIMIT %s
        """
        result = self.db.execute_query(query, (tld, limit))
        return result
        
    def get_urls_by_domain_tld(self, domain, tld, limit=100):
        """Belirli bir domain ve TLD için tam URL'leri ve ilgili bilgileri getir"""
        query = """
        SELECT 
            CONCAT(
                COALESCE(protocol || '://', ''), 
                COALESCE(subdomain || '.', ''), 
                main_domain, '.', tld, 
                COALESCE(':' || port, ''), 
                COALESCE(path, '/')
            ) as full_url,
            username,
            password,
            protocol,
            subdomain,
            main_domain,
            tld,
            path,
            port,
            created_at
        FROM log
        WHERE main_domain = %s AND tld = %s
        ORDER BY created_at DESC
        LIMIT %s
        """
        headers, result = self.db.execute_query_with_headers(query, (domain, tld, limit))
        return headers, result

# ========================
# GUI Sınıfı
# ========================
class DatabaseSearchGUI:
    """Veritabanı arama arayüzü"""
    
    def __init__(self, root, search_engine):
        self.root = root
        self.search_engine = search_engine
        
        self.root.title("PostgreSQL Veritabanı Arama")
        self.root.geometry("1200x800")
        
        self.create_widgets()
        self.setup_menu()
        
    def setup_menu(self):
        """Menü oluştur"""
        menu_bar = tk.Menu(self.root)
        
        # Dosya menüsü
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Veritabanı İstatistikleri", command=self.show_db_stats)
        file_menu.add_separator()
        file_menu.add_command(label="Çıkış", command=self.root.quit)
        menu_bar.add_cascade(label="Dosya", menu=file_menu)
        
        # TLD Analiz menüsü
        tld_menu = tk.Menu(menu_bar, tearoff=0)
        tld_menu.add_command(label="TLD İstatistikleri", command=self.show_tld_stats)
        tld_menu.add_command(label="En Çok Kullanılan Domain-TLD", command=self.show_domain_tld_combinations)
        tld_menu.add_command(label="TLD Büyüme Analizi", command=self.show_tld_growth)
        tld_menu.add_command(label="TLD'ye Göre Domain Analizi", command=self.show_domain_by_tld)
        menu_bar.add_cascade(label="TLD Analiz", menu=tld_menu)
        
        # Yardım menüsü
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="Yardım", command=self.show_help)
        help_menu.add_command(label="Hakkında", command=self.show_about)
        menu_bar.add_cascade(label="Yardım", menu=help_menu)
        
        self.root.config(menu=menu_bar)
    
    def create_widgets(self):
        """Widget'ları oluştur"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Sol panelde arama alanları
        left_frame = ttk.Frame(main_frame, padding="5")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)
        
        # Arama alanları başlığı
        search_title = ttk.Label(left_frame, text="Arama Kriterleri", font=("Arial", 12, "bold"))
        search_title.grid(row=0, column=0, columnspan=3, pady=5)
        
        # Arama alanları oluştur
        self.search_fields = []
        self.create_search_fields(left_frame)
        
        # Arama butonları
        button_frame = ttk.Frame(left_frame)
        button_frame.grid(row=len(self.search_fields) + 1, column=0, columnspan=3, pady=10)
        
        self.search_button = ttk.Button(button_frame, text="Ara", command=self.perform_search)
        self.search_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_button = ttk.Button(button_frame, text="Temizle", command=self.clear_search)
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        # Önceden tanımlanmış arama şablonları
        preset_frame = ttk.LabelFrame(left_frame, text="Hızlı Aramalar")
        preset_frame.grid(row=len(self.search_fields) + 2, column=0, columnspan=3, pady=10, sticky="ew")
        
        ttk.Button(preset_frame, text="TLD: com", 
                  command=lambda: self.set_preset_search("tld", "=", "com")).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="TLD: tr", 
                  command=lambda: self.set_preset_search("tld", "=", "tr")).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="Android", 
                  command=lambda: self.set_preset_search("android_token", "IS NOT NULL", "")).pack(side=tk.LEFT, padx=2)
        
        # Sağ panelde sonuçlar
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Sonuç bilgisi
        self.result_info = ttk.Label(right_frame, text="Sonuç bulunamadı")
        self.result_info.pack(fill=tk.X, pady=5)
        
        # Arama sorgusu
        self.query_frame = ttk.LabelFrame(right_frame, text="SQL Sorgusu")
        self.query_frame.pack(fill=tk.X, pady=5)
        
        self.query_text = tk.Text(self.query_frame, height=3, wrap=tk.WORD)
        self.query_text.pack(fill=tk.X, expand=True)
        
        # Sonuç tablosu
        table_frame = ttk.Frame(right_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Treeview
        self.tree = ttk.Treeview(table_frame)
        self.tree["columns"] = ()
        
        # Scrollbar
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=vsb.set)
        
        # Yatay scrollbar
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.configure(xscrollcommand=hsb.set)
        
        self.tree.pack(fill=tk.BOTH, expand=True)
    
    def create_search_fields(self, parent):
        """Arama alanlarını oluştur"""
        fields = [
            "id", "android_token", "protocol", "domain", "subdomain", "tld", "port", 
            "path", "username", "password", "created_at"
        ]
        
        operators = ["=", "!=", ">", "<", "LIKE", "STARTS WITH", "ENDS WITH", 
                    "IS NULL", "IS NOT NULL", "IN", "NOT IN", "DOMAIN+TLD"]
        
        for i, field in enumerate(fields):
            field_label = ttk.Label(parent, text=field)
            field_label.grid(row=i+1, column=0, padx=5, pady=2, sticky=tk.W)
            
            # Operatör combobox
            operator_var = tk.StringVar()
            operator_combobox = ttk.Combobox(parent, textvariable=operator_var, 
                                          values=operators, width=10)
            operator_combobox.set("=")
            operator_combobox.grid(row=i+1, column=1, padx=5, pady=2)
            
            # Değer girişi
            value_var = tk.StringVar()
            value_entry = ttk.Entry(parent, textvariable=value_var, width=25)
            value_entry.grid(row=i+1, column=2, padx=5, pady=2)
            
            # Değerleri görüntüleme butonu
            values_button = ttk.Button(
                parent, text="Değerler", 
                command=lambda f=field: self._show_distinct_values(f)
            )
            values_button.grid(row=i+1, column=3, padx=5, pady=2)
            
            self.search_fields.append({
                "name": field,
                "operator_var": operator_var,
                "value_var": value_var,
                "entry": value_entry,
                "values_button": values_button
            })

    def _show_distinct_values(self, field_name):
        """Belirli bir alan için benzersiz değerleri göster"""
        values = self.search_engine.get_distinct_values(field_name)
        
        if not values:
            messagebox.showinfo("Bilgi", f"{field_name} için benzersiz değer bulunamadı.")
            return
            
        # Yeni pencere oluştur
        top = tk.Toplevel(self.root)
        top.title(f"{field_name} Değerleri")
        top.geometry("300x400")
        
        # Liste oluştur
        listbox = tk.Listbox(top, width=40, height=20)
        listbox.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Scrollbar ekle
        scrollbar = ttk.Scrollbar(listbox, orient="vertical", command=listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        listbox.configure(yscrollcommand=scrollbar.set)
        
        # Değerleri ekle
        for value in values:
            if value is not None:
                listbox.insert(tk.END, str(value))
        
        # Seçilen değeri entry'ye ekle
        def select_value():
            selected_idx = listbox.curselection()
            if selected_idx:
                value = listbox.get(selected_idx[0])
                # İlgili alanı bul ve değerini ayarla
                for field in self.search_fields:
                    if field["name"] == field_name:
                        field["value_var"].set(value)
                        break
                top.destroy()
        
        # Seçim butonu
        select_button = ttk.Button(top, text="Seç", command=select_value)
        select_button.pack(pady=10)

    def set_preset_search(self, field_name, operator, value):
        """Önceden tanımlanmış arama kriterini ayarla"""
        self.clear_search()
        
        # İlgili alanı bul ve operatör ve değeri ayarla
        for field in self.search_fields:
            if field["name"] == field_name:
                field["operator_var"].set(operator)
                field["value_var"].set(value)
                break
                
        # Aramayı gerçekleştir
        self.perform_search()

    def perform_search(self):
        """Arama yap"""
        search_params = []
        
        for field in self.search_fields:
            name = field["name"]
            operator = field["operator_var"].get()
            value = field["value_var"].get()
            
            search_params.append({
                "name": name,
                "operator": operator,
                "value": value
            })
        
        try:
            result = self.search_engine.search(search_params)
            self.display_results(result)
        except Exception as e:
            messagebox.showerror("Hata", f"Arama sırasında hata oluştu: {str(e)}")
    
    def clear_search(self):
        """Arama kriterlerini temizle"""
        for field in self.search_fields:
            field["operator_var"].set("=")
            field["value_var"].set("")
        
        # Sonuçları temizle
        self.tree["columns"] = ()
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.result_info.config(text="Sonuç bulunamadı")
        self.query_text.delete("1.0", tk.END)
    
    def display_results(self, result):
        """Sonuçları görüntüle"""
        # Sonuç bilgisi
        self.result_info.config(text=f"{result['count']} sonuç bulundu")
        
        # SQL sorgusunu göster
        self.query_text.delete("1.0", tk.END)
        self.query_text.insert("1.0", f"{result['query']}\n\nParameters: {result['params']}")
        
        # Treeview temizle
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Tüm sütunları al
        all_headers = result['headers']
        
        # URL oluşturmak için gerekli alanları belirle
        url_fields = ['protocol', 'subdomain', 'domain', 'main_domain', 'tld', 'port', 'path']
        
        # Sadece gösterilecek sütunlar
        display_headers = ["url", "username", "password"]
        
        # Treeview sütunlarını ayarla
        self.tree["columns"] = display_headers
        
        # Sütun başlıklarını ayarla
        self.tree.column("#0", width=0, stretch=tk.NO)
        
        # Sütun genişliklerini ve başlıklarını ayarla
        column_config = {
            "url": {"title": "URL", "width": 600, "anchor": tk.W},
            "username": {"title": "Kullanıcı Adı", "width": 150, "anchor": tk.W},
            "password": {"title": "Şifre", "width": 150, "anchor": tk.W}
        }
        
        for header in display_headers:
            config = column_config.get(header, {"title": header.capitalize(), "width": 150, "anchor": tk.W})
            self.tree.column(header, anchor=config["anchor"], width=config["width"])
            self.tree.heading(header, text=config["title"], anchor=config["anchor"])
        
        # Sonuçları ekle
        credential_count = 0
        
        # Sonuçları global olarak sakla (dışa aktarma için)
        self.current_results = []
        
        for i, row in enumerate(result['results']):
            # URL oluşturma
            url = self._create_full_url(row, all_headers)
            
            # Kimlik bilgilerini al
            username = ""
            password = ""
            
            username_idx = all_headers.index('username') if 'username' in all_headers else -1
            password_idx = all_headers.index('password') if 'password' in all_headers else -1
            
            if username_idx >= 0 and username_idx < len(row) and row[username_idx]:
                username = str(row[username_idx])
            
            if password_idx >= 0 and password_idx < len(row) and row[password_idx]:
                password = str(row[password_idx])
            
            # Sonuçları sakla
            self.current_results.append({"url": url, "username": username, "password": password})
            
            # Satırı ekle
            item_id = self.tree.insert("", tk.END, text=str(i), values=(url, username, password))
            
            # Kimlik bilgisi varsa satırı vurgula
            if username or password:
                self.tree.item(item_id, tags=('credentials',))
                credential_count += 1
            elif "admin" in url.lower() or "login" in url.lower() or "panel" in url.lower():
                self.tree.item(item_id, tags=('important',))
            else:
                self.tree.item(item_id, tags=('normal',))
        
        # Stilleri tanımla
        self.tree.tag_configure('credentials', background='#FFFF99')
        self.tree.tag_configure('important', background='#E8F5E9')
        self.tree.tag_configure('normal', background='#FFFFFF')
        
        # Durum bilgisi güncelle
        self.result_info.config(text=f"{result['count']} sonuç bulundu | Kimlik bilgisi içeren: {credential_count}")
        
        # Dışa aktarma butonları ekle
        if hasattr(self, 'export_frame'):
            self.export_frame.destroy()
            
        self.export_frame = ttk.Frame(self.root)
        self.export_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(self.export_frame, text="Dışa Aktar:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(self.export_frame, text="TXT", command=lambda: self.export_results("txt")).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.export_frame, text="CSV", command=lambda: self.export_results("csv")).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.export_frame, text="JSON", command=lambda: self.export_results("json")).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.export_frame, text="ULP", command=lambda: self.export_results("ulp")).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.export_frame, text="COMBO", command=lambda: self.export_results("combo")).pack(side=tk.LEFT, padx=2)
        
        # Double click event'i
        def on_tree_double_click(event):
            region = self.tree.identify("region", event.x, event.y)
            if region == "heading":
                return
                
            item = self.tree.identify('item', event.x, event.y)
            if item:
                # Seçilen satırın değerlerini alma
                values = self.tree.item(item, "values")
                if values and len(values) >= 3:
                    url, username, password = values[0], values[1], values[2]
                    self._copy_credentials_to_clipboard(url, username, password)
                
        self.tree.bind("<Double-1>", on_tree_double_click)
    
    def export_results(self, format_type):
        """Arama sonuçlarını belirtilen formatta dışa aktar"""
        if not hasattr(self, 'current_results') or not self.current_results:
            messagebox.showinfo("Bilgi", "Dışa aktarılacak sonuç bulunamadı.")
            return
            
        # Dosya adı oluştur
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Kaydetme dosyasını seç
        if format_type == "txt":
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialfile=f"url_export_{timestamp}.txt"
            )
            
            if filename:
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        for item in self.current_results:
                            f.write(f"URL: {item['url']}\n")
                            if item['username']:
                                f.write(f"Kullanıcı Adı: {item['username']}\n")
                            if item['password']:
                                f.write(f"Şifre: {item['password']}\n")
                            f.write("-" * 80 + "\n")
                    messagebox.showinfo("Başarılı", f"Sonuçlar başarıyla dışa aktarıldı:\n{filename}")
                except Exception as e:
                    messagebox.showerror("Hata", f"Dışa aktarma sırasında hata oluştu: {str(e)}")
        
        elif format_type == "csv":
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialfile=f"url_export_{timestamp}.csv"
            )
            
            if filename:
                try:
                    import csv
                    with open(filename, 'w', encoding='utf-8', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(["URL", "Kullanıcı Adı", "Şifre"])
                        for item in self.current_results:
                            writer.writerow([item['url'], item['username'], item['password']])
                    messagebox.showinfo("Başarılı", f"Sonuçlar başarıyla dışa aktarıldı:\n{filename}")
                except Exception as e:
                    messagebox.showerror("Hata", f"Dışa aktarma sırasında hata oluştu: {str(e)}")
        
        elif format_type == "json":
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                initialfile=f"url_export_{timestamp}.json"
            )
            
            if filename:
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(self.current_results, f, ensure_ascii=False, indent=2)
                    messagebox.showinfo("Başarılı", f"Sonuçlar başarıyla dışa aktarıldı:\n{filename}")
                except Exception as e:
                    messagebox.showerror("Hata", f"Dışa aktarma sırasında hata oluştu: {str(e)}")
        
        elif format_type == "ulp":
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialfile=f"ulp_export_{timestamp}.txt"
            )
            
            if filename:
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        for item in self.current_results:
                            if item['url'] and (item['username'] or item['password']):
                                f.write(f"{item['url']}:{item['username']}:{item['password']}\n")
                    messagebox.showinfo("Başarılı", f"ULP formatında dışa aktarıldı:\n{filename}")
                except Exception as e:
                    messagebox.showerror("Hata", f"Dışa aktarma sırasında hata oluştu: {str(e)}")
        
        elif format_type == "combo":
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialfile=f"combo_export_{timestamp}.txt"
            )
            
            if filename:
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        for item in self.current_results:
                            if item['username'] or item['password']:
                                f.write(f"{item['username']}:{item['password']}\n")
                    messagebox.showinfo("Başarılı", f"Combo formatında dışa aktarıldı:\n{filename}")
                except Exception as e:
                    messagebox.showerror("Hata", f"Dışa aktarma sırasında hata oluştu: {str(e)}")
    
    def _create_full_url(self, row, all_headers):
        """Tam URL oluştur"""
        protocol = ""
        subdomain = ""
        domain = ""
        tld = ""
        port = ""
        path = ""
        
        # İndeksleri bul
        protocol_idx = all_headers.index('protocol') if 'protocol' in all_headers else -1
        subdomain_idx = all_headers.index('subdomain') if 'subdomain' in all_headers else -1
        domain_idx = -1
        
        if 'domain' in all_headers:
            domain_idx = all_headers.index('domain')
        elif 'main_domain' in all_headers:
            domain_idx = all_headers.index('main_domain')
            
        tld_idx = all_headers.index('tld') if 'tld' in all_headers else -1
        port_idx = all_headers.index('port') if 'port' in all_headers else -1
        path_idx = all_headers.index('path') if 'path' in all_headers else -1
        
        # Değerleri çıkar
        if protocol_idx >= 0 and protocol_idx < len(row) and row[protocol_idx]:
            protocol = str(row[protocol_idx]) + "://"
        
        if subdomain_idx >= 0 and subdomain_idx < len(row) and row[subdomain_idx]:
            subdomain = str(row[subdomain_idx]) + "."
        
        if domain_idx >= 0 and domain_idx < len(row) and row[domain_idx]:
            domain = str(row[domain_idx])
        
        if tld_idx >= 0 and tld_idx < len(row) and row[tld_idx]:
            tld = "." + str(row[tld_idx])
        
        if port_idx >= 0 and port_idx < len(row) and row[port_idx]:
            port = ":" + str(row[port_idx])
        
        if path_idx >= 0 and path_idx < len(row) and row[path_idx]:
            path = str(row[path_idx])
        elif path_idx < 0:
            path = "/"
        
        # Tam URL
        full_url = f"{protocol}{subdomain}{domain}{tld}{port}{path}"
        return full_url
    
    def _copy_credentials_to_clipboard(self, url, username, password):
        """Kimlik bilgilerini panoya kopyala"""
        creds = f"URL: {url}\n"
        if username:
            creds += f"Kullanıcı Adı: {username}\n"
        if password:
            creds += f"Şifre: {password}"
            
        self.root.clipboard_clear()
        self.root.clipboard_append(creds)
        messagebox.showinfo("Bilgi", "Kimlik bilgileri panoya kopyalandı")

    def show_detail_popup(self, values, display_headers, all_headers, row):
        """Seçilen satırın detaylarını gösteren popup"""
        top = tk.Toplevel(self.root)
        top.title("Kayıt Detayları")
        top.geometry("600x450")
        
        # Ana frame
        main_frame = ttk.Frame(top, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # URL Oluşturma
        url_frame = ttk.LabelFrame(main_frame, text="URL", padding="5")
        url_frame.pack(fill=tk.X, pady=5)
        
        # URL bileşenlerini çıkart
        protocol = ""
        subdomain = ""
        domain = ""
        tld = ""
        port = ""
        path = ""
        
        protocol_idx = display_headers.index('protocol') if 'protocol' in display_headers else -1
        if protocol_idx >= 0 and values[protocol_idx]:
            protocol = values[protocol_idx] + "://"
        
        subdomain_idx = display_headers.index('subdomain') if 'subdomain' in display_headers else -1
        if subdomain_idx >= 0 and values[subdomain_idx]:
            subdomain = values[subdomain_idx] + "."
        
        domain_idx = -1
        if 'domain' in display_headers:
            domain_idx = display_headers.index('domain')
        elif 'main_domain' in display_headers:
            domain_idx = display_headers.index('main_domain')
            
        if domain_idx >= 0 and values[domain_idx]:
            domain = values[domain_idx]
        
        tld_idx = display_headers.index('tld') if 'tld' in display_headers else -1
        if tld_idx >= 0 and values[tld_idx]:
            tld = "." + values[tld_idx]
        
        port_idx = display_headers.index('port') if 'port' in display_headers else -1
        if port_idx >= 0 and values[port_idx]:
            port = ":" + values[port_idx]
        
        path_idx = display_headers.index('path') if 'path' in display_headers else -1
        if path_idx >= 0 and values[path_idx]:
            path = values[path_idx]
        elif path_idx < 0:
            path = "/"
        
        full_url = f"{protocol}{subdomain}{domain}{tld}{port}{path}"
        
        # URL alanı
        url_entry = ttk.Entry(url_frame, width=70)
        url_entry.insert(0, full_url)
        url_entry.pack(fill=tk.X, padx=5, pady=5)
        
        # URL kopyalama butonu
        def copy_url():
            top.clipboard_clear()
            top.clipboard_append(full_url)
            messagebox.showinfo("Bilgi", "URL panoya kopyalandı")
            
        ttk.Button(url_frame, text="URL'yi Kopyala", command=copy_url).pack(anchor=tk.E, padx=5, pady=5)
        
        # Kimlik bilgileri frame
        cred_frame = ttk.LabelFrame(main_frame, text="Kimlik Bilgileri", padding="5")
        cred_frame.pack(fill=tk.X, pady=5)
        
        # Kullanıcı adı
        username = ""
        username_idx = display_headers.index('username') if 'username' in display_headers else -1
        if username_idx >= 0 and values[username_idx]:
            username = values[username_idx]
            
        ttk.Label(cred_frame, text="Kullanıcı Adı:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        username_entry = ttk.Entry(cred_frame, width=40)
        username_entry.insert(0, username)
        username_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Şifre
        password = ""
        password_idx = display_headers.index('password') if 'password' in display_headers else -1
        if password_idx >= 0 and values[password_idx]:
            password = values[password_idx]
            
        ttk.Label(cred_frame, text="Şifre:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        password_entry = ttk.Entry(cred_frame, width=40)
        password_entry.insert(0, password)
        password_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Kimlik bilgilerini kopyalama butonu
        def copy_credentials():
            if username or password:
                creds = f"URL: {full_url}\n"
                if username:
                    creds += f"Kullanıcı Adı: {username}\n"
                if password:
                    creds += f"Şifre: {password}"
                    
                top.clipboard_clear()
                top.clipboard_append(creds)
                messagebox.showinfo("Bilgi", "Kimlik bilgileri panoya kopyalandı")
            else:
                messagebox.showinfo("Bilgi", "Kopyalanacak kimlik bilgisi bulunamadı")
                
        ttk.Button(cred_frame, text="Kimlik Bilgilerini Kopyala", command=copy_credentials).grid(
            row=2, column=1, sticky=tk.E, padx=5, pady=5)
        
        # Diğer tüm alanları listele
        other_frame = ttk.LabelFrame(main_frame, text="Diğer Alanlar", padding="5")
        other_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Scrollable içerik
        canvas = tk.Canvas(other_frame)
        scrollbar = ttk.Scrollbar(other_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Tüm alanları ekle
        row_idx = 0
        for i, header in enumerate(display_headers):
            # URL ve kimlik bilgileri zaten gösterildiği için tekrar gösterme
            if header in ['username', 'password']:
                continue
                
            display_name = header.replace('_', ' ').title()
            field_value = values[i] if i < len(values) else ""
            
            ttk.Label(scrollable_frame, text=f"{display_name}:").grid(
                row=row_idx, column=0, sticky=tk.W, padx=5, pady=2)
                
            value_entry = ttk.Entry(scrollable_frame, width=50)
            value_entry.insert(0, field_value)
            value_entry.configure(state="readonly")
            value_entry.grid(row=row_idx, column=1, sticky=tk.W, padx=5, pady=2)
            
            row_idx += 1
        
        # Kapat butonu
        ttk.Button(main_frame, text="Kapat", command=top.destroy).pack(
            anchor=tk.E, padx=5, pady=10)

    def _create_stat_box(self, parent, row, column, title, value, tag):
        """İstatistik kutusu oluştur"""
        colors = {
            "database": "#E1F5FE",
            "table": "#E8F5E9",
            "records": "#FFF9C4",
            "auth": "#FFEBEE",
            "today": "#E8EAF6",
            "week": "#F3E5F5",
            "month": "#E0F2F1",
            "android": "#F9FBE7"
        }
        
        frame = ttk.Frame(parent, padding=10)
        frame.grid(row=row, column=column, padx=5, pady=5, sticky=tk.NSEW)
        
        # Stil için çerçeve (ttk ile doğrudan background yapılamadığı için)
        style_frame = tk.Frame(frame, background=colors.get(tag, "#FFFFFF"))
        style_frame.place(relwidth=1, relheight=1)
        
        # İçerik frame
        content = ttk.Frame(frame)
        content.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # Başlık ve değer
        ttk.Label(content, text=title, font=("Arial", 9, "normal")).pack(anchor=tk.CENTER)
        
        # Boyutlar için farklı stil kullan
        if "database" in tag or "table" in tag:
            ttk.Label(content, text=value, font=("Arial", 14, "bold"), foreground="#0277BD").pack(anchor=tk.CENTER)
        else:
            ttk.Label(content, text=value, font=("Arial", 14, "bold")).pack(anchor=tk.CENTER)
            
    def show_db_stats(self):
        """Veritabanı istatistiklerini göster"""
        try:
            # Ana veritabanı istatistikleri
            size_query = """
            SELECT 
                pg_size_pretty(pg_database_size(current_database())) as db_size,
                pg_size_pretty(pg_total_relation_size('log')) as table_total_size,
                pg_size_pretty(pg_relation_size('log')) as table_size,
                pg_size_pretty(pg_indexes_size('log')) as index_size,
                (SELECT COUNT(*) FROM log) as record_count,
                (SELECT MAX(created_at) FROM log) as last_record,
                (SELECT MIN(created_at) FROM log) as first_record;
            """
            size_result = self.search_engine.db.execute_query(size_query)
            
            # TLD dağılımları
            tld_query = """
            SELECT tld, COUNT(*) as count
            FROM log
            WHERE tld IS NOT NULL
            GROUP BY tld
            ORDER BY count DESC
            LIMIT 10;
            """
            tld_result = self.search_engine.db.execute_query(tld_query)
            
            # Domain dağılımları
            domain_query = """
            SELECT domain, COUNT(*) as count
            FROM log
            WHERE domain IS NOT NULL
            GROUP BY domain
            ORDER BY count DESC
            LIMIT 10;
            """
            domain_result = self.search_engine.db.execute_query(domain_query)
            
            # Protokol dağılımları
            protocol_query = """
            SELECT protocol, COUNT(*) as count
            FROM log
            WHERE protocol IS NOT NULL
            GROUP BY protocol
            ORDER BY count DESC;
            """
            protocol_result = self.search_engine.db.execute_query(protocol_query)
            
            # Android token sayısı
            android_query = """
            SELECT COUNT(*) as android_count
            FROM log
            WHERE android_token IS NOT NULL;
            """
            android_result = self.search_engine.db.execute_query(android_query)
            
            # Bugün ve son hafta içindeki kayıt sayıları
            time_query = """
            SELECT 
                (SELECT COUNT(*) FROM log WHERE created_at >= CURRENT_DATE) as today_count,
                (SELECT COUNT(*) FROM log WHERE created_at >= CURRENT_DATE - INTERVAL '7 days') as week_count,
                (SELECT COUNT(*) FROM log WHERE created_at >= CURRENT_DATE - INTERVAL '30 days') as month_count;
            """
            time_result = self.search_engine.db.execute_query(time_query)
            
            # Kimlik bilgisi içeren kayıt sayısı
            auth_query = """
            SELECT COUNT(*) as auth_count
            FROM log
            WHERE username IS NOT NULL OR password IS NOT NULL;
            """
            auth_result = self.search_engine.db.execute_query(auth_query)
            
            if size_result:
                # Ana istatistik değerlerini çıkar
                db_size, table_total_size, table_size, index_size, record_count, last_record, first_record = size_result[0]
                android_count = android_result[0][0] if android_result else 0
                today_count, week_count, month_count = time_result[0] if time_result else (0, 0, 0)
                auth_count = auth_result[0][0] if auth_result else 0
                
                # Yeni pencere oluştur
                top = tk.Toplevel(self.root)
                top.title("Veritabanı İstatistikleri")
                top.geometry("900x700")
                
                # Notebook (tabbed interface) oluştur
                notebook = ttk.Notebook(top)
                notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                
                # Ana özet sekmesi
                summary_frame = ttk.Frame(notebook, padding=10)
                notebook.add(summary_frame, text="Genel Özet")
                
                # Başlık
                ttk.Label(summary_frame, text="Veritabanı İstatistikleri", 
                        font=("Arial", 14, "bold")).grid(row=0, column=0, columnspan=4, pady=10, sticky=tk.W)
                
                # Tarih bilgisi
                now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                ttk.Label(summary_frame, text=f"Son güncelleme: {now}", 
                        font=("Arial", 9, "italic")).grid(row=1, column=0, columnspan=4, pady=(0, 15), sticky=tk.W)
                
                # Ana istatistikler (2x2 grid)
                # İlk satır
                self._create_stat_box(summary_frame, 2, 0, "Veritabanı Boyutu", db_size, "database")
                self._create_stat_box(summary_frame, 2, 1, "Tablo Toplam Boyutu", table_total_size, "database")
                self._create_stat_box(summary_frame, 2, 2, "Tablo Veri Boyutu", table_size, "table")
                self._create_stat_box(summary_frame, 2, 3, "İndeks Boyutu", index_size, "table")
                
                # İkinci satır
                self._create_stat_box(summary_frame, 3, 0, "Toplam Kayıt", f"{record_count:,}", "records")
                self._create_stat_box(summary_frame, 3, 1, "Auth. Kayıtları", f"{auth_count:,}", "auth")
                self._create_stat_box(summary_frame, 3, 2, "Bugün", f"{today_count:,}", "today")
                self._create_stat_box(summary_frame, 3, 3, "Son 7 Gün", f"{week_count:,}", "week")
                
                # Üçüncü satır
                self._create_stat_box(summary_frame, 4, 0, "Son 30 Gün", f"{month_count:,}", "month")
                self._create_stat_box(summary_frame, 4, 1, "Android", f"{android_count:,}", "android")
                
                # Zaman bilgisi
                time_frame = ttk.LabelFrame(summary_frame, text="Zaman Aralığı", padding=10)
                time_frame.grid(row=5, column=0, columnspan=4, pady=15, sticky=tk.EW)
                
                if first_record and last_record:
                    date_diff = last_record - first_record
                    days = date_diff.days
                    seconds = date_diff.seconds
                    hours = seconds // 3600
                    minutes = (seconds % 3600) // 60
                    
                    time_text = f"İlk Kayıt: {first_record.strftime('%d.%m.%Y')}\n"
                    time_text += f"Son Kayıt: {last_record.strftime('%d.%m.%Y')}\n"
                    time_text += f"Toplam Süre: {days} gün, {hours} saat, {minutes} dakika"
                    
                    ttk.Label(time_frame, text=time_text).pack(anchor=tk.W)
                
                # TLD Dağılımı sekmesi
                tld_frame = ttk.Frame(notebook, padding=10)
                notebook.add(tld_frame, text="TLD Dağılımı")
                
                # TLD başlık
                ttk.Label(tld_frame, text="En Çok Kullanılan TLD'ler", 
                        font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))
                
                # TLD tablo
                tld_tree = ttk.Treeview(tld_frame, columns=("tld", "count", "percent"), show="headings", height=10)
                tld_tree.heading("tld", text="TLD")
                tld_tree.heading("count", text="Sayı")
                tld_tree.heading("percent", text="Yüzde")
                
                tld_tree.column("tld", width=100, anchor=tk.W)
                tld_tree.column("count", width=100, anchor=tk.E)
                tld_tree.column("percent", width=100, anchor=tk.E)
                
                # TLD scrollbar
                tld_scroll = ttk.Scrollbar(tld_frame, orient="vertical", command=tld_tree.yview)
                tld_tree.configure(yscrollcommand=tld_scroll.set)
                
                tld_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                tld_scroll.pack(side=tk.RIGHT, fill=tk.Y)
                
                # TLD verilerini doldur
                for tld, count in tld_result:
                    percent = (count / record_count) * 100 if record_count > 0 else 0
                    tld_tree.insert("", tk.END, values=(tld, f"{count:,}", f"%{percent:.2f}"))
                
                # Domain Dağılımı sekmesi
                domain_frame = ttk.Frame(notebook, padding=10)
                notebook.add(domain_frame, text="Domain Dağılımı")
                
                # Domain başlık
                ttk.Label(domain_frame, text="En Çok Kullanılan Domain'ler", 
                         font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))
                
                # Domain tablo
                domain_tree = ttk.Treeview(domain_frame, columns=("domain", "count", "percent"), show="headings", height=10)
                domain_tree.heading("domain", text="Domain")
                domain_tree.heading("count", text="Sayı")
                domain_tree.heading("percent", text="Yüzde")
                
                domain_tree.column("domain", width=250, anchor=tk.W)
                domain_tree.column("count", width=100, anchor=tk.E)
                domain_tree.column("percent", width=100, anchor=tk.E)
                
                # Domain scrollbar
                domain_scroll = ttk.Scrollbar(domain_frame, orient="vertical", command=domain_tree.yview)
                domain_tree.configure(yscrollcommand=domain_scroll.set)
                
                domain_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                domain_scroll.pack(side=tk.RIGHT, fill=tk.Y)
                
                # Domain verilerini doldur
                for domain, count in domain_result:
                    percent = (count / record_count) * 100 if record_count > 0 else 0
                    domain_tree.insert("", tk.END, values=(domain, f"{count:,}", f"%{percent:.2f}"))
                
                # Protokol Dağılımı sekmesi
                protocol_frame = ttk.Frame(notebook, padding=10)
                notebook.add(protocol_frame, text="Protokol Dağılımı")
                
                # Protokol başlık
                ttk.Label(protocol_frame, text="Protokol Dağılımı", 
                         font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))
                
                # Protokol tablo
                protocol_tree = ttk.Treeview(protocol_frame, columns=("protocol", "count", "percent"), show="headings", height=10)
                protocol_tree.heading("protocol", text="Protokol")
                protocol_tree.heading("count", text="Sayı")
                protocol_tree.heading("percent", text="Yüzde")
                
                protocol_tree.column("protocol", width=100, anchor=tk.W)
                protocol_tree.column("count", width=100, anchor=tk.E)
                protocol_tree.column("percent", width=100, anchor=tk.E)
                
                # Protokol scrollbar
                protocol_scroll = ttk.Scrollbar(protocol_frame, orient="vertical", command=protocol_tree.yview)
                protocol_tree.configure(yscrollcommand=protocol_scroll.set)
                
                protocol_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                protocol_scroll.pack(side=tk.RIGHT, fill=tk.Y)
                
                # Protokol verilerini doldur
                for protocol, count in protocol_result:
                    percent = (count / record_count) * 100 if record_count > 0 else 0
                    protocol_tree.insert("", tk.END, values=(protocol, f"{count:,}", f"%{percent:.2f}"))
                
                # SQL Sorguları sekmesi
                sql_frame = ttk.Frame(notebook, padding=10)
                notebook.add(sql_frame, text="SQL Sorguları")
                
                # SQL başlık
                ttk.Label(sql_frame, text="Kullanılan SQL Sorguları", 
                         font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))
                
                # SQL metin alanı
                sql_text = scrolledtext.ScrolledText(sql_frame, wrap=tk.WORD, width=80, height=20)
                sql_text.pack(fill=tk.BOTH, expand=True)
                
                # SQL sorgularını ekle
                sql_queries = [
                    ("Ana İstatistikler:", size_query),
                    ("TLD Dağılımı:", tld_query),
                    ("Domain Dağılımı:", domain_query),
                    ("Protokol Dağılımı:", protocol_query),
                    ("Android Token İstatistiği:", android_query),
                    ("Zaman İstatistikleri:", time_query),
                    ("Kimlik Bilgisi İstatistiği:", auth_query)
                ]
                
                for title, query in sql_queries:
                    sql_text.insert(tk.END, f"\n{title}\n\n")
                    sql_text.insert(tk.END, f"{query}\n")
                    sql_text.insert(tk.END, "-" * 80 + "\n")
                
                sql_text.configure(state="disabled")
                
                # Alt bilgi
                footer_frame = ttk.Frame(top, padding=(10, 0, 10, 10))
                footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
                
                ttk.Button(footer_frame, text="Kapat", command=top.destroy).pack(side=tk.RIGHT)
                ttk.Label(footer_frame, text="MicroLogParser Veritabanı İstatistikleri", 
                         font=("Arial", 8, "italic")).pack(side=tk.LEFT)
                
            else:
                messagebox.showinfo("Bilgi", "İstatistik bilgisi alınamadı.")
        except Exception as e:
            messagebox.showerror("Hata", f"İstatistikler alınırken hata oluştu: {str(e)}")
    
    def show_tld_stats(self):
        """TLD istatistiklerini göster"""
        try:
            stats = self.search_engine.get_tld_stats(limit=20)
            
            if stats:
                # Yeni pencere oluştur
                top = tk.Toplevel(self.root)
                top.title("TLD İstatistikleri")
                top.geometry("500x400")
                
                # Treeview oluştur
                frame = ttk.Frame(top, padding="10")
                frame.pack(fill=tk.BOTH, expand=True)
                
                tree = ttk.Treeview(frame, columns=("tld", "count"), show="headings")
                tree.heading("tld", text="TLD")
                tree.heading("count", text="Sayı")
                tree.column("tld", width=150)
                tree.column("count", width=100)
                tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                
                # Scrollbar ekle
                scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                tree.configure(yscrollcommand=scrollbar.set)
                
                # Verileri ekle
                for tld, count in stats:
                    tree.insert("", tk.END, values=(tld, count))
            else:
                messagebox.showinfo("Bilgi", "TLD istatistikleri bulunamadı.")
        except Exception as e:
            messagebox.showerror("Hata", f"TLD istatistikleri alınırken hata oluştu: {str(e)}")

    def show_domain_tld_combinations(self):
        """En çok kullanılan domain-TLD kombinasyonlarını göster"""
        try:
            combinations = self.search_engine.get_domain_tld_combinations(limit=50)
            
            if combinations:
                # Yeni pencere oluştur
                top = tk.Toplevel(self.root)
                top.title("Domain-TLD Kombinasyonları")
                top.geometry("600x500")
                
                # Treeview oluştur
                frame = ttk.Frame(top, padding="10")
                frame.pack(fill=tk.BOTH, expand=True)
                
                tree = ttk.Treeview(frame, columns=("domain", "tld", "count"), show="headings")
                tree.heading("domain", text="Domain")
                tree.heading("tld", text="TLD")
                tree.heading("count", text="Sayı")
                tree.column("domain", width=200)
                tree.column("tld", width=100)
                tree.column("count", width=80)
                tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                
                # Scrollbar ekle
                scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                tree.configure(yscrollcommand=scrollbar.set)
                
                # Verileri ekle
                for domain, tld, count in combinations:
                    tree.insert("", tk.END, values=(domain, tld, count))
                    
                # Arama düğmeleri için alt panel
                button_frame = ttk.Frame(top, padding="10")
                button_frame.pack(fill=tk.X)
                
                def search_selected():
                    selection = tree.selection()
                    if selection:
                        item = tree.item(selection[0])
                        domain, tld, _ = item["values"]
                        
                        # Ana pencerede aramayı ayarla ve gerçekleştir
                        self.set_preset_search("domain", "=", domain)
                        
                        # TLD araması da ekle
                        for field in self.search_fields:
                            if field["name"] == "tld":
                                field["operator_var"].set("=")
                                field["value_var"].set(tld)
                                break
                        
                        self.perform_search()
                        top.destroy()
                
                def show_urls():
                    selection = tree.selection()
                    if selection:
                        item = tree.item(selection[0])
                        domain, tld, _ = item["values"]
                        self.show_urls_for_domain_tld(domain, tld)
                
                ttk.Button(button_frame, text="Seçili Kombinasyonu Ara", 
                         command=search_selected).pack(side=tk.LEFT, padx=5)
                ttk.Button(button_frame, text="URL'leri Göster", 
                         command=show_urls).pack(side=tk.LEFT, padx=5)
            else:
                messagebox.showinfo("Bilgi", "Domain-TLD kombinasyonları bulunamadı.")
        except Exception as e:
            messagebox.showerror("Hata", f"Domain-TLD kombinasyonları alınırken hata oluştu: {str(e)}")
            
    def show_tld_growth(self):
        """TLD büyüme analizini göster"""
        # Gün sayısını seçmek için dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("TLD Büyüme Analizi")
        dialog.geometry("300x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Input alanları
        ttk.Label(dialog, text="Gün sayısı:").grid(row=0, column=0, padx=10, pady=10)
        days_var = tk.StringVar(value="30")
        days_entry = ttk.Entry(dialog, textvariable=days_var, width=10)
        days_entry.grid(row=0, column=1, padx=10, pady=10)
        
        ttk.Label(dialog, text="Gösterilecek TLD sayısı:").grid(row=1, column=0, padx=10, pady=10)
        limit_var = tk.StringVar(value="10")
        limit_entry = ttk.Entry(dialog, textvariable=limit_var, width=10)
        limit_entry.grid(row=1, column=1, padx=10, pady=10)
        
        def on_submit():
            try:
                days = int(days_var.get())
                limit = int(limit_var.get())
                dialog.destroy()
                self._show_tld_growth_results(days, limit)
            except ValueError:
                messagebox.showerror("Hata", "Lütfen geçerli sayılar girin.")
        
        ttk.Button(dialog, text="Analiz Et", command=on_submit).grid(row=2, column=0, columnspan=2, pady=10)
        
    def _show_tld_growth_results(self, days, limit):
        """TLD büyüme sonuçlarını göster"""
        try:
            growth_data = self.search_engine.get_tld_growth(days, limit)
            
            if growth_data:
                # Yeni pencere oluştur
                top = tk.Toplevel(self.root)
                top.title(f"TLD Büyüme Analizi (Son {days} gün)")
                top.geometry("700x500")
                
                # Treeview oluştur
                frame = ttk.Frame(top, padding="10")
                frame.pack(fill=tk.BOTH, expand=True)
                
                tree = ttk.Treeview(frame, columns=("tld", "recent", "old", "growth"), show="headings")
                tree.heading("tld", text="TLD")
                tree.heading("recent", text=f"Son {days} Gün")
                tree.heading("old", text="Önceki Dönem")
                tree.heading("growth", text="Büyüme")
                tree.column("tld", width=150)
                tree.column("recent", width=100)
                tree.column("old", width=100)
                tree.column("growth", width=100)
                tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                
                # Scrollbar ekle
                scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                tree.configure(yscrollcommand=scrollbar.set)
                
                # Verileri ekle
                for tld, recent, old, growth in growth_data:
                    tree.insert("", tk.END, values=(tld, recent, old, growth))
                    
                # Açıklama metni
                text_frame = ttk.Frame(top, padding="10")
                text_frame.pack(fill=tk.X)
                
                info_text = f"""
                Bu analiz, son {days} gün içinde en hızlı büyüyen TLD'leri göstermektedir.
                'Son {days} Gün' sütunu son dönemde görülen kayıt sayısını,
                'Önceki Dönem' sütunu daha önceki dönemde görülen kayıt sayısını,
                'Büyüme' sütunu ise iki dönem arasındaki farkı gösterir.
                """
                
                text = tk.Text(text_frame, wrap=tk.WORD, height=5)
                text.pack(fill=tk.X)
                text.insert("1.0", info_text)
                text.config(state=tk.DISABLED)
                
                # TLD'yi aramak için düğme
                def search_tld():
                    selection = tree.selection()
                    if selection:
                        item = tree.item(selection[0])
                        tld = item["values"][0]
                        self.set_preset_search("tld", "=", tld)
                        top.destroy()
                
                ttk.Button(text_frame, text="Seçili TLD'yi Ara", 
                          command=search_tld).pack(pady=5)
            else:
                messagebox.showinfo("Bilgi", "TLD büyüme verisi bulunamadı.")
        except Exception as e:
            messagebox.showerror("Hata", f"TLD büyüme analizi yapılırken hata oluştu: {str(e)}")
    
    def show_domain_by_tld(self):
        """TLD'ye göre domain analizini göster"""
        # TLD seçmek için dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("TLD Seçin")
        dialog.geometry("300x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # TLD'leri listele
        ttk.Label(dialog, text="TLD Seçin:").pack(pady=5)
        
        # Listbox ve scrollbar
        frame = ttk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        listbox = tk.Listbox(frame)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        listbox.configure(yscrollcommand=scrollbar.set)
        
        # TLD'leri al
        tlds = self.search_engine.get_distinct_values('tld')
        for tld in tlds:
            if tld:
                listbox.insert(tk.END, tld)
        
        def on_select():
            selection = listbox.curselection()
            if selection:
                tld = listbox.get(selection[0])
                dialog.destroy()
                self._show_domains_for_tld(tld)
        
        ttk.Button(dialog, text="Seç", command=on_select).pack(pady=10)
    
    def _show_domains_for_tld(self, tld):
        """Belirli bir TLD için domainleri göster"""
        try:
            domains = self.search_engine.get_domain_stats_by_tld(tld)
            
            if domains:
                # Yeni pencere oluştur
                top = tk.Toplevel(self.root)
                top.title(f"'{tld}' TLD'si İçin Domain Analizi")
                top.geometry("500x500")
                
                # Treeview oluştur
                frame = ttk.Frame(top, padding="10")
                frame.pack(fill=tk.BOTH, expand=True)
                
                tree = ttk.Treeview(frame, columns=("domain", "count"), show="headings")
                tree.heading("domain", text="Domain")
                tree.heading("count", text="Sayı")
                tree.column("domain", width=300)
                tree.column("count", width=100)
                tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                
                # Scrollbar ekle
                scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                tree.configure(yscrollcommand=scrollbar.set)
                
                # Verileri ekle
                for domain, count in domains:
                    tree.insert("", tk.END, values=(domain, count))
                    
                # Arama düğmeleri için alt panel
                button_frame = ttk.Frame(top, padding="10")
                button_frame.pack(fill=tk.X)
                
                def search_domain():
                    selection = tree.selection()
                    if selection:
                        item = tree.item(selection[0])
                        domain = item["values"][0]
                        
                        # Ana pencerede aramayı ayarla ve gerçekleştir
                        self.set_preset_search("domain", "=", domain)
                        
                        # TLD araması da ekle
                        for field in self.search_fields:
                            if field["name"] == "tld":
                                field["operator_var"].set("=")
                                field["value_var"].set(tld)
                                break
                        
                        self.perform_search()
                        top.destroy()
                
                def show_urls():
                    selection = tree.selection()
                    if selection:
                        item = tree.item(selection[0])
                        domain = item["values"][0]
                        self.show_urls_for_domain_tld(domain, tld)
                
                ttk.Button(button_frame, text="Seçili Domain'i Ara", 
                          command=search_domain).pack(side=tk.LEFT, padx=5)
                ttk.Button(button_frame, text="URL'leri Göster", 
                          command=show_urls).pack(side=tk.LEFT, padx=5)
            else:
                messagebox.showinfo("Bilgi", f"'{tld}' TLD'si için domain bulunamadı.")
        except Exception as e:
            messagebox.showerror("Hata", f"Domain analizi yapılırken hata oluştu: {str(e)}")
    
    def show_urls_for_domain_tld(self, domain, tld):
        """Belirli bir domain ve TLD için URL'leri göster"""
        try:
            # SQL sorgusunu URL, kullanıcı adı ve şifre içerecek şekilde güncelle
            headers, urls = self.search_engine.get_urls_by_domain_tld(domain, tld, limit=200)
            
            if urls:
                # Yeni pencere oluştur
                top = tk.Toplevel(self.root)
                top.title(f"URL'ler: {domain}.{tld}")
                top.geometry("900x600")
                
                # Bilgi başlığı
                info_label = ttk.Label(top, text=f"{domain}.{tld} için bulunan URL'ler", font=("Arial", 12, "bold"))
                info_label.pack(pady=(10, 5))
                
                # Treeview oluştur
                frame = ttk.Frame(top, padding="10")
                frame.pack(fill=tk.BOTH, expand=True)
                
                # Görüntülenecek sütunları belirle
                display_columns = ["full_url", "username", "password"]
                
                # Treeview tanımla
                tree = ttk.Treeview(frame, columns=display_columns, show="headings")
                
                # Sütun başlıkları ve genişlikleri
                column_config = {
                    "full_url": {"title": "URL", "width": 600, "anchor": tk.W},
                    "username": {"title": "Kullanıcı Adı", "width": 150, "anchor": tk.W},
                    "password": {"title": "Şifre", "width": 150, "anchor": tk.W}
                }
                
                # Sütunları yapılandır
                for col in display_columns:
                    if col in column_config:
                        tree.heading(col, text=column_config[col]["title"])
                        tree.column(col, width=column_config[col]["width"], anchor=column_config[col]["anchor"])
                    else:
                        tree.heading(col, text=col.capitalize())
                        tree.column(col, width=150, anchor=tk.W)
                
                # Dikey scrollbar
                vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
                vsb.pack(side=tk.RIGHT, fill=tk.Y)
                tree.configure(yscrollcommand=vsb.set)
                
                # Yatay scrollbar
                hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
                hsb.pack(side=tk.BOTTOM, fill=tk.X)
                tree.configure(xscrollcommand=hsb.set)
                
                tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                
                # Verileri ekle
                credential_count = 0
                export_data = []
                
                for row in urls:
                    # Gerekli sütun indekslerini bul
                    full_url_idx = headers.index("full_url") if "full_url" in headers else -1
                    username_idx = headers.index("username") if "username" in headers else -1
                    password_idx = headers.index("password") if "password" in headers else -1
                    
                    # Değerleri al
                    full_url = row[full_url_idx] if full_url_idx >= 0 and full_url_idx < len(row) else ""
                    username = row[username_idx] if username_idx >= 0 and username_idx < len(row) else ""
                    password = row[password_idx] if password_idx >= 0 and password_idx < len(row) else ""
                    
                    # Dışa aktarma için veri sakla
                    export_data.append({"url": full_url, "username": username, "password": password})
                    
                    # Satırı ekle
                    values = (full_url, username, password)
                    item_id = tree.insert("", tk.END, values=values)
                    
                    # Kimlik bilgisi varsa satırı vurgula
                    if username or password:
                        tree.item(item_id, tags=('credentials',))
                        credential_count += 1
                    elif "admin" in str(full_url).lower() or "login" in str(full_url).lower() or "panel" in str(full_url).lower():
                        tree.item(item_id, tags=('important',))
                    else:
                        tree.item(item_id, tags=('normal',))
                
                # Stiller tanımla
                tree.tag_configure('credentials', background='#FFFF99', foreground='#000000')
                tree.tag_configure('important', background='#E8F5E9', foreground='#000000')
                tree.tag_configure('normal', background='#FFFFFF')
                
                # Butonlar için frame
                button_frame = ttk.Frame(top, padding="10")
                button_frame.pack(fill=tk.X)
                
                # Kopyalama fonksiyonları
                def copy_url():
                    selection = tree.selection()
                    if selection:
                        item = tree.item(selection[0])
                        url = item["values"][0]
                        top.clipboard_clear()
                        top.clipboard_append(url)
                        messagebox.showinfo("Kopyalandı", "URL panoya kopyalandı.")
                
                def copy_credentials():
                    selection = tree.selection()
                    if selection:
                        item = tree.item(selection[0])
                        values = item["values"]
                        url = values[0] if len(values) > 0 else ""
                        username = values[1] if len(values) > 1 else ""
                        password = values[2] if len(values) > 2 else ""
                        
                        if username or password:
                            credentials_text = f"URL: {url}\nKullanıcı Adı: {username}\nŞifre: {password}"
                            top.clipboard_clear()
                            top.clipboard_append(credentials_text)
                            messagebox.showinfo("Kopyalandı", "Kimlik bilgileri panoya kopyalandı.")
                        else:
                            messagebox.showinfo("Bilgi", "Bu kaydın kimlik bilgileri bulunmamaktadır.")
                
                # Dışa aktarma fonksiyonları
                def export_to_txt():
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = filedialog.asksaveasfilename(
                        defaultextension=".txt",
                        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                        initialfile=f"{domain}_{tld}_export_{timestamp}.txt"
                    )
                    
                    if filename:
                        try:
                            with open(filename, 'w', encoding='utf-8') as f:
                                f.write(f"Domain: {domain}.{tld}\n")
                                f.write(f"Toplam URL: {len(export_data)}\n")
                                f.write(f"Kimlik Bilgisi Olan: {credential_count}\n")
                                f.write("-" * 80 + "\n\n")
                                
                                for item in export_data:
                                    f.write(f"URL: {item['url']}\n")
                                    if item['username']:
                                        f.write(f"Kullanıcı Adı: {item['username']}\n")
                                    if item['password']:
                                        f.write(f"Şifre: {item['password']}\n")
                                    f.write("-" * 80 + "\n")
                            messagebox.showinfo("Başarılı", f"Sonuçlar başarıyla dışa aktarıldı:\n{filename}")
                        except Exception as e:
                            messagebox.showerror("Hata", f"Dışa aktarma sırasında hata oluştu: {str(e)}")
                
                def export_to_csv():
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = filedialog.asksaveasfilename(
                        defaultextension=".csv",
                        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                        initialfile=f"{domain}_{tld}_export_{timestamp}.csv"
                    )
                    
                    if filename:
                        try:
                            import csv
                            with open(filename, 'w', encoding='utf-8', newline='') as f:
                                writer = csv.writer(f)
                                writer.writerow(["URL", "Kullanıcı Adı", "Şifre"])
                                for item in export_data:
                                    writer.writerow([item['url'], item['username'], item['password']])
                            messagebox.showinfo("Başarılı", f"Sonuçlar başarıyla dışa aktarıldı:\n{filename}")
                        except Exception as e:
                            messagebox.showerror("Hata", f"Dışa aktarma sırasında hata oluştu: {str(e)}")
                
                def export_to_json():
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = filedialog.asksaveasfilename(
                        defaultextension=".json",
                        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                        initialfile=f"{domain}_{tld}_export_{timestamp}.json"
                    )
                    
                    if filename:
                        try:
                            export_obj = {
                                "domain": domain,
                                "tld": tld,
                                "total": len(export_data),
                                "with_credentials": credential_count,
                                "data": export_data
                            }
                            with open(filename, 'w', encoding='utf-8') as f:
                                json.dump(export_obj, f, ensure_ascii=False, indent=2)
                            messagebox.showinfo("Başarılı", f"Sonuçlar başarıyla dışa aktarıldı:\n{filename}")
                        except Exception as e:
                            messagebox.showerror("Hata", f"Dışa aktarma sırasında hata oluştu: {str(e)}")
                
                def export_to_ulp():
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = filedialog.asksaveasfilename(
                        defaultextension=".txt",
                        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                        initialfile=f"{domain}_{tld}_ulp_{timestamp}.txt"
                    )
                    
                    if filename:
                        try:
                            with open(filename, 'w', encoding='utf-8') as f:
                                for item in export_data:
                                    if item['url'] and (item['username'] or item['password']):
                                        f.write(f"{item['url']}:{item['username']}:{item['password']}\n")
                            messagebox.showinfo("Başarılı", f"ULP formatında dışa aktarıldı:\n{filename}")
                        except Exception as e:
                            messagebox.showerror("Hata", f"Dışa aktarma sırasında hata oluştu: {str(e)}")
                
                def export_to_combo():
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = filedialog.asksaveasfilename(
                        defaultextension=".txt",
                        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                        initialfile=f"{domain}_{tld}_combo_{timestamp}.txt"
                    )
                    
                    if filename:
                        try:
                            with open(filename, 'w', encoding='utf-8') as f:
                                for item in export_data:
                                    if item['username'] or item['password']:
                                        f.write(f"{item['username']}:{item['password']}\n")
                            messagebox.showinfo("Başarılı", f"Combo formatında dışa aktarıldı:\n{filename}")
                        except Exception as e:
                            messagebox.showerror("Hata", f"Dışa aktarma sırasında hata oluştu: {str(e)}")
                
                # Sol taraftaki butonlar
                left_buttons = ttk.Frame(button_frame)
                left_buttons.pack(side=tk.LEFT)
                
                ttk.Button(left_buttons, text="URL'yi Kopyala", command=copy_url).pack(side=tk.LEFT, padx=5)
                ttk.Button(left_buttons, text="Kimlik Bilgilerini Kopyala", command=copy_credentials).pack(side=tk.LEFT, padx=5)
                
                # Dışa aktarma butonları
                export_buttons = ttk.Frame(button_frame)
                export_buttons.pack(side=tk.LEFT, padx=20)
                
                ttk.Label(export_buttons, text="Dışa Aktar:").pack(side=tk.LEFT, padx=(0, 5))
                ttk.Button(export_buttons, text="TXT", command=export_to_txt).pack(side=tk.LEFT, padx=2)
                ttk.Button(export_buttons, text="CSV", command=export_to_csv).pack(side=tk.LEFT, padx=2)
                ttk.Button(export_buttons, text="JSON", command=export_to_json).pack(side=tk.LEFT, padx=2)
                ttk.Button(export_buttons, text="ULP", command=export_to_ulp).pack(side=tk.LEFT, padx=2)
                ttk.Button(export_buttons, text="COMBO", command=export_to_combo).pack(side=tk.LEFT, padx=2)
                
                # Kapat butonu
                ttk.Button(button_frame, text="Kapat", command=top.destroy).pack(side=tk.RIGHT, padx=5)
                
                # Status bilgisi
                status_frame = ttk.Frame(top)
                status_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
                
                status_label = ttk.Label(
                    status_frame, 
                    text=f"Toplam: {len(urls)} URL | Kimlik Bilgisi Olan: {credential_count}", 
                    relief=tk.SUNKEN, 
                    anchor=tk.W, 
                    padding=(5, 2)
                )
                status_label.pack(fill=tk.X)
                
                # Çift tıklama olayı
                def on_double_click(event):
                    region = tree.identify("region", event.x, event.y)
                    if region == "heading":
                        return  # Başlık üzerindeki çift tıklamaları yoksay
                        
                    item = tree.identify('item', event.x, event.y)
                    if item:
                        # URL'yi panoya kopyala
                        selected_item = tree.item(item)
                        values = selected_item["values"]
                        url = values[0] if len(values) > 0 else ""
                        username = values[1] if len(values) > 1 else ""
                        password = values[2] if len(values) > 2 else ""
                        
                        if username or password:
                            credentials_text = f"URL: {url}\nKullanıcı Adı: {username}\nŞifre: {password}"
                            top.clipboard_clear()
                            top.clipboard_append(credentials_text)
                            # Status'u güncelle
                            status_label.config(text=f"Kimlik bilgileri kopyalandı!")
                        else:
                            # Sadece URL'yi kopyala
                            top.clipboard_clear()
                            top.clipboard_append(url)
                            # Status'u güncelle
                            status_label.config(text=f"URL kopyalandı: {url}")
                        
                        # 3 saniye sonra status'u normal haline döndür
                        top.after(3000, lambda: status_label.config(
                            text=f"Toplam: {len(urls)} URL | Kimlik Bilgisi Olan: {credential_count}"
                        ))
                
                tree.bind("<Double-1>", on_double_click)
                
            else:
                messagebox.showinfo("Bilgi", f"'{domain}.{tld}' için URL bulunamadı.")
        except Exception as e:
            messagebox.showerror("Hata", f"URL'ler alınırken hata oluştu: {str(e)}")

    def show_help(self):
        """Yardım bilgisini göster"""
        help_text = """
        Veritabanı Arama Uygulaması Kullanımı:
        
        1. Arama yapmak için soldaki alanları kullanabilirsiniz.
        2. Her alan için operatör seçebilir ve değer girebilirsiniz.
        3. "Değerler" düğmesine tıklayarak mevcut değerleri görebilirsiniz.
        4. "Ara" düğmesi ile aramayı gerçekleştirebilirsiniz.
        5. "Temizle" düğmesi ile arama kriterlerini sıfırlayabilirsiniz.
        6. SQL sorgusu üst kısımda gösterilir.
        
        Operatörler:
        - LIKE: İçinde geçen metni arar (ILIKE kullanılır, büyük/küçük harf duyarsız)
        - =, !=, >, <: Standart karşılaştırma operatörleri
        - STARTS WITH: Belirli bir metin ile başlayanları arar
        - ENDS WITH: Belirli bir metin ile bitenleri arar
        - IS NULL, IS NOT NULL: Boş veya dolu alanları arar
        - IN, NOT IN: Virgülle ayrılmış değerler listesinde olanları/olmayanları arar
        - DOMAIN+TLD: domain.tld formatında girilen değeri domain ve tld alanlarında arar
        
        TLD Analiz Menüsü:
        - TLD İstatistikleri: En çok kullanılan TLD'leri gösterir
        - En Çok Kullanılan Domain-TLD: En popüler domain-TLD kombinasyonlarını gösterir
        - TLD Büyüme Analizi: Belirli bir zaman diliminde en hızlı büyüyen TLD'leri gösterir
        - TLD'ye Göre Domain Analizi: Belirli bir TLD için en popüler domainleri gösterir
        
        İpucu: Birçok pencerede seçtiğiniz değerleri aramak için düğmeler bulunmaktadır.
        Doğrudan bir URL'yi görmek isterseniz, domain-TLD kombinasyonlarında veya
        domain analizinde "URL'leri Göster" düğmesini kullanabilirsiniz.
        """
        
        # Yeni pencere oluştur
        top = tk.Toplevel(self.root)
        top.title("Yardım")
        top.geometry("600x500")
        
        text = tk.Text(top, wrap=tk.WORD, padx=10, pady=10)
        text.pack(fill=tk.BOTH, expand=True)
        text.insert("1.0", help_text)
        text.config(state=tk.DISABLED)
        
    def show_about(self):
        """Hakkında bilgisini göster"""
        about_text = """
        MicroLogParser Veritabanı Arama Uygulaması
        Sürüm: 1.1
        
        Bu uygulama, MicroLogParser ile toplanan URL kayıtlarını aramak 
        ve analiz etmek için tasarlanmıştır.
        
        PostgreSQL veritabanında depolanan log kayıtlarını sorgulayabilir,
        veritabanı istatistiklerini görüntüleyebilir ve TLD analizleri 
        yapabilirsiniz.
        
        Yeni Özellikler (v1.1):
        - Gelişmiş TLD analiz ve istatistik araçları
        - Domain-TLD kombinasyonları analizi
        - TLD büyüme trendleri
        - Belirli domain-TLD kombinasyonları için URL listesi
        - IN ve NOT IN operatörleri ile çoklu değer araması
        - DOMAIN+TLD operatörü ile birleşik arama
        """
        
        messagebox.showinfo("Hakkında", about_text)

# ========================
# Ana Program
# ========================
if __name__ == "__main__":
    root = tk.Tk()
    
    # Veritabanı bağlantısı oluştur
    db_conn = DatabaseConnection()
    if not db_conn.connect():
        messagebox.showerror("Bağlantı Hatası", "Veritabanına bağlanılamadı.\nLütfen db_config.ini dosyasını kontrol edin.")
        sys.exit(1)
    
    # Arama motoru oluştur
    search_engine = SearchEngine(db_conn)
    
    # GUI oluştur
    app = DatabaseSearchGUI(root, search_engine)
    
    # Uygulama kapatıldığında bağlantıyı kapat
    def on_closing():
        db_conn.close()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop() 
