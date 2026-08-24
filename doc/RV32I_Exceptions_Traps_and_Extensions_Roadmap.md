# RV32I Exceptions, Traps, and Extensions Roadmap

## Purpose

This document defines the staged path from the current RV32I subset to a more complete RISC-V execution environment. It separates the newly contracted synchronous-trap foundation from implementation evidence, base-ISA completion, full machine-mode behavior, interrupts, and optional ISA extensions.

## Status

This is a planning and scope-control document. It does not claim support merely because work appears in a milestone. Support claims require RTL and test evidence under the project documentation policy.

The architectural baseline is the RISC-V Unprivileged ISA, version 20240411. Privileged behavior shall cite an explicit privileged-architecture version when that work begins.

## 1. Stage Order

The recommended order is:

1. freeze the execution-environment contract;
2. implement the contracted synchronous exception, minimum CSR, and trap architecture;
3. complete and verify required base-RV32I instruction behavior;
4. complete Zicsr and machine-mode return and privilege behavior;
5. add machine interrupts;
6. add optional extensions only when software requirements justify them.

This order avoids adding interrupts or extensions on top of undefined exception and environment behavior.

## 2. Stage 1: Execution-Environment Contract

Before trap RTL is added, define the environment in which software runs.

Required decisions:

- reset vector;
- instruction and data architectural ranges;
- RAM, ROM, and MMIO windows;
- behavior for unmapped addresses;
- required access widths for each MMIO device;
- misaligned-access policy;
- memory-ordering assumptions relevant to FENCE;
- whether self-modifying code is supported;
- whether software starts directly in machine mode;
- required startup ABI assumptions;
- required host communication, timer, and interrupt devices.

This stage is complete when a software image can be linked against a stable memory map and reset contract.

## 3. Stage 2: Synchronous Exceptions and Trap Entry

This stage implements and verifies the synchronous-trap contract before adding broader architectural state.

Minimum exception classes:

- instruction-address misaligned;
- instruction-access fault;
- illegal instruction;
- breakpoint;
- load-address misaligned;
- load-access fault;
- store or AMO address misaligned;
- store or AMO access fault;
- environment call from machine mode.

The current contract baseline establishes:

- one `rv32_trap_pkg::trap_req_t` report containing validity, interrupt class, cause code, and `tval`;
- decentralized detection in the unit with the required semantic knowledge and centralized core qualification, arbitration, retention, and trap entry;
- decoder-owned illegal-encoding reports with no semantic legality field and with the raw instruction in `tval`;
- transaction-qualified LSU reports for instruction, load, and store faults;
- a defensive LSU invalid-uop report using `EXC_ILLEGAL_INST` and zero `tval`;
- a retained report and explicit core `TRAP` state for precise synchronous entry;
- minimum machine trap state consisting of `mtvec`, `mepc`, `mcause`, and `mtval`;
- `mepc` equal to the faulting instruction PC, with no normal GPR, CSR, or PC commit from the trapped instruction;
- CSR/SYSTEM-owned exact SYSTEM and CSR-access legality reports;
- decoder-trap precedence followed by qualification of only the selected specialist source;
- control-target misalignment reported before normal commit; and
- machine interrupts and full privilege-stack behavior deferred.

Remaining decisions in this stage include reset values, supported `mtvec` modes, CSR WARL behavior, and any priority needed beyond decoder precedence and the serialized synchronous sources.

The per-cause `tval` policy for CSR/SYSTEM exceptions remains to be fixed by the execution-environment and privileged-architecture contract. Decoder illegal encodings already use the raw instruction, CTRL target misalignment uses the attempted target, and the defensive LSU invalid-uop path uses zero.

Misaligned loads and stores shall complete locally in the LSU with their architectural address-misaligned causes and effective-address `tval`, without issuing a DMEM request. Misaligned multi-transfer emulation remains outside the single-transfer LSU contract.

This stage is complete when RTL and tests show that a faulting instruction cannot perform a later normal commit and that control reaches a defined trap target with sufficient metadata for software handling.

## 4. Stage 3: Base RV32I Completion

Complete mandatory or environment-visible base instructions not already implemented.

Required instruction outcomes:

| Instruction | Required behavior |
| --- | --- |
| FENCE | Legal serialization no-op: no register write, no LSU request, sequential next PC |
| ECALL | Structurally decoded SYSTEM operation that reports a machine-mode environment-call exception |
| EBREAK | Structurally decoded SYSTEM operation that reports a breakpoint exception |
| Unsupported reserved encodings | Illegal-instruction exception |

Required work:

- add RTL decode coverage for FENCE and all structurally valid SYSTEM forms;
- implement exact ECALL, EBREAK, and unsupported-SYSTEM behavior in the CSR/SYSTEM boundary;
- report unsupported or reserved encodings from the decoder or CSR/SYSTEM boundary that owns the relevant legality decision;
- verify that FENCE matches the selected serialization-no-op memory model; and
- add directed tests for each newly legal or trapping encoding.

This stage is complete when the supported base-ISA statement names no silent omissions.

## 5. Stage 4: Complete Zicsr and Machine-Mode Behavior

Complete the structurally decoded CSR instructions and expand machine-mode state only as required by the target software stack.

The current implementation contract already requires CSR operation classification, prior-value writeback, minimum trap CSRs, and a machine-mode-only MRET PC result. This stage completes architectural policy around that foundation.

Required work:

- define the supported CSR address set beyond the minimum trap CSRs;
- implement and verify read, write, set, and clear CSR forms;
- define read-only and WARL behavior;
- add `mstatus` and any required ID or counter CSRs;
- complete `mtvec`, `mepc`, `mcause`, and `mtval` reset and WARL behavior;
- complete MRET privilege and interrupt-enable side effects;
- define behavior for unsupported CSR addresses; and
- add CSR read-modify-write corner-case tests.

Do not implement the full privileged architecture unless the target software requires it. A small, explicit machine-mode subset is preferable to an undocumented partial implementation.

## 6. Stage 5: Machine Interrupts

Add asynchronous interrupts only after synchronous traps and CSR state are stable.

Minimum candidate sources:

- machine timer interrupt;
- machine external interrupt;
- optionally machine software interrupt.

Required work:

- define synchronizers for asynchronous inputs;
- define pending and enable state;
- define priority relative to synchronous exceptions;
- define sampling points in the non-pipelined FSM;
- define `mip`, `mie`, and `mstatus` interactions;
- define direct versus vectored `mtvec` behavior; and
- prove that interrupts are taken only at architecturally precise boundaries.

Interrupt requests should reuse `rv32_trap_pkg::trap_req_t`, whose `interrupt` field already distinguishes interrupts from synchronous exceptions.

## 7. Stage 6: Optional ISA Extensions

Extensions shall be requirement-driven.

### 7.1 Zifencei

Add only if instruction memory can observe stale data after writes or if self-modifying code is supported. Required work includes instruction-side invalidation semantics, not only decode.

### 7.2 Zicsr

Zicsr is already part of the contracted decoder and minimum CSR/SYSTEM foundation. Its support claim remains pending until the execution boundary, CSR policy, and tests are complete.

### 7.3 M Extension

Add multiply and divide only if required by toolchain output or performance goals.

Design questions:

- iterative versus combinational implementation;
- divide-by-zero and overflow behavior;
- additional wait states;
- result timing and commit integration.

### 7.4 C Extension

Compressed instructions significantly affect fetch and PC alignment.

Required architectural changes include:

- 16-bit instruction alignment;
- variable instruction length;
- fetch extraction across word boundaries;
- revised branch and jump alignment checks;
- revised `mepc` and `mtval` behavior;
- decoder front-end expansion.

Do not treat C as a decoder-only extension.

### 7.5 A Extension

Atomics require memory-system ownership decisions before decoder work begins.

Required architectural changes include:

- reservation state;
- LR/SC semantics;
- atomic read-modify-write behavior;
- ordering and FENCE interaction;
- external-bus atomicity guarantees.

### 7.6 Other Extensions

Bit-manipulation, counters, debug, floating-point, vector, and supervisor-mode features should be planned separately because each changes software contracts and verification scope materially.

## 8. Support Matrix

| Feature | Category | Planned status |
| --- | --- | --- |
| FENCE | Base RV32I completion | Contracted as a serialization no-op; RTL and tests pending |
| ECALL / EBREAK | Base RV32I plus traps | Structural decode and trap outcomes contracted; RTL and tests pending |
| Machine CSRs | Machine-mode support | Minimum trap state contracted; reset, WARL, and broader set pending |
| MRET | Machine-mode support | Minimal `mepc` PC path contracted; full privilege effects pending |
| WFI | Optional machine-mode behavior | Add only with interrupt policy |
| Zicsr | CSR extension | Structurally contracted; execution and compliance evidence pending |
| Synchronous exceptions | Execution environment | Representation and precise core path contracted; RTL and tests pending |
| Machine interrupts | Privileged behavior | Add after precise synchronous traps |
| Zifencei | Optional extension | Add with self-modifying-code requirement |
| M | Optional extension | Add if software or performance requires it |
| C | Optional extension | Requires fetch redesign |
| A | Optional extension | Requires memory-system atomicity design |

## 9. Fault and Misalignment Policy

Fault policy shall remain layered:

- unsupported or reserved instruction encodings: reported directly by the decoder before specialist dispatch;
- instruction-address misalignment: reported by CTRL validation of a taken control-transfer target before normal commit;
- load/store misalignment: reported locally by the LSU without a memory-adapter request;
- impossible LSU micro-operations: reported defensively by the LSU as illegal instructions without a memory-adapter request;
- architectural-range and physical-memory failures: detected by memory adapters and translated by the LSU into access-fault reports;
- CSR or privilege violations: detected by CSR/SYSTEM logic;
- PMP or access-control violations: added later if protection mechanisms are introduced.

Each layer shall report one architectural cause without duplicating ownership. The core shall qualify candidates by FSM state and selected execution class, and a decoder trap shall prevent specialist dispatch. Any additional cause priority shall be explicit when a single active unit could detect multiple conditions.

## 10. Software and Compliance Strategy

Each stage shall add tests at three levels:

### 10.1 Directed RTL Tests

Verify exact state transitions, cause codes, retained metadata, request suppression, commit suppression, and return behavior.

### 10.2 Architectural Instruction Tests

Run applicable RISC-V architectural tests for the declared ISA string and privilege subset.

### 10.3 Software Tests

Use small freestanding programs before attempting larger software stacks:

1. reset and branch-only smoke test;
2. load/store and stack test;
3. illegal-instruction trap test;
4. ECALL handler test;
5. CSR read-modify-write test;
6. timer-interrupt test;
7. optional extension-specific test.

Toolchain flags and ISA strings shall match implemented extensions exactly.

## 11. Milestones

### Milestone A: Freeze the Environment

Deliverables:

- memory map;
- reset vector;
- MMIO contract;
- linker script;
- startup assumptions.

### Milestone B: Implement Precise Synchronous Traps

Deliverables:

- shared report integration across the decoder, LSU, CTRL, CSR/SYSTEM, and core;
- state-qualified source selection with decoder-trap precedence;
- five-state core flow with retained trap metadata;
- minimum machine trap CSRs and trap-vector control transfer;
- illegal-instruction, access-fault, and misalignment handling; and
- directed proof that trapped instructions cannot perform normal commit.

### Milestone C: Complete Base RV32I

Deliverables:

- FENCE serialization no-op;
- ECALL and EBREAK exact SYSTEM handling;
- reserved-encoding behavior;
- architectural compliance tests.

### Milestone D: Complete Machine Mode

Deliverables:

- complete Zicsr instruction-family behavior;
- required machine CSRs beyond the trap minimum;
- full MRET and `mstatus` behavior;
- trap software tests.

### Milestone E: Add Interrupts

Deliverables:

- timer path;
- enable and pending CSRs;
- precise interrupt entry;
- interrupt return tests.

### Milestone F: Add Requirement-Driven Extensions

Each extension requires its own contract, RTL plan, and verification plan.

## 12. Evidence Required for Support Claims

A feature may be listed as supported only when:

- decode exists for all required encodings;
- execution semantics are implemented;
- architectural side effects are precise;
- error and trap behavior is defined;
- directed tests pass;
- relevant architectural tests pass or documented exclusions exist;
- software-visible documentation names the feature and constraints.

Planned, partial, and supported are distinct statuses.

## 13. Unresolved Decisions

The following remain open until an implementation plan or decision record resolves them:

- reset vector and complete execution-environment map;
- exact reset values and WARL behavior for `mtvec`, `mepc`, `mcause`, and `mtval`;
- exact CSR/SYSTEM `tval` values for synchronous exception classes;
- exact machine CSR set beyond the minimum trap state;
- privilege and `mstatus` semantics for complete MRET behavior;
- interrupt synchronization and priority;
- whether atomic operations are required;
- whether compressed instructions are required;
- whether instruction-cache or self-modifying-code support is required;
- which privileged-architecture version governs machine-mode work.

## References

- [RISC-V Unprivileged ISA, 20240411](https://docs.riscv.org/reference/isa/unpriv/unpriv-index.html)
- [RISC-V Privileged Architecture](https://docs.riscv.org/reference/isa/priv/priv-index.html)
- [RISC-V Architectural Test Framework](https://github.com/riscv-non-isa/riscv-arch-test)
- [RISC-V Compliance Working Group repositories](https://github.com/riscv-non-isa)
- [Core architecture](RV32I_Core_Architecture.md)
- [Core implementation](RV32I_Core_Implementation.md)
- [Instruction decoder contract](RV32I_Instruction_Decoder_Design_Contract.md)
- [LSU contract](RV32I_LSU_Contract.md)
- [CSR/SYSTEM contract](RV32I_CSR_SYSTEM_Design_Contract.md)
- [Memory subsystem contract](RV32I_Memory_Subsystem_Design_Contract.md)

## Metadata

- Document type: roadmap
- Scope: exceptions, traps, machine mode, interrupts, base-ISA completion, and optional extensions
- Evidence policy: Section 12 of this roadmap
