# RV32I CSR/SYSTEM Design Contract

**Scope:** Zicsr execution, exact SYSTEM interpretation, machine trap state, and CSR/SYSTEM trap reporting

**Governing architecture:** [RV32I Core Architecture](RV32I_Core_Architecture.md)

**Core integration:** [RV32I Core Implementation](RV32I_Core_Implementation.md)

## 1. Purpose

This document defines the semantic boundary between the core and the planned CSR/SYSTEM execution unit. Package definitions are authoritative for encoded operation values and trap fields. This contract defines normal result semantics, state-dependent legality ownership, trap reporting, and commit qualification.

## 2. Execution Boundary

The CSR/SYSTEM unit shall consume the decoded `csr_op`, `sem.imm[11:0]`, `csr_uimm`, retained `rs1` value, current instruction PC, and raw instruction context required by the selected trap-value policy.

It shall expose independent candidates for:

- the prior CSR value used for destination-register writeback;
- the normal CSR/SYSTEM next PC;
- a pending CSR mutation; and
- a `rv32_trap_pkg::trap_req_t` trap report.

The trap-reporting port is conceptually:

```systemverilog
output rv32_trap_pkg::trap_req_t trap_o
```

The unit shall not access the GPR file, select a destination register, write the core PC directly, arbitrate against another trap source, or initiate architectural trap entry.

## 3. Normal Zicsr Semantics

For a legal CSR operation, the unit shall return the prior CSR value and clear trap validity. It shall implement:

- `CSR_RW` and `CSR_RWI` replacement semantics;
- `CSR_RS` and `CSR_RSI` set-bit semantics;
- `CSR_RC` and `CSR_RCI` clear-bit semantics;
- suppression of `CSR_RS` or `CSR_RC` writes when the register source is `x0`; and
- suppression of `CSR_RSI` or `CSR_RCI` writes when `csr_uimm` is zero.

The unit shall produce pending write intent and data but shall mutate an instruction-addressed CSR only when the core authorizes normal `COMMIT`.

Ordinary Zicsr operations shall use CSR result writeback and the sequential normal-PC path.

## 4. Exact SYSTEM Interpretation

For `csr_op == CSR_SYS`, the unit shall interpret `sem.imm[11:0]` at minimum as follows:

| `imm[11:0]` | Outcome |
| --- | --- |
| `12'h000` | ECALL exception |
| `12'h001` | EBREAK exception |
| `12'h302` | MRET normal execution with `mepc` as the normal PC result |
| Other | Illegal-instruction exception |

The instruction decoder owns only structural `CSR_SYS` dispatch and shall not duplicate this exact-encoding policy.

## 5. CSR and SYSTEM Trap Ownership

The unit shall own legality checks that require CSR- or SYSTEM-specific knowledge, including:

- unimplemented CSR addresses;
- writes to read-only CSRs;
- insufficient privilege;
- unsupported CSR operations;
- unsupported exact `CSR_SYS` encodings; and
- other CSR access violations.

An illegal CSR or SYSTEM access shall report `EXC_ILLEGAL_INST` unless a later privileged-architecture requirement defines another cause. ECALL and EBREAK shall report their defined synchronous causes.

Whenever the unit reports a synchronous trap:

```text
trap_o.valid     = 1
trap_o.interrupt = 0
```

Normal Zicsr and MRET execution shall clear `trap_o.valid`. The exact `tval` policy for CSR/SYSTEM exceptions remains an execution-environment and privileged-architecture decision; the interface shall preserve enough raw instruction and PC context to implement that policy.

## 6. Machine Trap State

The initial unit or its core-owned integration state shall provide at least:

- `mtvec`;
- `mepc`;
- `mcause`; and
- `mtval`.

Core-authorized `TRAP` entry shall update this state from the retained selected report and faulting instruction PC. Normal instruction-directed CSR mutation shall remain `COMMIT`-qualified. Full `mstatus`, privilege-stack, nested-trap, and interrupt-enable behavior remains deferred.

## 7. Core Qualification

The core shall consider the CSR/SYSTEM trap candidate only in `EXECUTE`, only after the decoder trap is clear, and only for the selected CSR/SYSTEM execution class. A qualified trap shall suppress the unit's normal result, pending CSR mutation, and normal PC result and shall enter the core `TRAP` path.

The unit detects CSR/SYSTEM conditions; the core retains and arbitrates the report and owns precise architectural entry.

## 8. Conformance

Verification shall demonstrate that:

- every legal Zicsr form returns the prior CSR value and correct pending mutation without a trap;
- zero-source set and clear forms suppress CSR writes as required;
- ECALL, EBREAK, MRET, and unsupported exact SYSTEM encodings produce their defined outcomes;
- unimplemented, read-only, privilege, and unsupported-operation failures report the required trap;
- a qualified trap cannot produce a normal GPR, CSR, or PC commit;
- normal CSR updates occur only under `COMMIT` authorization;
- trap-state updates occur only under `TRAP` authorization; and
- decoder encoding checks and core trap arbitration are not duplicated in this unit.

## Related Documents

- [Core architecture](RV32I_Core_Architecture.md)
- [Core implementation](RV32I_Core_Implementation.md)
- [Instruction decoder contract](RV32I_Instruction_Decoder_Design_Contract.md)
- [Exceptions, traps, and extensions roadmap](RV32I_Exceptions_Traps_and_Extensions_Roadmap.md)

## Metadata

- Document type: planned module contract
- Authority: CSR/SYSTEM semantic ownership and trap-reporting boundary
- RTL authority: future CSR/SYSTEM unit and `rtl/core/type/rv32_inst_pkg.sv`
- Verification authority: future CSR/SYSTEM unit tests and core integration tests
