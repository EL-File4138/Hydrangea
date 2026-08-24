import random

import cocotb
from cocotb.triggers import Timer


# Encodings from rv32_inst_pkg.sv. inst_sem_t is packed MSB-first in declaration
# order, so these constants also describe the public sem_o port layout.
ALU_ADD = 0b0000
ALU_SUB = 0b1000
ALU_SLL = 0b0001
ALU_SLT = 0b0010
ALU_SLTU = 0b0011
ALU_XOR = 0b0100
ALU_SRL = 0b0101
ALU_SRA = 0b1101
ALU_OR = 0b0110
ALU_AND = 0b0111

CTRL_BEQ = 0b000
CTRL_BNE = 0b001
CTRL_BLT = 0b100
CTRL_BGE = 0b101
CTRL_BLTU = 0b110
CTRL_BGEU = 0b111
CTRL_JALR = 0b010
CTRL_JAL = 0b011

LSU_LB = 0b0000
LSU_LH = 0b0001
LSU_LW = 0b0010
LSU_LBU = 0b0100
LSU_LHU = 0b0101
LSU_SB = 0b1000
LSU_SH = 0b1001
LSU_SW = 0b1010

WB_ALU = 0b000
WB_LSU = 0b001
WB_CTRL = 0b010
WB_IMM = 0b011
WB_CSR = 0b100

PC_SEQ = 0b00
PC_CTRL = 0b01
PC_CSR = 0b10

CSR_SYS = 0b000
CSR_RW = 0b001
CSR_RS = 0b010
CSR_RC = 0b011
CSR_RWI = 0b101
CSR_RSI = 0b110
CSR_RCI = 0b111

EXC_ILLEGAL_INST = 0b0000000000000000000000000000010


def sign_extend(value, width):
    sign_bit = 1 << (width - 1)
    return ((value ^ sign_bit) - sign_bit) & 0xFFFFFFFF


def i_imm(inst):
    return sign_extend(inst >> 20, 12)


def s_imm(inst):
    return sign_extend(((inst >> 25) << 5) | ((inst >> 7) & 0x1F), 12)


def b_imm(inst):
    return sign_extend(
        ((inst >> 31) << 12)
        | (((inst >> 7) & 1) << 11)
        | (((inst >> 25) & 0x3F) << 5)
        | (((inst >> 8) & 0xF) << 1),
        13,
    )


def j_imm(inst):
    return sign_extend(
        ((inst >> 31) << 20)
        | (((inst >> 12) & 0xFF) << 12)
        | (((inst >> 20) & 1) << 11)
        | (((inst >> 21) & 0x3FF) << 1),
        21,
    )


def decode_reference(inst):
    """Return contract semantics, or None for a decoder-owned illegal encoding."""
    opcode, funct3, funct7 = inst & 0x7F, (inst >> 12) & 7, (inst >> 25) & 0x7F
    common = {
        "rs1": (inst >> 15) & 0x1F,
        "rs2": (inst >> 20) & 0x1F,
        "rd": (inst >> 7) & 0x1F,
        "pc_src": PC_SEQ,
    }

    if opcode == 0b0110011:
        ops = {
            (0b0000000, 0b000): ALU_ADD,
            (0b0100000, 0b000): ALU_SUB,
            (0b0000000, 0b001): ALU_SLL,
            (0b0000000, 0b010): ALU_SLT,
            (0b0000000, 0b011): ALU_SLTU,
            (0b0000000, 0b100): ALU_XOR,
            (0b0000000, 0b101): ALU_SRL,
            (0b0100000, 0b101): ALU_SRA,
            (0b0000000, 0b110): ALU_OR,
            (0b0000000, 0b111): ALU_AND,
        }
        if (funct7, funct3) not in ops:
            return None
        return common | {
            "rs1_used": 1,
            "rs2_used": 1,
            "rd_write": 1,
            "imm": 0,
            "alu_op": ops[funct7, funct3],
            "wb_src": WB_ALU,
        }

    if opcode == 0b0010011:
        ops = {
            0b000: ALU_ADD,
            0b010: ALU_SLT,
            0b011: ALU_SLTU,
            0b100: ALU_XOR,
            0b110: ALU_OR,
            0b111: ALU_AND,
        }
        if funct3 in ops:
            alu_op, imm = ops[funct3], i_imm(inst)
        elif funct3 == 0b001 and funct7 == 0b0000000:
            alu_op, imm = ALU_SLL, (inst >> 20) & 0x1F
        elif funct3 == 0b101 and funct7 in (0b0000000, 0b0100000):
            alu_op = ALU_SRA if funct7 == 0b0100000 else ALU_SRL
            imm = (inst >> 20) & 0x1F
        else:
            return None
        return common | {
            "rs1_used": 1,
            "rs2_used": 0,
            "rd_write": 1,
            "imm": imm,
            "alu_op": alu_op,
            "wb_src": WB_ALU,
        }

    if opcode == 0b0000011:
        ops = {
            0b000: LSU_LB,
            0b001: LSU_LH,
            0b010: LSU_LW,
            0b100: LSU_LBU,
            0b101: LSU_LHU,
        }
        if funct3 not in ops:
            return None
        return common | {
            "rs1_used": 1,
            "rs2_used": 0,
            "rd_write": 1,
            "imm": i_imm(inst),
            "lsu_op": ops[funct3],
            "wb_src": WB_LSU,
        }

    if opcode == 0b0100011:
        ops = {0b000: LSU_SB, 0b001: LSU_SH, 0b010: LSU_SW}
        if funct3 not in ops:
            return None
        return common | {
            "rs1_used": 1,
            "rs2_used": 1,
            "rd_write": 0,
            "imm": s_imm(inst),
            "lsu_op": ops[funct3],
            "wb_src": WB_LSU,
        }

    if opcode == 0b1100011:
        ops = {
            0b000: CTRL_BEQ,
            0b001: CTRL_BNE,
            0b100: CTRL_BLT,
            0b101: CTRL_BGE,
            0b110: CTRL_BLTU,
            0b111: CTRL_BGEU,
        }
        if funct3 not in ops:
            return None
        return common | {
            "rs1_used": 1,
            "rs2_used": 1,
            "rd_write": 0,
            "imm": b_imm(inst),
            "ctrl_op": ops[funct3],
            "wb_src": WB_CTRL,
            "pc_src": PC_CTRL,
        }

    if opcode == 0b0110111:
        return common | {
            "rs1_used": 0,
            "rs2_used": 0,
            "rd_write": 1,
            "imm": inst & 0xFFFFF000,
            "wb_src": WB_IMM,
        }
    if opcode == 0b0010111:
        return common | {
            "rs1_used": 0,
            "rs2_used": 0,
            "rd_write": 1,
            "imm": inst & 0xFFFFF000,
            "alu_op": ALU_ADD,
            "wb_src": WB_ALU,
        }
    if opcode == 0b1101111:
        return common | {
            "rs1_used": 0,
            "rs2_used": 0,
            "rd_write": 1,
            "imm": j_imm(inst),
            "ctrl_op": CTRL_JAL,
            "wb_src": WB_CTRL,
            "pc_src": PC_CTRL,
        }
    if opcode == 0b1100111 and funct3 == 0b000:
        return common | {
            "rs1_used": 1,
            "rs2_used": 0,
            "rd_write": 1,
            "imm": i_imm(inst),
            "ctrl_op": CTRL_JALR,
            "wb_src": WB_CTRL,
            "pc_src": PC_CTRL,
        }

    if opcode == 0b1110011:
        ops = {
            0b000: CSR_SYS,
            0b001: CSR_RW,
            0b010: CSR_RS,
            0b011: CSR_RC,
            0b101: CSR_RWI,
            0b110: CSR_RSI,
            0b111: CSR_RCI,
        }
        if funct3 not in ops:
            return None
        immediate, system = bool(funct3 & 4), funct3 == CSR_SYS
        return common | {
            "rs1_used": int(not immediate and not system),
            "rs2_used": 0,
            "rd_write": int(not system),
            "imm": i_imm(inst),
            "csr_op": ops[funct3],
            "csr_uimm": ((inst >> 15) & 0x1F) if immediate else 0,
            "wb_src": WB_CSR,
            "pc_src": PC_CSR if system else PC_SEQ,
        }

    if opcode == 0b0001111 and funct3 == 0b000:
        return common | {
            "rs1_used": 0,
            "rs2_used": 0,
            "rd_write": 0,
            "imm": 0,
            "wb_src": WB_ALU,
            "pc_src": PC_SEQ,
        }
    return None


def unpack_semantic(value):
    return {
        "rs1": (value >> 69) & 0x1F,
        "rs2": (value >> 64) & 0x1F,
        "rd": (value >> 59) & 0x1F,
        "rs1_used": (value >> 58) & 1,
        "rs2_used": (value >> 57) & 1,
        "rd_write": (value >> 56) & 1,
        "imm": (value >> 24) & 0xFFFFFFFF,
        "alu_op": (value >> 20) & 0xF,
        "ctrl_op": (value >> 17) & 7,
        "lsu_op": (value >> 13) & 0xF,
        "csr_op": (value >> 10) & 7,
        "csr_uimm": (value >> 5) & 0x1F,
        "wb_src": (value >> 2) & 7,
        "pc_src": value & 3,
    }


def unpack_trap(value):
    return {
        "valid": (value >> 64) & 1,
        "interrupt": (value >> 63) & 1,
        "code": (value >> 32) & 0x7FFFFFFF,
        "tval": value & 0xFFFFFFFF,
    }


def assert_no_trap(dut, inst):
    assert unpack_trap(dut.inst_trap_o.value.to_unsigned())["valid"] == 0, (
        f"{inst:#010x} trapped"
    )


def assert_illegal_trap(dut, inst):
    assert unpack_trap(dut.inst_trap_o.value.to_unsigned()) == {
        "valid": 1,
        "interrupt": 0,
        "code": EXC_ILLEGAL_INST,
        "tval": inst,
    }


async def assert_decodes_as(dut, inst, expected):
    dut.inst_i.value = inst
    await Timer(1, "ns")
    assert_no_trap(dut, inst)
    actual = unpack_semantic(dut.sem_o.value.to_unsigned())
    for field, value in expected.items():
        if field == "rs1" and not expected["rs1_used"]:
            continue
        if field == "rs2" and not expected["rs2_used"]:
            continue
        if field == "rd" and not expected["rd_write"]:
            continue
        assert actual[field] == value, (
            f"{inst:#010x}: {field}={actual[field]:#x}, expected {value:#x}"
        )


def encode_r(funct7, rs2, rs1, funct3, rd):
    return (
        (funct7 << 25)
        | (rs2 << 20)
        | (rs1 << 15)
        | (funct3 << 12)
        | (rd << 7)
        | 0b0110011
    )


def encode_i(imm, rs1, funct3, rd, opcode=0b0010011):
    return ((imm & 0xFFF) << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode


def encode_s(imm, rs2, rs1, funct3):
    return (
        (((imm >> 5) & 0x7F) << 25)
        | (rs2 << 20)
        | (rs1 << 15)
        | (funct3 << 12)
        | ((imm & 0x1F) << 7)
        | 0b0100011
    )


def encode_b(imm, rs2, rs1, funct3):
    return (
        (((imm >> 12) & 1) << 31)
        | (((imm >> 5) & 0x3F) << 25)
        | (rs2 << 20)
        | (rs1 << 15)
        | (funct3 << 12)
        | (((imm >> 1) & 0xF) << 8)
        | (((imm >> 11) & 1) << 7)
        | 0b1100011
    )


def encode_j(imm, rd):
    return (
        (((imm >> 20) & 1) << 31)
        | (((imm >> 1) & 0x3FF) << 21)
        | (((imm >> 11) & 1) << 20)
        | (((imm >> 12) & 0xFF) << 12)
        | (rd << 7)
        | 0b1101111
    )


DIRECTED_CASES = (
    *(
        (name, encode_r(f7, 29, 17, f3, 3))
        for name, f7, f3 in (
            ("add", 0, 0),
            ("sub", 0x20, 0),
            ("sll", 0, 1),
            ("slt", 0, 2),
            ("sltu", 0, 3),
            ("xor", 0, 4),
            ("srl", 0, 5),
            ("sra", 0x20, 5),
            ("or", 0, 6),
            ("and", 0, 7),
        )
    ),
    *(
        (name, encode_i(imm, 17, f3, 3))
        for name, imm, f3 in (
            ("addi", -2048, 0),
            ("slti", -1, 2),
            ("sltiu", 2047, 3),
            ("xori", 0x555, 4),
            ("ori", -512, 6),
            ("andi", 511, 7),
            ("slli", 31, 1),
            ("srli", 31, 5),
            ("srai", (0x20 << 5) | 31, 5),
        )
    ),
    *(
        (name, encode_i(-2048, 17, f3, 3, 0b0000011))
        for name, f3 in (("lb", 0), ("lh", 1), ("lw", 2), ("lbu", 4), ("lhu", 5))
    ),
    *(
        (name, encode_s(-2048, 29, 17, f3))
        for name, f3 in (("sb", 0), ("sh", 1), ("sw", 2))
    ),
    *(
        (name, encode_b(-4096, 29, 17, f3))
        for name, f3 in (
            ("beq", 0),
            ("bne", 1),
            ("blt", 4),
            ("bge", 5),
            ("bltu", 6),
            ("bgeu", 7),
        )
    ),
    ("lui", 0xABCDE000 | (3 << 7) | 0b0110111),
    ("auipc", 0xABCDE000 | (3 << 7) | 0b0010111),
    ("jal", encode_j(-1 << 20, 3)),
    ("jalr", encode_i(2047, 17, 0, 3, 0b1100111)),
    ("fence", 0x0FF0000F),
    ("system", encode_i(0x302, 0, CSR_SYS, 0, 0b1110011)),
    *(
        (name, encode_i(0xC00, 17, f3, 3, 0b1110011))
        for name, f3 in (
            ("csrrw", CSR_RW),
            ("csrrs", CSR_RS),
            ("csrrc", CSR_RC),
            ("csrrwi", CSR_RWI),
            ("csrrsi", CSR_RSI),
            ("csrrci", CSR_RCI),
        )
    ),
)


assert len(DIRECTED_CASES) == 45


def make_instruction_test(name, inst):
    @cocotb.test(name=f"decode_{name}")
    async def instruction_test(dut):
        await assert_decodes_as(dut, inst, decode_reference(inst))

    return instruction_test


for name, inst in DIRECTED_CASES:
    globals()[f"decode_{name}"] = make_instruction_test(name, inst)


@cocotb.test()
async def decoder_owned_illegal_encodings_report_traps_and_benign_defaults(dut):
    invalid = (
        0,
        0xFFFFFFFF,
        encode_r(1, 2, 1, 0, 3),
        encode_r(0x20, 2, 1, 1, 3),
        encode_i(0x20, 1, 1, 3),
        encode_i(0x40, 1, 5, 3),
        encode_i(0, 1, 3, 3, 0b0000011),
        encode_s(0, 2, 1, 3),
        encode_b(0, 2, 1, 2),
        encode_i(0, 1, 1, 3, 0b1100111),
        0x0000100F,
        encode_i(0, 1, 4, 3, 0b1110011),
    )
    for inst in invalid:
        assert decode_reference(inst) is None
        dut.inst_i.value = inst
        await Timer(1, "ns")
        assert_illegal_trap(dut, inst)
        assert dut.sem_o.value.to_unsigned() == 0


@cocotb.test()
async def random_instruction_legality_matches_reference(dut):
    for _ in range(2200):
        inst = random.getrandbits(32)
        dut.inst_i.value = inst
        await Timer(1, "ns")
        legal = decode_reference(inst) is not None
        trap = unpack_trap(dut.inst_trap_o.value.to_unsigned())
        assert trap["valid"] == int(not legal), (
            f"{inst:#010x}: trap={trap['valid']}, legal={legal}"
        )
        if not legal:
            assert_illegal_trap(dut, inst)
