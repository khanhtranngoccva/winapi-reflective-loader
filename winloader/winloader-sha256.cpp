#include "winloader-sha256.h"
#include "winloader-numbers.h"
#include "winloader-mem-string.h"

#define WINLOADER_SHA256_CHUNK_SIZE 64

// Supports at most 4096 bytes in the buffer, including the last 64 bits at the end and a null byte right in front.
// The maximum string length supported is 4096 - 8 - 1 = 4087 bytes, after that, hashing function will not work as expected.
#define MAX_ALLOWED_SHA256_BUF_SIZE 4096

void winloader::sha256(const char *input, char output[32]) {
    unsigned __int32 sha256_hash_values[8] = {
            0x6a09e667,
            0xbb67ae85,
            0x3c6ef372,
            0xa54ff53a,
            0x510e527f,
            0x9b05688c,
            0x1f83d9ab,
            0x5be0cd19,
    };

    unsigned __int32 sha256_round_constants[64] = {
            0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
            0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
            0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
            0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
            0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
            0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
            0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
            0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
    };

    auto string_length = winloader::strlen(input);
    // Pad data with 0's until data is a multiple of 512 bits, which is 64 bytes. (technically, 64 bits less than 512, but these 64 bits will be later appended.)
    auto temp_buffer_length = winloader::min(minimum_divisible_by(string_length + 1, WINLOADER_SHA256_CHUNK_SIZE), MAX_ALLOWED_SHA256_BUF_SIZE);
    char buffer[MAX_ALLOWED_SHA256_BUF_SIZE];
    winloader::memset(buffer, 0, MAX_ALLOWED_SHA256_BUF_SIZE);
    // Copy input to temp buffer.
    winloader::memcpy(buffer, input, string_length);
    // Append a single 1 to the end of the buffer.
    buffer[string_length] = (char) 0b10000000;
    auto size_field = (unsigned __int64 *) &buffer[temp_buffer_length - 8];
    // Append size of field in bits, arranged in big-endian order (amd64 CPUs are little endian!).
    *size_field = endian_swap(string_length * 8);

    unsigned __int32 message_schedule[64]{};
    for (size_t i = 0; i < temp_buffer_length; i += WINLOADER_SHA256_CHUNK_SIZE) {
        // Initialize a 64-element 32-bit word array, set everything to 0.
        winloader::memset(message_schedule, 0, sizeof(message_schedule));
        // Copy the entirety of the chunk to the memory array.
        winloader::memcpy(message_schedule, &buffer[i], WINLOADER_SHA256_CHUNK_SIZE);
        // Modify the message schedule.
        for (size_t j = 16; j < 64; j++) {
            auto j15 = winloader::endian_swap(message_schedule[j - 15]);
            auto j2 = winloader::endian_swap(message_schedule[j - 2]);
            auto j16 = winloader::endian_swap(message_schedule[j - 16]);
            auto j7 = winloader::endian_swap(message_schedule[j - 7]);
            auto s0 = right_rotate(j15, 7) ^ right_rotate(j15, 18) ^ (j15 >> 3);
            auto s1 = right_rotate(j2, 17) ^ right_rotate(j2, 19) ^ (j2 >> 10);
            auto o = endian_swap(j16 + s0 + j7 + s1);
            message_schedule[j] = o;
        }
        // Perform the compression algorithm. It apparently seems this pseudocode part uses little endian encoding instead.
        auto a = sha256_hash_values[0];
        auto b = sha256_hash_values[1];
        auto c = sha256_hash_values[2];
        auto d = sha256_hash_values[3];
        auto e = sha256_hash_values[4];
        auto f = sha256_hash_values[5];
        auto g = sha256_hash_values[6];
        auto h = sha256_hash_values[7];
        for (unsigned int j = 0; j < 64; j++) {
            auto s1_1 = winloader::right_rotate(e, 6);
            auto s1_2 = winloader::right_rotate(e, 11);
            auto s1_3 = winloader::right_rotate(e, 25);
            auto s1 = s1_1 ^ s1_2 ^ s1_3;
            auto ch = (e & f) ^ ((~e) & g);
            auto constant_token = sha256_round_constants[j];
            auto message_token = winloader::endian_swap(message_schedule[j]);
            auto temp1 = h + s1 + ch + constant_token + message_token;
            auto s0_1 = winloader::right_rotate(a, 2);
            auto s0_2 = winloader::right_rotate(a, 13);
            auto s0_3 = winloader::right_rotate(a, 22);
            auto s0 = s0_1 ^ s0_2 ^ s0_3;
            auto maj = (a & b) ^ (a & c) ^ (b & c);
            auto temp2 = s0 + maj;
            h = g;
            g = f;
            f = e;
            e = d + temp1;
            d = c;
            c = b;
            b = a;
            a = temp1 + temp2;
        }
        sha256_hash_values[0] += a;
        sha256_hash_values[1] += b;
        sha256_hash_values[2] += c;
        sha256_hash_values[3] += d;
        sha256_hash_values[4] += e;
        sha256_hash_values[5] += f;
        sha256_hash_values[6] += g;
        sha256_hash_values[7] += h;
    }
    auto output_temp = (unsigned __int32 *) output;
    for (unsigned int i = 0; i < 8; i++) {
        output_temp[i] = winloader::endian_swap(sha256_hash_values[i]);
    }
}
