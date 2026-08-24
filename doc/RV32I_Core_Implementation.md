# RV32I Core Implementation

## Purpose

This document defines the planned implementation structure of `rv32_core`. It translates the architectural model into retained state, state-machine behavior, datapath selection, synchronous trap handling, and module linkage. RTL remains authoritative once implementation exists.

## 1. Scope

The implementation shall provide a single-issue, non-pipelined RV32I core with one active instruction at a time. It shall integrate:

- the instruction decoder;
- the register file;
- the ALU;
- the control-transfer unit;
- the LSU;
- a CSR/SYSTEM execution boundary;
- the shared synchronous-trap representation; and
- separate instruction and data adapter channels.

Machine interrupts, nested-trap policy, and full privilege-state transitions remain deferred. The initial trap path is a precise machine-mode synchronous-exception path.

## 2. Ownership and Module Boundaries

The core shall own:

- transaction lifetime and request retention;
- instruction and operand retention;
- state-machine sequencing;
- normal result and PC selection;
- trap-source qualification, arbitration, and retention;
- architectural GPR commit authorization; and
- entry into and return from the trap path.

The decoder owns structural instruction classification and illegal-encoding reports. The ALU owns arithmetic and logical results and has no trap responsibility in the current RV32I scope. The control-transfer unit owns branch decisions, targets, link values, and applicable target-alignment reports. The LSU owns load/store formatting, memory-operation reports, fetch access-fault reports, and defensive invalid-uop reports. The CSR/SYSTEM boundary owns CSR semantics, exact SYSTEM legality, CSR-access reports, machine trap state, and MRET results.

Trap detection is decentralized across the units with the required semantic knowledge. Architectural trap handling remains centralized in the core. No unit may select the trap vector or mutate trap state directly because it detected a condition.

No execution unit may write the PC or register file directly.

## 3. External Interface Shape

The core shall expose clock and reset plus one instruction-side and one data-side adapter interface. The preferred integration form uses `rv32_mem_if` modports so the LSU remains the sole core-side memory client.

Exact top-level port names and reset-vector configuration remain RTL decisions. The interface shall preserve the architectural address convention defined by the memory subsystem contract.

## 4. Persistent State

The core requires at least:

```systemverilog
logic [31:0] pc_q;
logic [31:0] ir_q;
rv32_inst_pkg::inst_sem_t sem_q;
logic [31:0] rs1_q;
logic [31:0] rs2_q;
logic [31:0] wb_data_q;
logic [31:0] normal_pc_q;
rv32_trap_pkg::trap_req_t trap_q;
core_state_t state_q;
```

The CSR/SYSTEM boundary shall retain, at minimum, `mtvec`, `mepc`, `mcause`, and `mtval`. It may retain CSR write intent and data in core-owned or unit-owned pending state, but normal CSR mutation shall remain commit-qualified.

`trap_q` is required because source trap reports are transaction-qualified and need not remain valid after the core leaves the reporting state. On every transition into `TRAP`, the core shall capture the complete selected report before the source request is released.

The retained PC and instruction shall obey `pc_q == address of ir_q` throughout `EXECUTE` and `LSU_WAIT`. The trap path may therefore write `mepc = pc_q` without a second instruction-PC register.

## 5. Core State Machine

The initial controller shall use five architectural states:

```text
FETCH --success--------------------> EXECUTE
EXECUTE --normal non-LSU----------> COMMIT
EXECUTE --LSU---------------------> LSU_WAIT
LSU_WAIT --successful completion--> COMMIT
FETCH | EXECUTE | LSU_WAIT --trap-> TRAP
COMMIT | TRAP --------------------> FETCH
```

### 5.1 FETCH

The core shall present `pc_q` to the LSU and hold the instruction request until completion.

On a successful fetch completion, the core captures the instruction and enters `EXECUTE`. On a fetch completion carrying a valid fetch-path trap report, it captures the report and enters `TRAP` without capturing or executing an instruction. No other synchronous trap source shall be considered in `FETCH`.

### 5.2 EXECUTE

The core decodes `ir_q` and first examines the decoder trap candidate. If that candidate is valid, the core shall capture it and enter `TRAP` without meaningfully consuming the semantic record, reading execution operands, or dispatching a specialist unit.

Only when the decoder trap is clear shall the core read declared register dependencies and present retained operands to the selected execution boundary.

Dispatch shall follow the semantic record:

- a memory operation captures all LSU transaction fields and enters `LSU_WAIT`;
- a CSR or SYSTEM operation consumes the CSR/SYSTEM result or trap report;
- a control transfer consumes the control-transfer result or an instruction-address validation trap; and
- immediate, ALU, and no-result FENCE operations capture their normal result and advance to `COMMIT`.

After successful decode, the core shall consider only the trap source belonging to the selected combinational execution class. A qualified CTRL or CSR/SYSTEM trap shall be captured and shall enter `TRAP` instead of `COMMIT`. A memory operation shall enter `LSU_WAIT`, where its data-side LSU trap becomes eligible. Trap candidates from unselected units shall be ignored.

### 5.3 LSU_WAIT

The core shall assert the data request continuously and hold its operation, address, store data, destination metadata, and writeback intent stable until completion.

On a successful load completion, the core captures the returned data and enters `COMMIT`. On a successful store completion, it enters `COMMIT` with destination-write intent clear. On a completion carrying a valid data-side LSU trap, it captures the report and enters `TRAP` without normal writeback. No other synchronous source shall be considered in `LSU_WAIT`.

### 5.4 COMMIT

`COMMIT` is the only state that may perform a normal GPR write, a normal instruction-directed CSR write, or a normal PC update.

No synchronous trap from the committing instruction shall be accepted in `COMMIT`. A later interrupt design may define an architecturally precise sampling point in this state.

The core shall:

- write the selected result when destination-write intent is set and `rd != x0`;
- authorize any pending legal CSR update;
- update the PC from the retained normal PC result; and
- return to `FETCH`.

### 5.5 TRAP

`TRAP` is the only state that may commit a captured synchronous exception.

Normal execution trap candidates shall not be accepted while the core is in `TRAP`.

The core and CSR/SYSTEM boundary shall atomically:

- write the faulting instruction PC to `mepc`;
- write `{trap_q.interrupt, trap_q.code}` to `mcause`;
- write `trap_q.tval` to `mtval`;
- update the PC from the supported `mtvec` trap-vector interpretation;
- suppress GPR writeback and any pending normal CSR update; and
- return to `FETCH`.

The initial synchronous path requires `trap_q.interrupt == 0`.

## 6. Datapath Selection

### 6.1 Operand Selection

The core shall use decoder source-usage flags to determine register-file dependencies. Unused operands may be driven to benign values, but downstream behavior shall not depend on them.

### 6.2 Writeback Selection

The retained writeback source shall select one normal producer:

| Source class | Producer |
| --- | --- |
| Immediate | normalized decoder immediate |
| ALU | arithmetic or logical result |
| CTRL | control-transfer link value |
| MEM | LSU load result |
| CSR | prior CSR value or CSR/SYSTEM-defined result |

Result selection shall not authorize a register write. Commit requires retained destination-write intent and a nonzero destination index.

### 6.3 Normal PC Selection

The decoder's PC-source class is independent of writeback selection:

| PC source | Normal result |
| --- | --- |
| Sequential | `pc_q + 4` |
| CTRL | branch or jump next PC |
| CSR | CSR/SYSTEM next PC, including `mepc` for MRET |

The core shall retain the selected normal result before `COMMIT`. Trap entry overrides normal PC selection in `TRAP`; it shall not appear as a decoder PC-source encoding.

### 6.4 Effective Address and Control Targets

For memory operations, the core shall form the 32-bit wrapped sum of the retained `rs1` value and normalized immediate and pass that architectural byte address to the LSU.

For a taken control transfer, CTRL shall validate the target after all instruction-specific target rules, including JALR low-bit clearing. A target that violates the core's four-byte instruction alignment shall produce `EXC_INST_ADDR_MISALIGNED` with the attempted target in `tval`. An untaken branch shall not report a target-alignment exception.

## 7. CSR and SYSTEM Execution

The CSR/SYSTEM boundary shall consume the decoded CSR operation, `imm[11:0]` CSR or SYSTEM field, five-bit immediate source, retained `rs1` value, destination index, current PC, and raw instruction where required for trap metadata. It shall expose a `rv32_trap_pkg::trap_req_t` trap candidate independently of its normal result outputs.

For CSR read-modify-write instructions it shall:

- return the prior CSR value as the normal destination result;
- apply CSRRW replacement semantics;
- apply CSRRS set-bit semantics;
- apply CSRRC clear-bit semantics;
- suppress CSRRS or CSRRC writes when the register source is `x0`;
- suppress CSRRSI or CSRRCI writes when the immediate source is zero; and
- report illegal CSR addresses, privilege failures, read-only write attempts, and other unsupported CSR accesses as illegal instructions.

For `CSR_SYS`, it shall interpret `imm[11:0]` at minimum as follows:

| `imm[11:0]` | CSR/SYSTEM outcome |
| --- | --- |
| `12'h000` | ECALL exception |
| `12'h001` | EBREAK exception |
| `12'h302` | MRET normal execution |
| Other | Illegal-instruction exception |

Unimplemented CSR addresses, writes to read-only CSRs, insufficient privilege, unsupported CSR operations, and other CSR-access violations shall report `EXC_ILLEGAL_INST` unless a later privileged-architecture contract requires another cause.

Ordinary register and immediate Zicsr operations shall use CSR writeback with the sequential normal-PC source and shall clear trap validity. `CSR_SYS` shall use the CSR/SYSTEM normal-PC source, but an ECALL, EBREAK, or illegal exact SYSTEM encoding shall report a trap before that normal result can commit. MRET shall return `mepc` through the normal CSR PC path.

The initial machine-mode-only MRET behavior does not imply full `mstatus` or privilege-stack semantics. Those semantics shall be added with the later privilege and interrupt stage.

## 8. Trap Sourcing and Precision

All trap-capable boundaries shall use `rv32_trap_pkg::trap_req_t`. Detection is decentralized, while qualification, arbitration, retention, and architectural entry remain core responsibilities.

The source model is:

| Source | Detection responsibility | Qualifying context |
| --- | --- | --- |
| Fetch-side LSU report | Instruction-access failure | Active fetch completion in `FETCH` |
| Instruction decoder report | Illegal or unsupported encoding | Current instruction in `EXECUTE`, before specialist dispatch |
| CTRL report | Taken instruction-target misalignment | CTRL-class instruction in `EXECUTE` |
| CSR/SYSTEM report | ECALL, EBREAK, exact SYSTEM illegality, and CSR-access legality | CSR-class instruction in `EXECUTE` |
| Data-side LSU report | Alignment fault, access fault, or defensive invalid LSU uop | Active data completion in `LSU_WAIT` |
| Future interrupt report | Deferred asynchronous policy | Future architecturally defined sampling point |

The ALU has no architecturally meaningful trap condition in the current RV32I scope and shall not receive a trap output merely for symmetry.

Source qualification shall follow the FSM:

```text
FETCH:
    consider fetch-side LSU trap only

EXECUTE:
    consider decoder trap first
    if decoder trap is clear, consider only the selected specialist source

LSU_WAIT:
    consider data-side LSU trap only

COMMIT:
    accept no synchronous current-instruction trap

TRAP:
    accept no normal execution trap
```

A decoder trap has precedence over all specialist execution. Its semantic record shall be ignored, and no LSU, CSR/SYSTEM, CTRL, or other specialist operation shall be meaningfully dispatched for that instruction.

Required report outcomes include:

| Detecting unit and condition | Cause | `tval` or retained context |
| --- | --- | --- |
| Decoder illegal or unsupported encoding | `EXC_ILLEGAL_INST` | Raw retained instruction |
| CTRL taken target misaligned | `EXC_INST_ADDR_MISALIGNED` | Attempted target |
| LSU invalid micro-operation | `EXC_ILLEGAL_INST` | Zero |
| CSR/SYSTEM illegal exact encoding or access | `EXC_ILLEGAL_INST` | CSR/SYSTEM policy context |
| CSR/SYSTEM breakpoint | `EXC_BREAKPOINT` | Retained PC and raw instruction |
| CSR/SYSTEM environment call from machine mode | `EXC_ECALL_MMODE` | Retained PC and raw instruction |

Other LSU cause and `tval` semantics are defined by the LSU contract. Exact CSR/SYSTEM `tval` values remain part of the execution-environment and privileged-architecture policy; the unit shall retain sufficient context to implement that policy without changing the common event boundary.

The same core intake model shall accommodate a future interrupt arbiter using the common representation. Interrupt sampling, arbitration, and priority relative to synchronous exceptions remain deferred.

For the selected execution boundary, a successful result and an accepted trap are mutually exclusive architectural outcomes. Success advances toward `COMMIT`; failure advances toward `TRAP`, and any simultaneously present normal result is ignored.

A captured synchronous exception is precise when:

- `mepc` identifies the faulting instruction;
- no GPR or normal CSR update from that instruction occurs;
- no normal next-PC result is committed; and
- `mcause` and `mtval` describe the selected report.

## 9. Commit and Stability Invariants

The implementation shall preserve these invariants:

- one instruction is active at a time;
- the retained instruction remains stable from fetch completion through normal commit or trap entry;
- a valid decoder trap suppresses semantic consumption and specialist dispatch;
- only the trap source qualified by the current FSM state and selected execution class may be accepted;
- `pc_q` changes only on reset, `COMMIT`, or `TRAP`;
- normal GPR and instruction-directed CSR writes occur only in `COMMIT`;
- trap-state CSR writes occur only in `TRAP`;
- `COMMIT` and `TRAP` are mutually exclusive outcomes for an instruction;
- pending LSU request fields remain stable until completion;
- a trapped instruction performs no later normal commit; and
- register `x0` always reads as zero and ignores writes.

## 10. Reset Behavior

Reset shall place the core in `FETCH`, initialize the PC from the configured reset vector, clear pending write and trap intent, and initialize machine trap state to documented implementation values.

No GPR write, CSR write, or data-memory request may occur solely because reset is asserted or released.

## 11. Verification Obligations

Core-level verification shall cover:

- reset and first fetch;
- all normal state transitions;
- request retention under instruction and data backpressure;
- ALU, immediate, control, load, store, CSR, SYSTEM, and FENCE paths;
- decoder-owned illegal-encoding reports with raw-instruction `tval`;
- decoder-trap precedence over every specialist unit;
- rejection of inactive or wrong-state trap candidates;
- writeback and normal PC-source independence;
- load writeback only after successful completion;
- no destination write for stores, branches, SYSTEM operations, FENCE, or trapped instructions;
- illegal-instruction, breakpoint, environment-call, instruction-target, instruction-access, load, and store trap causes;
- exact `mepc` and `mcause` updates and faithful `mtval` capture from each report;
- trap-vector PC selection and MRET return through distinct paths;
- suppression of normal CSR writes when a CSR operation traps;
- local LSU trap completion without a DMEM request;
- defensive invalid-LSU-uop completion with `EXC_ILLEGAL_INST` and zero `tval`;
- no duplicate commit under stretched ready; and
- `x0` immutability.

Assertions should encode the state, stability, commit, trap exclusivity, and transaction-qualification invariants directly.

## 12. Implementation Sequence

Recommended implementation order:

1. stabilize shared instruction and trap package types without a semantic legality field;
2. complete decoder CSR, SYSTEM, FENCE, and encoding-trap semantics;
3. implement and unit-test the CSR/SYSTEM boundary;
4. implement the five-state core controller and retained datapath;
5. integrate state-qualified decoder, LSU, CSR/SYSTEM, and control-target trap reports;
6. add focused core-level tests for normal and exceptional flows; and
7. add a small integration program covering load, store, branch, CSR, trap entry, and MRET.

## 13. Deferred Decisions

The following remain explicit follow-up decisions:

- exact top-level naming and reset-vector configuration;
- CSR reset values and WARL behavior, including supported `mtvec` modes;
- CSR/SYSTEM `tval` values for illegal accesses, breakpoints, and environment calls;
- the implemented CSR address set beyond `mtvec`, `mepc`, `mcause`, and `mtval`;
- full `mstatus`, privilege-stack, and nested-trap semantics;
- interrupt inputs, synchronization, arbitration, and priority; and
- implementation-specific memory backend selection outside the core.

## Module Contracts

- [Core architecture](RV32I_Core_Architecture.md)
- [Instruction decoder contract](RV32I_Instruction_Decoder_Design_Contract.md)
- [CTRL unit contract](RV32I_CTRL_Design_Contract.md)
- [LSU contract](RV32I_LSU_Contract.md)
- [CSR/SYSTEM contract](RV32I_CSR_SYSTEM_Design_Contract.md)
- [Memory subsystem contract](RV32I_Memory_Subsystem_Design_Contract.md)
- [Exceptions, traps, and extensions roadmap](RV32I_Exceptions_Traps_and_Extensions_Roadmap.md)

## Metadata

- Document type: implementation contract
- Scope: planned `rv32_core` controller, datapath, CSR/SYSTEM, and synchronous-trap integration
- Architectural authority: [RV32I Core Architecture](RV32I_Core_Architecture.md)
- Interface authority: package definitions and module RTL
- Verification authority: module and core integration tests
