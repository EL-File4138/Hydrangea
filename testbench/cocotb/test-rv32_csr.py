import cocotb
from cocotb.triggers import Timer


CSR_SYS = 0b000
CSR_RW = 0b001
CSR_RS = 0b010
CSR_RC = 0b011
CSR_RWI = 0b101
CSR_RSI = 0b110
CSR_RCI = 0b111

MSTATUS = 0x300
MEPC = 0x341
EXC_ILLEGAL_INST = 2
EXC_BREAKPOINT = 3
EXC_ECALL_M = 11


def trap_fields(dut):
    trap = dut.trap_o.value.to_unsigned()
    return (
        (trap >> 64) & 1,
        (trap >> 63) & 1,
        (trap >> 32) & 0x7FFF_FFFF,
        trap & 0xFFFF_FFFF,
    )


def write_fields(dut):
    write = dut.csr_wr_o.value.to_unsigned()
    return (write >> 44) & 1, (write >> 32) & 0xFFF, write & 0xFFFF_FFFF


async def drive(
    dut,
    op,
    imm=0x340,
    uimm=0,
    rs1=0,
    rd_is_zero=False,
    rs1_is_zero=False,
    read_legal=True,
    read_data=0,
    write_legal=True,
    second_read_legal=True,
    second_read_data=0,
):
    dut.csr_op_i.value = op
    dut.csr_imm_i.value = imm
    dut.csr_uimm_i.value = uimm
    dut.rs1_var_i.value = rs1
    dut.rd_is_zero_i.value = int(rd_is_zero)
    dut.rs1_is_zero_i.value = int(rs1_is_zero)
    dut.csr_rlegal_i[0].value = int(read_legal)
    dut.csr_rlegal_i[1].value = int(second_read_legal)
    dut.csr_rdata_i[0].value = read_data
    dut.csr_rdata_i[1].value = second_read_data
    dut.csr_wr_legal_i.value = int(write_legal)
    await Timer(1, "ns")


def assert_no_trap(dut):
    assert trap_fields(dut) == (0, 0, 0, 0)


def assert_illegal(dut):
    assert trap_fields(dut) == (1, 0, EXC_ILLEGAL_INST, 0)


def assert_write(dut, address, data):
    assert write_fields(dut) == (1, address, data)


def assert_no_write(dut):
    assert write_fields(dut) == (0, 0, 0)


@cocotb.test()
async def csrrw_reads_old_value_and_writes_rs1(dut):
    """CSRRW writes rs1 even when x0 suppresses architectural destination writeback."""
    await drive(dut, CSR_RW, imm=0x340, rs1=0xDEAD_BEEF, read_data=0x1234_5678)
    assert dut.csr_raddr_o[0].value == 0x340
    assert dut.rd_result_o.value == 0x1234_5678
    assert_write(dut, 0x340, 0xDEAD_BEEF)
    assert_no_trap(dut)

    await drive(dut, CSR_RW, imm=0x340, rs1=0xA5A5_A5A5, rd_is_zero=True)
    assert dut.csr_raddr_o[0].value == 0
    assert dut.rd_result_o.value == 0
    assert_write(dut, 0x340, 0xA5A5_A5A5)
    assert_no_trap(dut)


@cocotb.test()
async def register_set_and_clear_follow_source_zero_suppression(dut):
    """CSRRS/CSRRC return the old value and suppress writes only for x0 sources."""
    old = 0xA55A_00F0
    mask = 0x0F0F_F00F
    for op, expected in ((CSR_RS, old | mask), (CSR_RC, old & ~mask & 0xFFFF_FFFF)):
        await drive(dut, op, imm=0x305, rs1=mask, read_data=old)
        assert dut.csr_raddr_o[0].value == 0x305
        assert dut.rd_result_o.value == old
        assert_write(dut, 0x305, expected)
        assert_no_trap(dut)

        await drive(dut, op, imm=0x305, rs1_is_zero=True, read_data=old)
        assert dut.rd_result_o.value == old
        assert_no_write(dut)
        assert_no_trap(dut)


@cocotb.test()
async def immediate_csr_operations_use_zero_extended_uimm(dut):
    """Immediate forms use csr_uimm, with zero suppressing only set and clear."""
    old = 0xFFFF_00F0
    await drive(dut, CSR_RWI, imm=0x304, uimm=0b10101, read_data=old)
    assert dut.rd_result_o.value == old
    assert_write(dut, 0x304, 0b10101)
    assert_no_trap(dut)

    for op, expected in (
        (CSR_RSI, old | 0b10101),
        (CSR_RCI, old & ~0b10101 & 0xFFFF_FFFF),
    ):
        await drive(dut, op, imm=0x304, uimm=0b10101, read_data=old)
        assert dut.rd_result_o.value == old
        assert_write(dut, 0x304, expected)
        assert_no_trap(dut)

        await drive(dut, op, imm=0x304, uimm=0, read_data=old)
        assert dut.rd_result_o.value == old
        assert_no_write(dut)
        assert_no_trap(dut)

    await drive(dut, CSR_RWI, imm=0x304, uimm=0, rd_is_zero=True)
    assert_write(dut, 0x304, 0)
    assert_no_trap(dut)


@cocotb.test()
async def illegal_bank_responses_raise_illegal_instruction_traps(dut):
    """Illegal read or required write candidates prevent normal CSR execution."""
    await drive(dut, CSR_RS, read_legal=False, rs1=1)
    assert dut.csr_raddr_o[0].value == 0x340
    assert_no_write(dut)
    assert_illegal(dut)

    await drive(dut, CSR_RW, write_legal=False, rs1=1, read_data=2)
    assert dut.rd_result_o.value == 2
    assert_write(dut, 0x340, 1)
    assert_illegal(dut)

    await drive(dut, CSR_RS, write_legal=False, rs1_is_zero=True, read_data=2)
    assert_no_write(dut)
    assert_no_trap(dut)

    await drive(dut, 0b100)
    assert_no_write(dut)
    assert_illegal(dut)


@cocotb.test()
async def system_ecall_ebreak_and_mret_follow_contract(dut):
    """Exact SYSTEM encodings trap or perform the specified MRET restoration."""
    await drive(dut, CSR_SYS, imm=0x000, rd_is_zero=True, rs1_is_zero=True)
    assert trap_fields(dut) == (1, 0, EXC_ECALL_M, 0)
    assert_no_write(dut)

    await drive(dut, CSR_SYS, imm=0x001, rd_is_zero=True, rs1_is_zero=True)
    assert trap_fields(dut) == (1, 0, EXC_BREAKPOINT, 0)
    assert_no_write(dut)

    await drive(
        dut,
        CSR_SYS,
        imm=0x302,
        rd_is_zero=True,
        rs1_is_zero=True,
        read_data=0x8000_1040,
        second_read_data=0x0000_1880,
    )
    assert dut.csr_raddr_o[0].value == MEPC
    assert dut.csr_raddr_o[1].value == MSTATUS
    assert_write(dut, MSTATUS, 0x0000_1888)
    assert dut.pc_valid_o.value == 1
    assert dut.pc_o.value == 0x8000_1040
    assert_no_trap(dut)

    await drive(
        dut,
        CSR_SYS,
        imm=0x302,
        rd_is_zero=True,
        rs1_is_zero=True,
        second_read_legal=False,
    )
    assert_no_write(dut)
    assert dut.pc_valid_o.value == 0
    assert_illegal(dut)

    await drive(
        dut, CSR_SYS, imm=0x302, rd_is_zero=True, rs1_is_zero=True, write_legal=False
    )
    assert dut.csr_raddr_o[0].value == MEPC
    assert dut.csr_raddr_o[1].value == MSTATUS
    assert_write(dut, MSTATUS, 0x0000_0080)
    assert dut.pc_valid_o.value == 0
    assert_illegal(dut)

    await drive(dut, CSR_SYS, imm=0x123, rd_is_zero=True, rs1_is_zero=True)
    assert_no_write(dut)
    assert_illegal(dut)


@cocotb.test()
async def wfi_is_a_legal_noop_and_system_encodings_require_zero_registers(dut):
    """WFI has no controller effect, while malformed exact SYSTEM forms trap."""
    await drive(dut, CSR_SYS, imm=0x105, rd_is_zero=True, rs1_is_zero=True)
    assert dut.csr_raddr_o[0].value == 0
    assert dut.csr_raddr_o[1].value == 0
    assert_no_write(dut)
    assert dut.pc_valid_o.value == 0
    assert_no_trap(dut)

    for imm in (0x000, 0x001, 0x105, 0x302):
        for rd_is_zero, rs1_is_zero in ((False, True), (True, False)):
            await drive(
                dut, CSR_SYS, imm=imm, rd_is_zero=rd_is_zero, rs1_is_zero=rs1_is_zero
            )
            assert_no_write(dut)
            assert dut.pc_valid_o.value == 0
            assert_illegal(dut)
