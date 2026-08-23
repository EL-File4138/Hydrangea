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

WB_ALU = 0b00
WB_LSU = 0b01
WB_CTRL = 0b10
WB_IMM = 0b11


def sign_extend(value, width):
    sign_bit = 1 << (width - 1)
    return ((value ^ sign_bit) - sign_bit) & 0xFFFFFFFF


def i_imm(inst):
    return sign_extend(inst >> 20, 12)


def s_imm(inst):
    return sign_extend(((inst >> 25) << 5) | ((inst >> 7) & 0x1F), 12)


def b_imm(inst):
    value = (
        ((inst >> 31) << 12)
        | (((inst >> 7) & 1) << 11)
        | (((inst >> 25) & 0x3F) << 5)
        | (((inst >> 8) & 0xF) << 1)
    )
    return sign_extend(value, 13)


def j_imm(inst):
    value = (
        ((inst >> 31) << 20)
        | (((inst >> 12) & 0xFF) << 12)
        | (((inst >> 20) & 1) << 11)
        | (((inst >> 21) & 0x3FF) << 1)
    )
    return sign_extend(value, 21)


def decode_reference(inst):
    """Return required contract fields, or None for an unimplemented encoding."""
    opcode = inst & 0x7F
    funct3 = (inst >> 12) & 0x7
    funct7 = (inst >> 25) & 0x7F
    common = {
        "rs1": (inst >> 15) & 0x1F,
        "rs2": (inst >> 20) & 0x1F,
        "rd": (inst >> 7) & 0x1F,
    }

    if opcode == 0b0110011:  # OP
        alu_ops = {
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
        alu_op = alu_ops.get((funct7, funct3))
        if alu_op is None:
            return None
        return common | {"rs1_used": 1, "rs2_used": 1, "rd_write": 1,
                         "imm": 0, "alu_op": alu_op, "wb_src": WB_ALU}

    if opcode == 0b0010011:  # OP-IMM
        alu_ops = {0b000: ALU_ADD, 0b010: ALU_SLT, 0b011: ALU_SLTU,
                   0b100: ALU_XOR, 0b110: ALU_OR, 0b111: ALU_AND}
        if funct3 in alu_ops:
            alu_op, imm = alu_ops[funct3], i_imm(inst)
        elif funct3 == 0b001 and funct7 == 0b0000000:
            alu_op, imm = ALU_SLL, (inst >> 20) & 0x1F
        elif funct3 == 0b101 and funct7 in (0b0000000, 0b0100000):
            alu_op = ALU_SRA if funct7 == 0b0100000 else ALU_SRL
            imm = (inst >> 20) & 0x1F
        else:
            return None
        return common | {"rs1_used": 1, "rs2_used": 0, "rd_write": 1,
                         "imm": imm, "alu_op": alu_op, "wb_src": WB_ALU}

    if opcode == 0b0000011:  # LOAD
        lsu_ops = {0b000: LSU_LB, 0b001: LSU_LH, 0b010: LSU_LW,
                   0b100: LSU_LBU, 0b101: LSU_LHU}
        if funct3 not in lsu_ops:
            return None
        return common | {"rs1_used": 1, "rs2_used": 0, "rd_write": 1,
                         "imm": i_imm(inst), "lsu_op": lsu_ops[funct3],
                         "wb_src": WB_LSU}

    if opcode == 0b0100011:  # STORE
        lsu_ops = {0b000: LSU_SB, 0b001: LSU_SH, 0b010: LSU_SW}
        if funct3 not in lsu_ops:
            return None
        return common | {"rs1_used": 1, "rs2_used": 1, "rd_write": 0,
                         "imm": s_imm(inst), "lsu_op": lsu_ops[funct3]}

    if opcode == 0b1100011:  # BRANCH
        ctrl_ops = {0b000: CTRL_BEQ, 0b001: CTRL_BNE, 0b100: CTRL_BLT,
                    0b101: CTRL_BGE, 0b110: CTRL_BLTU, 0b111: CTRL_BGEU}
        if funct3 not in ctrl_ops:
            return None
        return common | {"rs1_used": 1, "rs2_used": 1, "rd_write": 0,
                         "imm": b_imm(inst), "ctrl_op": ctrl_ops[funct3]}

    if opcode == 0b0110111:  # LUI
        return common | {"rs1_used": 0, "rs2_used": 0, "rd_write": 1,
                         "imm": inst & 0xFFFFF000, "wb_src": WB_IMM}

    if opcode == 0b0010111:  # AUIPC
        return common | {"rs1_used": 0, "rs2_used": 0, "rd_write": 1,
                         "imm": inst & 0xFFFFF000, "alu_op": ALU_ADD,
                         "wb_src": WB_ALU}

    if opcode == 0b1101111:  # JAL
        return common | {"rs1_used": 0, "rs2_used": 0, "rd_write": 1,
                         "imm": j_imm(inst), "ctrl_op": CTRL_JAL,
                         "wb_src": WB_CTRL}

    if opcode == 0b1100111 and funct3 == 0:  # JALR
        return common | {"rs1_used": 1, "rs2_used": 0, "rd_write": 1,
                         "imm": i_imm(inst), "ctrl_op": CTRL_JALR,
                         "wb_src": WB_CTRL}

    return None


def unpack_semantic(value):
    return {
        "legal": (value >> 63) & 1,
        "rs1": (value >> 58) & 0x1F,
        "rs2": (value >> 53) & 0x1F,
        "rd": (value >> 48) & 0x1F,
        "rs1_used": (value >> 47) & 1,
        "rs2_used": (value >> 46) & 1,
        "rd_write": (value >> 45) & 1,
        "imm": (value >> 13) & 0xFFFFFFFF,
        "alu_op": (value >> 9) & 0xF,
        "ctrl_op": (value >> 6) & 0x7,
        "lsu_op": (value >> 2) & 0xF,
        "wb_src": value & 0x3,
    }


async def assert_decodes_as(dut, inst, expected):
    dut.inst_i.value = inst
    await Timer(1, "ns")
    actual = unpack_semantic(dut.sem_o.value.to_unsigned())
    assert actual["legal"] == 1, f"{inst:#010x} was rejected"
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
    return (funct7 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | 0b0110011


def encode_i(imm, rs1, funct3, rd, opcode=0b0010011):
    return ((imm & 0xFFF) << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode


def encode_s(imm, rs2, rs1, funct3):
    return (((imm >> 5) & 0x7F) << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | ((imm & 0x1F) << 7) | 0b0100011


def encode_b(imm, rs2, rs1, funct3):
    return (((imm >> 12) & 1) << 31) | (((imm >> 5) & 0x3F) << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (((imm >> 1) & 0xF) << 8) | (((imm >> 11) & 1) << 7) | 0b1100011


def encode_j(imm, rd):
    return (((imm >> 20) & 1) << 31) | (((imm >> 1) & 0x3FF) << 21) | (((imm >> 11) & 1) << 20) | (((imm >> 12) & 0xFF) << 12) | (rd << 7) | 0b1101111


DIRECTED_CASES = (
    ("add", encode_r(0, 29, 17, 0, 3)),
    ("sub", encode_r(0x20, 29, 17, 0, 3)),
    ("sll", encode_r(0, 29, 17, 1, 3)),
    ("slt", encode_r(0, 29, 17, 2, 3)),
    ("sltu", encode_r(0, 29, 17, 3, 3)),
    ("xor", encode_r(0, 29, 17, 4, 3)),
    ("srl", encode_r(0, 29, 17, 5, 3)),
    ("sra", encode_r(0x20, 29, 17, 5, 3)),
    ("or", encode_r(0, 29, 17, 6, 3)),
    ("and", encode_r(0, 29, 17, 7, 3)),
    ("addi", encode_i(-2048, 17, 0, 3)),
    ("slti", encode_i(-1, 17, 2, 3)),
    ("sltiu", encode_i(2047, 17, 3, 3)),
    ("xori", encode_i(0x555, 17, 4, 3)),
    ("ori", encode_i(-512, 17, 6, 3)),
    ("andi", encode_i(511, 17, 7, 3)),
    ("slli", encode_i(31, 17, 1, 3)),
    ("srli", encode_i(31, 17, 5, 3)),
    ("srai", encode_i((0x20 << 5) | 31, 17, 5, 3)),
    ("lb", encode_i(-2048, 17, 0, 3, 0b0000011)),
    ("lh", encode_i(-2048, 17, 1, 3, 0b0000011)),
    ("lw", encode_i(-2048, 17, 2, 3, 0b0000011)),
    ("lbu", encode_i(-2048, 17, 4, 3, 0b0000011)),
    ("lhu", encode_i(-2048, 17, 5, 3, 0b0000011)),
    ("sb", encode_s(-2048, 29, 17, 0)),
    ("sh", encode_s(-2048, 29, 17, 1)),
    ("sw", encode_s(-2048, 29, 17, 2)),
    ("beq", encode_b(-4096, 29, 17, 0)),
    ("bne", encode_b(-4096, 29, 17, 1)),
    ("blt", encode_b(-4096, 29, 17, 4)),
    ("bge", encode_b(-4096, 29, 17, 5)),
    ("bltu", encode_b(-4096, 29, 17, 6)),
    ("bgeu", encode_b(-4096, 29, 17, 7)),
    ("lui", 0xABCDE000 | (3 << 7) | 0b0110111),
    ("auipc", 0xABCDE000 | (3 << 7) | 0b0010111),
    ("jal", encode_j(-1 << 20, 3)),
    ("jalr", encode_i(2047, 17, 0, 3, 0b1100111)),
)


def _make_instruction_test(name, inst):
    @cocotb.test(name=f"decode_{name}")
    async def instruction_test(dut):
        """Check the semantic record for one implemented RV32I instruction."""
        expected = decode_reference(inst)
        assert expected is not None
        await assert_decodes_as(dut, inst, expected)

    return instruction_test


assert len(DIRECTED_CASES) == 37
for _name, _inst in DIRECTED_CASES:
    globals()[f"decode_{_name}"] = _make_instruction_test(_name, _inst)


@cocotb.test()
async def boundary_invalid_encodings_are_rejected(dut):
    """Check malformed lengths and reserved function encodings at decode boundaries."""
    invalid_cases = [
        0x00000000,                         # inst[1:0] != 2'b11
        0xFFFFFFFF,                         # unsupported major opcode
        encode_r(0x01, 2, 1, 0, 3),         # OP: unsupported funct7
        encode_r(0x20, 2, 1, 1, 3),         # OP: SUB funct7 with SLL funct3
        encode_i(0x020, 1, 1, 3),           # SLLI: nonzero upper bits
        encode_i(0x040, 1, 5, 3),           # SRLI/SRAI: unsupported upper bits
        encode_i(0, 1, 0b011, 3, 0b0000011),  # LOAD: reserved funct3
        encode_s(0, 2, 1, 0b011),           # STORE: reserved funct3
        encode_b(0, 2, 1, 0b010),           # BRANCH: reserved funct3
        encode_i(0, 1, 0b001, 3, 0b1100111),  # JALR requires funct3 == 000
        0x0000000F,                         # FENCE is deferred
        0x00000073,                         # ECALL is deferred
        0x00100073,                         # EBREAK is deferred
    ]
    for inst in invalid_cases:
        assert decode_reference(inst) is None
        dut.inst_i.value = inst
        await Timer(1, "ns")
        assert unpack_semantic(dut.sem_o.value.to_unsigned())["legal"] == 0, (
            f"illegal encoding accepted: {inst:#010x}"
        )


@cocotb.test()
async def random_instruction_legality_matches_reference(dut):
    """Compare legality for 2200 uniformly random instruction words."""
    for _ in range(2200):
        inst = random.getrandbits(32)
        dut.inst_i.value = inst
        await Timer(1, "ns")
        actual_legal = unpack_semantic(dut.sem_o.value.to_unsigned())["legal"]
        expected_legal = decode_reference(inst) is not None
        assert actual_legal == expected_legal, (
            f"{inst:#010x}: legal={actual_legal}, expected {expected_legal}"
        )
