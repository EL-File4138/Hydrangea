# RV32I Exceptions, Traps, and Extensions Roadmap

## Purpose

This document orders work that remains after the established decoder, LSU, CSR, SYSTEM, and standalone trap-controller behavior. Module contracts own implemented semantics; this document owns sequencing and scope control for unexecuted integration and extensions.

## Status

This is a planning and scope-control document. It does not claim support merely because work appears in a milestone. Support claims require RTL and test evidence under the project documentation policy.

The architectural baseline is the RISC-V Unprivileged ISA, version 20240411. Privileged behavior shall cite an explicit privileged-architecture version when that work begins.

## 1. Stage Order

The recommended order is:

1. freeze the execution-environment mechanisms and per-build profile-completion rule (**complete**);
2. integrate the established synchronous exception, CSR, and trap controllers into the core;
3. complete Core-level verification and applicable architectural tests for the declared base and Zicsr subset;
4. add the scoped machine timer interrupt;
5. add optional extensions only when software requirements justify them.

This order avoids adding interrupts or extensions on top of undefined exception and environment behavior.

## 2. Stage 1: Execution-Environment Contract

**Status:** Complete at the mechanism and profile-requirement level; each concrete build remains subject to profile closure.

The [execution-environment contract](../Philosophy/RV32I_Execution_Environment_Contract.md), as clarified by its [configuration/profile amendment](../RV32I_Execution_Environment_Profile_Amendment.md), freezes:

- reset into Machine mode at a configured, aligned, fetchable `ResetVector`;
- logical Harvard IMEM and DMEM paths using full architectural addresses, with maps and physical topology resolved by each profile;
- coherent per-build resolution of reset, memory, linker entry, stack, image-loading, and any device values;
- no required MMIO, host device, timer, or interrupt source for the first pure-Core simulation milestone;
- explicit access-fault and misalignment behavior;
- serialized memory execution with base FENCE as a legal no-op;
- no runtime self-modifying code or FENCE.I; and
- the placement-independent RV32 ILP32 startup and stack rules needed to link a freestanding image.

Section 12 maps every Stage 1 question to a frozen mechanism or profile-resolution obligation. The current adapter defaults may still provide a direct-preload, zero-based 256 KiB shared-RAM simulation, but those numerical values are not Core invariants. Every concrete simulation or FPGA build shall satisfy the closure checklist in Section 11 before its software configuration is claimed consistent. Profile-resolved values, implementation-local choices, and absent future facilities are classified in the [execution-environment deferred decisions register](../Philosophy/RV32I_Execution_Environment_Deferred_Decisions.md).

## 3. Established Module Foundation

The following behavior is implemented and directly tested at module boundaries. Its authoritative semantics are in the linked contracts, not this roadmap:

- ALU, register-file, decoder, CTRL, LSU, CSR/SYSTEM controller, and CSR register-bank behavior, including base FENCE, exact SYSTEM forms, Zicsr, MRET, and the current 15 CSR views;
- one `rv32_trap_pkg::trap_req_t` representation for synchronous reports; and
- `rv32_trap` construction of four-lane machine trap-entry candidates and Direct-mode `mtvec` selection, with its 4/4 module regression passing.

Core integration remains unimplemented. It must retain and qualify one source report, select the `rv32_trap` transaction only in `TRAP`, commit it atomically, and suppress the trapped instruction's normal PC, GPR, and CSR effects.

## 4. Stage 2: Core Trap and CSR Integration

Required work:

- implement the five-state Core flow and retained instruction, result, CSR, and trap state;
- qualify fetch, decoder, CTRL, CSR/SYSTEM, and LSU reports in their defined FSM contexts, with decoder precedence;
- route accepted `trap_q` and the retained faulting PC through `rv32_trap` during `TRAP`;
- commit the accepted four-lane transaction atomically and redirect the PC only when `rv32_trap` declares it legal;
- integrate normal Zicsr and MRET transactions into `COMMIT`; and
- add Core-level directed tests for precise trap entry, suppression, MRET, and CSR commit rejection.

## 5. Stage 3: Base and Zicsr Evidence

Run applicable architectural RV32I and Zicsr tests for the declared subset, or document each exclusion. Add small software tests for illegal instruction, ECALL, CSR read-modify-write, trap entry, and MRET. Do not claim Core-level support from standalone module regressions.

## 6. Stage 4: Machine Timer Interrupt

Add the machine timer interrupt only after synchronous traps and the frozen CSR state are stable. Machine external and machine software interrupts require a later scope amendment.

The single in-scope asynchronous source is the machine timer interrupt.

Required work:

- define the timer peripheral/source interface and any required synchronization;
- drive `mip.MTIP` from the timer pending condition;
- enforce eligibility through `mstatus.MIE && mie.MTIE && mip.MTIP`;
- define priority relative to synchronous exceptions;
- define sampling points in the non-pipelined FSM;
- capture the next instruction address in `mepc`; and
- prove that interrupts are taken only at architecturally precise boundaries.

Interrupt requests should reuse `rv32_trap_pkg::trap_req_t`, whose `interrupt` field already distinguishes interrupts from synchronous exceptions.

## 7. Stage 5: Optional ISA Extensions

Extensions shall be requirement-driven.

### 7.1 Zifencei

Add only if instruction memory can observe stale data after writes or if self-modifying code is supported. Required work includes instruction-side invalidation semantics, not only decode.

### 7.2 M Extension

Add multiply and divide only if required by toolchain output or performance goals.

Design questions:

- iterative versus combinational implementation;
- divide-by-zero and overflow behavior;
- additional wait states;
- result timing and commit integration.

### 7.3 C Extension

Compressed instructions significantly affect fetch and PC alignment.

Required architectural changes include:

- 16-bit instruction alignment;
- variable instruction length;
- fetch extraction across word boundaries;
- revised branch and jump alignment checks;
- revised `mepc` and `mtval` behavior;
- decoder front-end expansion.

Do not treat C as a decoder-only extension.

### 7.4 A Extension

Atomics require memory-system ownership decisions before decoder work begins.

Required architectural changes include:

- reservation state;
- LR/SC semantics;
- atomic read-modify-write behavior;
- ordering and FENCE interaction;
- external-bus atomicity guarantees.

### 7.5 Other Extensions

Bit-manipulation, counters, debug, floating-point, vector, and supervisor-mode features should be planned separately because each changes software contracts and verification scope materially.

## 8. Support Matrix

| Feature | Remaining work |
| --- | --- |
| Core synchronous traps | Integrate source qualification, retained trap state, `rv32_trap`, atomic bank commit, and Direct-mode PC redirection |
| Core base RV32I and Zicsr | Integrate established FENCE, SYSTEM, CSR, MRET, CTRL, and LSU outcomes; add Core and architectural evidence |
| Machine timer interrupt | Define source, sampling, arbitration, RTL, and tests |
| Zifencei | Add with self-modifying-code requirement |
| M | Add if software or performance requires it |
| C | Requires fetch redesign |
| A | Requires memory-system atomicity design |

## 9. Integration Policy

Core integration shall preserve the source ownership defined by the decoder, CTRL, LSU, CSR/SYSTEM, and memory contracts. It shall qualify only the source applicable to the current FSM state and selected execution class; a decoder trap shall prevent specialist dispatch. Any added priority beyond that established ordering requires an explicit contract update.

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

### Milestone B: Integrate Precise Synchronous Traps

Deliverables:

- shared report integration across the decoder, LSU, CTRL, CSR/SYSTEM controller, `rv32_trap`, and core;
- state-qualified source selection with decoder-trap precedence;
- five-state core flow with retained trap metadata;
- `rv32_trap` candidate acceptance, atomic bank commit, and Direct trap-vector control transfer;
- established illegal-instruction, access-fault, and misalignment reports; and
- directed proof that trapped instructions cannot perform normal commit.

### Milestone C: Establish Core-Level Base and Zicsr Evidence

Deliverables:

- Core tests for FENCE, SYSTEM, Zicsr, and MRET;
- applicable architectural tests or documented exclusions; and
- trap software tests.

### Milestone D: Add the Machine Timer Interrupt

Deliverables:

- timer path;
- hardware-driven `MTIP` and `MIE && MTIE && MTIP` eligibility;
- a defined sampling and arbitration point;
- precise interrupt entry;
- interrupt return tests.

### Milestone E: Add Requirement-Driven Extensions

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

## 13. Open Profile and Architecture Work

The following remain open until an implementation plan, concrete profile, or decision record resolves them. Profile-resolved values do not represent unresolved Core architecture:

- concrete reset, boot, memory, MMIO, and device values for any additional platform profile, under the mechanisms and closure rule in the [deferred decisions register](../Philosophy/RV32I_Execution_Environment_Deferred_Decisions.md);
- machine timer interface, synchronization, sampling, and priority;
- `mcycle`, `minstret`, their RV32 high halves, and `mcountinhibit` after retirement signaling is stable;
- whether atomic operations are required;
- whether compressed instructions are required;
- whether instruction-cache or self-modifying-code support is required;
- which privileged-architecture version governs machine-mode work.

## References

- [RISC-V Unprivileged ISA, 20240411](https://docs.riscv.org/reference/isa/unpriv/unpriv-index.html)
- [RISC-V Privileged Architecture](https://docs.riscv.org/reference/isa/priv/priv-index.html)
- [RISC-V Architectural Test Framework](https://github.com/riscv-non-isa/riscv-arch-test)
- [RISC-V Compliance Working Group repositories](https://github.com/riscv-non-isa)
- [Core architecture](../Philosophy/RV32I_Core_Architecture.md)
- [Execution-environment contract](../Philosophy/RV32I_Execution_Environment_Contract.md)
- [Execution-environment configuration/profile amendment](../RV32I_Execution_Environment_Profile_Amendment.md)
- [Execution-environment deferred decisions](../Philosophy/RV32I_Execution_Environment_Deferred_Decisions.md)
- [Core implementation](RV32I_Core_Implementation.md)
- [Instruction decoder contract](../Implementation/Controller/RV32I_Instruction_Decoder_Design_Contract.md)
- [Trap controller contract](../Implementation/Controller/RV32I_Trap_Controller_Design_Contract.md)
- [ALU contract](../Implementation/Execution/RV32I_ALU_Design_Contract.md)
- [CTRL contract](../Implementation/Execution/RV32I_CTRL_Design_Contract.md)
- [LSU contract](../Implementation/Execution/RV32I_LSU_Contract.md)
- [CSR/SYSTEM controller contract](../Implementation/Execution/RV32I_CSR_SYSTEM_Design_Contract.md)
- [Register-file contract](../Implementation/State/RV32I_Register_File_Design_Contract.md)
- [Core-owned state contract](../Implementation/State/RV32I_Core_Owned_State_Design_Contract.md)
- [CSR register-bank contract](../Implementation/State/RV32I_CSR_Register_Bank_Design_Contract.md)
- [Memory subsystem contract](../Implementation/IO/RV32I_Memory_Subsystem_Design_Contract.md)

## Metadata

- Document type: roadmap
- Scope: exceptions, traps, machine mode, interrupts, base-ISA completion, and optional extensions
- Evidence policy: Section 12 of this roadmap
