import random

import cocotb
from cocotb.triggers import Timer

# Encodings from rv32_inst_pkg.sv.
CTRL_BEQ = 0b000
CTRL_BNE = 0b001
CTRL_JALR = 0b010
CTRL_JAL = 0b011
CTRL_BLT = 0b100
CTRL_BGE = 0b101
CTRL_BLTU = 0b110
CTRL_BGEU = 0b111

MASK32 = 0xFFFFFFFF


def signed32(value):
    return value if value < (1 << 31) else value - (1 << 32)


def branch_taken(ctrl_op_i, operand_a, operand_b):
    if ctrl_op_i == CTRL_BEQ:
        return operand_a == operand_b
    if ctrl_op_i == CTRL_BNE:
        return operand_a != operand_b
    if ctrl_op_i == CTRL_BLT:
        return signed32(operand_a) < signed32(operand_b)
    if ctrl_op_i == CTRL_BGE:
        return signed32(operand_a) >= signed32(operand_b)
    if ctrl_op_i == CTRL_BLTU:
        return operand_a < operand_b
    if ctrl_op_i == CTRL_BGEU:
        return operand_a >= operand_b
    raise ValueError(f"not a conditional branch: {ctrl_op_i}")


async def drive_ctrl(dut, ctrl_op_i, pc, operand_a, operand_b, imm):
    dut.ctrl_op_i.value = ctrl_op_i
    dut.pc_v_i.value = pc
    dut.operand_a_i.value = operand_a
    dut.operand_b_i.value = operand_b
    dut.imm_i.value = imm
    await Timer(1, "ns")
    return dut.pc_v_o.value.to_unsigned(), dut.rd_v_o.value.to_unsigned()


async def assert_branch(dut, ctrl_op_i, pc, operand_a, operand_b, imm):
    actual_pc, _ = await drive_ctrl(dut, ctrl_op_i, pc, operand_a, operand_b, imm)
    expected_pc = (
        pc + (imm if branch_taken(ctrl_op_i, operand_a, operand_b) else 4)
    ) & MASK32
    assert actual_pc == expected_pc, (
        f"ctrl_op_i={ctrl_op_i:#x}, pc={pc:#010x}, a={operand_a:#010x}, "
        f"b={operand_b:#010x}, imm={imm:#010x}: pc_v_o={actual_pc:#010x}, "
        f"expected {expected_pc:#010x}"
    )


BRANCH_CASES = (
    ("beq", CTRL_BEQ, ((7, 7), (7, 8))),
    ("bne", CTRL_BNE, ((7, 8), (7, 7))),
    ("blt", CTRL_BLT, ((0x80000000, 0xFFFFFFFF), (0x7FFFFFFF, 0))),
    ("bge", CTRL_BGE, ((0, 0xFFFFFFFF), (0x80000000, 0))),
    ("bltu", CTRL_BLTU, ((0, 0xFFFFFFFF), (7, 7), (0xFFFFFFFF, 0))),
    ("bgeu", CTRL_BGEU, ((0xFFFFFFFF, 0), (0, 0xFFFFFFFF))),
)


def _make_branch_test(name, ctrl_op_i, operands):
    @cocotb.test(name=f"{name}_taken_and_fallthrough")
    async def branch_test(dut):
        """Check both target and pc+4 paths for one conditional branch."""
        for operand_a, operand_b in operands:
            await assert_branch(dut, ctrl_op_i, 0x100, operand_a, operand_b, 0xFFFFFFF0)

    return branch_test


for _name, _ctrl_op_i, _operands in BRANCH_CASES:
    globals()[f"{_name}_taken_and_fallthrough"] = _make_branch_test(
        _name, _ctrl_op_i, _operands
    )


@cocotb.test()
async def jal_writes_link_and_uses_instruction_pc(dut):
    """JAL targets pc_v_i + imm_i and writes pc_v_i + 4, including wraparound."""
    for pc, imm in ((0x100, 0xFFFFFFF0), (0xFFFFFFFC, 4)):
        actual_pc, actual_rd = await drive_ctrl(dut, CTRL_JAL, pc, 0, 0, imm)
        assert actual_pc == (pc + imm) & MASK32
        assert actual_rd == (pc + 4) & MASK32


@cocotb.test()
async def jalr_writes_link_and_clears_target_lsb(dut):
    """JALR targets (operand_a_i + imm_i) & ~1 and writes pc_v_i + 4."""
    for pc, operand_a, imm in ((0x100, 0x20000001, 2), (0xFFFFFFFC, 0xFFFFFFFF, 2)):
        actual_pc, actual_rd = await drive_ctrl(dut, CTRL_JALR, pc, operand_a, 0, imm)
        assert actual_pc == ((operand_a + imm) & ~1) & MASK32
        assert actual_rd == (pc + 4) & MASK32


@cocotb.test()
async def random_control_targets_match_reference(dut):
    """Exercise every CTRL micro-op with randomly generated 32-bit operands."""
    ctrl_op_is = (
        CTRL_BEQ,
        CTRL_BNE,
        CTRL_BLT,
        CTRL_BGE,
        CTRL_BLTU,
        CTRL_BGEU,
        CTRL_JAL,
        CTRL_JALR,
    )
    for _ in range(2200):
        ctrl_op_i = random.choice(ctrl_op_is)
        pc = random.getrandbits(32)
        operand_a = random.getrandbits(32)
        operand_b = random.getrandbits(32)
        imm = random.getrandbits(32)
        actual_pc, actual_rd = await drive_ctrl(
            dut, ctrl_op_i, pc, operand_a, operand_b, imm
        )

        if ctrl_op_i == CTRL_JAL:
            expected_pc = (pc + imm) & MASK32
            expected_rd = (pc + 4) & MASK32
        elif ctrl_op_i == CTRL_JALR:
            expected_pc = ((operand_a + imm) & ~1) & MASK32
            expected_rd = (pc + 4) & MASK32
        else:
            expected_pc = (
                pc + (imm if branch_taken(ctrl_op_i, operand_a, operand_b) else 4)
            ) & MASK32
            expected_rd = None

        assert actual_pc == expected_pc, (
            f"ctrl_op_i={ctrl_op_i:#x}: pc_v_o={actual_pc:#010x}, expected {expected_pc:#010x}"
        )
        if expected_rd is not None:
            assert actual_rd == expected_rd, (
                f"ctrl_op_i={ctrl_op_i:#x}: rd_v_o={actual_rd:#010x}, expected {expected_rd:#010x}"
            )
