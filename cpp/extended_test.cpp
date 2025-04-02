#include <iostream>
#include <string>
#include <vector>
#include "lib/prepare_url.hpp"

void test_url(const std::string& url) {
    std::cout << "Testing URL: " << url << std::endl;
    
    try {
        auto result = prepare_url(url);
        
        std::cout << "  Protocol: " << result["protocol"] << std::endl;
        std::cout << "  Domain: " << result["domain"] << std::endl;
        std::cout << "  Subdomain: " << result["subdomain"] << std::endl;
        std::cout << "  Main domain: " << result["main_domain"] << std::endl;
        std::cout << "  TLD: " << result["tld"] << std::endl;
        std::cout << "  Port: " << result["port"] << std::endl;
        std::cout << "  Path: " << result["path"] << std::endl;
        std::cout << "  Etc: " << result["etc"] << std::endl;
        
        std::cout << std::endl;
    }
    catch (const std::exception& e) {
        std::cerr << "  Error: " << e.what() << std::endl;
        std::cout << std::endl;
    }
}

int main() {
    std::cout << "Extended Domain Parsing Tests\n";
    std::cout << "---------------------------\n\n";
    
    // Temel testler
    test_url("https://example.com/");
    test_url("https://www.example.com/");
    
    // Türkçe domainler
    test_url("https://site.com.tr/");
    test_url("https://test.edu.tr/");
    test_url("https://app.gov.tr/");
    test_url("https://domain.web.tr/");
    test_url("https://deneme.bel.tr/");
    test_url("https://blog.example.com.tr/");
    
    // Diğer ülke domainleri
    test_url("https://example.co.uk/");
    test_url("https://test.com.au/");
    test_url("https://site.co.nz/");
    test_url("https://company.co.jp/");
    test_url("https://website.com.br/");
    test_url("https://test.com.cn/");
    
    // Karmaşık subdomainler
    test_url("https://dev.api.example.com/");
    test_url("https://beta.test.staging.example.org/");
    test_url("https://dev.example.web.tr/");
    
    // Özel TLD'ler
    test_url("https://example.io/");
    test_url("https://example.dev/");
    test_url("https://example.app/");
    test_url("https://github.io/");
    test_url("https://example.github.io/");
    
    // IDN domainleri (uluslararası domain adları)
    test_url("https://örnek.com/");
    test_url("https://例子.com/");
    test_url("https://пример.рф/");
    
    // Localhost ve IP
    test_url("http://localhost/");
    test_url("http://localhost.localdomain/");
    test_url("http://127.0.0.1/");
    test_url("https://192.0.2.1:8080/");
    
    // Android URL'leri
    test_url("android://token@com.example.app/:credentials");
    
    // Hatalı URL'ler
    test_url("example.com"); // protokol yok
    test_url("http://"); // domain yok
    test_url("https://example");
    
    return 0;
} 