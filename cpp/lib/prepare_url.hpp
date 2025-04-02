#ifndef PREPARE_URL_HPP
#define PREPARE_URL_HPP
#include <cstdlib>
#include <string>
#include <Poco/URI.h>
#include <Poco/Net/HTMLForm.h>
#include <iostream>
#include <unordered_map>
#include <sstream>
#include <regex>
#include <vector>
#include <algorithm>

// IP adresi kontrolü için yardımcı fonksiyon
bool is_ip_address(const std::string& domain) {
    std::regex ipv4_regex("^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$");
    return std::regex_match(domain, ipv4_regex);
}

// URL'den ek parçaları (parametre, sorgu, fragment) çıkaran yardımcı fonksiyon
std::string get_etc_part(const Poco::URI& parsed_url) {
    std::string etc;
    
    if (!parsed_url.getQuery().empty()) {
        etc += "?" + parsed_url.getQuery();
    }
    
    if (!parsed_url.getFragment().empty()) {
        etc += "#" + parsed_url.getFragment();
    }
    
    return etc;
}

// Bilinen TLD listesi - İki seviyeli TLD'ler için
bool is_known_two_level_tld(const std::string& last_part, const std::string& second_level) {
    // Ülke kodlarına göre bilinen TLD'ler
    static const std::unordered_map<std::string, std::vector<std::string>> country_tlds = {
        // Türkiye 
        {"tr", {"com", "net", "org", "web", "gov", "edu", "bel", "gen", "av", "dr", "pol", "k12", "mil", "tsk", "name", "tel", "info"}},
        // Birleşik Krallık
        {"uk", {"co", "org", "me", "ac", "gov", "ltd", "plc", "net", "sch", "nhs"}},
        // Avustralya
        {"au", {"com", "net", "org", "edu", "gov", "asn", "id"}},
        // Yeni Zelanda
        {"nz", {"co", "net", "org", "school", "govt", "iwi", "ac", "geek", "gen", "kiwi", "maori"}},
        // Güney Afrika
        {"za", {"co", "org", "gov", "ac", "edu", "law", "net", "web"}},
        // Hindistan
        {"in", {"co", "net", "org", "gen", "firm", "ac", "edu", "res", "gov", "mil"}},
        // Brezilya
        {"br", {"com", "net", "org", "edu", "gov", "mil", "art", "eco", "emp", "ind", "inf", "rio", "srv", "wiki"}},
        // Japonya
        {"jp", {"co", "or", "ac", "ad", "ed", "go", "gr", "lg", "ne", "or"}},
        // Kanada
        {"ca", {"ab", "bc", "mb", "nb", "nf", "nl", "ns", "nt", "nu", "on", "pe", "qc", "sk", "yk"}},
        // Çin
        {"cn", {"com", "net", "org", "gov", "edu", "ac", "ah", "bj", "cq", "fj", "gd", "gs", "gz", "gx", "ha", "hb", "he", "hi", "hl", "hn", "jl", "js", "jx", "ln", "nm", "nx", "qh", "sc", "sd", "sh", "sn", "sx", "tj", "xj", "xz", "yn", "zj"}},
        // Rusya
        {"ru", {"com", "net", "org", "edu", "gov", "mil", "ac", "int", "pp", "msk", "spb"}},
        // Fransa
        {"fr", {"com", "asso", "nom", "prd", "presse", "tm", "gouv"}},
        // İtalya
        {"it", {"co", "gov", "edu"}},
        // İspanya
        {"es", {"com", "nom", "org", "gob", "edu"}},
        // Almanya
        {"de", {"com", "net", "org"}}
    };
    
    // Genel bilinen iki seviyeli TLD'ler (ülke kodu olmayan)
    static const std::vector<std::pair<std::string, std::string>> generic_two_level_tlds = {
        {"eu", "europa"}, {"io", "github"}, {"io", "gitlab"}, {"io", "vercel"}, 
        {"dev", "github"}, {"app", "github"}, {"co", "github"}, {"pages", "github"}
    };
    
    // Ülke kodu tabanlı TLD kontrolü
    auto it = country_tlds.find(last_part);
    if (it != country_tlds.end()) {
        return std::find(it->second.begin(), it->second.end(), second_level) != it->second.end();
    }
    
    // Özel iki seviyeli TLD kontrolü
    for (const auto& tld_pair : generic_two_level_tlds) {
        if (last_part == tld_pair.first && second_level == tld_pair.second) {
            return true;
        }
    }
    
    // Genel ikinci seviye kontrolü
    // Eğer ikinci seviye yaygın bir TLD ise (com, org, net gibi) ve son kısım ülke kodu ise
    static const std::vector<std::string> common_second_levels = {"co", "com", "org", "net", "edu", "gov", "mil", "ac"};
    
    // Son kısım bilinen bir ülke kodu ise ve ikinci seviye yaygın bir TLD ise
    static const std::vector<std::string> known_country_codes = {"af", "al", "dz", "as", "ad", "ao", "ai", "aq", "ag", "ar", "am", "aw", "au", "at", "az", "bs", "bh", "bd", "bb", "by", "be", "bz", "bj", "bm", "bt", "bo", "ba", "bw", "bv", "br", "io", "bn", "bg", "bf", "bi", "kh", "cm", "ca", "cv", "ky", "cf", "td", "cl", "cn", "cx", "cc", "co", "km", "cg", "cd", "ck", "cr", "ci", "hr", "cu", "cy", "cz", "dk", "dj", "dm", "do", "ec", "eg", "sv", "gq", "er", "ee", "et", "fk", "fo", "fj", "fi", "fr", "gf", "pf", "tf", "ga", "gm", "ge", "de", "gh", "gi", "gr", "gl", "gd", "gp", "gu", "gt", "gn", "gw", "gy", "ht", "hm", "va", "hn", "hk", "hu", "is", "in", "id", "ir", "iq", "ie", "il", "it", "jm", "jp", "jo", "kz", "ke", "ki", "kp", "kr", "kw", "kg", "la", "lv", "lb", "ls", "lr", "ly", "li", "lt", "lu", "mo", "mk", "mg", "mw", "my", "mv", "ml", "mt", "mh", "mq", "mr", "mu", "yt", "mx", "fm", "md", "mc", "mn", "ms", "ma", "mz", "mm", "na", "nr", "np", "nl", "an", "nc", "nz", "ni", "ne", "ng", "nu", "nf", "mp", "no", "om", "pk", "pw", "ps", "pa", "pg", "py", "pe", "ph", "pn", "pl", "pt", "pr", "qa", "re", "ro", "ru", "rw", "sh", "kn", "lc", "pm", "vc", "ws", "sm", "st", "sa", "sn", "sc", "sl", "sg", "sk", "si", "sb", "so", "za", "gs", "es", "lk", "sd", "sr", "sj", "sz", "se", "ch", "sy", "tw", "tj", "tz", "th", "tl", "tg", "tk", "to", "tt", "tn", "tr", "tm", "tc", "tv", "ug", "ua", "ae", "gb", "us", "um", "uy", "uz", "vu", "ve", "vn", "vg", "vi", "wf", "eh", "ye", "zm", "zw"};
    
    if (std::find(known_country_codes.begin(), known_country_codes.end(), last_part) != known_country_codes.end() &&
        std::find(common_second_levels.begin(), common_second_levels.end(), second_level) != common_second_levels.end()) {
        return true;
    }
    
    return false;
}

std::unordered_map<std::string, std::string> prepare_url(const std::string& targetUrl) {
    std::unordered_map<std::string, std::string> return_data;
    
    // Varsayılan değerleri ayarla
    return_data["origin"] = "";
    return_data["protocol"] = "";
    return_data["domain"] = "";
    return_data["main_domain"] = "";
    return_data["subdomain"] = "";
    return_data["tld"] = "";
    return_data["port"] = "";
    return_data["path"] = "";
    return_data["etc"] = "";
    return_data["android_token"] = "";
    return_data["android_package"] = "";
    return_data["android_credentials"] = "";
    
    try {
        // URL boş ise boş sonuç döndür
        if (targetUrl.empty()) {
            return return_data;
        }
        
        // URL'yi decode et
        std::string decoded_url;
        Poco::URI::decode(targetUrl, decoded_url);
        return_data["origin"] = decoded_url;
        
        // Android URL'leri için özel işleme
        if (decoded_url.size() >= 10 && decoded_url.substr(0, 10) == "android://") {
            // Android URL formatı: android://token@package_name/:credentials
            size_t protocol_end = decoded_url.find("://");
            
            if (protocol_end != std::string::npos) {
                size_t token_pos = protocol_end + 3;
                size_t package_pos = decoded_url.find("@", token_pos);
                
                if (package_pos != std::string::npos && package_pos > token_pos) {
                    std::string token;
                    
                    // Güvenli bir şekilde token'ı çıkar
                    if (package_pos > token_pos) {
                        token = decoded_url.substr(token_pos, package_pos - token_pos);
                    }
                    
                    std::string package_name;
                    std::string credentials = "";
                    
                    size_t credentials_pos = decoded_url.find("/:", package_pos);
                    
                    if (credentials_pos != std::string::npos && credentials_pos > package_pos) {
                        // Güvenli bir şekilde package_name'i çıkar
                        package_name = decoded_url.substr(package_pos + 1, credentials_pos - (package_pos + 1));
                        
                        // Credentials'ı çıkar, eğer URL'nin sonunda ise
                        if (credentials_pos + 2 < decoded_url.size()) {
                            credentials = decoded_url.substr(credentials_pos + 2);
                        }
                    } else {
                        // Credentials yoksa, kalan kısmı package_name olarak al
                        if (package_pos + 1 < decoded_url.size()) {
                            package_name = decoded_url.substr(package_pos + 1);
                        }
                    }
                    
                    // Başındaki ve sonundaki / işaretlerini temizle
                    if (!package_name.empty() && package_name[0] == '/') {
                        package_name = package_name.substr(1);
                    }
                    if (!package_name.empty() && package_name[package_name.length() - 1] == '/') {
                        package_name = package_name.substr(0, package_name.length() - 1);
                    }
                    
                    return_data["protocol"] = "android";
                    return_data["domain"] = package_name;
                    return_data["main_domain"] = package_name;
                    return_data["android_token"] = token;
                    return_data["android_package"] = package_name;
                    return_data["android_credentials"] = credentials;
                    
                    return return_data;
                }
            }
        }
        
        // Normal URL ayrıştırma
        try {
            Poco::URI parsed_url(decoded_url);
            std::string protocol = parsed_url.getScheme();
            std::string domain = parsed_url.getHost();
            std::string auth_info = parsed_url.getUserInfo();
            std::string path = parsed_url.getPath();
            unsigned short port = parsed_url.getPort();
            
            return_data["protocol"] = protocol;
            
            // Auth bilgisini domain'den ayır
            if (!auth_info.empty() && !domain.empty()) {
                if (domain.find('@') != std::string::npos) {
                    size_t pos = domain.find('@');
                    if (pos < domain.size() - 1) {
                        domain = domain.substr(pos + 1);
                    }
                }
            }
            
            // Port bilgisini domain'den ayır
            std::string port_str = "";
            if (port != 0 && port != 80 && port != 443) {
                port_str = std::to_string(port);
                return_data["port"] = port_str;
            }
            
            return_data["domain"] = domain;
            
            // IP adresi kontrolü
            if (is_ip_address(domain)) {
                return_data["main_domain"] = domain;
                // IP adresi için subdomain ve tld yok
            } else {
                // Domain parçalarını böl
                std::vector<std::string> domain_parts;
                std::stringstream ss(domain);
                std::string part;
                
                while (std::getline(ss, part, '.')) {
                    domain_parts.push_back(part);
                }
                
                // localhost özel durumu
                if (domain == "localhost" || domain == "localhost.localdomain") {
                    return_data["main_domain"] = "localhost";
                    // localhost için subdomain ve tld yok
                } 
                else if (domain_parts.size() >= 2) {
                    // Son kısım her zaman TLD'nin bir parçasıdır (ülke kodu veya com/net/org gibi)
                    std::string last_part = domain_parts[domain_parts.size() - 1];
                    
                    // İki seviyeli TLD'ler için ikinci seviye
                    std::string second_level = "";
                    if (domain_parts.size() >= 2) {
                        second_level = domain_parts[domain_parts.size() - 2];
                    }
                    
                    // İki seviyeli TLD kontrolü
                    bool is_two_level_tld = is_known_two_level_tld(last_part, second_level);
                    
                    if (is_two_level_tld && domain_parts.size() >= 3) {
                        // İki seviyeli TLD (örn: com.tr, org.uk gibi)
                        return_data["tld"] = domain_parts[domain_parts.size() - 2] + "." + 
                                          domain_parts[domain_parts.size() - 1];
                        
                        // Ana domain, TLD'den bir önceki parça
                        return_data["main_domain"] = domain_parts[domain_parts.size() - 3];
                        
                        // Subdomain, ana domain'den önceki tüm parçalar
                        if (domain_parts.size() > 3) {
                            std::string subdomain;
                            for (size_t i = 0; i < domain_parts.size() - 3; ++i) {
                                if (i > 0) subdomain += ".";
                                subdomain += domain_parts[i];
                            }
                            return_data["subdomain"] = subdomain;
                        }
                    } else {
                        // Tek seviyeli TLD: örn. com, org, net
                        return_data["tld"] = domain_parts[domain_parts.size() - 1];
                        
                        // Ana domain, TLD'den önceki parça
                        return_data["main_domain"] = domain_parts[domain_parts.size() - 2];
                        
                        // Subdomain, ana domain'den önceki tüm parçalar
                        if (domain_parts.size() > 2) {
                            std::string subdomain;
                            for (size_t i = 0; i < domain_parts.size() - 2; ++i) {
                                if (i > 0) subdomain += ".";
                                subdomain += domain_parts[i];
                            }
                            return_data["subdomain"] = subdomain;
                        }
                    }
                }
            }
            
            // Path bilgisi
            if (!path.empty()) {
                return_data["path"] = path;
            }
            
            // Ek bilgiler (query, fragment)
            std::string etc = get_etc_part(parsed_url);
            if (!etc.empty()) {
                return_data["etc"] = etc;
            }
        }
        catch (const Poco::Exception& e) {
            std::cerr << "[ERROR]: Error parsing URL with Poco: " << e.displayText() << '\n';
            // URL hatalı olsa bile bir sonuç döndür
            return_data["protocol"] = decoded_url.find("://") != std::string::npos ? 
                                     decoded_url.substr(0, decoded_url.find("://")) : "http";
        }
        
    } catch (const Poco::Exception& e) {
        std::cerr << "[ERROR]: Error in prepare_url: " << e.displayText() << '\n';
    } catch (const std::exception& e) {
        std::cerr << "[ERROR]: Standard exception in prepare_url: " << e.what() << '\n';
    } catch (...) {
        std::cerr << "[ERROR]: Unknown error in prepare_url\n";
    }
    
    return return_data;
}

#endif