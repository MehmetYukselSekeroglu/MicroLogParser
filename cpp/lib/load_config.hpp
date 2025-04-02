#ifndef LOAD_CONFIG_HPP
#define LOAD_CONFIG_HPP

#include <nlohmann/json.hpp>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

#ifdef _WIN32
    #define CONFIG_FILE "config\\config.json"
#else
    #define CONFIG_FILE "config/config.json"
#endif

/**
 * @brief Yapılandırma dosyasını yükler
 * @return JSON formatında yapılandırma verileri
 * @throws std::runtime_error Dosya açılamaz veya ayrıştırılamazsa
 */
nlohmann::json loadConfig(void) {
    std::ifstream configFile(CONFIG_FILE);

    if (!configFile.is_open()) {
        throw std::runtime_error(std::string("Error while opening config file: ") + CONFIG_FILE);
    }

    nlohmann::json configData;

    try {
        configFile >> configData;
    }
    catch (const std::exception& e) {
        throw std::runtime_error("Error while loading config file: " + std::string(e.what()));
    }
    
    configFile.close();
    return configData;
}

#endif
