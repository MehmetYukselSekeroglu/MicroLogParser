# MicroLogParser C++ Edition

Yüksek performanslı, çok thread destekli log verileri ayrıştırıcı ve SQL dönüştürücü. Bu program, URL ve kimlik bilgilerini içeren log dosyalarını okur, ayrıştırır ve PostgreSQL tablosuna uygun SQL INSERT ifadeleri oluşturur.

## Özellikler

- Çok iş parçacıklı (multi-threaded) tasarım ile yüksek performans
- Bellek kullanımını optimize eden kuyruk tabanlı işleme
- Otomatik thread sayısı belirleme
- Toplu SQL yazma ile I/O performansını artırma
- İlerleme ve performans istatistikleri
- Farklı URL ve kimlik bilgisi formatlarını destekler

**Yazar: Mehmet Yüksel Şekeroğlu**
**Son güncelleme: 2 Nisan 2025**

## Derleme

C++17 ve Poco Net/Foundation gerekir. Depoda CMakeLists.txt bulunmaz.
Depo kökünden doğrudan derleme:

```bash
mkdir -p cpp/build
g++ -std=c++17 -O2 -pthread cpp/main.cpp -o cpp/build/MicroLogParser -lPocoNet -lPocoFoundation
./cpp/build/MicroLogParser examples/synthetic.sample output.sql 2 5000
```

Örnek girdiler sentetiktir; gerçek veri veya erişim bilgisi içermez.

## Kullanım

Program aşağıdaki parametrelerle çalıştırılır:

```bash
./MicroLogParser <input_file> <output_file> [threads] [batch_size]
```

Parametreler:
- `input_file`: İşlenecek log dosyası (gerekli)
- `output_file`: Oluşturulan SQL ifadelerinin yazılacağı dosya (gerekli)
- `threads`: İşleme iş parçacığı sayısı (opsiyonel, varsayılan: CPU çekirdek sayısı)
- `batch_size`: Toplu yazma için SQL ifade sayısı (opsiyonel, varsayılan: 5000)

Örnek:
```bash
./MicroLogParser logs.txt output.sql 8 10000
```

## Performans Optimizasyonları

- Çok iş parçacıklı (multi-threaded) mimari
- Verimli bellek yönetimi için thread-safe kuyruk yapısı
- Büyük tampon boyutları ile I/O performansı iyileştirmeleri
- SQL ifadelerinin toplu yazılması
- String işlemleri için önden bellek ayırma (memory reservation)
- Derleyici optimizasyonları (-O3, -march=native, vb.)

## Format Desteği

Aşağıdaki format tiplerini destekler:

- `URL username:password`
- `protocol:domain:username:password`
- `protocol:domain:port:username:password`
- `URL|username|password`
- `android://token@package_name/:credentials username:password`
- ve diğer varyasyonlar

## SQL Şeması

Oluşturulan SQL ifadeleri, aşağıdaki şemaya uygun bir PostgreSQL tablosuna ekleme yapar:

```sql
CREATE TABLE IF NOT EXISTS log (
    id BIGSERIAL PRIMARY KEY,
    android_token VARCHAR(100) DEFAULT NULL,
    android_package VARCHAR(100) DEFAULT NULL,
    protocol VARCHAR(10) NOT NULL DEFAULT 'http',
    subdomain VARCHAR(100) DEFAULT NULL,
    domain VARCHAR(100) DEFAULT NULL,
    port SMALLINT DEFAULT NULL,
    path VARCHAR(1000) DEFAULT NULL,
    path_etc VARCHAR(1000) DEFAULT NULL,
    query VARCHAR(1000) DEFAULT NULL,
    fragment VARCHAR(1000) DEFAULT NULL,
    username VARCHAR(100) DEFAULT NULL,
    password VARCHAR(100) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
``` 