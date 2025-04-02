#include <iostream>
#include <string>
#include "lib/prepare_url.hpp"

int main() {
    std::cout << "URL Parser Test\n";
    std::cout << "---------------\n";
    
    // Farklı URL tiplerini test et
    std::vector<std::string> urls = {
        "https://example.com",
        "http://user:pass@subdomain.example.co.uk:8080/path?query=value#fragment",
        "android://token@com.example.app/:credentials",
        "android://123",  // Hatalı Android URL'i - @ işareti yok
        "ftp://files.example.net",
        "",  // Boş URL
        "https://www.example.com/path with spaces",
        "https://192.0.2.1:8080",
        "example.com"  // Protokolsüz
    };
    
    for (const auto& url : urls) {
        std::cout << "\nTesting URL: " << (url.empty() ? "<empty>" : url) << std::endl;
        
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
            
            if (result["protocol"] == "android") {
                std::cout << "  Android token: " << result["android_token"] << std::endl;
                std::cout << "  Android package: " << result["android_package"] << std::endl;
                std::cout << "  Android credentials: " << result["android_credentials"] << std::endl;
            }
        } catch (const std::exception& e) {
            std::cerr << "Error: " << e.what() << std::endl;
        }
    }
    
    return 0;
} 