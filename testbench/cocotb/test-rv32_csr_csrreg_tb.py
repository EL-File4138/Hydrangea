import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


CSR_SYS = 0b000
CSR_RW = 0b001
CSR_RS = 0b010
MSTATUS = 0x300
MISA = 0x301
MSTATUSH = 0x310
MSCRATCH = 0x340
MEPC = 0x341
MIP = 0x344


def trap_fields(dut):
    trap = dut.trap_o.value.to_unsigned()
    return (
        (trap >> 64) & 1,
        (trap >> 63) & 1,
        (trap >> 32) & 0x7FFF_FFFF,
        trap & 0xFFFF_FFFF,
    )


async def drive(dut, op, imm=0, uimm=0, rs1=0, rd_is_zero=False, rs1_is_zero=False):
    dut.csr_op_i.value = op
    dut.csr_imm_i.value = imm
    dut.csr_uimm_i.value = uimm
    dut.rs1_var_i.value = rs1
    dut.rd_is_zero_i.value = int(rd_is_zero)
    dut.rs1_is_zero_i.value = int(rs1_is_zero)
    await Timer(1, "ns")


async def reset_dut(dut):
    await drive(dut, CSR_SYS, imm=0x123)
    dut.rst_ni.value = 0
    await RisingEdge(dut.clk_i)
    dut.rst_ni.value = 1
    await Timer(1, "ns")


async def commit(dut):
    await RisingEdge(dut.clk_i)
    await Timer(1, "ns")


@cocotb.test()
async def controller_and_bank_complete_zicsr_transactions(dut):
    """Bank legality feeds the controller combinationally and its accepted writes commit."""
    cocotb.start_soon(Clock(dut.clk_i, 2, "ns").start())
    await reset_dut(dut)

    await drive(dut, CSR_RW, imm=MSCRATCH, rs1=0x1234_5678)
    assert dut.rd_result_o.value == 0
    assert trap_fields(dut) == (0, 0, 0, 0)
    await commit(dut)

    await drive(dut, CSR_RS, imm=MSCRATCH, rs1=0x0000_00F0)
    assert dut.rd_result_o.value == 0x1234_5678
    assert trap_fields(dut) == (0, 0, 0, 0)
    await commit(dut)

    await drive(dut, CSR_RS, imm=MSCRATCH, rs1_is_zero=True)
    assert dut.rd_result_o.value == 0x1234_56F8
    assert trap_fields(dut) == (0, 0, 0, 0)

    for address, data, expected in (
        (MISA, 0, 0x4000_0100),
        (MSTATUSH, 0xFFFF_FFFF, 0),
        (MIP, 0xFFFF_FFFF, 0),
    ):
        await drive(dut, CSR_RW, imm=address, rs1=data)
        assert trap_fields(dut) == (0, 0, 0, 0)
        await commit(dut)
        await drive(dut, CSR_RS, imm=address, rs1_is_zero=True)
        assert dut.rd_result_o.value == expected
        assert trap_fields(dut) == (0, 0, 0, 0)

    await drive(dut, CSR_RW, imm=MISA, rs1=0xDEAD_BEEF)
    assert trap_fields(dut) == (0, 0, 0, 0)
    await commit(dut)
    await drive(dut, CSR_RS, imm=MISA, rs1_is_zero=True)
    assert dut.rd_result_o.value == 0x4000_0100


@cocotb.test()
async def mret_reads_bank_state_and_commits_status_restoration(dut):
    """MRET reads MEPC/MSTATUS, restores status through the shared bank lane, and returns PC."""
    cocotb.start_soon(Clock(dut.clk_i, 2, "ns").start())
    await reset_dut(dut)

    await drive(dut, CSR_RW, imm=MEPC, rs1=0x8000_1043)
    await commit(dut)
    await drive(dut, CSR_RW, imm=MSTATUS, rs1=0x0000_1880)
    await commit(dut)

    await drive(dut, CSR_SYS, imm=0x302, rd_is_zero=True, rs1_is_zero=True)
    assert dut.pc_valid_o.value == 1
    assert dut.pc_o.value == 0x8000_1040
    assert trap_fields(dut) == (0, 0, 0, 0)
    await commit(dut)

    await drive(dut, CSR_RS, imm=MSTATUS, rs1_is_zero=True)
    assert dut.rd_result_o.value == 0x0000_1888
    assert trap_fields(dut) == (0, 0, 0, 0)
