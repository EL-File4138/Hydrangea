import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, ReadOnly, RisingEdge, Timer


async def reset_dut(dut):
    dut.rst_ni.value = 0
    await Timer(1, "ns")
    dut.rst_ni.value = 1
    await Timer(1, "ns")


@cocotb.test()
async def rw_cycle(dut):
    """Test read/write cycle of the sync RAM"""
    clock = Clock(dut.clk_i, 1, "ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    for i in range(2200):
        # Generate random values for write
        write_addr = random.randint(0, 255) << 2
        write_data = random.randint(0, 2**32 - 1)

        await FallingEdge(dut.clk_i)

        # Set write inputs
        dut.addr_i.value = write_addr
        dut.write_data_i.value = write_data
        dut.write_type_i.value = 0b10  # Write a word
        dut.write_enable_i.value = 1

        # Wait for a clock cycle to perform the write
        await RisingEdge(dut.clk_i)

        await FallingEdge(dut.clk_i)

        # Disable write enable for read operation
        dut.write_enable_i.value = 0

        # Clear write inputs
        dut.write_data_i.value = 0
        dut.write_type_i.value = 0

        # Wait for a clock cycle to perform the read
        await RisingEdge(dut.clk_i)

        await ReadOnly()

        # Check if the read data matches the written data
        assert dut.read_data_o.value.to_unsigned() == write_data, (
            f"Read/Write cycle failed: {dut.read_data_o.value.to_unsigned()} != {write_data}"
        )


@cocotb.test()
async def random_rw_cycle(dut):
    """Test non-sequenced read/write cycle of the sync RAM"""
    clock = Clock(dut.clk_i, 1, "ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    for i in range(440):
        # Maintain a 5 entry list of previous writes to check against reads
        WORD_COUNT = 256

        addresses = random.sample(range(WORD_COUNT), 5)

        write_queue = [
            (word_addr << 2, random.getrandbits(32)) for word_addr in addresses
        ]
        written_entry = []

        while write_queue or written_entry:
            # Determine whether to do a random write or not based on the items left in the queue
            if random.uniform(0, 1) < (1 / len(write_queue) if write_queue else 0):
                write_addr, write_data = write_queue.pop()
                written_entry.append((write_addr, write_data))

                await FallingEdge(dut.clk_i)

                # Set write inputs
                dut.addr_i.value = write_addr
                dut.write_data_i.value = write_data
                dut.write_type_i.value = 0b10  # Write a word
                dut.write_enable_i.value = 1

                # Wait for a clock cycle to perform the write
                await RisingEdge(dut.clk_i)

                await FallingEdge(dut.clk_i)

                # Disable write enable for read operation
                dut.write_enable_i.value = 0

                # Clear write inputs
                dut.write_data_i.value = 0
                dut.write_type_i.value = 0

            # Determine whether to do a random write or not based on the items left in the queue
            if (
                random.uniform(0, 1) > (1 / len(write_queue) if write_queue else 0)
                and written_entry
            ):
                read_addr, expected_data = written_entry.pop()

                await FallingEdge(dut.clk_i)

                # Set read address
                dut.addr_i.value = read_addr
                # Ensure that write enable is disabled for read operation
                dut.write_enable_i.value = 0

                # Wait for a clock cycle to perform the read
                await RisingEdge(dut.clk_i)

                await ReadOnly()

                # Check if the read data matches the expected data
                if expected_data is not None:
                    assert dut.read_data_o.value.to_unsigned() == expected_data, (
                        f"Read/Write cycle failed: {dut.read_data_o.value.to_unsigned()} != {expected_data}"
                    )


@cocotb.test()
async def data_patterns(dut):
    """Test read/write cycle of the sync RAM with specific data patterns"""
    clock = Clock(dut.clk_i, 1, "ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    # Define specific data patterns to test
    data_patterns = [
        0x00000000,  # All zeros
        0xFFFFFFFF,  # All ones
        0xAAAAAAAA,  # Alternating bits (1010...)
        0x55555555,  # Alternating bits (0101...)
        0x12345678,  # Arbitrary pattern
        0x87654321,  # Arbitrary pattern
    ]

    for write_data in data_patterns:
        write_addr = random.randint(0, 255) << 2

        await FallingEdge(dut.clk_i)

        # Set write inputs
        dut.addr_i.value = write_addr
        dut.write_data_i.value = write_data
        dut.write_type_i.value = 0b10  # Write a word
        dut.write_enable_i.value = 1

        # Wait for a clock cycle to perform the write
        await RisingEdge(dut.clk_i)

        await FallingEdge(dut.clk_i)

        # Disable write enable for read operation
        dut.write_enable_i.value = 0

        # Clear write inputs
        dut.write_data_i.value = 0
        dut.write_type_i.value = 0

        # Wait for a clock cycle to perform the read
        await RisingEdge(dut.clk_i)

        await ReadOnly()

        # Check if the read data matches the written data
        assert dut.read_data_o.value.to_unsigned() == write_data, (
            f"Read/Write cycle failed: {dut.read_data_o.value.to_unsigned()} != {write_data}"
        )


@cocotb.test()
async def sequential_write(dut):
    """Test sequential write of the sync RAM"""
    clock = Clock(dut.clk_i, 1, "ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    for i in range(32):
        write_addr = i << 2  # Word-aligned addresses
        write_data = 0xFFFFFFFF - i  # Decreasing pattern

        await FallingEdge(dut.clk_i)

        # Set write inputs
        dut.addr_i.value = write_addr
        dut.write_data_i.value = write_data
        dut.write_type_i.value = 0b10  # Write a word
        dut.write_enable_i.value = 1

        # Wait for a clock cycle to perform the write
        await RisingEdge(dut.clk_i)

        await FallingEdge(dut.clk_i)

        # Disable write enable for read operation
        dut.write_enable_i.value = 0

        # Clear write inputs
        dut.write_data_i.value = 0
        dut.write_type_i.value = 0


@cocotb.test()
async def sequential_read(dut):
    """Test sequential read of the sync RAM"""
    clock = Clock(dut.clk_i, 1, "ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    for i in range(32):
        await FallingEdge(dut.clk_i)
        dut.addr_i.value = i << 2
        dut.write_data_i.value = 0xFFFFFFFF - i
        dut.write_type_i.value = 0b10
        dut.write_enable_i.value = 1
        await RisingEdge(dut.clk_i)

    for i in range(32):
        read_addr = i << 2  # Word-aligned addresses

        await FallingEdge(dut.clk_i)

        # Set read address
        dut.addr_i.value = read_addr
        # Ensure that write enable is disabled for read operation
        dut.write_enable_i.value = 0

        # Check if immediate read without waiting for a synchronous event reads the previous round of data (except for the first read, which is undefined)
        assert (
            dut.read_data_o.value.to_unsigned() == 0xFFFFFFFF - (i - 1)
            if i > 0
            else True
        ), (
            f"Immediate read failed: {dut.read_data_o.value.to_unsigned()} != {0xFFFFFFFF - (i - 1) if i > 0 else 0}"
        )

        # Wait for a clock cycle to perform the read
        await RisingEdge(dut.clk_i)

        await ReadOnly()

        # Check if the read data matches the expected data
        expected_data = 0xFFFFFFFF - i
        assert dut.read_data_o.value.to_unsigned() == expected_data, (
            f"Read/Write cycle failed: {dut.read_data_o.value.to_unsigned()} != {expected_data}"
        )


@cocotb.test()
async def byte_rw(dut):
    """Test read/write cycle of the sync RAM with byte writes"""
    clock = Clock(dut.clk_i, 1, "ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    for i in range(2200):
        # Generate random values for write
        write_addr = random.randint(0, 1023)
        write_data = random.randint(0, 2**8 - 1)

        await FallingEdge(dut.clk_i)

        # Set write inputs
        dut.addr_i.value = write_addr
        dut.write_data_i.value = write_data
        dut.write_type_i.value = 0b00  # Write a byte
        dut.write_enable_i.value = 1

        # Wait for a clock cycle to perform the write
        await RisingEdge(dut.clk_i)

        await FallingEdge(dut.clk_i)

        # Disable write enable for read operation
        dut.write_enable_i.value = 0

        # Clear write inputs
        dut.write_data_i.value = 0
        dut.write_type_i.value = 0

        # Wait for a clock cycle to perform the read
        await RisingEdge(dut.clk_i)

        await ReadOnly()

        # Deduct byte index in the read word
        byte_index = write_addr % 4

        # Check if the read byte matches the written byte
        read_byte = (dut.read_data_o.value.to_unsigned() >> (byte_index * 8)) & 0xFF
        assert read_byte == write_data, (
            f"Read/Write cycle failed: {read_byte} != {write_data}"
        )


@cocotb.test()
async def halfword_rw(dut):
    """Test read/write cycle of the sync RAM with halfword writes"""
    clock = Clock(dut.clk_i, 1, "ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    for i in range(2200):
        # Generate random values for write
        write_addr = random.randint(0, 511) << 1
        write_data = random.randint(0, 2**16 - 1)

        await FallingEdge(dut.clk_i)

        # Set write inputs
        dut.addr_i.value = write_addr
        dut.write_data_i.value = write_data
        dut.write_type_i.value = 0b01  # Write a halfword
        dut.write_enable_i.value = 1

        # Wait for a clock cycle to perform the write
        await RisingEdge(dut.clk_i)

        await FallingEdge(dut.clk_i)

        # Disable write enable for read operation
        dut.write_enable_i.value = 0

        # Clear write inputs
        dut.write_data_i.value = 0
        dut.write_type_i.value = 0

        # Wait for a clock cycle to perform the read
        await RisingEdge(dut.clk_i)

        await ReadOnly()

        # Deduct halfword index in the read word
        halfword_index = write_addr % 2

        # Check if the read halfword matches the written halfword
        read_halfword = (
            dut.read_data_o.value.to_unsigned() >> (halfword_index * 16)
        ) & 0xFFFF
        assert read_halfword == write_data, (
            f"Read/Write cycle failed: {read_halfword} != {write_data}"
        )


@cocotb.test()
async def concurrent_rw_cycle(dut):
    """Test concurrent read/write cycle of the sync RAM"""
    clock = Clock(dut.clk_i, 1, "ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    for i in range(2200):
        # Generate random values for write
        write_addr = random.randint(0, 255) << 2
        write_data = random.randint(0, 2**32 - 1)

        await FallingEdge(dut.clk_i)

        dut.addr_i.value = write_addr

        # Wait for a clock cycle to perform the read
        await RisingEdge(dut.clk_i)

        await ReadOnly()

        # Record old read data before the write operation
        old_read_data = dut.read_data_o.value.to_unsigned()

        await FallingEdge(dut.clk_i)

        # Set write inputs
        dut.write_data_i.value = write_data
        dut.write_type_i.value = 0b10  # Write a word
        dut.write_enable_i.value = 1

        # Wait for a clock cycle to perform the read/write
        await RisingEdge(dut.clk_i)

        await ReadOnly()

        # Check if the read data matches the old read data only for this cycle, since the write operation is synchronous and will not affect the read data until the next clock cycle
        assert dut.read_data_o.value.to_unsigned() == old_read_data, (
            f"Concurrent Read/Write cycle failed: {dut.read_data_o.value.to_unsigned()} != {old_read_data}"
        )

        await FallingEdge(dut.clk_i)

        # Disable write enable for read operation
        dut.write_enable_i.value = 0

        # Wait for another clock cycle to perform the read after the write operation
        await RisingEdge(dut.clk_i)

        await ReadOnly()

        # Check if the read data matches the written data after the write operation
        assert dut.read_data_o.value.to_unsigned() == write_data, (
            f"Concurrent Read/Write cycle failed: {dut.read_data_o.value.to_unsigned()} != {write_data}"
        )


@cocotb.test()
async def asynchronous_reset_clears_memory(dut):
    """Assert rst_ni between clock edges and verify a prior RAM write is erased."""
    clock = Clock(dut.clk_i, 1, "ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    await FallingEdge(dut.clk_i)
    dut.addr_i.value = 0
    dut.write_data_i.value = 0xDEADBEEF
    dut.write_type_i.value = 0b10
    dut.write_enable_i.value = 1
    await RisingEdge(dut.clk_i)

    dut.rst_ni.value = 0
    await Timer(1, "ns")
    dut.rst_ni.value = 1
    dut.write_enable_i.value = 0
    await RisingEdge(dut.clk_i)
    await ReadOnly()
    assert dut.read_data_o.value.to_unsigned() == 0
