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
    std::cout << "Testing domain and TLD parsing\n";
    std::cout << "-----------------------------\n\n";
    
    // .tr uzantılı adresler
    test_url("https://example.web.tr/");
    test_url("https://deneme.bel.tr/");
    test_url("https://test.edu.tr/");
    test_url("https://site.com.tr/");
    test_url("https://domain.web.tr/");
    test_url("https://app.gov.tr/");
    
    // Diğer iki seviyeli TLD'ler
    test_url("https://example.co.uk/");
    test_url("https://test.com.au/");
    test_url("https://site.co.nz/");
    
    // Alt domainli örnekler
    test_url("https://blog.example.com.tr/");
    test_url("https://mail.test.edu.tr/");
    test_url("https://dev.example.web.tr/");
    
    return 0;
} 