#include <stdint.h>

static uint32_t data_seed = 0x12345678u;
static uint32_t bss_scratch;

static uint32_t fibonacci(uint32_t n)
{
    uint32_t a = 0u;
    uint32_t b = 1u;

    while (n-- != 0u) {
        uint32_t next = a + b;
        a = b;
        b = next;
    }
    return a;
}

int main(void)
{
    uint32_t sum = 0u;
    uint32_t i;

    for (i = 1u; i <= 100u; ++i) {
        sum += i;
    }

    bss_scratch = sum ^ data_seed;

    return (int)(fibonacci(10u) + bss_scratch);
}
