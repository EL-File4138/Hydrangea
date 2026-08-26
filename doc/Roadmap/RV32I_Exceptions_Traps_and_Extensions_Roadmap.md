# RV32I Exceptions, Traps, and Extensions Roadmap

**Execution environment:** [RV32I Execution-Environment Contract](../Philosophy/RV32I_Execution_Environment_Contract.md)

**Software contract:** [RV32I Software Authoring Contract](../Philosophy/RV32I_Software_Authoring_Contract.md)

**Platform roadmap:** [RV32I SoC and Platform Roadmap](RV32I_SoC_and_Platform_Roadmap.md)

## Purpose

This document orders Core and ISA work across synchronous exceptions, compliance evidence, interrupts, and optional extensions. Module and Core contracts own implemented semantics and evidence; this document owns sequencing, closure criteria, and scope control.

## Status

This is the plan of record. It does not claim support merely because work appears in a milestone, and it does not duplicate volatile regression counts or concrete implementation snapshots. Support claims require evidence recorded by the applicable implementation contract.

The architectural baseline is the RISC-V Unprivileged ISA, version 20240411. Privileged behavior shall cite an explicit privileged-architecture version when that work begins.

## 1. Stage Order

The recommended order is:

1. freeze the execution-environment mechanisms and Core/SoC/image authority split;
2. integrate the synchronous exception, CSR, and trap controllers into the Core;
3. complete Core-level verification and applicable architectural tests for the declared base and Zicsr subset;
4. add the scoped machine timer interrupt;
5. add optional extensions only when software requirements justify them.

This order avoids adding interrupts or extensions on top of undefined exception and environment behavior.

## 2. Stage 1: Execution-Environment Contract

**Status:** Cross-boundary mechanisms and authority split complete; each SoC/platform and deployment image closes under its governing document.

The [execution-environment contract](../Philosophy/RV32I_Execution_Environment_Contract.md) freezes:

- reset into Machine mode at a platform-configured, aligned, fetchable `ResetVector`;
- one 32-bit architectural address space behind separate logical IMEM and DMEM Core interfaces;
- SoC ownership of RAM, ROM, MMIO, permissions, physical topology, reset wiring, and external errors;
- deployment-image ownership of section layout, stack/heap, `__mtvec_base`, startup, and application handoff;
- no required MMIO, host device, timer, or interrupt source for a minimal pure-Core deployment;
- external-error conversion into access faults and local misalignment traps;
- serialized memory execution with base FENCE as a legal no-op; and
- application runtime self-modifying code ruled out while Zifencei is absent.

[Section 12 of the execution-environment contract](../Philosophy/RV32I_Execution_Environment_Contract.md#12-decision-disposition) records each decision's authority. A deployment shall satisfy the contract's [cross-authority closure rules](../Philosophy/RV32I_Execution_Environment_Contract.md#11-cross-authority-closure), the [software contract](../Philosophy/RV32I_Software_Authoring_Contract.md), and the applicable [SoC/platform roadmap](RV32I_SoC_and_Platform_Roadmap.md) milestones before broader support is claimed.

## 3. Implementation and Evidence Authority

The linked module contracts define ALU, register-file, decoder, CTRL, LSU, CSR/SYSTEM, CSR-bank, trap-report, and trap-entry semantics. The [Core design contract](../Implementation/RV32I_Core_Design_Contract.md) alone records the concrete FSM mapping, retained-state mapping, RTL integration status, verification commands, and results.

Roadmap sequencing assumes those authorities rather than copying their implementation snapshots. A changed module boundary or Core mapping shall update its implementation contract before this roadmap is used to claim milestone closure.

## 4. Stage 2: Core Trap and CSR Integration

**Closure authority:** [Core design contract](../Implementation/RV32I_Core_Design_Contract.md).

Required integrated behavior:

- one active instruction lifetime with invariant instruction identity;
- deterministic execution semantics and request fields derived from invariant retained state;
- state-qualified fetch, decoder, CTRL, CSR/SYSTEM, and LSU trap acceptance with decoder precedence;
- precise separation between ordinary commit and trap entry;
- atomic legal trap-state commitment and Direct-mode redirection; and
- fail-closed behavior when a mandatory trap-state update cannot be accepted.

Additional evidence work:

- add broader CSR rejection and architectural instruction coverage;
- add assertions for lifetime stability, commit exclusivity, and unreachable trap-entry failure.

## 5. Stage 3: Base and Zicsr Evidence

Run applicable architectural RV32I and Zicsr tests for the declared subset, or document each exclusion. Add small software tests for illegal instruction, ECALL, CSR read-modify-write, trap entry, and MRET. Do not claim Core-level support from standalone module regressions.

## 6. Stage 4: Machine Timer Interrupt

Add the machine timer interrupt only after synchronous traps and the frozen CSR state are stable and the SoC/platform roadmap defines the timer source. Machine external and machine software interrupts require later scope and concrete hardware requirements.

The single in-scope asynchronous source is the machine timer interrupt.

Required work:

- add Vectored-mode `mtvec` behavior as a project prerequisite for the first interrupt;
- preserve `__mtvec_base` as the Direct-handler or Vectored-table base under the software contract;
- define the timer peripheral/source interface and any required synchronization;
- drive `mip.MTIP` from the timer pending condition;
- enforce eligibility through `mstatus.MIE && mie.MTIE && mip.MTIP`;
- define priority relative to synchronous exceptions;
- define sampling points in the non-pipelined FSM;
- capture the next instruction address in `mepc`; and
- prove that interrupts are taken only at architecturally precise boundaries.

Interrupt requests should reuse `rv32_trap_pkg::trap_req_t`, whose `is_interrupt` field already distinguishes interrupts from synchronous exceptions.

## 7. Stage 5: Optional ISA Extensions

Extensions shall be requirement-driven.

### 7.1 Zifencei

Application runtime self-modifying code is out of scope, even when physical memory is writable and executable. Reconsider Zifencei only after a deliberate software requirement exists. Required work then includes complete instruction-visibility and invalidation semantics, not only decode.

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
| Core synchronous traps | Maintain integration evidence in the Core contract; add assertions and broader boundary tests |
| Core base RV32I and Zicsr | Establish applicable architectural and software evidence |
| Machine timer interrupt | Define SoC source; add Vectored mode, sampling, arbitration, RTL, software, and tests |
| Zifencei | Out of scope until a runtime self-modifying-code requirement exists |
| M | Add if software or performance requires it |
| C | Requires fetch redesign |
| A | Requires memory-system atomicity design |

## 9. Integration Policy

Core integration preserves the source ownership defined by the decoder, CTRL, LSU, CSR/SYSTEM, and memory contracts. It qualifies only the source applicable to the current FSM state and selected execution class. A decoder trap suppresses architectural acceptance of specialist results, though combinational evaluation need not be physically gated. Any added priority beyond the contracted ordering requires an explicit contract update.

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

**Authority baseline:** Cross-boundary mechanisms and the authority split are frozen; SoC and image closure remain deployment-specific.

Frozen deliverables:

- platform-configured `ResetVector` mechanism;
- one unified architectural address space with logical IMEM/DMEM ports;
- SoC ownership of maps, permissions, devices, reset, and discovery;
- deployment-image ownership of layout, startup, traps, and application handoff; and
- cross-authority closure criteria for reset, access, fault, loading, and handoff.

Concrete SoC work now proceeds under the [SoC/platform roadmap](RV32I_SoC_and_Platform_Roadmap.md); image work proceeds under the [software contract](../Philosophy/RV32I_Software_Authoring_Contract.md).

### Milestone B: Integrate Precise Synchronous Traps

Closure deliverables:

- shared report integration across the decoder, LSU, CTRL, CSR/SYSTEM controller, `rv32_trap`, and core;
- state-qualified source selection with decoder-trap precedence;
- five-state core flow with retained trap metadata;
- `rv32_trap` candidate acceptance, atomic bank commit, and Direct trap-vector control transfer;
- illegal-instruction, access-fault, and misalignment reports; and
- evidence that trapped instructions cannot perform normal commit.

Remaining evidence:

- assertions for lifetime stability, commit exclusivity, and unreachable trap-entry failure; and
- broader boundary and architectural evidence under Milestone C.

### Milestone C: Establish Core-Level Base and Zicsr Evidence

Deliverables:

- directed Core evidence for FENCE, SYSTEM, Zicsr, and MRET;
- delayed-memory/backpressure and fail-closed trap-entry evidence;
- applicable architectural tests or documented exclusions; and
- trap software tests.

### Milestone D: Add the Machine Timer Interrupt

Deliverables:

- SoC timer source and platform ABI completed under the SoC/platform roadmap;
- Vectored-mode `mtvec` and trap-target selection;
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

## 13. Open Core and Extension Work

Platform maps, devices, discovery, reset wiring, and image transport are tracked by the [SoC/platform roadmap](RV32I_SoC_and_Platform_Roadmap.md). Linker, startup, stack/heap, trap-symbol, UART-shim, and application-handoff work is tracked by the [software contract](../Philosophy/RV32I_Software_Authoring_Contract.md).

The remaining Core/ISA work is:

- Vectored-mode trap support and machine-timer interface, synchronization, sampling, and priority;
- `mcycle`, `minstret`, their RV32 high halves, and `mcountinhibit` after retirement signaling is stable;
- whether atomic operations are required;
- whether compressed instructions are required;
- which privileged-architecture version governs machine-mode work.

Caches, speculative or out-of-order memory behavior, parallel Core transactions, multiple harts, lower privilege modes, PMP, MMU, virtual memory, coherent/cache-visible independent masters, and runtime self-modifying code are baseline non-goals rather than open profile decisions.

## References

- [RISC-V Unprivileged ISA, 20240411](https://docs.riscv.org/reference/isa/unpriv/unpriv-index.html)
- [RISC-V Privileged Architecture](https://docs.riscv.org/reference/isa/priv/priv-index.html)
- [RISC-V Architectural Test Framework](https://github.com/riscv-non-isa/riscv-arch-test)
- [RISC-V Compliance Working Group repositories](https://github.com/riscv-non-isa)
- [Core architecture](../Philosophy/RV32I_Core_Architecture.md)
- [Execution-environment contract](../Philosophy/RV32I_Execution_Environment_Contract.md)
- [Software authoring contract](../Philosophy/RV32I_Software_Authoring_Contract.md)
- [SoC and platform roadmap](RV32I_SoC_and_Platform_Roadmap.md)
- [Core design contract](../Implementation/RV32I_Core_Design_Contract.md)
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
- Evidence policy: Section 12 of this roadmap; concrete results remain in the Core and module implementation contracts
