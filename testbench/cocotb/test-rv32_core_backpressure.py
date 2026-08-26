import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


ST_FETCH = 0
ST_IO_WAIT = 2


def i_type(imm, rs1, funct3, rd, opcode=0x13):
    return ((imm & 0xFFF) << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode


async def reset_dut(dut):
    dut.imem_ready_i.value = 0
    dut.imem_rdata_i.value = 0
    dut.imem_err_i.value = 0
    dut.dmem_ready_i.value = 0
    dut.dmem_rdata_i.value = 0
    dut.dmem_err_i.value = 0
    dut.rst_ni.value = 0
    await RisingEdge(dut.clk_i)
    dut.rst_ni.value = 1
    await RisingEdge(dut.clk_i)
    await Timer(1, "ns")


async def complete_fetch(dut, instruction):
    assert dut.imem_req_o.value == 1
    dut.imem_rdata_i.value = instruction
    dut.imem_ready_i.value = 1
    await RisingEdge(dut.clk_i)
    dut.imem_ready_i.value = 0
    await Timer(1, "ns")


async def advance_to_next_fetch(dut):
    await RisingEdge(dut.clk_i)
    await RisingEdge(dut.clk_i)
    await Timer(1, "ns")


@cocotb.test()
async def delayed_memory_response_program(dut):
    """Core remains in FETCH/IO_WAIT and retains request fields until each ready event."""
    cocotb.start_soon(Clock(dut.clk_i, 2, "ns").start())
    await reset_dut(dut)

    assert dut.imem_req_o.value == 1
    for _ in range(4):
        assert int(dut.state_o.value) == ST_FETCH
        assert int(dut.pc_o.value) == 0
        assert int(dut.imem_addr_o.value) == 0
        await RisingEdge(dut.clk_i)

    await complete_fetch(dut, i_type(0x100, 0, 0, 1))
    await advance_to_next_fetch(dut)
    assert int(dut.pc_o.value) == 4
    await complete_fetch(dut, i_type(0, 1, 2, 2, 0x03))
    await RisingEdge(dut.clk_i)
    await Timer(1, "ns")

    assert int(dut.state_o.value) == ST_IO_WAIT
    held_fields = (
        int(dut.dmem_req_o.value),
        int(dut.dmem_we_o.value),
        int(dut.dmem_addr_o.value),
        int(dut.dmem_wdata_o.value),
        int(dut.dmem_wstrb_o.value),
    )
    assert held_fields == (1, 0, 0x100, 0, 0)
    for _ in range(5):
        await RisingEdge(dut.clk_i)
        assert int(dut.state_o.value) == ST_IO_WAIT
        assert (
            int(dut.dmem_req_o.value),
            int(dut.dmem_we_o.value),
            int(dut.dmem_addr_o.value),
            int(dut.dmem_wdata_o.value),
            int(dut.dmem_wstrb_o.value),
        ) == held_fields

    dut.dmem_rdata_i.value = 0xDEAD_BEEF
    dut.dmem_ready_i.value = 1
    await RisingEdge(dut.clk_i)
    dut.dmem_ready_i.value = 0
    await advance_to_next_fetch(dut)
    await complete_fetch(dut, i_type(1, 2, 0, 3))
    await RisingEdge(dut.clk_i)
    await RisingEdge(dut.clk_i)
    await Timer(1, "ns")

    assert int(dut.gpr_o[2].value) == 0xDEAD_BEEF
    assert int(dut.gpr_o[3].value) == 0xDEAD_BEF0
