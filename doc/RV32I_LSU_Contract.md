# RV32I LSU Design Contract

**Scope:** Instruction-fetch pass-through and RV32I load/store semantics

**Governing architecture:** [RV32I Core Architecture](RV32I_Core_Architecture.md)

**Core integration:** [RV32I Core Implementation](RV32I_Core_Implementation.md)

**Memory contract:** [RV32I Memory Subsystem Design Contract](RV32I_Memory_Subsystem_Design_Contract.md)

## 1. Purpose

This document defines the semantic boundary of `rv32_lsu`. RTL is authoritative for ports, encoded operation values, and combinational implementation details. This contract defines ownership, transaction behavior, result meaning, and architectural trap reporting.

The terms **shall**, **shall not**, and **may** denote a requirement, a prohibition, and an implementation choice, respectively.

## 2. Subsystem Role

`rv32_lsu` contains two independent paths:

- an instruction-fetch transaction pass-through between the core and the IMEM adapter; and
- a data path that translates decoded load/store semantics into DMEM transactions.

Hosting both paths does not make instruction fetch a load/store operation. The paths use separate `rv32_mem_if` instances and share no architectural state.

The LSU shall remain stateless and memory-map agnostic. It shall not own the PC, instruction register, general-purpose register file, architectural writeback, address-range decoding, local-memory rebasing, MMIO selection, or backend protocol state.

## 3. Ownership

### 3.1 Core

The core shall own request lifetime, operand lookup, instruction and data-operation sequencing, response capture, architectural commit, and handling of reported LSU traps. It shall hold each asserted request and all associated inputs stable until completion.

### 3.2 LSU

The LSU shall own:

- instruction-request pass-through;
- data effective-address generation;
- load/store direction, width, and signedness semantics;
- natural-alignment validation;
- architectural byte-lane selection;
- lane-positioned store data and write strobes;
- load extraction and sign or zero extension; and
- local trap completion for a misaligned data operation or defensive invalid micro-operation.

### 3.3 Adapters

The IMEM and DMEM adapters shall own architectural-range validation, physical address mapping, backend sequencing, latency, and backend error detection. The LSU shall translate adapter errors into architectural access-fault reports and shall not issue backend-local addresses or signals.

## 4. Core-Facing Semantics

### 4.1 Instruction fetch

The core supplies an explicit 32-bit architectural byte address and a level-sensitive fetch request. The LSU forwards the transaction to the IMEM adapter and returns its completion, instruction word, and architectural trap report.

The LSU shall not infer that the supplied address is the live PC and shall not update the instruction register.

### 4.2 Data access

The core supplies the decoded LSU operation, base-register value, store-source value, and normalized immediate. These are operand values, not architectural register indices.

The effective data address is the 32-bit sum of the base value and immediate. The LSU shall present that full architectural byte address to the DMEM adapter without rebasing or truncation.

A successful load result shall be a fully selected and sign- or zero-extended 32-bit value. The load-result output is inactive for stores. A failed data transaction shall return a trap report rather than a boolean core-facing error. The LSU shall not select a destination register or authorize writeback.

## 5. Adapter-Facing Data Convention

The LSU shall be a requester on independent IMEM and DMEM instances of `rv32_mem_if`.

For writes, `wdata` shall be positioned in the destination architectural byte lanes, and each asserted `wstrb` bit shall identify the corresponding valid byte lane. Adapters may translate this representation into backend-native byte enables but shall not reconstruct ISA store semantics.

For reads, an adapter shall return a raw 32-bit word in architectural byte-lane order. The LSU shall use the effective-address low bits to select a byte or halfword and shall apply load extension locally.

The IMEM path shall issue read-only transactions and shall drive inactive write fields to zero.

## 6. Transaction Semantics

Core-side and adapter-side requests are level-sensitive transaction-valid signals, not one-cycle pulses. While a request is pending, the requester shall hold the request fields stable.

A transaction completes when `req && ready` is observed on a rising clock edge. `err` qualifies that completion and shall be meaningful only when `ready` is asserted. After completion, the requester shall deassert `req` before starting another transaction on the same interface. No explicit error-clear transaction exists.

Core-facing completion and trap outputs shall be consumed only while the corresponding fetch or data request is asserted. A core-facing transaction completes when that request and its ready output are asserted together.

The LSU shall not capture requests or contain a transaction FSM. The core owns the core-facing request lifetime, and each adapter owns backend temporal behavior.

The baseline permits at most one outstanding transaction per interface. The baseline core does not overlap instruction and data transactions.

## 7. Architectural Trap Reports

The LSU shall expose `if_trap_o` and `data_trap_o`, each typed as `rv32_trap_pkg::trap_req_t`. The common structure carries:

| Field | Meaning |
| --- | --- |
| `valid` | A trap is reported for the active transaction |
| `interrupt` | Trap class; always clear for LSU-generated reports |
| `code[30:0]` | Architectural exception cause |
| `tval[31:0]` | Architectural trap value; the faulting address for memory faults |

Every reported LSU trap shall have `valid = 1` and `interrupt = 0`. The LSU shall report:

| Condition | Cause | `tval` |
| --- | --- | --- |
| Instruction access fault | `EXC_INST_ACCESS_FAULT` | Requested instruction address |
| Load address misaligned | `EXC_LOAD_ADDR_MISALIGNED` | Effective data address |
| Load access fault | `EXC_LOAD_ACCESS_FAULT` | Effective data address |
| Store address misaligned | `EXC_STORE_ADDR_MISALIGNED` | Effective data address |
| Store access fault | `EXC_STORE_ACCESS_FAULT` | Effective data address |
| Invalid LSU micro-operation | `EXC_ILLEGAL_INST` | Zero |

Adapter-originated access faults shall be reported only for an active, locally valid transaction. Instruction traps shall be invalid when the fetch request is clear. Data completion and data traps shall be inactive when the data request is clear.

The LSU remains a synchronous-exception source only. Interrupt construction and arbitration remain outside this contract.

## 8. Local Data Traps

Byte accesses may use any byte address. Halfword accesses require `address[0] == 0`, and word accesses require `address[1:0] == 2'b00`.

For an asserted local data-validation fault with a defined architectural cause, including a misaligned data request or invalid LSU micro-operation, the LSU shall:

- suppress the DMEM request;
- report immediate data completion with a valid architectural trap; and
- produce no architectural side effect directly.

An active data request carrying an impossible or unsupported `lsu_op_i` value shall report `EXC_ILLEGAL_INST` with `tval = 0`. This defensive path exists because the LSU need not receive the original instruction bits. It shall remain unreachable under correct decoder and core dispatch and may additionally be guarded by assertions.

The LSU outcome classes are therefore:

```text
valid operation    -> normal memory semantics
local memory fault -> architectural alignment trap
invalid LSU uop    -> illegal-instruction trap
adapter failure    -> architectural access-fault trap
```

Trap qualification, arbitration, and execution-environment policy remain core responsibilities.

## 9. Conformance

Verification shall demonstrate that:

- fetch transactions pass through without acquiring data-load/store semantics;
- effective addresses remain full 32-bit architectural byte addresses;
- store data and strobes match the addressed lanes;
- load selection and extension cover every implemented width and lane;
- misaligned operations complete locally with the correct cause and effective-address `tval` and issue no DMEM request;
- every invalid LSU micro-operation completes locally with `EXC_ILLEGAL_INST`, zero `tval`, and no DMEM request;
- defensive invalid-operation reporting remains transaction-qualified and does not replace decoder encoding checks;
- pending request inputs remain stable;
- adapter errors are translated into transaction-qualified instruction, load, or store access-fault reports;
- inactive core-facing requests suppress trap validity and data completion;
- the LSU contains no transaction-lifetime or architectural state; and
- replacing either memory adapter does not change LSU semantics.

This contract requires revision if instruction fetch leaves the LSU boundary, the LSU becomes stateful, the transaction-lifetime rules change, or load/store semantic ownership moves across the LSU/adapter boundary.
