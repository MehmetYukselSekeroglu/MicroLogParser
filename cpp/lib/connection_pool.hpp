#ifndef CONNECTION_POOL_HPP
#define CONNECTION_POOL_HPP

#include <mutex>
#include <vector>
#include <iostream>
#include <stdexcept>
#include <postgresql/libpq-fe.h>
#include <condition_variable>

/**
 * @brief PostgreSQL bağlantı havuzu yönetimi için sınıf
 */
class ConnectionPoolToolkit {
    private:
        std::string connectionInfo;
        size_t poolSize;
        std::vector<PGconn*> connectionPool;
        mutable std::mutex mtx;
        std::condition_variable cv;

    public:
        /**
         * @brief Bağlantı havuzu oluşturucu
         * @param CONNECTION_INFO PostgreSQL bağlantı bilgisi
         * @param POOL_SIZE Havuz boyutu
         */
        ConnectionPoolToolkit(const std::string& CONNECTION_INFO, size_t POOL_SIZE):
            connectionInfo(CONNECTION_INFO),
            poolSize(POOL_SIZE) {
            std::cout << "[INFO]: " << poolSize << " boyutunda bağlantı havuzu oluşturuluyor..." << std::endl;
            
            connectionPool.reserve(poolSize);
            for (size_t i = 0; i < poolSize; ++i) {
                PGconn* conn = PQconnectdb(connectionInfo.c_str());

                if (PQstatus(conn) == CONNECTION_BAD) {
                    std::cerr << "[ERROR]: Bağlantı başarısız: " << PQerrorMessage(conn) << std::endl;
                    PQfinish(conn);
                    
                    // Önceden oluşturulan bağlantıları temizle
                    for (auto& existingConn : connectionPool) {
                        PQfinish(existingConn);
                    }
                    
                    throw std::runtime_error("Veritabanı bağlantısı başarısız!");
                }
                connectionPool.push_back(conn);
            }
            std::cout << "[INFO]: Bağlantı havuzu başarıyla oluşturuldu." << std::endl;
        }
        
        /**
         * @brief Yıkıcı - tüm bağlantıları kapatır
         */
        ~ConnectionPoolToolkit() {
            std::cout << "[INFO]: Tüm bağlantılar kapatılıyor..." << std::endl;
            for (auto& conn : connectionPool) {
                PQfinish(conn);
            }
            connectionPool.clear();
            std::cout << "[INFO]: Tüm bağlantılar kapatıldı." << std::endl;
        }
        
        /**
         * @brief Havuzdan bir bağlantı alır
         * @return PostgreSQL bağlantı nesnesi
         * @throws std::runtime_error Bağlantı alınamazsa
         */
        PGconn* getConnection() {
            std::unique_lock<std::mutex> lock(mtx);
            cv.wait(lock, [this]() { return !connectionPool.empty(); });
            
            PGconn* connection = connectionPool.back();
            connectionPool.pop_back();
            
            // Bağlantının hala geçerli olduğunu kontrol et
            if (PQstatus(connection) != CONNECTION_OK) {
                PQfinish(connection);
                connection = PQconnectdb(connectionInfo.c_str());
                if (PQstatus(connection) == CONNECTION_BAD) {
                    throw std::runtime_error("Yeni bağlantı oluşturulamadı: " + std::string(PQerrorMessage(connection)));
                }
            }
            
            return connection;
        }
        
        /**
         * @brief Kullanılan bağlantıyı havuza geri verir
         * @param connection Geri verilecek bağlantı
         */
        void releaseConnection(PGconn* connection) {
            if (!connection) return;
            
            {
                std::lock_guard<std::mutex> lock(mtx);
                connectionPool.push_back(connection);
            }
            cv.notify_one();
        }
        
        /**
         * @brief Mevcut havuz boyutunu döndürür
         * @return Havuzdaki bağlantı sayısı
         */
        size_t getPoolSize() const {
            std::lock_guard<std::mutex> lock(mtx);
            return connectionPool.size();
        }
};

#endif