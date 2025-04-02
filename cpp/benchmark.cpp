#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <filesystem>
#include <chrono>
#include <nlohmann/json.hpp>
#include "lib/load_config.hpp"
#include "lib/line_proccess_ULP.hpp"

int main(int argc, char* argv[]) {
    try {
        if (argc != 2) {
            std::cerr << "Usage: " << argv[0] << " <input_file>" << std::endl;
            return 1;
        }

        const std::string input_path = argv[1];

        if (!std::filesystem::exists(input_path)) {
            std::cerr << "Input file does not exist: " << input_path << std::endl;
            return 1;
        }

        std::ifstream input_stream(input_path, std::ios::in);
        
        if (!input_stream.is_open()) {
            std::cerr << "Error while opening input file: " << input_path << std::endl;
            return 1;
        }

        // Dosya tamponunu artır
        input_stream.rdbuf()->pubsetbuf(new char[1024 * 1024], 1024 * 1024);
        
        // Performans için IO senkronizasyonunu devre dışı bırak
        std::ios_base::sync_with_stdio(false);
        
        unsigned int counter = 0;
        std::string line;
        line.reserve(1024); // Tipik satır uzunluğu için bellek ayır
        
        // Başlangıç zamanını kaydet
        const auto start_time = std::chrono::high_resolution_clock::now();
        
        while (std::getline(input_stream, line)) {
            if (counter == 1000) {
                // Bitiş zamanını kaydet
                const auto end_time = std::chrono::high_resolution_clock::now();
                
                // Geçen süreyi hesapla (saniye cinsinden)
                const auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time).count() / 1000.0;
                
                std::cout << "1000 line processed in " << duration << " seconds" << std::endl;
                std::cout << "Processing speed: " << (1000.0 / duration) << " lines per second" << std::endl;
                break;
            }
            
            auto result = processLine(line);
            counter++;
        }

        input_stream.close();
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
}
