import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


ST_FETCH = 0
ST_TRAP = 4

CSR_MSTATUS = 0x300
CSR_MSTATUS_INDEX = 0
CSR_MSCRATCH = 0x340
CSR_MTVEC_INDEX = 3
CSR_MEPC_INDEX = 6
CSR_MCAUSE_INDEX = 7
CSR_MTVAL_INDEX = 8

EXC_INST_ADDR_MISALIGNED = 0
EXC_INST_ACCESS_FAULT = 1
EXC_ILLEGAL_INST = 2
EXC_BREAKPOINT = 3
EXC_LOAD_ADDR_MISALIGNED = 4
EXC_LOAD_ACCESS_FAULT = 5
EXC_ECALL_M = 11


def r_type(funct7, rs2, rs1, funct3, rd):
    return (
        (funct7 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | 0x33
    )


def i_type(imm, rs1, funct3, rd, opcode=0x13):
    return ((imm & 0xFFF) << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode


def s_type(imm, rs2, rs1, funct3):
    return (
        ((imm & 0xFE0) << 20)
        | (rs2 << 20)
        | (rs1 << 15)
        | (funct3 << 12)
        | ((imm & 0x1F) << 7)
        | 0x23
    )


def b_type(imm, rs2, rs1, funct3):
    return (
        ((imm & 0x1000) << 19)
        | ((imm & 0x7E0) << 20)
        | (rs2 << 20)
        | (rs1 << 15)
        | (funct3 << 12)
        | ((imm & 0x1E) << 7)
        | ((imm & 0x800) >> 4)
        | 0x63
    )


def u_type(imm20, rd, opcode):
    return (imm20 << 12) | (rd << 7) | opcode


def j_type(imm, rd):
    return (
        ((imm & 0x100000) << 11)
        | (imm & 0xFF000)
        | ((imm & 0x800) << 9)
        | ((imm & 0x7FE) << 20)
        | (rd << 7)
        | 0x6F
    )


def csr_type(csr, source, funct3, rd):
    return (csr << 20) | (source << 15) | (funct3 << 12) | (rd << 7) | 0x73


def gpr(dut, index):
    return dut.gpr_o[index].value.to_unsigned()


def csr(dut, index):
    return dut.csr_o[index].value.to_unsigned()


async def reset_and_load(
    dut, program, *, mtvec=0x80, data_words=None, install_trap_loop=True
):
    """Backdoor-load RAM after async reset and before the first fetch edge."""
    dut.rst_ni.value = 0
    await RisingEdge(dut.clk_i)
    await Timer(1, "ns")
    for address in range(256):
        dut.u_memory.u_sync_ram.mem_cell[address].value = 0
    for word_index, instruction in enumerate(program):
        dut.u_memory.u_sync_ram.mem_cell[word_index].value = instruction
    for word_index, data in (data_words or {}).items():
        dut.u_memory.u_sync_ram.mem_cell[word_index].value = data
    if install_trap_loop:
        dut.u_memory.u_sync_ram.mem_cell[mtvec >> 2].value = j_type(0, 0)
    dut.u_core.csr_register_bank.reg_cell[CSR_MTVEC_INDEX].value = mtvec
    dut.rst_ni.value = 1
    await RisingEdge(dut.clk_i)
    await Timer(1, "ns")


async def run_cycles(dut, count):
    for _ in range(count):
        await RisingEdge(dut.clk_i)
    await Timer(1, "ns")


async def wait_for_pc(dut, expected_pc, max_cycles=800):
    for _ in range(max_cycles):
        if dut.pc_o.value.to_unsigned() == expected_pc:
            return
        await RisingEdge(dut.clk_i)
    raise AssertionError(
        f"PC did not reach {expected_pc:#010x}; got {dut.pc_o.value.to_unsigned():#010x}"
    )


@cocotb.test()
async def single_instruction_program(dut):
    """A one-instruction program executes through fetch, commit, and a self-loop."""
    cocotb.start_soon(Clock(dut.clk_i, 2, "ns").start())
    await reset_and_load(dut, [i_type(42, 0, 0, 1), j_type(0, 0)])
    await wait_for_pc(dut, 4)
    await run_cycles(dut, 20)

    assert gpr(dut, 1) == 42
    assert gpr(dut, 0) == 0
    assert dut.state_o.value != ST_TRAP


@cocotb.test()
async def byte_copy_and_checksum_program(dut):
    """Copy eight bytes, compute their checksum, store it, and publish it in MSCRATCH."""
    p = [
        i_type(0x100, 0, 0, 1),  # Source pointer.
        i_type(0x140, 0, 0, 2),  # Destination pointer.
        i_type(8, 0, 0, 3),  # Bytes remaining.
        i_type(0, 0, 0, 4),  # Accumulated checksum.
        i_type(0, 1, 4, 5, 0x03),  # LBU x5, 0(x1)
        s_type(0, 5, 2, 0),  # SB x5, 0(x2)
        r_type(0, 5, 4, 0, 4),  # ADD x4, x4, x5
        i_type(1, 1, 0, 1),
        i_type(1, 2, 0, 2),
        i_type(-1, 3, 0, 3),
        b_type(-24, 0, 3, 1),  # BNE x3, x0, loop
        s_type(0x180, 4, 0, 2),  # Persist checksum.
        i_type(0x180, 0, 2, 6, 0x03),
        csr_type(CSR_MSCRATCH, 4, 0b001, 7),
        csr_type(CSR_MSCRATCH, 0, 0b010, 8),
        j_type(0, 0),
    ]
    cocotb.start_soon(Clock(dut.clk_i, 2, "ns").start())
    await reset_and_load(dut, p, data_words={0x40: 0x0B07_0503, 0x41: 0x1713_110D})
    loop_pc = (len(p) - 1) * 4
    await wait_for_pc(dut, loop_pc, max_cycles=1500)
    await run_cycles(dut, 20)

    assert gpr(dut, 4) == 98 and gpr(dut, 6) == 98 and gpr(dut, 8) == 98
    assert csr(dut, 5) == 98
    assert dut.u_memory.u_sync_ram.mem_cell[0x50].value.to_unsigned() == 0x0B07_0503
    assert dut.u_memory.u_sync_ram.mem_cell[0x51].value.to_unsigned() == 0x1713_110D
    assert dut.u_memory.u_sync_ram.mem_cell[0x60].value.to_unsigned() == 98
    assert dut.state_o.value != ST_TRAP


@cocotb.test()
async def signed_bubble_sort_program(dut):
    """Nested loops sort four signed words using conditional loads, swaps, and jumps."""
    p = [
        i_type(0x100, 0, 0, 1),  # Base address.
        i_type(3, 0, 0, 2),  # Outer pass count.
        i_type(0, 1, 0, 4),  # outer: scan pointer = base
        i_type(0, 2, 0, 5),  # comparisons left = pass count
        i_type(0, 4, 2, 6, 0x03),  # inner: LW x6, 0(x4)
        i_type(4, 4, 2, 7, 0x03),  # LW x7, 4(x4)
        b_type(8, 6, 7, 4),  # BLT x7, x6, swap
        j_type(12, 0),  # Skip swap when already ordered.
        s_type(0, 7, 4, 2),  # swap: SW x7, 0(x4)
        s_type(4, 6, 4, 2),  # SW x6, 4(x4)
        i_type(4, 4, 0, 4),  # advance: pointer += 4
        i_type(-1, 5, 0, 5),
        b_type(-32, 0, 5, 1),  # BNE x5, x0, inner
        i_type(-1, 2, 0, 2),
        b_type(-48, 0, 2, 1),  # BNE x2, x0, outer
        0x0000000F,  # FENCE after in-place updates.
        j_type(0, 0),
    ]
    cocotb.start_soon(Clock(dut.clk_i, 2, "ns").start())
    await reset_and_load(
        dut,
        p,
        data_words={0x40: 42, 0x41: 0xFFFF_FFFD, 0x42: 7, 0x43: 0},
    )
    await wait_for_pc(dut, 64, max_cycles=1200)

    assert dut.u_memory.u_sync_ram.mem_cell[0x40].value.to_unsigned() == 0xFFFF_FFFD
    assert dut.u_memory.u_sync_ram.mem_cell[0x41].value.to_unsigned() == 0
    assert dut.u_memory.u_sync_ram.mem_cell[0x42].value.to_unsigned() == 7
    assert dut.u_memory.u_sync_ram.mem_cell[0x43].value.to_unsigned() == 42
    assert dut.state_o.value.to_unsigned() != ST_TRAP


@cocotb.test()
async def zicsr_read_modify_write_operations(dut):
    """Execute every Zicsr read/write form against MSCRATCH through Core retirement."""
    p = [
        i_type(0x55, 0, 0, 1),
        csr_type(CSR_MSCRATCH, 1, 0b001, 2),  # CSRRW
        i_type(0x0F, 0, 0, 3),
        csr_type(CSR_MSCRATCH, 3, 0b010, 4),  # CSRRS
        csr_type(CSR_MSCRATCH, 3, 0b011, 5),  # CSRRC
        csr_type(CSR_MSCRATCH, 0b11010, 0b101, 6),  # CSRRWI
        csr_type(CSR_MSCRATCH, 0b00101, 0b110, 7),  # CSRRSI
        csr_type(CSR_MSCRATCH, 0b00011, 0b111, 8),  # CSRRCI
        j_type(0, 0),
    ]
    cocotb.start_soon(Clock(dut.clk_i, 2, "ns").start())
    await reset_and_load(dut, p)
    await wait_for_pc(dut, 32, max_cycles=600)

    assert (gpr(dut, 2), gpr(dut, 4), gpr(dut, 5)) == (0, 0x55, 0x5F)
    assert (gpr(dut, 6), gpr(dut, 7), gpr(dut, 8)) == (0x50, 0x1A, 0x1F)
    assert csr(dut, 5) == 0x1C


@cocotb.test()
async def ecall_mret_handler_program(dut):
    """Trap state records ECALL context, redirects to MTVEC, then MRET resumes execution."""
    handler = [
        csr_type(0x341, 0, 0b010, 3),  # CSRRS x3, mepc, x0
        i_type(4, 3, 0, 3),
        csr_type(0x341, 3, 0b001, 0),  # CSRRW x0, mepc, x3
        0x3020_0073,  # MRET
    ]
    p = [
        i_type(0x40, 0, 0, 1),
        csr_type(0x305, 1, 0b001, 0),  # Set MTVEC through Core.
        i_type(8, 0, 0, 1),
        csr_type(CSR_MSTATUS, 1, 0b001, 0),  # Set MIE before ECALL.
        0x0000_0073,
        i_type(42, 0, 0, 2),
        j_type(0, 0),
    ]
    p.extend([0] * ((0x40 // 4) - len(p)))
    p.extend(handler)
    cocotb.start_soon(Clock(dut.clk_i, 2, "ns").start())
    await reset_and_load(dut, p, mtvec=0x40, install_trap_loop=False)
    await wait_for_pc(dut, 0x40, max_cycles=500)

    assert csr(dut, CSR_MEPC_INDEX) == 16
    assert csr(dut, CSR_MCAUSE_INDEX) == EXC_ECALL_M
    assert csr(dut, CSR_MTVAL_INDEX) == 0
    assert csr(dut, CSR_MSTATUS_INDEX) == 0x0000_1880

    await wait_for_pc(dut, 24, max_cycles=500)
    assert gpr(dut, 2) == 42
    assert gpr(dut, 3) == 20
    assert csr(dut, CSR_MEPC_INDEX) == 20
    assert csr(dut, CSR_MSTATUS_INDEX) == 0x0000_1888


async def assert_trap(dut, program, code, tval, mepc=0):
    await reset_and_load(dut, program)
    await wait_for_pc(dut, 0x80, max_cycles=300)
    assert csr(dut, CSR_MEPC_INDEX) == mepc
    assert csr(dut, CSR_MCAUSE_INDEX) == code
    assert csr(dut, CSR_MTVAL_INDEX) == tval
    assert csr(dut, CSR_MSTATUS_INDEX) == 0x0000_1800


@cocotb.test()
async def invalid_instruction_trap_programs(dut):
    """Illegal encodings, SYSTEM events, and CTRL traps save precise context."""
    cocotb.start_soon(Clock(dut.clk_i, 2, "ns").start())
    await assert_trap(dut, [0xFFFF_FFFF], EXC_ILLEGAL_INST, 0xFFFF_FFFF)
    await assert_trap(dut, [0x0000_0073], EXC_ECALL_M, 0)
    await assert_trap(dut, [0x0010_0073], EXC_BREAKPOINT, 0)
    await assert_trap(dut, [j_type(2, 0)], EXC_INST_ADDR_MISALIGNED, 2)


@cocotb.test()
async def lsu_fault_trap_programs(dut):
    """Local LSU and adapter faults reach the shared trap path with no normal commit."""
    cocotb.start_soon(Clock(dut.clk_i, 2, "ns").start())
    await assert_trap(dut, [i_type(1, 0, 2, 1, 0x03)], EXC_LOAD_ADDR_MISALIGNED, 1)
    await assert_trap(
        dut,
        [u_type(0x40, 1, 0x37), i_type(0, 1, 2, 2, 0x03)],
        EXC_LOAD_ACCESS_FAULT,
        0x0004_0000,
        mepc=4,
    )
