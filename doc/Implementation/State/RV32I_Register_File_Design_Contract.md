# RV32I Register File Design Contract

**Scope:** RV32I general-purpose register storage and Core-facing read/write behavior

**Status:** Implemented; current module regression passes 6/6 tests

**Governing architecture:** [RV32I Core Architecture](../../Philosophy/RV32I_Core_Architecture.md)

**Core-owned state:** [RV32I Core-Owned State Design Contract](RV32I_Core_Owned_State_Design_Contract.md)

**Core integration:** [RV32I Core Design Contract](../RV32I_Core_Design_Contract.md)

## 1. Boundary

`rv32_register_file` shall implement 32 architectural 32-bit GPR addresses with two independent combinational read ports and one clocked write port.

Core owns instruction semantics, source and destination selection, writeback-data selection, and commit authorization. The register file shall not decode instructions, select writeback sources, update the PC, or report traps.

## 2. Read and Write Semantics

Each read port shall return the current architectural value of its selected register independently. Reads of `x0` shall always return zero.

When `write_enable_i` is asserted, the selected write shall take effect on the active clock edge. Writes to `x1` through `x31` shall become visible to subsequent combinational reads. A write addressed to `x0` shall be ignored; physical cell zero and every architectural `x0` read remain zero.

The module does not provide an architectural bypass guarantee for a read and write to the same nonzero address around one edge. Core sequencing shall avoid depending on an unspecified pre-edge value.

## 3. Reset and Core Commitment

Asserting active-low reset shall clear the physical register cells. Reset behavior is asynchronous in the current RTL.

Core shall assert the write port only for a normal instruction accepted in `COMMIT`, with destination-write intent derived from the retained instruction. Trapped instructions, stores, branches, FENCE, and SYSTEM operations without GPR results shall not cause a register-file write.

## 4. Invariants and Verification

The architectural invariants are:

1. `x0` always reads as zero.
2. The two read ports are independent and combinational.
3. At most one GPR write is accepted per clock edge.
4. Reset clears all nonzero architectural registers.
5. Register-file mutation occurs only through the clocked write port or reset.

Verification shall cover independent concurrent reads, writes and overwrites of `x1` through `x31`, `x0` read/write behavior, and asynchronous reset. The module regression is `testbench/cocotb/test-rv32_register_file.py`.

## Metadata

- Document type: module contract
- RTL authority: `rtl/core/reg/rv32_register_file.sv`
- Verification authority: `testbench/cocotb/test-rv32_register_file.py` and the passing directed Core regressions
