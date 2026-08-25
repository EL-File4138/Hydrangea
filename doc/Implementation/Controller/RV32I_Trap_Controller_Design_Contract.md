# RV32I Trap Controller Design Contract

**Scope:** Combinational construction and qualification of machine-mode trap-entry candidates

**Status:** Implemented; current module regression passes 4/4 tests

**Governing architecture:** [RV32I Core Architecture](../../Philosophy/RV32I_Core_Architecture.md)

**CSR register bank:** [RV32I CSR Register Bank Design Contract](../State/RV32I_CSR_Register_Bank_Design_Contract.md)

**Core integration:** [RV32I Core Implementation](../../Roadmap/RV32I_Core_Implementation.md)

## 1. Boundary and Ownership

`rv32_trap` shall consume one retained and Core-qualified `rv32_trap_pkg::trap_req_t`, the corresponding architectural return PC, two CSR read responses, and legality feedback for four candidate CSR writes.

It shall be purely combinational. It does not detect source faults, arbitrate trap sources, retain a report, commit CSR state, or own the PC. Core retains and selects the report; the CSR bank alone commits state.

## 2. CSR Reads and Candidate Transaction

The controller shall request concurrent reads of:

```text
read[0] = mstatus
read[1] = mtvec
```

For a valid trap with both reads legal, it shall construct four candidate write lanes:

```text
mepc          <- pc_i
mcause        <- {trap_i.interrupt, trap_i.code}
mtval         <- trap_i.tval
mstatus.MPIE  <- old mstatus.MIE
mstatus.MIE   <- 0
mstatus.MPP   <- M
```

The `mstatus` candidate shall preserve fields not changed by trap entry and shall set `MPP` to Machine mode (`2'b11`). The candidates use the common `csr_write_t` interface and remain subject to normal per-CSR legalization in the bank.

## 3. Trap PC and Acceptance

The controller shall form the Direct-mode trap target:

```text
pc_o = {mtvec[31:2], 2'b00}
```

It shall assert `legal_o` and `pc_valid_o` only when:

- `trap_i.valid` is asserted;
- both required CSR reads are legal; and
- all four candidate CSR write lanes are legal.

An invalid trap or an illegal required read shall suppress every write candidate and clear both acceptance outputs. An illegal write lane may leave the complete candidate transaction visible for diagnosis, but shall clear `legal_o` and `pc_valid_o` so that Core cannot commit it.

## 4. Core Integration

Core shall invoke this boundary only for the retained report selected for `TRAP`. An accepted trap transaction shall take priority over every retained normal CSR candidate and shall be committed atomically through the bank's global transaction enable. Core shall update its PC from `pc_o` only when `pc_valid_o` is asserted.

The controller is a trap-entry candidate generator, not a dedicated architectural trap handler. Core continues to own source qualification, sequencing, precise normal-effect suppression, and the transition back to `FETCH`.

## 5. Verification

Verification shall cover exception and interrupt `mcause` formation, fault-PC and `tval` preservation, `MIE`/`MPIE`/`MPP` transitions, Direct-mode target alignment, inactive input behavior, illegal CSR reads, and rejection by each candidate write lane. The module regression is `testbench/cocotb/test-rv32_trap.py`.

## Metadata

- Document type: module contract
- RTL authority: `rtl/core/ctrl/rv32_trap.sv`, `rtl/core/type/rv32_trap_pkg.sv`, and `rtl/core/type/rv32_csr_pkg.sv`
- Verification authority: `testbench/cocotb/test-rv32_trap.py` and later Core integration tests
