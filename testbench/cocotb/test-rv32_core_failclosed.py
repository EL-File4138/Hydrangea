import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


ST_TRAP = 4
CSR_MEPC_INDEX = 6
CSR_MCAUSE_INDEX = 7
CSR_MTVAL_INDEX = 8


async def reset_and_load_illegal_instruction(dut):
    dut.rst_ni.value = 0
    await RisingEdge(dut.clk_i)
    await Timer(1, "ns")
    for address in range(256):
        dut.u_memory.u_sync_ram.mem_cell[address].value = 0
    dut.u_memory.u_sync_ram.mem_cell[0].value = 0xFFFF_FFFF
    dut.rst_ni.value = 1
    await RisingEdge(dut.clk_i)


@cocotb.test()
async def rejected_trap_write_program(dut):
    """A rejected mandatory trap write keeps the core in TRAP without side effects."""
    cocotb.start_soon(Clock(dut.clk_i, 2, "ns").start())
    await reset_and_load_illegal_instruction(dut)

    for _ in range(20):
        await RisingEdge(dut.clk_i)
        if dut.state_o.value.to_unsigned() == ST_TRAP:
            break
    else:
        raise AssertionError("core did not enter TRAP after the illegal instruction")

    for _ in range(12):
        await RisingEdge(dut.clk_i)
        assert dut.state_o.value.to_unsigned() == ST_TRAP
        assert dut.pc_o.value.to_unsigned() == 0
        assert dut.csr_o[CSR_MEPC_INDEX].value.to_unsigned() == 0
        assert dut.csr_o[CSR_MCAUSE_INDEX].value.to_unsigned() == 0
        assert dut.csr_o[CSR_MTVAL_INDEX].value.to_unsigned() == 0
