import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, ReadOnly, RisingEdge, Timer


async def reset_dut(dut):
    for port in ("imem", "dmem"):
        getattr(dut, f"{port}_req_i").value = 0
        getattr(dut, f"{port}_we_i").value = 0
        getattr(dut, f"{port}_addr_i").value = 0
        getattr(dut, f"{port}_wdata_i").value = 0
        getattr(dut, f"{port}_wstrb_i").value = 0
    dut.rst_ni.value = 0
    await Timer(1, "ns")
    dut.rst_ni.value = 1
    await RisingEdge(dut.clk_i)


async def transaction(dut, port, *, we, addr, wdata=0, wstrb=0):
    await FallingEdge(dut.clk_i)
    getattr(dut, f"{port}_req_i").value = 1
    getattr(dut, f"{port}_we_i").value = we
    getattr(dut, f"{port}_addr_i").value = addr
    getattr(dut, f"{port}_wdata_i").value = wdata
    getattr(dut, f"{port}_wstrb_i").value = wstrb

    await RisingEdge(dut.clk_i)
    await ReadOnly()
    if not getattr(dut, f"{port}_ready_o").value:
        await RisingEdge(dut.clk_i)
        await ReadOnly()

    assert getattr(dut, f"{port}_ready_o").value == 1
    response = (
        getattr(dut, f"{port}_rdata_o").value.to_unsigned(),
        int(getattr(dut, f"{port}_err_o").value),
    )

    await FallingEdge(dut.clk_i)
    getattr(dut, f"{port}_req_i").value = 0
    await RisingEdge(dut.clk_i)
    await RisingEdge(dut.clk_i)
    return response


@cocotb.test()
async def default_unified_map_is_shared_and_preserves_lanes(dut):
    """Both default address maps expose the same RAM bytes."""
    cocotb.start_soon(Clock(dut.clk_i, 2, "ns").start())
    await reset_dut(dut)

    _, err = await transaction(
        dut, "dmem", we=1, addr=0, wdata=0x1122_3344, wstrb=0b1111
    )
    assert err == 0
    _, err = await transaction(
        dut, "dmem", we=1, addr=2, wdata=0x00AA_0000, wstrb=0b0100
    )
    assert err == 0

    rdata, err = await transaction(dut, "imem", we=0, addr=0)
    assert err == 0
    assert rdata == 0x11AA_3344


@cocotb.test()
async def invalid_addresses_and_imem_writes_fail(dut):
    """Failures complete on the selected interface with ready and err asserted."""
    cocotb.start_soon(Clock(dut.clk_i, 2, "ns").start())
    await reset_dut(dut)

    _, err = await transaction(dut, "imem", we=0, addr=0x0004_0000)
    assert err == 1
    _, err = await transaction(
        dut, "imem", we=1, addr=0, wdata=0xDEAD_BEEF, wstrb=0b1111
    )
    assert err == 1
