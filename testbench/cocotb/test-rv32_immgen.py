import random

import cocotb
from cocotb.triggers import Timer


@cocotb.test()
async def bit_width(dut):
    """Test the bit width of the immediate generator output."""
    # Randomly charge the input instruction and type
    for _ in range(100):
        dut.inst_i.value = random.randint(0, 2**32 - 1)
        dut.inst_fmt_i.value = random.randint(1, 5)
        await Timer(1, 'ns')  # Wait for a short time to allow the DUT to process

        # Check the bit width of the output
        assert dut.imm_o.value.to_unsigned() < 2**32, f"Output exceeds 32 bits: {dut.imm_o.value}"

@cocotb.test()
async def I_type(dut):
    """Test the immediate generator for I-type instructions."""
    for _ in range(100):
        inst = random.randint(0, 2**32 - 1)
        dut.inst_i.value = inst
        dut.inst_fmt_i.value = 1  # I-type format
        await Timer(1, "ns")

        expected_output = ((inst >> 20) & 0xFFF)
        if expected_output & 0x800:
            expected_output |= 0xFFFFF000

        assert dut.imm_o.value.to_unsigned() == expected_output, (
            f"I-type immediate mismatch: {dut.imm_o.value.to_unsigned():#010x} != {expected_output:#010x}"
        )

@cocotb.test()
async def S_type(dut):
    """Test the immediate generator for S-type instructions."""
    for _ in range(100):
        inst = random.randint(0, 2**32 - 1)
        dut.inst_i.value = inst
        dut.inst_fmt_i.value = 2  # S-type format
        await Timer(1, "ns")

        expected_output = ((inst >> 25) & 0x7F) << 5 | ((inst >> 7) & 0x1F)
        if expected_output & 0x800:
            expected_output |= 0xFFFFF000

        assert dut.imm_o.value.to_unsigned() == expected_output, (
            f"S-type immediate mismatch: {dut.imm_o.value.to_unsigned():#010x} != {expected_output:#010x}"
        )


@cocotb.test()
async def B_type(dut):
    """Test the immediate generator for B-type instructions."""
    for _ in range(100):
        inst = random.randint(0, 2**32 - 1)
        dut.inst_i.value = inst
        dut.inst_fmt_i.value = 3  # B-type format
        await Timer(1, "ns")

        expected_output = (
            ((inst >> 31) & 0x1) << 12
            | ((inst >> 7) & 0x1) << 11
            | ((inst >> 25) & 0x3F) << 5
            | ((inst >> 8) & 0xF) << 1
        )
        if expected_output & 0x1000:
            expected_output |= 0xFFFFE000

        assert dut.imm_o.value.to_unsigned() == expected_output, (
            f"B-type immediate mismatch: {dut.imm_o.value.to_unsigned():#010x} != {expected_output:#010x}"
        )


@cocotb.test()
async def U_type(dut):
    """Test the immediate generator for U-type instructions."""
    for _ in range(100):
        inst = random.randint(0, 2**32 - 1)
        dut.inst_i.value = inst
        dut.inst_fmt_i.value = 4  # U-type format
        await Timer(1, "ns")

        expected_output = inst & 0xFFFFF000

        assert dut.imm_o.value.to_unsigned() == expected_output, (
            f"U-type immediate mismatch: {dut.imm_o.value.to_unsigned():#010x} != {expected_output:#010x}"
        )


@cocotb.test()
async def J_type(dut):
    """Test the immediate generator for J-type instructions."""
    for _ in range(100):
        inst = random.randint(0, 2**32 - 1)
        dut.inst_i.value = inst
        dut.inst_fmt_i.value = 5  # J-type format
        await Timer(1, "ns")

        expected_output = (
            ((inst >> 31) & 0x1) << 20
            | ((inst >> 12) & 0xFF) << 12
            | ((inst >> 20) & 0x1) << 11
            | ((inst >> 21) & 0x3FF) << 1
        )
        if expected_output & 0x100000:
            expected_output |= 0xFFE00000

        assert dut.imm_o.value.to_unsigned() == expected_output, (
            f"J-type immediate mismatch: {dut.imm_o.value.to_unsigned():#010x} != {expected_output:#010x}"
        )
