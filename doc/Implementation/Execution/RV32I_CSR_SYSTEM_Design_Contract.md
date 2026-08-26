# RV32I CSR/SYSTEM Controller Design Contract

**Scope:** Zicsr instruction semantics, exact SYSTEM interpretation, CSR-access traps, and production of CSR-bank transactions

**Status:** Implemented, regression-tested, and frozen for Core integration

**Governing architecture:** [RV32I Core Architecture](../../Philosophy/RV32I_Core_Architecture.md)

**CSR register bank:** [RV32I CSR Register Bank Design Contract](../State/RV32I_CSR_Register_Bank_Design_Contract.md)

**Core integration:** [RV32I Core Design Contract](../RV32I_Core_Design_Contract.md)

## 1. Purpose

This document defines the semantic boundary of the combinational `rv32_csr_controller` controller. Package definitions and module RTL are authoritative for encoded fields and exact port spelling. The register-bank contract is authoritative for storage topology, address dispatch, per-CSR semantics, reset, and atomic commitment.

The controller implements instruction behavior and interprets bank legality responses. It does not own CSR storage, commit architectural state, arbitrate traps, or perform trap entry.

## 2. Controller Boundary

The controller shall consume:

- decoded `csr_op_i`;
- `csr_imm_i[11:0]` as an architectural CSR address or exact SYSTEM field;
- `csr_uimm_i[4:0]` for immediate Zicsr forms;
- the architectural `rs1` value through `rs1_var_i`;
- `rd_is_zero_i` and `rs1_is_zero_i` for Zicsr suppression rules;
- two CSR-bank read legality and data responses; and
- legality feedback for its candidate CSR write.

It shall produce:

- two CSR read addresses;
- the prior CSR value for possible GPR writeback;
- zero or one candidate `csr_write_t` lane;
- an MRET PC result and validity flag; and
- one `rv32_trap_pkg::trap_req_t` candidate.

The controller shall be purely combinational and shall retain no architectural or transaction state.

## 3. Register-Bank Interface

The controller uses two combinational read ports. Ordinary Zicsr operations use read port zero when a read is architecturally required. MRET uses both ports concurrently.

The candidate write uses the shared bank lane type:

```systemverilog
typedef struct packed {
    logic        write_enable;
    logic [11:0] address;
    logic [31:0] write_data;
} csr_write_t;
```

The package spellings are authoritative. An ordinary Zicsr or MRET status update is the one-enabled-lane case of the shared bank transaction interface; there is no dedicated controller-only write path.

The candidate is resolved by the bank's per-CSR semantics and returned to the controller as `csr_wr_legal_i`. This legality feedback qualifies the instruction result but does not commit the candidate. Parent Core logic alone authorizes the bank's global write enable at the architectural commit point.

## 4. Zicsr Access Rules

The controller shall implement all six Zicsr operations with the following architectural access behavior:

| Operation | CSR read | CSR write |
| --- | --- | --- |
| `CSR_RW` | iff `rd != x0` | always |
| `CSR_RS` | always | iff `rs1 != x0` |
| `CSR_RC` | always | iff `rs1 != x0` |
| `CSR_RWI` | iff `rd != x0` | always |
| `CSR_RSI` | always | iff `csr_uimm != 0` |
| `CSR_RCI` | always | iff `csr_uimm != 0` |

A suppressed read shall not address the instruction-selected CSR through a read port and therefore cannot fail. The associated `CSR_RW` or `CSR_RWI` write remains required and may independently be illegal.

A suppressed write shall produce a disabled candidate lane. Its unused write-legality feedback shall not make the instruction illegal.

A required read that receives an illegal bank response shall terminate the instruction with an illegal-instruction report and shall suppress any candidate write. A candidate write that receives an illegal bank response shall also terminate the instruction with an illegal-instruction report. The candidate may remain visible for combinational legality evaluation, but Core shall not commit it when the trap report is valid.

## 5. Zicsr Result Computation

For a required legal read, `rd_result_o` shall contain the prior architectural CSR value. The candidate write value shall be:

```text
CSR_RW  : rs1
CSR_RS  : old | rs1
CSR_RC  : old & ~rs1

CSR_RWI : zero_extend(csr_uimm)
CSR_RSI : old | zero_extend(csr_uimm)
CSR_RCI : old & ~zero_extend(csr_uimm)
```

For `CSR_RW` and `CSR_RWI` with `rd == x0`, no prior value is required for architectural writeback and the controller may return a benign zero result.

The controller returns only the candidate result. Core remains responsible for destination-register authorization and architectural GPR commitment.

## 6. Exact SYSTEM Interpretation

For `csr_op_i == CSR_SYS`, the controller shall interpret `csr_imm_i` exactly as follows:

| `csr_imm_i` | Outcome |
| --- | --- |
| `12'h000` with `rs1 == x0` and `rd == x0` | `make_exception(EXC_ECALL_M, 0)` |
| `12'h001` with `rs1 == x0` and `rd == x0` | `make_exception(EXC_BREAKPOINT, 0)` |
| `12'h105` with `rs1 == x0` and `rd == x0` | WFI no-op |
| `12'h302` with `rs1 == x0` and `rd == x0` | MRET execution |
| Other | `make_exception(EXC_ILLEGAL_INST, 0)` |

Any nonzero `rs1` or `rd` for these exact SYSTEM operations is illegal. WFI shall produce no CSR read, candidate write, trap, or PC redirect; Core consequently selects sequential `pc + 4`. The instruction decoder owns structural `CSR_SYS` dispatch and shall not duplicate this exact-encoding policy.

### 6.1 MRET

MRET shall issue two concurrent reads:

```text
read[0] = mepc
read[1] = mstatus
```

When both reads are legal, the controller shall construct one candidate `mstatus` write equivalent to:

```text
new_mstatus       = old_mstatus
new_mstatus.MIE   = old_mstatus.MPIE
new_mstatus.MPIE  = 1
```

The register bank applies its normal `mstatus` field filtering to that candidate.

MRET succeeds only when both required reads and the candidate `mstatus` write are legal. On success:

- `pc_valid_o` shall be asserted;
- `pc_o` shall contain the bank's aligned `mepc` read value;
- the `mstatus` candidate shall remain enabled for Core commitment; and
- the trap report shall be clear.

If either read is illegal, the controller shall suppress the write candidate, clear `pc_valid_o`, and report `make_exception(EXC_ILLEGAL_INST, 0)`. If the `mstatus` write is illegal, the controller shall clear `pc_valid_o` and report the same exception; Core shall not commit the candidate.

## 7. Trap Detection and Ownership

The controller shall use the common `make_exception(code, tval)` helper for ECALL, EBREAK, unsupported SYSTEM operations, unsupported CSR operations, illegal required reads, illegal candidate writes, and defensive MRET access failures.

Every controller-generated report is synchronous:

```text
trap_o.is_valid     = 1
trap_o.is_interrupt = 0
```

The current controller reports zero `tval` for all of these conditions. It uses `EXC_ECALL_M` for ECALL, `EXC_BREAKPOINT` for EBREAK, and `EXC_ILLEGAL_INST` for all CSR/SYSTEM legality failures.

The controller detects and reports these conditions. Core qualifies the active report, arbitrates it against other sources, retains it, and performs precise trap entry. No dedicated trap-handler controller is introduced.

## 8. Architectural Commitment and Core Integration

Core shall consider the controller outputs only for a selected CSR/SYSTEM execution class in `EXECUTE`, after confirming that the decoder trap candidate is clear.

Successful Zicsr and MRET candidates may proceed to `COMMIT` while remaining deterministic functions of invariant instruction state. A valid controller trap shall instead select `TRAP` and shall prevent commitment of:

- the candidate GPR result;
- the normal PC result; and
- the candidate CSR write.

MRET's `mstatus` candidate originates in this controller. Core trap entry does not pass through this controller: Core constructs the four-lane atomic transaction for `mstatus`, `mepc`, `mcause`, and `mtval` and redirects the PC to Direct-mode `mtvec`.

All CSR mutation still occurs in the CSR register bank. Parent integration selects the applicable controller, trap-entry, timer, or future-extension transaction and authorizes its global commitment.

## 9. Validation Status

The dedicated controller regression at `testbench/cocotb/test-rv32_csr_controller.py` passes **6/6** tests. Its combined cases cover:

- all six Zicsr computations;
- `rd == x0` read suppression for `CSR_RW` and `CSR_RWI`;
- zero-source write suppression for register and immediate set/clear forms;
- required-read and candidate-write illegality;
- write suppression after a failed required read;
- ECALL, EBREAK, WFI, malformed exact-SYSTEM, and illegal SYSTEM reports;
- successful MRET;
- MRET read and status-write failures; and
- MRET PC-valid suppression on failure.

The controller/register-bank integration regression at `testbench/cocotb/test-rv32_csr_csrreg_tb.py` passes **2/2** tests, covering legal and illegal Zicsr commitment plus MRET status restoration through the shared bank interface.

These passing regressions satisfy the controller completion criterion. The CSR controller and register bank are complete and frozen for Core integration except for bug fixes or explicit contract changes.

## 10. Design Invariants

1. `rv32_csr_controller` is purely combinational and owns no CSR storage.
2. The controller uses two bank read ports and produces at most one candidate write lane.
3. Suppressed Zicsr reads and writes do not create legality failures.
4. A failed required read suppresses any dependent candidate write.
5. A valid trap prevents Core commitment even if an illegal candidate remains exposed for bank feedback.
6. MRET PC validity requires two legal reads and a legal `mstatus` candidate.
7. The controller converts bank illegality into instruction-level traps but does not duplicate address dispatch or per-field semantics.
8. Core owns trap arbitration and entry; the bank owns all CSR state commitment.
9. Exact SYSTEM operations require `rs1 == x0` and `rd == x0`; legal WFI is side-effect free.

## Related Documents

- [Core architecture](../../Philosophy/RV32I_Core_Architecture.md)
- [Core design contract](../RV32I_Core_Design_Contract.md)
- [CSR register-bank contract](../State/RV32I_CSR_Register_Bank_Design_Contract.md)
- [Instruction decoder contract](../Controller/RV32I_Instruction_Decoder_Design_Contract.md)
- [Trap controller contract](../Controller/RV32I_Trap_Controller_Design_Contract.md)
- [Exceptions, traps, and extensions roadmap](../../Roadmap/RV32I_Exceptions_Traps_and_Extensions_Roadmap.md)

## Metadata

- Document type: module contract
- Authority: Zicsr and SYSTEM instruction semantics, CSR-access trap conversion, MRET result generation, and controller-generated bank transactions
- RTL authority: `rtl/core/exec/rv32_csr_controller.sv`, `rtl/core/type/rv32_inst_pkg.sv`, `rtl/core/type/rv32_csr_pkg.sv`, and `rtl/core/type/rv32_trap_pkg.sv`
- Verification authority: `testbench/cocotb/test-rv32_csr_controller.py`, `testbench/cocotb/test-rv32_csr_csrreg_tb.py`, and the passing directed Core regressions
