import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer


async def reset_dut(dut):
    dut.rst_ni.value = 0
    await Timer(1, "ns")
    dut.rst_ni.value = 1
    await Timer(1, "ns")


@cocotb.test()
async def rw_cycle(dut):
    """Test read/write cycle of the register file"""
    clock = Clock(dut.clk_i, 1, "ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)
    for i in range(2200):
        # Generate random values for write
        write_addr_a = random.randint(1, 31)  # Register addresses 1-31
        write_data_a = random.randint(0, 2**32 - 1)
        write_addr_b = random.choice([addr for addr in range(1, 32) if addr != write_addr_a]) # Register addresses 1-31 excluding write_addr_a
        write_data_b = random.randint(0, 2**32 - 1)

        for write_addr, write_data in [
            (write_addr_a, write_data_a),
            (write_addr_b, write_data_b),
        ]:
            # Set write inputs
            dut.write_addr_i.value = write_addr
            dut.write_data_i.value = write_data
            dut.write_enable_i.value = 1

            # Wait for a clock cycle to perform the write
            await Timer(1, "ns")

            # Disable write enable for read operation
            dut.write_enable_i.value = 0

            # Clear write inputs
            dut.write_addr_i.value = 0
            dut.write_data_i.value = 0

        # Set read address to the same as write address
        dut.read_addr_a_i.value = write_addr_a

        # Wait for a clock cycle to perform the read
        await Timer(1, "ns")

        # Check if the read data matches the written data
        assert dut.read_data_a_o.value.to_unsigned() == write_data_a, (
            f"Read/Write cycle failed: {dut.read_data_a_o.value.to_unsigned()} != {write_data_a}"
        )

        # Set read address to the same as write address
        dut.read_addr_b_i.value = write_addr_b

        # Wait for a clock cycle to perform the read
        await Timer(1, "ns")

        # Check if the read data matches the written data
        assert dut.read_data_b_o.value.to_unsigned() == write_data_b, (
            f"Read/Write cycle failed: {dut.read_data_b_o.value.to_unsigned()} != {write_data_b}"
        )


@cocotb.test()
async def concurrent_read(dut):
    """Test concurrent read of the register file"""
    clock = Clock(dut.clk_i, 1, "ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)
    for i in range(100):
        # Generate random values for write
        write_addr_a = random.randint(1, 31)  # Register addresses 1-31
        write_data_a = random.randint(0, 2**32 - 1)
        write_addr_b = random.choice([addr for addr in range(1, 32) if addr != write_addr_a]) # Register addresses 1-31 excluding write_addr_a
        write_data_b = random.randint(0, 2**32 - 1)

        for write_addr, write_data in [
            (write_addr_a, write_data_a),
            (write_addr_b, write_data_b),
        ]:
            # Set write inputs
            dut.write_addr_i.value = write_addr
            dut.write_data_i.value = write_data
            dut.write_enable_i.value = 1

            # Wait for a clock cycle to perform the write
            await Timer(1, "ns")

            # Disable write enable for read operation
            dut.write_enable_i.value = 0

            # Clear write inputs
            dut.write_addr_i.value = 0
            dut.write_data_i.value = 0

        # Set read addresses to the same as write addresses
        dut.read_addr_a_i.value = write_addr_a
        dut.read_addr_b_i.value = write_addr_b

        # Wait for a clock cycle to perform the read
        await Timer(1, "ns")

        # Check if the read data matches the written data
        assert dut.read_data_a_o.value.to_unsigned() == write_data_a, (
            f"Concurrent Read failed: {dut.read_data_a_o.value.to_unsigned()} != {write_data_a}"
        )
        assert dut.read_data_b_o.value.to_unsigned() == write_data_b, (
            f"Concurrent Read failed: {dut.read_data_b_o.value.to_unsigned()} != {write_data_b}"
        )

@cocotb.test()
async def overwrite(dut):
    """Test overwrite of the register file"""
    clock = Clock(dut.clk_i, 1, "ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)
    for i in range(100):
        # Generate random values for write
        write_addr = random.randint(1, 31)  # Register addresses 1-31
        write_data_a = random.randint(0, 2**32 - 1)
        write_data_b = random.randint(0, 2**32 - 1)

        # First write operation
        dut.write_addr_i.value = write_addr
        dut.write_data_i.value = write_data_a
        dut.write_enable_i.value = 1

        # Wait for a clock cycle to perform the write
        await Timer(1, "ns")

        # Second write operation to the same address
        dut.write_data_i.value = write_data_b

        # Wait for a clock cycle to perform the second write
        await Timer(1, "ns")

        # Disable write enable for read operation
        dut.write_enable_i.value = 0

        # Clear write inputs
        dut.write_addr_i.value = 0
        dut.write_data_i.value = 0

        # Set read address to the same as write address
        dut.read_addr_a_i.value = write_addr

        # Wait for a clock cycle to perform the read
        await Timer(1, "ns")

        # Check if the read data matches the last written data
        assert dut.read_data_a_o.value.to_unsigned() == write_data_b, (
            f"Same Port Overwrite failed: {dut.read_data_a_o.value.to_unsigned()} != {write_data_b}"
        )

@cocotb.test()
async def zero_read(dut):
    """Test that reading from register 0 always returns 0"""
    await reset_dut(dut)
    for i in range(100):
        # Set read address to register 0
        dut.read_addr_a_i.value = 0

        # Wait for a clock cycle to perform the read
        await Timer(1, "ns")

        # Check if the read data is always 0
        assert dut.read_data_a_o.value.to_unsigned() == 0, (
            f"Zero Read failed: {dut.read_data_a_o.value.to_unsigned()} != 0"
        )

@cocotb.test()
async def zero_write(dut):
    """Test that writing to register 0 has no effect"""
    await reset_dut(dut)
    for i in range(100):
        # Set write address to register 0
        dut.write_addr_i.value = 0
        dut.write_data_i.value = random.randint(0, 2**32 - 1)
        dut.write_enable_i.value = 1

        # Wait for a clock cycle to perform the write
        await Timer(1, "ns")

        # Disable write enable for read operation
        dut.write_enable_i.value = 0

        # Clear write inputs
        dut.write_addr_i.value = 0
        dut.write_data_i.value = 0

        # Set read address to register 0
        dut.read_addr_a_i.value = 0

        # Wait for a clock cycle to perform the read
        await Timer(1, "ns")

        # Check if the read data is always 0
        assert dut.read_data_a_o.value.to_unsigned() == 0, (
            f"Zero Write failed: {dut.read_data_a_o.value.to_unsigned()} != 0"
        )


@cocotb.test()
async def asynchronous_reset_clears_registers(dut):
    """Assert rst_ni between clock edges and verify register contents clear immediately."""
    clock = Clock(dut.clk_i, 1, "ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    dut.write_addr_i.value = 1
    dut.write_data_i.value = 0xDEADBEEF
    dut.write_enable_i.value = 1
    await Timer(1, "ns")
    dut.write_enable_i.value = 0
    dut.read_addr_a_i.value = 1
    await Timer(1, "ns")
    assert dut.read_data_a_o.value.to_unsigned() == 0xDEADBEEF

    dut.rst_ni.value = 0
    await Timer(1, "ns")
    assert dut.read_data_a_o.value.to_unsigned() == 0
    dut.rst_ni.value = 1
