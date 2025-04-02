#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <queue>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <atomic>
#include <chrono>
#include <filesystem>
#include <iomanip>
#include <unordered_map>
#include "lib/line_proccess_ULP.hpp"

// Thread-safe kuyruk yapısı
template <typename T>
class ThreadSafeQueue {
private:
    std::queue<T> queue;
    mutable std::mutex mutex;
    std::condition_variable cv;
    bool terminated = false;

public:
    void push(T item) {
        {
            std::lock_guard<std::mutex> lock(mutex);
            queue.push(std::move(item));
        }
        cv.notify_one();
    }

    bool pop(T& item, bool wait = true) {
        std::unique_lock<std::mutex> lock(mutex);
        
        if (wait) {
            cv.wait(lock, [this] { 
                return !queue.empty() || terminated; 
            });
        }
        
        if (queue.empty()) {
            return false;
        }
        
        item = std::move(queue.front());
        queue.pop();
        return true;
    }

    void terminate() {
        {
            std::lock_guard<std::mutex> lock(mutex);
            terminated = true;
        }
        cv.notify_all();
    }

    size_t size() const {
        std::lock_guard<std::mutex> lock(mutex);
        return queue.size();
    }

    bool empty() const {
        std::lock_guard<std::mutex> lock(mutex);
        return queue.empty();
    }
};

// Çalışma istatistikleri
struct WorkStats {
    std::atomic<uint64_t> total_lines{0};
    std::atomic<uint64_t> processed_lines{0};
    std::atomic<uint64_t> failed_lines{0};
    std::atomic<uint64_t> sql_statements{0};
    std::chrono::high_resolution_clock::time_point start_time;
    
    WorkStats() : start_time(std::chrono::high_resolution_clock::now()) {}
    
    double elapsed_seconds() const {
        auto now = std::chrono::high_resolution_clock::now();
        return std::chrono::duration<double>(now - start_time).count();
    }
    
    double lines_per_second() const {
        double seconds = elapsed_seconds();
        return seconds > 0 ? static_cast<double>(processed_lines) / seconds : 0;
    }
    
    double sql_per_second() const {
        double seconds = elapsed_seconds();
        return seconds > 0 ? static_cast<double>(sql_statements) / seconds : 0;
    }
    
    void print_stats() const {
        double seconds = elapsed_seconds();
        double progress = total_lines > 0 ? 
                         static_cast<double>(processed_lines) / total_lines * 100.0 : 0;
        
        std::cout << std::fixed << std::setprecision(2);
        std::cout << "İlerleme: " << processed_lines << "/" << total_lines 
                  << " satır (%" << progress << ")\n";
        std::cout << "Oluşturulan SQL: " << sql_statements << " ifade\n";
        std::cout << "Başarısız satırlar: " << failed_lines << "\n";
        std::cout << "Hız: " << lines_per_second() << " satır/sn, " 
                  << sql_per_second() << " SQL/sn\n";
        std::cout << "Geçen süre: " << seconds << " saniye\n";
        std::cout << "-------------------------------------------\n";
    }
};

// SQL değerini güvenli şekilde formatla
std::string format_sql_value(const std::string& value) {
    if (value.empty()) {
        return "NULL";
    }
    
    // Değerin başındaki ve sonundaki boşlukları temizle
    std::string trimmed_value = value;
    
    // Baştaki boşlukları atla
    size_t start = 0;
    while (start < trimmed_value.size() && std::isspace(trimmed_value[start])) {
        ++start;
    }
    
    // Sondaki boşlukları atla
    size_t end = trimmed_value.size();
    while (end > start && std::isspace(trimmed_value[end - 1])) {
        --end;
    }
    
    // Başındaki ve sonundaki boşlukları kırp
    trimmed_value = trimmed_value.substr(start, end - start);
    
    std::string escaped;
    escaped.reserve(trimmed_value.size() * 1.2); // Tahmini yer ayır
    
    escaped.push_back('\'');
    for (size_t i = 0; i < trimmed_value.size(); i++) {
        char c = trimmed_value[i];
        
        // PostgreSQL için zararlı olabilecek karakterleri işle
        if (c == '\'') {
            // PostgreSQL'de tek tırnak işareti çift tek tırnakla kaçırılır
            escaped.push_back('\'');
            escaped.push_back('\'');
        } else if (c == '\\') {
            // Ters eğik çizgi PostgreSQL'de sorun yaratabilir
            // PostgreSQL'de iki ters eğik çizgi bir ters eğik çizgi olarak yorumlanır
            escaped.push_back('\\');
            escaped.push_back('\\');
        } else if (c == '\r' || c == '\n' || c == '\t') {
            // Satır sonu karakterlerini (CR, LF) ve tab'ı boşluğa çevir
            escaped.push_back(' ');
        } else if (c == 0 || c == '\0') {
            // Null karakterleri atla
            continue;
        } else if ((unsigned char)c < 32 || (unsigned char)c > 126) {
            // Basılabilir olmayan ASCII ve yüksek ASCII karakterleri güvenle değiştir
            // ASCII 32 (space) ile 126 (~) arası yazdırılabilir karakterlerdir
            escaped.push_back('_');
        } else {
            escaped.push_back(c);
        }
    }
    escaped.push_back('\'');
    
    return escaped;
}

// Satırı işle ve SQL ifadesi oluştur
std::string process_line_to_sql(const std::string& line, WorkStats& stats) {
    auto result = processLine(line);
    
    if (!result) {
        stats.failed_lines++;
        return "";
    }
    
    stats.processed_lines++;
    
    // SQL ifadesi için değerleri hazırla
    std::unordered_map<std::string, std::string> sql_values;
    
    const auto& [protocol, main_domain, subdomain, tld, port, path, etc, username, password] = *result;
    
    sql_values["protocol"] = protocol;
    
    if (protocol == "android") {
        // Android için özel alanlar
        sql_values["android_token"] = subdomain;  // Android format için subdomain token içerir
        sql_values["android_package"] = main_domain;  // Android format için main_domain package içerir
        sql_values["domain"] = "";
        sql_values["subdomain"] = "";
        sql_values["tld"] = "";
        sql_values["port"] = "";
        sql_values["path"] = "";
        sql_values["path_etc"] = "";
    }
    else {
        // Normal URL formatı
        sql_values["android_token"] = "";
        sql_values["android_package"] = "";
        sql_values["domain"] = main_domain;
        sql_values["subdomain"] = subdomain;
        sql_values["tld"] = tld;
        sql_values["port"] = port;
        sql_values["path"] = path;
        sql_values["path_etc"] = etc;
    }
    
    // Query ve fragment bilgilerini ayır
    std::string query, fragment;
    
    if (!etc.empty()) {
        size_t query_pos = etc.find('?');
        size_t fragment_pos = etc.find('#');
        
        if (query_pos != std::string::npos) {
            if (fragment_pos != std::string::npos) {
                query = etc.substr(query_pos + 1, fragment_pos - (query_pos + 1));
                fragment = etc.substr(fragment_pos + 1);
            } else {
                query = etc.substr(query_pos + 1);
            }
        } else if (fragment_pos != std::string::npos) {
            fragment = etc.substr(fragment_pos + 1);
        }
    }
    
    sql_values["query"] = query;
    sql_values["fragment"] = fragment;
    sql_values["username"] = username;
    sql_values["password"] = password;
    
    // SQL ifadesini oluştur
    std::string columns, values;
    bool first = true;
    
    // Sütunları belirli bir sırada ekle (alfabetik değil)
    std::vector<std::string> ordered_keys = {
        "protocol", "domain", "subdomain", "tld", "port", "path", 
        "path_etc", "query", "fragment", "android_package", "android_token", 
        "username", "password"
    };
    
    for (const auto& key : ordered_keys) {
        auto it = sql_values.find(key);
        if (it != sql_values.end()) {
            if (!first) {
                columns += ", ";
                values += ", ";
            }
            columns += key;
            values += it->second.empty() ? "NULL" : format_sql_value(it->second);
            first = false;
        }
    }
    
    stats.sql_statements++;
    return "INSERT INTO log (" + columns + ") VALUES (" + values + ");";
}

// Satırları oku ve işleme kuyruğuna ekle
void reader_thread(const std::string& input_file, 
                  ThreadSafeQueue<std::string>& line_queue,
                  WorkStats& stats) {
    try {
        std::ifstream input(input_file, std::ios::in);
        
        if (!input) {
            std::cerr << "Error: Cannot open input file: " << input_file << std::endl;
            return;
        }
        
        // Okuma performansı için
        const size_t BUFFER_SIZE = 1024 * 1024; // 1 MB
        input.rdbuf()->pubsetbuf(new char[BUFFER_SIZE], BUFFER_SIZE);
        
        std::string line;
        line.reserve(1024); // Tipik satır boyu için rezerv
        
        while (std::getline(input, line)) {
            stats.total_lines++;
            line_queue.push(line);
        }
        
        std::cout << "Okuma tamamlandı: " << stats.total_lines << " satır okundu." << std::endl;
    }
    catch (const std::exception& e) {
        std::cerr << "Error in reader thread: " << e.what() << std::endl;
    }
    
    // İşlem bitti, kuyruğu sonlandır
    line_queue.terminate();
}

// Satırları işleyip SQL ifadeleri oluştur
void worker_thread(ThreadSafeQueue<std::string>& line_queue,
                  ThreadSafeQueue<std::string>& sql_queue,
                  WorkStats& stats) {
    try {
        std::string line;
        
        while (line_queue.pop(line)) {
            std::string sql = process_line_to_sql(line, stats);
            if (!sql.empty()) {
                sql_queue.push(sql);
            }
        }
    }
    catch (const std::exception& e) {
        std::cerr << "Error in worker thread: " << e.what() << std::endl;
    }
}

// SQL ifadelerini yaz
void writer_thread(const std::string& output_file,
                  ThreadSafeQueue<std::string>& sql_queue,
                  WorkStats& stats,
                  size_t batch_size) {
    try {
        std::ofstream output(output_file, std::ios::out);
        if (!output) {
            std::cerr << "Error: Cannot open output file: " << output_file << std::endl;
            return;
        }
        
        // Yazma performansı için
        const size_t BUFFER_SIZE = 8 * 1024 * 1024; // 8 MB
        output.rdbuf()->pubsetbuf(new char[BUFFER_SIZE], BUFFER_SIZE);
        
        // SQL başlangıç
        auto now = std::chrono::system_clock::now();
        std::time_t now_time = std::chrono::system_clock::to_time_t(now);
        
        output << "-- Auto-generated SQL from MicroLogParser C++ Edition\n";
        output << "-- Generated at: " << std::ctime(&now_time);
        output << "-- Her ifade ayrı bir transaction içinde çalışacak şekilde düzenlenmiştir\n\n";
        
        std::vector<std::string> batch;
        batch.reserve(batch_size);
        
        std::string sql;
        auto last_write = std::chrono::high_resolution_clock::now();
        
        while (sql_queue.pop(sql)) {
            batch.push_back(sql);
            
            // Belirli sayıya ulaşınca veya belirli süre geçince yaz
            auto now = std::chrono::high_resolution_clock::now();
            auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - last_write).count();
            
            if (batch.size() >= batch_size || (elapsed >= 2 && !batch.empty())) {
                for (const auto& statement : batch) {
                    // Her SQL ifadesini kendi transaction'ı içinde çalıştır
                    output << "BEGIN;\n";
                    output << statement << ";\n";
                    output << "COMMIT;\n\n";
                }
                output.flush();
                
                batch.clear();
                last_write = now;
                
                // İlerleme bilgisi
                stats.print_stats();
            }
        }
        
        // Kalan ifadeleri yaz
        if (!batch.empty()) {
            for (const auto& statement : batch) {
                // Her SQL ifadesini kendi transaction'ı içinde çalıştır
                output << "BEGIN;\n";
                output << statement << ";\n";
                output << "COMMIT;\n\n";
            }
        }
        
        output.close();
        
        std::cout << "Yazma işlemi tamamlandı." << std::endl;
    }
    catch (const std::exception& e) {
        std::cerr << "Error in writer thread: " << e.what() << std::endl;
    }
}

// Dosyadaki satır sayısını hızlı sayma
uint64_t count_lines(const std::string& file_path) {
    std::ifstream file(file_path, std::ios::in | std::ios::binary);
    if (!file) {
        return 0;
    }
    
    file.seekg(0, std::ios::end);
    size_t file_size = file.tellg();
    file.seekg(0, std::ios::beg);
    
    constexpr size_t BUFFER_SIZE = 16 * 1024 * 1024; // 16 MB
    char buffer[BUFFER_SIZE];
    
    uint64_t line_count = 0;
    size_t bytes_read;
    
    while (file) {
        file.read(buffer, BUFFER_SIZE);
        bytes_read = file.gcount();
        
        for (size_t i = 0; i < bytes_read; ++i) {
            if (buffer[i] == '\n') {
                ++line_count;
            }
        }
    }
    
    return line_count;
}

int main(int argc, char* argv[]) {
    try {
        if (argc < 3) {
            std::cerr << "Kullanım: " << argv[0] << " <input_file> <output_file> [threads] [batch_size]" << std::endl;
            return 1;
        }
        
        std::string input_file = argv[1];
        std::string output_file = argv[2];
        
        if (!std::filesystem::exists(input_file)) {
            std::cerr << "Hata: Giriş dosyası bulunamadı: " << input_file << std::endl;
            return 1;
        }
        
        // Thread sayısı varsayılan olarak mantıklı bir değer
        size_t worker_count = std::thread::hardware_concurrency();
        if (worker_count == 0) worker_count = 4; // Tespit edilemezse varsayılan 4
        
        // Batch size (toplu yazma büyüklüğü)
        size_t batch_size = 5000;
        
        // Opsiyonel parametreler
        if (argc > 3) {
            worker_count = std::stoul(argv[3]);
        }
        if (argc > 4) {
            batch_size = std::stoul(argv[4]);
        }
        
        std::cout << "MicroLogParser C++ Edition\n";
        std::cout << "-------------------------\n";
        std::cout << "Input file: " << input_file << std::endl;
        std::cout << "Output file: " << output_file << std::endl;
        std::cout << "Worker threads: " << worker_count << std::endl;
        std::cout << "Batch size: " << batch_size << std::endl;
        
        // İstatistikler
        WorkStats stats;
        
        // Kuyruğu başlat
        ThreadSafeQueue<std::string> line_queue;
        ThreadSafeQueue<std::string> sql_queue;
        
        // Thread havuzlarını oluştur
        std::thread reader(reader_thread, std::ref(input_file), std::ref(line_queue), std::ref(stats));
        
        std::vector<std::thread> workers;
        workers.reserve(worker_count);
        
        for (size_t i = 0; i < worker_count; ++i) {
            workers.emplace_back(worker_thread, 
                                std::ref(line_queue), 
                                std::ref(sql_queue), 
                                std::ref(stats));
        }
        
        std::thread writer(writer_thread, 
                          std::ref(output_file), 
                          std::ref(sql_queue), 
                          std::ref(stats), 
                          batch_size);
        
        // Thread'lerin tamamlanmasını bekle
        reader.join();
        
        for (auto& worker : workers) {
            worker.join();
        }
        
        sql_queue.terminate();
        writer.join();
        
        // Sonuçları göster
        stats.print_stats();
        
        double elapsed = stats.elapsed_seconds();
        std::cout << "\nToplam çalışma süresi: " << elapsed << " saniye" << std::endl;
        std::cout << "Ortalama hız: " << stats.lines_per_second() << " satır/saniye" << std::endl;
        std::cout << "Toplam oluşturulan SQL: " << stats.sql_statements << " ifade" << std::endl;
        
    return 0;
    }
    catch (const std::exception& e) {
        std::cerr << "Hata: " << e.what() << std::endl;
        return 1;
    }
}