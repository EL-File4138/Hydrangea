import random

import cocotb
from cocotb.triggers import Timer


@cocotb.test()
async def boundary_slt(dut):
    """Test signed set-less-than boundaries."""
    for a, b, expected in [
        (0xFFFFFFFF, 0, 1),  # -1 < 0
        (0x80000000, 0xFFFFFFFF, 1),  # INT_MIN < -1
        (0x7FFFFFFF, 0, 0),  # INT_MAX > 0
    ]:
        dut.operand_a_i.value = a
        dut.operand_b_i.value = b
        dut.opcode_i.value = 0b0010
        await Timer(10, "ns")
        assert dut.result_o.value == expected, (
            f"Signed SLT failed: {a:#010x} < {b:#010x}"
        )


@cocotb.test()
async def boundary_sltu(dut):
    """Test unsigned set-less-than boundaries."""
    for a, b, expected in [
        (0xFFFFFFFF, 0, 0),  # UINT_MAX > 0
        (0x80000000, 0x7FFFFFFF, 0),  # 0x80000000 > 0x7fffffff
    ]:
        dut.operand_a_i.value = a
        dut.operand_b_i.value = b
        dut.opcode_i.value = 0b0011
        await Timer(10, "ns")
        assert dut.result_o.value == expected, (
            f"Unsigned SLTU failed: {a:#010x} < {b:#010x}"
        )


@cocotb.test()
async def boundary_sll(dut):
    """Test logical left-shift boundaries."""
    for a in [0, 1, 0xFFFFFFFF, 0x80000000, 0x7FFFFFFF]:
        for b in [0, 1, 31]:
            dut.operand_a_i.value = a
            dut.operand_b_i.value = b
            dut.opcode_i.value = 0b0001
            await Timer(10, "ns")
            expected = (a << b) & 0xFFFFFFFF
            assert dut.result_o.value == expected, f"SLL failed: a={a:#010x}, b={b}"


@cocotb.test()
async def boundary_srl(dut):
    """Test logical right-shift boundaries."""
    for a in [0, 1, 0xFFFFFFFF, 0x80000000, 0x7FFFFFFF]:
        for b in [0, 1, 31]:
            dut.operand_a_i.value = a
            dut.operand_b_i.value = b
            dut.opcode_i.value = 0b0101
            await Timer(10, "ns")
            expected = a >> b
            assert dut.result_o.value == expected, f"SRL failed: a={a:#010x}, b={b}"


@cocotb.test()
async def boundary_sra(dut):
    """Test arithmetic right-shift boundaries."""
    for a in [0, 1, 0xFFFFFFFF, 0x80000000, 0x7FFFFFFF]:
        for b in [0, 1, 31]:
            dut.operand_a_i.value = a
            dut.operand_b_i.value = b
            dut.opcode_i.value = 0b1101
            await Timer(10, "ns")
            a_signed = a if a < 0x80000000 else a - 2**32
            expected = (a_signed >> b) & 0xFFFFFFFF
            assert dut.result_o.value == expected, f"SRA failed: a={a:#010x}, b={b}"


@cocotb.test()
async def addition(dut):
    """Test addition operation of the ALU"""
    for i in range(2200):
        a = random.randint(0, 2**32 - 1)
        b = random.randint(0, 2**32 - 1)

        # Set input values
        dut.operand_a_i.value = a
        dut.operand_b_i.value = b
        dut.opcode_i.value = 0b0000  # Opcode as concanation of {func7[5], funct3}

        # Wait for a clock cycle
        await Timer(10, "ns")

        # Reparse a, b as signed integers for correct addition
        a_signed = a if a < 2**31 else a - 2**32
        b_signed = b if b < 2**31 else b - 2**32

        # Check the result
        assert dut.result_o.value == (a_signed + b_signed) & 0xFFFFFFFF, (
            f"Addition failed: {dut.result_o.value} != {a_signed + b_signed}"
        )


@cocotb.test()
async def subtraction(dut):
    """Test subtraction operation of the ALU"""
    for i in range(2200):
        a = random.randint(0, 2**32 - 1)
        b = random.randint(0, 2**32 - 1)

        # Set input values
        dut.operand_a_i.value = a
        dut.operand_b_i.value = b
        dut.opcode_i.value = 0b1000  # Opcode as concanation of {func7[5], funct3}

        # Wait for a clock cycle
        await Timer(10, "ns")

        # Reparse a, b as signed integers for correct subtraction
        a_signed = a if a < 2**31 else a - 2**32
        b_signed = b if b < 2**31 else b - 2**32

        # Check the result
        assert dut.result_o.value == (a_signed - b_signed) & 0xFFFFFFFF, (
            f"Subtraction failed: {dut.result_o.value} != {a_signed - b_signed}"
        )


@cocotb.test()
async def xor_op(dut):
    """Test XOR operation of the ALU"""
    for i in range(2200):
        a = random.randint(0, 2**32 - 1)
        b = random.randint(0, 2**32 - 1)

        # Set input values
        dut.operand_a_i.value = a
        dut.operand_b_i.value = b
        dut.opcode_i.value = 0b0100  # Opcode as concanation of {func7[5], funct3}

        # Wait for a clock cycle
        await Timer(10, "ns")

        # Check the result
        assert dut.result_o.value == (a ^ b) & 0xFFFFFFFF, (
            f"XOR failed: {dut.result_o.value} != {a ^ b}"
        )


@cocotb.test()
async def or_op(dut):
    """Test OR operation of the ALU"""
    for i in range(2200):
        a = random.randint(0, 2**32 - 1)
        b = random.randint(0, 2**32 - 1)

        # Set input values
        dut.operand_a_i.value = a
        dut.operand_b_i.value = b
        dut.opcode_i.value = 0b0110  # Opcode as concanation of {func7[5], funct3}

        # Wait for a clock cycle
        await Timer(10, "ns")

        # Check the result
        assert dut.result_o.value == (a | b) & 0xFFFFFFFF, (
            f"OR failed: {dut.result_o.value} != {a | b}"
        )


@cocotb.test()
async def and_op(dut):
    """Test AND operation of the ALU"""
    for i in range(2200):
        a = random.randint(0, 2**32 - 1)
        b = random.randint(0, 2**32 - 1)

        # Set input values
        dut.operand_a_i.value = a
        dut.operand_b_i.value = b
        dut.opcode_i.value = 0b0111  # Opcode as concanation of {func7[5], funct3}

        # Wait for a clock cycle
        await Timer(10, "ns")

        # Check the result
        assert dut.result_o.value == (a & b) & 0xFFFFFFFF, (
            f"AND failed: {dut.result_o.value} != {a & b}"
        )


@cocotb.test()
async def set_less_than_op(dut):
    """Test set less than operation of the ALU"""
    for i in range(2200):
        a = random.randint(0, 2**32 - 1)
        b = random.randint(0, 2**32 - 1)

        # Set input values
        dut.operand_a_i.value = a
        dut.operand_b_i.value = b
        dut.opcode_i.value = 0b0010  # Opcode as concanation of {func7[5], funct3}

        # Wait for a clock cycle
        await Timer(10, "ns")

        # Reparse a, b as signed integers for correct comparison
        a_signed = a if a < 2**31 else a - 2**32
        b_signed = b if b < 2**31 else b - 2**32

        # Check the result
        expected_result = 1 if a_signed < b_signed else 0
        assert dut.result_o.value == expected_result, (
            f"Set Less Than failed: {dut.result_o.value} != {expected_result}"
        )


@cocotb.test()
async def set_less_than_unsigned_op(dut):
    """Test set less than unsigned operation of the ALU"""
    for i in range(2200):
        a = random.randint(0, 2**32 - 1)
        b = random.randint(0, 2**32 - 1)

        # Set input values
        dut.operand_a_i.value = a
        dut.operand_b_i.value = b
        dut.opcode_i.value = 0b0011  # Opcode as concanation of {func7[5], funct3}

        # Wait for a clock cycle
        await Timer(10, "ns")

        # Check the result
        expected_result = 1 if a < b else 0
        assert dut.result_o.value == expected_result, (
            f"Set Less Than Unsigned failed: {dut.result_o.value} != {expected_result}"
        )


@cocotb.test()
async def shift_left_logical_op(dut):
    """Test shift left logical operation of the ALU"""
    for i in range(2200):
        a = random.randint(0, 2**32 - 1)
        b = random.randint(0, 31)  # Shift amount should be between 0 and 31

        # Set input values
        dut.operand_a_i.value = a
        dut.operand_b_i.value = b
        dut.opcode_i.value = 0b0001  # Opcode as concanation of {func7[5], funct3}

        # Wait for a clock cycle
        await Timer(10, "ns")

        # Check the result
        assert dut.result_o.value == (a << b) & 0xFFFFFFFF, (
            f"Shift Left Logical failed: {dut.result_o.value} != {(a << b) & 0xFFFFFFFF}"
        )


@cocotb.test()
async def shift_right_logical_op(dut):
    """Test shift right logical operation of the ALU"""
    for i in range(2200):
        a = random.randint(0, 2**32 - 1)
        b = random.randint(0, 31)  # Shift amount should be between 0 and 31

        # Set input values
        dut.operand_a_i.value = a
        dut.operand_b_i.value = b
        dut.opcode_i.value = 0b0101  # Opcode as concanation of {func7[5], funct3}

        # Wait for a clock cycle
        await Timer(10, "ns")

        # Check the result
        assert dut.result_o.value == (a >> b) & 0xFFFFFFFF, (
            f"Shift Right Logical failed: {dut.result_o.value} != {(a >> b) & 0xFFFFFFFF}"
        )


@cocotb.test()
async def shift_right_arithmetic_op(dut):
    """Test shift right arithmetic operation of the ALU"""
    for i in range(2200):
        a = random.randint(0, 2**32 - 1)
        b = random.randint(0, 31)  # Shift amount should be between 0 and 31

        # Set input values
        dut.operand_a_i.value = a
        dut.operand_b_i.value = b
        dut.opcode_i.value = 0b1101  # Opcode as concanation of {func7[5], funct3}

        # Wait for a clock cycle
        await Timer(10, "ns")

        # Reparse a as signed integer for correct arithmetic shift
        a_signed = a if a < 2**31 else a - 2**32

        # Check the result
        expected_result = (a_signed >> b) & 0xFFFFFFFF
        assert dut.result_o.value == expected_result, (
            f"Shift Right Arithmetic failed: {dut.result_o.value} != {expected_result}"
        )
