#ifndef LINE_PROCCES_ULP_HPP
#define LINE_PROCCES_ULP_HPP

#include <string>
#include <tuple>
#include <fstream>
#include <iostream>
#include <vector>
#include <mutex>
#include <optional>
#include "prepare_url.hpp"

// Protokol kontrolü ve ekleme
std::string check_and_add_protocol(const std::string& url) {
    if (url.empty()) {
        return url;
    }
    
    if (url.find("://") != std::string::npos) {
        return url; // Protokol zaten var
    }
    
    // Android url formatı
    if (url.find("android@") == 0) {
        return "android://" + url.substr(8);
    }
    
    // Varsayılan olarak http:// ekle
    return "http://" + url;
}

// Thread-safe dosya yazma işlemi için mutex
static std::mutex file_write_mutex;

// Başarısız satırları dosyaya yaz
void write_failed_line(const std::string& line) {
    std::lock_guard<std::mutex> lock(file_write_mutex);
    std::ofstream file("failed_lines.txt", std::ios::app);
    if (file.is_open()) {
        file << line << std::endl;
        file.close();
    } else {
        std::cerr << "[ERROR]: Failed to open failed_lines.txt" << std::endl;
    }
}

// Satırı işle ve ayrıştırılmış verileri tuple olarak döndür
// Tuple sırası: (protocol, main_domain, subdomain, tld, port, path, etc, username, password)
// Sütunlar şema.sql'deki sıra ile uyumlu olmalı
std::optional<std::tuple<std::string, std::string, std::string, std::string, std::string, 
                        std::string, std::string, std::string, std::string>> 
processLine(const std::string& currentLine) {
    try {
        if (currentLine.empty()) {
            return std::nullopt;
        }
        
        std::string processedLine = check_and_add_protocol(currentLine);
        
        // Android URL formatı için özel işleme
        if (processedLine.substr(0, 10) == "android://") {
            // Format: android://token@package_name/:credentials username:password
            if (processedLine.find(" ") != std::string::npos && std::count(processedLine.begin(), processedLine.end(), ' ') == 1) {
                size_t spacePos = processedLine.find(" ");
                std::string fullUrl = processedLine.substr(0, spacePos);
                std::string credentials = processedLine.substr(spacePos + 1);
                
                size_t colonPos = credentials.find(":");
                std::string username = credentials;
                std::string password = "";
                
                if (colonPos != std::string::npos) {
                    username = credentials.substr(0, colonPos);
                    password = credentials.substr(colonPos + 1);
                }
                
                auto parsedUrl = prepare_url(fullUrl);
                if (parsedUrl["origin"].empty()) {
                    write_failed_line(currentLine);
                    return std::nullopt;
                }
                
                return std::make_tuple(
                    parsedUrl["protocol"],
                    parsedUrl["domain"],
                    parsedUrl["android_token"],
                    "",  // tld - Android için boş
                    "",  // port - Android için boş
                    "",  // path - Android için boş
                    "",  // etc - Android için boş
                    username, 
                    password
                );
            }
            // Format: android://token@package:username:password
            else if (std::count(processedLine.begin(), processedLine.end(), ':') == 2) {
                std::vector<std::string> parts;
                size_t start = 0, end = 0;
                
                while ((end = processedLine.find(':', start)) != std::string::npos) {
                    parts.push_back(processedLine.substr(start, end - start));
                    start = end + 1;
                }
                parts.push_back(processedLine.substr(start));
                
                if (parts.size() >= 3) {
                    std::string fullUrl = parts[0] + ":" + parts[1];
                    std::string username = parts[2];
                    std::string password = "";
                    
                    if (parts.size() > 3) {
                        for (size_t i = 3; i < parts.size(); ++i) {
                            if (!password.empty()) password += ":";
                            password += parts[i];
                        }
                    }
                    
                    auto parsedUrl = prepare_url(fullUrl);
                    if (parsedUrl["origin"].empty()) {
                        write_failed_line(currentLine);
                        return std::nullopt;
                    }
                    
                    return std::make_tuple(
                        parsedUrl["protocol"],
                        parsedUrl["domain"],
                        parsedUrl["android_token"],
                        "",  // tld - Android için boş
                        "",  // port - Android için boş
                        "",  // path - Android için boş
                        "",  // etc - Android için boş
                        username, 
                        password
                    );
                }
            }
            // Format: android://token@package|username|password
            else if (std::count(processedLine.begin(), processedLine.end(), '|') == 2) {
                std::vector<std::string> parts;
                size_t start = 0, end = 0;
                
                while ((end = processedLine.find('|', start)) != std::string::npos) {
                    parts.push_back(processedLine.substr(start, end - start));
                    start = end + 1;
                }
                parts.push_back(processedLine.substr(start));
                
                if (parts.size() == 3) {
                    std::string fullUrl = parts[0];
                    std::string username = parts[1];
                    std::string password = parts[2];
                    
                    auto parsedUrl = prepare_url(fullUrl);
                    if (parsedUrl["origin"].empty()) {
                        write_failed_line(currentLine);
                        return std::nullopt;
                    }
                    
                    return std::make_tuple(
                        parsedUrl["protocol"],
                        parsedUrl["domain"],
                        parsedUrl["android_token"],
                        "", "", "", "",  // Boş alanlar
                        username, password
                    );
                }
            }
            // Format: android://token@package::username::password
            else if (processedLine.find("::") != std::string::npos) {
                std::vector<std::string> parts;
                size_t start = 0, end = 0;
                
                while ((end = processedLine.find("::", start)) != std::string::npos) {
                    parts.push_back(processedLine.substr(start, end - start));
                    start = end + 2;  // Skip "::"
                }
                parts.push_back(processedLine.substr(start));
                
                if (parts.size() == 3) {
                    std::string fullUrl = parts[0];
                    std::string username = parts[1];
                    std::string password = parts[2];
                    
                    auto parsedUrl = prepare_url(fullUrl);
                    if (parsedUrl["origin"].empty()) {
                        write_failed_line(currentLine);
                        return std::nullopt;
                    }
                    
                    return std::make_tuple(
                        parsedUrl["protocol"],
                        parsedUrl["domain"],
                        parsedUrl["android_token"],
                        "",  // tld - Android için boş
                        "",  // port - Android için boş
                        "",  // path - Android için boş
                        "",  // etc - Android için boş
                        username, 
                        password
                    );
                }
            }
            else {
                write_failed_line(currentLine);
                return std::nullopt;
            }
        }
        
        // Format: URL username:password
        if (std::count(processedLine.begin(), processedLine.end(), ' ') == 1) {
            size_t spacePos = processedLine.find(" ");
            std::string fullUrl = processedLine.substr(0, spacePos);
            std::string credentials = processedLine.substr(spacePos + 1);
            
            size_t colonPos = credentials.find(":");
            std::string username = credentials;
            std::string password = "";
            
            if (colonPos != std::string::npos) {
                username = credentials.substr(0, colonPos);
                password = credentials.substr(colonPos + 1);
            }
            
            auto parsedUrl = prepare_url(fullUrl);
            if (parsedUrl["origin"].empty()) {
                write_failed_line(currentLine);
                return std::nullopt;
            }
            
            return std::make_tuple(
                parsedUrl["protocol"],
                parsedUrl["main_domain"],
                parsedUrl["subdomain"],
                parsedUrl["tld"],
                parsedUrl["port"],
                parsedUrl["path"],
                parsedUrl["etc"],
                username,
                password
            );
        }
        
        // Format: protocol:domain:username:password veya protocol:domain:port:username:password
        else if (std::count(processedLine.begin(), processedLine.end(), ':') >= 3) {
            std::vector<std::string> parts;
            size_t start = 0, end = 0;
            
            while ((end = processedLine.find(':', start)) != std::string::npos) {
                parts.push_back(processedLine.substr(start, end - start));
                start = end + 1;
            }
            parts.push_back(processedLine.substr(start));
            
            if (parts.size() < 4) {
                write_failed_line(currentLine);
                return std::nullopt;
            }
            
            // Basic format: protocol:domain:username:password
            std::string fullUrl, username, password;
            
            if (parts.size() == 4) {
                fullUrl = parts[0] + ":" + parts[1];
                username = parts[2];
                password = parts[3];
            }
            // Format with port or complex password: protocol:domain:port:username:password...
            else {
                fullUrl = parts[0] + ":" + parts[1];
                // Check if third element is a port number
                bool isPort = true;
                for (char c : parts[2]) {
                    if (!std::isdigit(c)) {
                        isPort = false;
                        break;
                    }
                }
                
                if (isPort) {
                    fullUrl += ":" + parts[2];
                    username = parts[3];
                    // Combine remaining parts as password
                    password = "";
                    for (size_t i = 4; i < parts.size(); ++i) {
                        if (!password.empty()) password += ":";
                        password += parts[i];
                    }
                } else {
                    username = parts[2];
                    // Combine remaining parts as password
                    password = "";
                    for (size_t i = 3; i < parts.size(); ++i) {
                        if (!password.empty()) password += ":";
                        password += parts[i];
                    }
                }
            }
            
            auto parsedUrl = prepare_url(fullUrl);
            if (parsedUrl["origin"].empty()) {
                write_failed_line(currentLine);
                return std::nullopt;
            }
            
            return std::make_tuple(
                parsedUrl["protocol"],
                parsedUrl["main_domain"],
                parsedUrl["subdomain"],
                parsedUrl["tld"],
                parsedUrl["port"],
                parsedUrl["path"],
                parsedUrl["etc"],
                username,
                password
            );
        }
        
        // Format: URL|username|password
        else if (std::count(processedLine.begin(), processedLine.end(), '|') == 2) {
            std::vector<std::string> parts;
            size_t start = 0, end = 0;
            
            while ((end = processedLine.find('|', start)) != std::string::npos) {
                parts.push_back(processedLine.substr(start, end - start));
                start = end + 1;
            }
            parts.push_back(processedLine.substr(start));
            
            if (parts.size() == 3) {
                std::string fullUrl = parts[0];
                std::string username = parts[1];
                std::string password = parts[2];
                
                auto parsedUrl = prepare_url(fullUrl);
                if (parsedUrl["origin"].empty()) {
                    write_failed_line(currentLine);
                    return std::nullopt;
                }
                
                return std::make_tuple(
                    parsedUrl["protocol"],
                    parsedUrl["main_domain"],
                    parsedUrl["subdomain"],
                    parsedUrl["tld"],
                    parsedUrl["port"],
                    parsedUrl["path"],
                    parsedUrl["etc"],
                    username,
                    password
                );
            }
        }
        
        // Format: URL||username||password
        else if (processedLine.find("||") != std::string::npos) {
            std::vector<std::string> parts;
            size_t start = 0, end = 0;
            
            while ((end = processedLine.find("||", start)) != std::string::npos) {
                parts.push_back(processedLine.substr(start, end - start));
                start = end + 2;  // Skip "||"
            }
            parts.push_back(processedLine.substr(start));
            
            if (parts.size() == 3) {
                std::string fullUrl = parts[0];
                std::string username = parts[1];
                std::string password = parts[2];
                
                auto parsedUrl = prepare_url(fullUrl);
                if (parsedUrl["origin"].empty()) {
                    write_failed_line(currentLine);
                    return std::nullopt;
                }
                
                return std::make_tuple(
                    parsedUrl["protocol"],
                    parsedUrl["main_domain"],
                    parsedUrl["subdomain"],
                    parsedUrl["tld"],
                    parsedUrl["port"],
                    parsedUrl["path"],
                    parsedUrl["etc"],
                    username,
                    password
                );
            }
        }
        
        // Format: URL::username::password
        else if (processedLine.find("::") != std::string::npos) {
            std::vector<std::string> parts;
            size_t start = 0, end = 0;
            
            while ((end = processedLine.find("::", start)) != std::string::npos) {
                parts.push_back(processedLine.substr(start, end - start));
                start = end + 2;  // Skip "::"
            }
            parts.push_back(processedLine.substr(start));
            
            if (parts.size() == 3) {
                std::string fullUrl = parts[0];
                std::string username = parts[1];
                std::string password = parts[2];
                
                auto parsedUrl = prepare_url(fullUrl);
                if (parsedUrl["origin"].empty()) {
                    write_failed_line(currentLine);
                    return std::nullopt;
                }
                
                return std::make_tuple(
                    parsedUrl["protocol"],
                    parsedUrl["main_domain"],
                    parsedUrl["subdomain"],
                    parsedUrl["tld"],
                    parsedUrl["port"],
                    parsedUrl["path"],
                    parsedUrl["etc"],
                    username,
                    password
                );
            }
        }
        
        write_failed_line(currentLine);
        return std::nullopt;
    }
    catch (const std::exception& e) {
        std::cerr << "[ERROR]: Error in processLine: " << e.what() << std::endl;
        write_failed_line(currentLine);
        return std::nullopt;
    }
    catch (...) {
        std::cerr << "[ERROR]: Unknown error in processLine" << std::endl;
        write_failed_line(currentLine);
        return std::nullopt;
    }
}

#endif
