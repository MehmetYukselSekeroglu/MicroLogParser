#!/bin/bash

# Build dizini oluştur veya temizle
if [ ! -d "build" ]; then
    mkdir build
else
    echo "Cleaning build directory..."
    rm -rf build/*
fi

# Derleme
cd build
cmake ..
make -j$(nproc)

if [ $? -ne 0 ]; then
    echo "Build failed!"
    exit 1
fi

echo ""
echo "Running URL Parser test..."
./url_test

# Test data oluştur
echo "Creating test data..."
echo "https://example.com SYNTHETIC_USER:SYNTHETIC_PASSWORD" > test_data.txt
echo "http://test.example.org:8080/path?query=value SYNTHETIC_USER:SYNTHETIC_PASSWORD" >> test_data.txt
echo "ftp://files.example.net SYNTHETIC_USER:SYNTHETIC_PASSWORD" >> test_data.txt
echo "https://subdomain.example.com/login.php SYNTHETIC_USER:SYNTHETIC_PASSWORD" >> test_data.txt
echo "android://SYNTHETIC_TOKEN@com.example.app/:credentials SYNTHETIC_USER:SYNTHETIC_PASSWORD" >> test_data.txt
echo "android://123" >> test_data.txt
echo "http://example.com:8080/path/to/resource?param=value&other=123#section SYNTHETIC_USER:SYNTHETIC:COLON_PASSWORD" >> test_data.txt

# SQL oluşturma testini çalıştır
echo ""
echo "Running MicroLogParser with test data..."
./MicroLogParser test_data.txt output.sql 2

echo ""
echo "Generated SQL:"
cat output.sql

echo ""
echo "All tests completed." 