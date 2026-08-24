import random

import cocotb
from cocotb.triggers import Timer


LSU_LB = 0b0000
LSU_LH = 0b0001
LSU_LW = 0b0010
LSU_LBU = 0b0100
LSU_LHU = 0b0101
LSU_SB = 0b1000
LSU_SH = 0b1001
LSU_SW = 0b1010
LOAD_OPS = (LSU_LB, LSU_LH, LSU_LW, LSU_LBU, LSU_LHU)
STORE_OPS = (LSU_SB, LSU_SH, LSU_SW)
LEGAL_OPS = LOAD_OPS + STORE_OPS
RANDOM_CASES = 100


async def settle():
    await Timer(1, "ns")


def set_imem_response(dut, ready=0, rdata=0, err=0):
    dut.imem_ready_i.value = ready
    dut.imem_rdata_i.value = rdata
    dut.imem_err_i.value = err


def set_dmem_response(dut, ready=0, rdata=0, err=0):
    dut.dmem_ready_i.value = ready
    dut.dmem_rdata_i.value = rdata
    dut.dmem_err_i.value = err


async def drive_data(dut, op, base, imm, store_data=0, req=1):
    dut.data_req_i.value = req
    dut.lsu_op_i.value = op
    dut.base_i.value = base
    dut.imm_i.value = imm
    dut.store_data_i.value = store_data
    await settle()


def assert_dmem_request(dut, address, write_enable, wdata=0, wstrb=0):
    assert dut.dmem_req_o.value == 1
    assert dut.dmem_addr_o.value.to_unsigned() == address
    assert dut.dmem_we_o.value == write_enable
    assert dut.dmem_wdata_o.value.to_unsigned() == wdata
    assert dut.dmem_wstrb_o.value.to_unsigned() == wstrb


def reference_lsu(op, address, store_data, returned_word):
    lane = address & 0b11
    if op in (LSU_LB, LSU_LBU):
        value = (returned_word >> (8 * lane)) & 0xFF
        if op == LSU_LB and value & 0x80:
            value |= 0xFFFF_FF00
        return 0, 0, 0, value
    if op in (LSU_LH, LSU_LHU):
        value = (returned_word >> (8 * lane)) & 0xFFFF
        if op == LSU_LH and value & 0x8000:
            value |= 0xFFFF_0000
        return 0, 0, 0, value
    if op == LSU_LW:
        return 0, 0, 0, returned_word
    if op == LSU_SB:
        return 1, (store_data & 0xFF) << (8 * lane), 1 << lane, None
    if op == LSU_SH:
        return 1, (store_data & 0xFFFF) << (8 * lane), 0b0011 << lane, None
    if op == LSU_SW:
        return 1, store_data, 0b1111, None
    raise AssertionError(f"unexpected LSU operation {op}")


async def assert_reference_case(dut, op, address, store_data, returned_word):
    write_enable, wdata, wstrb, expected_load = reference_lsu(
        op, address, store_data, returned_word
    )
    set_dmem_response(dut, ready=1, rdata=returned_word)
    await drive_data(dut, op, 0, address, store_data)
    assert_dmem_request(dut, address, write_enable, wdata, wstrb)
    assert dut.data_ready_o.value == 1
    assert dut.data_err_o.value == 0
    if expected_load is not None:
        assert dut.load_result_o.value.to_unsigned() == expected_load


@cocotb.test()
async def fetch_request_passes_through_adapter_events(dut):
    """Forward fetch fields and propagate IMEM completion/data/error unchanged."""
    dut.if_req_i.value = 1
    dut.if_addr_i.value = 0xFFFF_FFFC
    set_imem_response(dut, ready=0)
    set_dmem_response(dut)
    await settle()

    assert dut.imem_req_o.value == 1
    assert dut.imem_we_o.value == 0
    assert dut.imem_addr_o.value.to_unsigned() == 0xFFFF_FFFC
    assert dut.imem_wdata_o.value.to_unsigned() == 0
    assert dut.imem_wstrb_o.value.to_unsigned() == 0
    assert dut.if_ready_o.value == 0

    set_imem_response(dut, ready=1, rdata=0x1234_5678, err=1)
    await settle()
    assert dut.if_ready_o.value == 1
    assert dut.if_rdata_o.value.to_unsigned() == 0x1234_5678
    assert dut.if_err_o.value == 1


@cocotb.test()
async def pending_data_request_keeps_adapter_transaction_live(dut):
    """A level-sensitive request remains presented until the adapter completes it."""
    dut.if_req_i.value = 0
    set_imem_response(dut)
    set_dmem_response(dut, ready=0)
    await drive_data(dut, LSU_SW, 0xFFFF_FFF8, 4, 0xDEAD_BEEF)

    assert_dmem_request(dut, 0xFFFF_FFFC, 1, 0xDEAD_BEEF, 0b1111)
    assert dut.data_ready_o.value == 0
    assert dut.data_err_o.value == 0
    await settle()
    assert_dmem_request(dut, 0xFFFF_FFFC, 1, 0xDEAD_BEEF, 0b1111)

    set_dmem_response(dut, ready=1)
    await settle()
    assert dut.data_ready_o.value == 1
    assert dut.data_err_o.value == 0


@cocotb.test()
async def store_lane_data_and_strobes_match_effective_address(dut):
    """Position byte/halfword stores in their addressed architectural lanes."""
    dut.if_req_i.value = 0
    set_imem_response(dut)
    set_dmem_response(dut, ready=1)
    base = 0x8000_1000

    for lane in range(4):
        await drive_data(dut, LSU_SB, base, lane, 0xA1B2_C3D4)
        assert_dmem_request(dut, base + lane, 1, 0xD4 << (8 * lane), 1 << lane)
        assert dut.data_ready_o.value == 1
        assert dut.data_err_o.value == 0

    for lane in (0, 2):
        await drive_data(dut, LSU_SH, base, lane, 0xA1B2_C3D4)
        assert_dmem_request(dut, base + lane, 1, 0xC3D4 << (8 * lane), 0b0011 << lane)

    await drive_data(dut, LSU_SW, base, 0, 0xA1B2_C3D4)
    assert_dmem_request(dut, base, 1, 0xA1B2_C3D4, 0b1111)


@cocotb.test()
async def loads_select_and_extend_each_lane(dut):
    """Select load lanes from raw DMEM words and apply the requested extension."""
    dut.if_req_i.value = 0
    set_imem_response(dut)
    raw_word = 0x80FF_7F01
    set_dmem_response(dut, ready=1, rdata=raw_word)
    base = 0x4000_0000

    for lane, expected_signed, expected_unsigned in (
        (0, 0x0000_0001, 0x0000_0001),
        (1, 0x0000_007F, 0x0000_007F),
        (2, 0xFFFF_FFFF, 0x0000_00FF),
        (3, 0xFFFF_FF80, 0x0000_0080),
    ):
        await drive_data(dut, LSU_LB, base, lane)
        assert_dmem_request(dut, base + lane, 0)
        assert dut.load_result_o.value.to_unsigned() == expected_signed
        await drive_data(dut, LSU_LBU, base, lane)
        assert dut.load_result_o.value.to_unsigned() == expected_unsigned

    for lane, expected_signed, expected_unsigned in (
        (0, 0x0000_7F01, 0x0000_7F01),
        (2, 0xFFFF_80FF, 0x0000_80FF),
    ):
        await drive_data(dut, LSU_LH, base, lane)
        assert dut.load_result_o.value.to_unsigned() == expected_signed
        await drive_data(dut, LSU_LHU, base, lane)
        assert dut.load_result_o.value.to_unsigned() == expected_unsigned

    await drive_data(dut, LSU_LW, base, 0)
    assert dut.load_result_o.value.to_unsigned() == raw_word


@cocotb.test()
async def invalid_or_misaligned_data_operations_complete_locally(dut):
    """Reject invalid operations locally without exposing a DMEM request."""
    dut.if_req_i.value = 0
    set_imem_response(dut)
    set_dmem_response(dut, ready=0)

    for op, imm in (
        (LSU_LH, 1), (LSU_LHU, 3), (LSU_LW, 2),
        (LSU_SH, 1), (LSU_SW, 3), (0b0011, 0), (0b1111, 0),
    ):
        await drive_data(dut, op, 0x100, imm, 0xDEAD_BEEF)
        assert dut.dmem_req_o.value == 0
        assert dut.data_ready_o.value == 1
        assert dut.data_err_o.value == 1


@cocotb.test()
async def adapter_error_is_reported_on_data_completion(dut):
    """Return DMEM errors through the data response without changing load semantics."""
    dut.if_req_i.value = 0
    set_imem_response(dut)
    set_dmem_response(dut, ready=1, rdata=0x1122_3344, err=1)
    await drive_data(dut, LSU_LW, 0x200, 0)

    assert_dmem_request(dut, 0x200, 0)
    assert dut.data_ready_o.value == 1
    assert dut.data_err_o.value == 1
    assert dut.load_result_o.value.to_unsigned() == 0x1122_3344


def random_legal_address(op):
    address = random.getrandbits(32)
    if op in (LSU_LH, LSU_LHU, LSU_SH):
        return address & ~0b1
    if op in (LSU_LW, LSU_SW):
        return address & ~0b11
    return address


@cocotb.test()
async def randomized_reference_model_covers_every_legal_operation(dut):
    """Compare each legal operation to an independent randomized reference model."""
    dut.if_req_i.value = 0
    set_imem_response(dut)
    for op in LEGAL_OPS:
        for _ in range(RANDOM_CASES):
            await assert_reference_case(
                dut,
                op,
                random_legal_address(op),
                random.getrandbits(32),
                random.getrandbits(32),
            )


@cocotb.test()
async def randomized_reference_model_covers_random_addresses(dut):
    """Exercise reference-model behavior at independently randomized addresses."""
    dut.if_req_i.value = 0
    set_imem_response(dut)
    for _ in range(RANDOM_CASES):
        op = random.choice(LEGAL_OPS)
        await assert_reference_case(
            dut,
            op,
            random_legal_address(op),
            random.getrandbits(32),
            random.getrandbits(32),
        )


@cocotb.test()
async def randomized_reference_model_covers_random_store_data(dut):
    """Exercise store lane placement against randomized architectural values."""
    dut.if_req_i.value = 0
    set_imem_response(dut)
    for _ in range(RANDOM_CASES):
        op = random.choice(STORE_OPS)
        await assert_reference_case(
            dut,
            op,
            random_legal_address(op),
            random.getrandbits(32),
            random.getrandbits(32),
        )


@cocotb.test()
async def randomized_reference_model_covers_random_returned_words(dut):
    """Exercise load lane selection and extension against randomized DMEM words."""
    dut.if_req_i.value = 0
    set_imem_response(dut)
    for _ in range(RANDOM_CASES):
        op = random.choice(LOAD_OPS)
        await assert_reference_case(
            dut,
            op,
            random_legal_address(op),
            random.getrandbits(32),
            random.getrandbits(32),
        )


@cocotb.test()
async def pending_data_request_keeps_dmem_fields_stable(dut):
    """A pending request must not alter DMEM fields before its completion event."""
    dut.if_req_i.value = 0
    set_imem_response(dut)
    for op in LEGAL_OPS:
        address = random_legal_address(op)
        store_data = random.getrandbits(32)
        set_dmem_response(dut, ready=0, rdata=random.getrandbits(32))
        await drive_data(dut, op, 0, address, store_data)
        assert dut.data_req_i.value == 1
        assert dut.data_ready_o.value == 0
        fields = (
            int(dut.dmem_req_o.value),
            int(dut.dmem_we_o.value),
            dut.dmem_addr_o.value.to_unsigned(),
            dut.dmem_wdata_o.value.to_unsigned(),
            dut.dmem_wstrb_o.value.to_unsigned(),
        )
        set_dmem_response(dut, ready=0, rdata=random.getrandbits(32))
        await settle()
        assert fields == (
            int(dut.dmem_req_o.value),
            int(dut.dmem_we_o.value),
            dut.dmem_addr_o.value.to_unsigned(),
            dut.dmem_wdata_o.value.to_unsigned(),
            dut.dmem_wstrb_o.value.to_unsigned(),
        )


@cocotb.test()
async def dmem_error_requires_a_completion_event(dut):
    """An adapter error is only visible when the adapter also signals ready."""
    dut.if_req_i.value = 0
    set_imem_response(dut)
    set_dmem_response(dut, ready=0, err=1)
    await drive_data(dut, LSU_LW, 0, 0)
    assert dut.dmem_req_o.value == 1
    assert dut.data_ready_o.value == 0
    assert dut.data_err_o.value == 0

    set_dmem_response(dut, ready=1, err=1)
    await settle()
    assert dut.data_ready_o.value == 1
    assert dut.data_err_o.value == 1


@cocotb.test()
async def local_error_completes_without_a_dmem_request(dut):
    """Misaligned and unsupported data operations fail locally and immediately."""
    dut.if_req_i.value = 0
    set_imem_response(dut)
    set_dmem_response(dut, ready=0)
    for op, address in ((LSU_LH, 1), (LSU_LW, 2), (LSU_SH, 3), (LSU_SW, 1), (0b0011, 0)):
        await drive_data(dut, op, 0, address, random.getrandbits(32))
        assert dut.data_err_o.value == 1
        assert dut.data_ready_o.value == 1
        assert dut.dmem_req_o.value == 0


@cocotb.test()
async def fetch_request_exactly_mirrors_core_request_fields(dut):
    """Every asserted Core fetch request is forwarded unchanged to IMEM."""
    dut.data_req_i.value = 0
    set_dmem_response(dut)
    set_imem_response(dut, ready=0)
    for _ in range(RANDOM_CASES):
        address = random.getrandbits(32)
        dut.if_req_i.value = 1
        dut.if_addr_i.value = address
        await settle()
        assert dut.imem_req_o.value == 1
        assert dut.imem_we_o.value == 0
        assert dut.imem_addr_o.value.to_unsigned() == address
        assert dut.imem_wdata_o.value.to_unsigned() == 0
        assert dut.imem_wstrb_o.value.to_unsigned() == 0
