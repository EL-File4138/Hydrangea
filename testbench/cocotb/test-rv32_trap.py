import cocotb
from cocotb.triggers import Timer


MSTATUS = 0x300
MTVEC = 0x305
MEPC = 0x341
MCAUSE = 0x342
MTVAL = 0x343


def pack_trap(valid, interrupt, code, tval):
    return (valid << 64) | (interrupt << 63) | (code << 32) | tval


def write_fields(dut, lane):
    write = dut.csr_wr_o[lane].value.to_unsigned()
    return (write >> 44) & 1, (write >> 32) & 0xFFF, write & 0xFFFF_FFFF


async def drive(
    dut, trap=0, pc=0, reads_legal=(True, True), reads=(0, 0), writes_legal=(True,) * 4
):
    dut.trap_i.value = trap
    dut.pc_i.value = pc
    for port in range(2):
        dut.csr_rlegal_i[port].value = int(reads_legal[port])
        dut.csr_rdata_i[port].value = reads[port]
    for lane in range(4):
        dut.csr_wr_legal_i[lane].value = int(writes_legal[lane])
    await Timer(1, "ns")


def assert_no_writes(dut):
    for lane in range(4):
        assert write_fields(dut, lane) == (0, 0, 0)


@cocotb.test()
async def accepted_exception_creates_atomic_machine_trap_transaction(dut):
    """An accepted exception saves context, disables MIE, and targets aligned MTVEC."""
    mstatus = 0xA5A5_0088
    mtvec = 0x8000_0103
    await drive(
        dut,
        trap=pack_trap(1, 0, 5, 0xDEAD_BEEF),
        pc=0x8000_0044,
        reads=(mstatus, mtvec),
    )

    assert dut.csr_raddr_o[0].value == MSTATUS
    assert dut.csr_raddr_o[1].value == MTVEC
    assert write_fields(dut, 0) == (1, MEPC, 0x8000_0044)
    assert write_fields(dut, 1) == (1, MCAUSE, 5)
    assert write_fields(dut, 2) == (1, MTVAL, 0xDEAD_BEEF)
    expected_mstatus = (mstatus & ~(1 << 3)) | (1 << 7) | (0b11 << 11)
    assert write_fields(dut, 3) == (1, MSTATUS, expected_mstatus)
    assert dut.pc_valid_o.value == 1
    assert dut.pc_o.value == 0x8000_0100
    assert dut.legal_o.value == 1


@cocotb.test()
async def accepted_interrupt_preserves_interrupt_class_in_mcause(dut):
    """Interrupt entry sets MCAUSE bit 31 while retaining the supplied cause code."""
    await drive(
        dut,
        trap=pack_trap(1, 1, 7, 0),
        pc=0xFFFF_FFFC,
        reads=(0x0000_1800, 0x0000_0042),
    )

    assert write_fields(dut, 0) == (1, MEPC, 0xFFFF_FFFC)
    assert write_fields(dut, 1) == (1, MCAUSE, 0x8000_0007)
    assert write_fields(dut, 2) == (1, MTVAL, 0)
    assert write_fields(dut, 3) == (1, MSTATUS, 0x0000_1800)
    assert dut.pc_o.value == 0x0000_0040
    assert dut.pc_valid_o.value == 1
    assert dut.legal_o.value == 1


@cocotb.test()
async def inactive_or_read_illegal_requests_do_not_issue_a_trap_transaction(dut):
    """No valid trap or unavailable trap CSRs suppresses all writes and PC selection."""
    await drive(dut, reads=(0x0000_1808, 0x100))
    assert_no_writes(dut)
    assert dut.pc_valid_o.value == 0
    assert dut.pc_o.value == 0x100
    assert dut.legal_o.value == 0

    for reads_legal in ((False, True), (True, False), (False, False)):
        await drive(
            dut,
            trap=pack_trap(1, 0, 2, 0x1234_5678),
            pc=0x400,
            reads_legal=reads_legal,
            reads=(0x0000_1808, 0x200),
        )
        assert_no_writes(dut)
        assert dut.pc_valid_o.value == 0
        assert dut.pc_o.value == 0
        assert dut.legal_o.value == 0


@cocotb.test()
async def write_legality_blocks_entry_without_changing_candidate_transaction(dut):
    """Every one of the four CSR lanes must be legal before the core may enter a trap."""
    trap = pack_trap(1, 0, 11, 0)
    for rejected_lane in range(4):
        writes_legal = [True] * 4
        writes_legal[rejected_lane] = False
        await drive(
            dut,
            trap=trap,
            pc=0x8000_1234,
            reads=(0x0000_1888, 0x4000_0081),
            writes_legal=writes_legal,
        )
        assert write_fields(dut, 0) == (1, MEPC, 0x8000_1234)
        assert write_fields(dut, 1) == (1, MCAUSE, 11)
        assert write_fields(dut, 2) == (1, MTVAL, 0)
        assert write_fields(dut, 3) == (1, MSTATUS, 0x0000_1880)
        assert dut.pc_o.value == 0x4000_0080
        assert dut.pc_valid_o.value == 0
        assert dut.legal_o.value == 0
