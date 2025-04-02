#include <iostream>
#include <string>

// SQL değerini güvenli şekilde formatla (main.cpp'den kopyalandı)
std::string format_sql_value(const std::string& value) {
    if (value.empty()) {
        return "NULL";
    }
    
    std::string escaped;
    escaped.reserve(value.size() * 1.2); // Tahmini yer ayır
    
    escaped.push_back('\'');
    for (char c : value) {
        if (c == '\'') {
            escaped.push_back('\\');
            escaped.push_back('\'');
        } else if (c == '\\') {
            escaped.push_back('\\');
            escaped.push_back('\\');
        } else if (c == 0 || c == '\r' || c == '\n') {
            // Null karakterleri ve satır sonu karakterlerini (CR, LF) atla
            continue;
        } else {
            escaped.push_back(c);
        }
    }
    escaped.push_back('\'');
    
    return escaped;
}

// Sorunlu karakter içeren verileri test eder
void test_special_characters() {
    std::string test_cases[] = {
        "normal_string",
        "string_with\nnewline",
        "string_with\r\nwindows_newline",
        "string_with\rcarriage_return",
        "string_with\'quote",
        "string_with\\backslash",
        "bharathi\r",  // Kullanıcının belirttiği sorunlu durum
        "username\r);", // SQL enjeksiyon girişimini andıran sorunlu durum
        "-- SQL comment\r\n DROP TABLE users;" // SQL enjeksiyon denemesi
    };
    
    std::cout << "Özel Karakter Temizleme Testi" << std::endl;
    std::cout << "---------------------------" << std::endl;
    
    for (const auto& test : test_cases) {
        std::string escaped = format_sql_value(test);
        
        std::cout << "Orijinal: [" << test << "]" << std::endl;
        std::cout << "İşlenmiş: " << escaped << std::endl;
        
        // Hex formatında göster
        std::cout << "Hex (orijinal): ";
        for (char c : test) {
            std::cout << std::hex << std::uppercase << (int)(unsigned char)c << " ";
        }
        std::cout << std::endl;
        
        std::cout << "Hex (işlenmiş): ";
        for (char c : escaped) {
            std::cout << std::hex << std::uppercase << (int)(unsigned char)c << " ";
        }
        std::cout << std::dec << std::endl << std::endl;
    }
}

int main() {
    test_special_characters();
    return 0;
} 