#pragma once


// Credits: https://blog.boot.dev/cryptography/how-sha-2-works-step-by-step-sha-256/
namespace winloader {
    void sha256(const char *input, char output[32]);
}