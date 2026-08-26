import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


MSTATUS = 0x300
MISA = 0x301
MIE = 0x304
MTVEC = 0x305
MSTATUSH = 0x310
MSCRATCH = 0x340
MEPC = 0x341
MCAUSE = 0x342
MTVAL = 0x343
MIP = 0x344
MVENDORID = 0xF11
MARCHID = 0xF12
MIMPID = 0xF13
MHARTID = 0xF14
MCONFIGPTR = 0xF15

IMPLEMENTED_CSRS = (
    MSTATUS,
    MISA,
    MIE,
    MTVEC,
    MSTATUSH,
    MSCRATCH,
    MEPC,
    MCAUSE,
    MTVAL,
    MIP,
    MVENDORID,
    MARCHID,
    MIMPID,
    MHARTID,
    MCONFIGPTR,
)


def set_write_lane(dut, lane, enabled=False, address=0, data=0):
    dut.wr_i[lane].value = (int(enabled) << 44) | (address << 32) | data


def set_read_address(dut, port, address):
    dut.rd_addr_i[port].value = address


def read_data(dut, port=0):
    return dut.rd_data_o[port].value.to_unsigned()


def read_legal(dut, port=0):
    return int(dut.rd_legal_o[port].value)


async def reset_dut(dut):
    dut.wr_en_i.value = 0
    for port in range(4):
        set_read_address(dut, port, 0)
    for lane in range(8):
        set_write_lane(dut, lane)
    dut.rst_ni.value = 0
    await RisingEdge(dut.clk_i)
    dut.rst_ni.value = 1
    await Timer(1, "ns")


async def commit(dut):
    await RisingEdge(dut.clk_i)
    await Timer(1, "ns")


async def write(dut, address, data):
    set_write_lane(dut, 0, enabled=True, address=address, data=data)
    dut.wr_en_i.value = 1
    await commit(dut)
    dut.wr_en_i.value = 0
    set_write_lane(dut, 0)


async def expect_read(dut, address, expected, port=0):
    set_read_address(dut, port, address)
    await Timer(1, "ns")
    assert read_legal(dut, port) == 1, f"CSR {address:#05x} unexpectedly illegal"
    assert read_data(dut, port) == expected, (
        f"CSR {address:#05x}: got {read_data(dut, port):#010x}, expected {expected:#010x}"
    )


@cocotb.test()
async def reset_exposes_contract_defined_csr_values(dut):
    """Reset uses each CSR implementation's reset semantics through dispatch."""
    cocotb.start_soon(Clock(dut.clk_i, 2, "ns").start())
    await reset_dut(dut)

    expected = {
        MSTATUS: 0x0000_1800,
        MISA: 0x4000_0100,
        MIE: 0,
        MTVEC: 0,
        MSTATUSH: 0,
        MSCRATCH: 0,
        MEPC: 0,
        MCAUSE: 0,
        MTVAL: 0,
        MIP: 0,
        MVENDORID: 0,
        MARCHID: 0,
        MIMPID: 0,
        MHARTID: 0,
        MCONFIGPTR: 0,
    }
    for port, address in enumerate(IMPLEMENTED_CSRS[:4]):
        set_read_address(dut, port, address)
    await Timer(1, "ns")
    for port, address in enumerate(IMPLEMENTED_CSRS[:4]):
        assert read_legal(dut, port) == 1
        assert read_data(dut, port) == expected[address]
    for address in IMPLEMENTED_CSRS[4:]:
        await expect_read(dut, address, expected[address])


@cocotb.test()
async def writable_csrs_apply_field_and_alignment_semantics(dut):
    """Writable CSR implementations preserve fixed fields and constrain aligned PCs."""
    cocotb.start_soon(Clock(dut.clk_i, 2, "ns").start())
    await reset_dut(dut)

    await write(dut, MSTATUS, 0xFFFF_FFFF)
    await expect_read(dut, MSTATUS, 0x0000_1888)
    await write(dut, MSTATUS, 0)
    await expect_read(dut, MSTATUS, 0x0000_1800)

    await write(dut, MTVEC, 0x1234_567B)
    await expect_read(dut, MTVEC, 0x1234_5678)
    await write(dut, MEPC, 0xCAFE_BABE)
    await expect_read(dut, MEPC, 0xCAFE_BABC)

    await write(dut, MIE, 0xFFFF_FFFF)
    await expect_read(dut, MIE, 0x0000_0080)
    await write(dut, MSCRATCH, 0x1357_9BDF)
    await expect_read(dut, MSCRATCH, 0x1357_9BDF)
    await write(dut, MCAUSE, 0x8000_0007)
    await expect_read(dut, MCAUSE, 0x8000_0007)
    await write(dut, MTVAL, 0xDEAD_BEEF)
    await expect_read(dut, MTVAL, 0xDEAD_BEEF)


@cocotb.test()
async def enabled_legal_lanes_commit_atomically(dut):
    """Distinct legal write lanes commit together, while global enable owns commit."""
    cocotb.start_soon(Clock(dut.clk_i, 2, "ns").start())
    await reset_dut(dut)

    set_write_lane(dut, 0, enabled=True, address=MSCRATCH, data=0x1111_1111)
    set_write_lane(dut, 1, enabled=True, address=MCAUSE, data=0x2222_2222)
    set_write_lane(dut, 2, enabled=True, address=MTVAL, data=0x3333_3333)
    dut.wr_en_i.value = 1
    await Timer(1, "ns")
    for lane in range(3):
        assert dut.wr_legal_o[lane].value == 1
    await commit(dut)
    dut.wr_en_i.value = 0
    for lane in range(8):
        set_write_lane(dut, lane)

    await expect_read(dut, MSCRATCH, 0x1111_1111)
    await expect_read(dut, MCAUSE, 0x2222_2222)
    await expect_read(dut, MTVAL, 0x3333_3333)

    set_write_lane(dut, 0, enabled=True, address=MSCRATCH, data=0x4444_4444)
    await commit(dut)
    set_write_lane(dut, 0)
    await expect_read(dut, MSCRATCH, 0x1111_1111)


@cocotb.test()
async def illegal_or_duplicate_lane_rejects_the_entire_transaction(dut):
    """An invalid atomic transaction cannot partially update any CSR cell."""
    cocotb.start_soon(Clock(dut.clk_i, 2, "ns").start())
    await reset_dut(dut)

    set_write_lane(dut, 0, enabled=True, address=MSCRATCH, data=0x1111_1111)
    set_write_lane(dut, 1, enabled=True, address=0x777, data=0x2222_2222)
    dut.wr_en_i.value = 1
    await Timer(1, "ns")
    assert dut.wr_legal_o[0].value == 1
    assert dut.wr_legal_o[1].value == 0
    await commit(dut)
    await expect_read(dut, MSCRATCH, 0)

    set_write_lane(dut, 0, enabled=True, address=MSCRATCH, data=0x3333_3333)
    set_write_lane(dut, 1, enabled=True, address=MSCRATCH, data=0x4444_4444)
    await commit(dut)
    await expect_read(dut, MSCRATCH, 0)

    set_write_lane(dut, 0, enabled=True, address=MVENDORID, data=0)
    set_write_lane(dut, 1)
    await Timer(1, "ns")
    assert dut.wr_legal_o[0].value == 0
    await commit(dut)
    dut.wr_en_i.value = 0
    for lane in range(8):
        set_write_lane(dut, lane)
    await expect_read(dut, MVENDORID, 0)


@cocotb.test()
async def unimplemented_reads_are_illegal(dut):
    """Dispatch fall-through is observable per read port."""
    cocotb.start_soon(Clock(dut.clk_i, 2, "ns").start())
    await reset_dut(dut)

    set_read_address(dut, 0, 0x777)
    set_read_address(dut, 1, MIP)
    await Timer(1, "ns")
    assert read_legal(dut, 0) == 0
    assert read_data(dut, 0) == 0
    assert read_legal(dut, 1) == 1
    assert read_data(dut, 1) == 0


@cocotb.test()
async def fixed_value_mrw_csrs_accept_writes_without_state_change(dut):
    """MRW CSRs retain fixed or hardware-owned fields while accepting writes."""
    cocotb.start_soon(Clock(dut.clk_i, 2, "ns").start())
    await reset_dut(dut)

    for address, expected in ((MSTATUSH, 0), (MIP, 0), (MISA, 0x4000_0100)):
        for data in (0, 0xFFFF_FFFF, 0x1357_9BDF):
            set_write_lane(dut, 0, enabled=True, address=address, data=data)
            dut.wr_en_i.value = 1
            await Timer(1, "ns")
            assert dut.wr_legal_o[0].value == 1
            await commit(dut)
            dut.wr_en_i.value = 0
            set_write_lane(dut, 0)
            await expect_read(dut, address, expected)
