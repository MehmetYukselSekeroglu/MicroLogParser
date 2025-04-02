# MicroLogParser

**Yazar ve geliştirici: Mehmet Yüksel Şekeroğlu**

**Son güncelleme: 2 Nisan 2025**

MicroLogParser, URL ve kullanıcı/parola alanları içeren satırları ayrıştıran,
PostgreSQL için SQL çıktısı üreten ve kayıtları Tkinter arayüzüyle sorgulayan bir
C++ / Python projesidir. Bu depodaki kullanım örnekleri sentetiktir; gerçek log,
veritabanı dökümü veya erişim bilgisi dağıtılmaz.

## Özellikler

- URL bileşenlerini protokol, domain, subdomain, TLD, port, yol ve sorguya ayırma.
- Türkçe ve bazı çok seviyeli alan adı uzantıları için ayrıştırma kuralları.
- Android uygulama adresleri ve farklı satır ayırıcıları için işleme dalları.
- C++ ve Python tarafında iş parçacıklı SQL üretimi.
- PostgreSQL kayıtları için arama, istatistik ve dışa aktarma arayüzü.
- SQL metnindeki bazı özel karakterleri düzenleyen `fix_sql.py` yardımcısı.

## Dizinler ve dosyalar

| Yol | Görev |
| --- | --- |
| `cpp/main.cpp` | C++ toplu işleme komut satırı aracı |
| `cpp/lib/prepare_url.hpp` | C++ URL ayrıştırıcı |
| `cpp/lib/line_proccess_ULP.hpp` | Satır formatlarını ayrıştırma |
| `cpp/test*.cpp`, `cpp/extended_test.cpp` | Ayrıştırıcı denemeleri |
| `cpp/benchmark.cpp` | Performans ölçüm yardımcısı |
| `python/main.py` | Python SQL üretim aracı |
| `python/UrlParser.py` | Python URL ayrıştırıcı |
| `python/LineProccesser_ULP.py` | Python satır ayrıştırıcı |
| `db_search.py` | PostgreSQL / Tkinter arama arayüzü |
| `schema.sql` | Tablolar ve indeksler |
| `fix_sql.py` | SQL düzeltme yardımcısı |
| `examples/synthetic.sample` | Yalnızca sentetik örnek satırlar |
| `.env.example` | Parola içermeyen ortam değişkeni şablonu |

## Python ile başlama

Komutları depo kökünden çalıştırın. GUI için Tkinter sistemde kurulu olmalıdır;
PostgreSQL bağlantısı için `psycopg2` gerekir. Ayrıştırıcı Python standart
kütüphanesini kullanır.

```bash
git clone https://github.com/MehmetYukselSekeroglu/MicroLogParser.git
cd MicroLogParser
python3 -m venv .venv
source .venv/bin/activate
python -m pip install psycopg2-binary
python python/main.py --help
python python/main.py --input examples/synthetic.sample --output output.sql --threads 2
```

`output.sql` üretilmiş veridir ve Git tarafından yok sayılır. Bu komut bir
PostgreSQL sunucusuna otomatik veri yüklemez.

## C++ ile derleme

C++17 derleyicisi, Poco Net/Foundation başlıkları ve kütüphaneleri gerekir.
Depoda `CMakeLists.txt` bulunmadığından doğrudan derleme örneği:

```bash
mkdir -p cpp/build
g++ -std=c++17 -O2 -pthread cpp/main.cpp -o cpp/build/MicroLogParser -lPocoNet -lPocoFoundation
./cpp/build/MicroLogParser examples/synthetic.sample output.sql 2 5000
```

Parametreler sırasıyla giriş dosyası, çıktı dosyası, isteğe bağlı iş parçacığı sayısı
ve toplu yazma boyutudur. `cpp/build_and_test.sh`, eski CMake akışına bağlıdır;
mevcut depoda doğrudan çalışabilir bir tam derleme akışı olarak doğrulanmamıştır.
`cpp/lib/load_config.hpp` ayrıca nlohmann/json; bağlantı havuzu başlığı libpq kullanır.

## PostgreSQL ve arama arayüzü

Önceden oluşturulmuş yerel bir veritabanına şemayı uygulayın:

```bash
psql -h 127.0.0.1 -U postgres -d micrologparser -f schema.sql
```

Şemadaki trigram GIN indeksleri için PostgreSQL `pg_trgm` uzantısının kurulu olması
gerekebilir. Gerekli uzantı ve veritabanı yetkilerini kendi ortamınızda hazırlayın.

Arayüzün ilk bağlantı varsayılanları `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER` ve
`PGPASSWORD` ortam değişkenlerinden alınır. Varsayılan parola boştur. `.env.example`
yalnızca şablondur; uygulama `.env` dosyalarını kendiliğinden yüklemez.

```bash
export PGHOST=127.0.0.1
export PGPORT=5432
export PGDATABASE=micrologparser
export PGUSER=postgres
# Gerekiyorsa parolayı terminal geçmişine yazmadan alın:
read -rsp 'PostgreSQL parolası: ' PGPASSWORD; echo
export PGPASSWORD
python db_search.py
unset PGPASSWORD
```

Yerel `db_config.ini` mevcutsa içindeki `[PostgreSQL]` alanları ortam varsayılanlarını
geçersiz kılar. Dosya yoksa uygulama yapılandırmayı oluşturur. Bu dosya bağlantı
parolasını düz metin saklayabilir; yerel tutun ve erişimini sınırlayın. Depoya eklenmez.

Arayüz; URL alanlarını ve kullanıcı/parola alanlarını sorgulayabilir, sonuçları
TXT, CSV, JSON, ULP ve COMBO biçimlerinde dışa aktarabilir. Çıktılar kaynak verinin
hassas alanlarını koruyabilir; uygulama otomatik anonimleştirme yapmaz.

## Sentetik örnekler

```text
https://example.com/login SYNTHETIC_USER:SYNTHETIC_PASSWORD
https://sub.example.org:8080/path?q=demo|SYNTHETIC_USER|SYNTHETIC_PASSWORD
android://SYNTHETIC_TOKEN@com.example.app/:credentials SYNTHETIC_USER:SYNTHETIC_PASSWORD
```

Bu kullanıcı, parola ve token dizeleri hiçbir hesaba ait değildir. Testlerdeki
adresler ayrıştırma girdileridir; ağ bağlantısı gerektirmez. Gerçek kurum alan adını
andıran eski test örnekleri de `example` tabanlı girdilerle değiştirilmiştir.

## Kontroller ve bilinen sınırlar

- `test_special_chars.cpp` bağımsız derlenebilen özel karakter duman testidir.
- C++ ayrıştırıcı denemeleri Poco bağımlılığı gerektirir.
- Python ve C++ uygulamalarının her uç durumda aynı çıktıyı verdiği varsayılmaz.
- TLD ayrıştırma kuralları tam bir Public Suffix List uygulaması değildir.
- Python ayrıştırıcı başarısız girdileri `failed_lines.txt` dosyasına yazabilir.
- SQL üretimi, sorgu arayüzü ve dışa aktarmalar hassas veriyi otomatik maskelemez.
- Eski README'deki kaynağı doğrulanmamış hız, veri hacmi ve ölçeklenebilirlik
  tabloları kaldırılmıştır; burada bir performans garantisi verilmez.
- Yerel sözdizimi ve sentetik testler; canlı PostgreSQL, GUI veya tam Poco
  entegrasyon testinin yerine geçmez.

## Depo hijyeni

`.gitignore`; yerel yapılandırmaları, ortam dosyalarını, derleme çıktılarını,
ham logları ve üretilmiş SQL dosyalarını dışarıda tutar. Şema ve açıkça adlandırılmış
örnek şablonlar sürüm kontrolünde kalır. `.gitignore`, önceden eklenmiş dosyalardan
hassas veriyi çıkarmaz; commit öncesi içerik kontrolü ayrıca gerekir.

Gerçek erişim anahtarlarını, parolaları, özel anahtarları, ham veri kümelerini,
veritabanı yedeklerini veya ekran görüntülerindeki hassas kayıtları eklemeyin.

## Katkı ve telif

**Mehmet Yüksel Şekeroğlu**

Hata bildirimlerini sentetik bir örnek, beklenen çıktı ve ortam bilgisiyle açın.
Gerçek kullanıcı/parola verisi paylaşmayın.

© Mehmet Yüksel Şekeroğlu. Tüm hakları saklıdır.
Depoda ayrı bir açık kaynak lisansı bulunmamaktadır. Herkese açık erişim, tek
başına yeniden kullanım veya dağıtım lisansı sağlamaz.
