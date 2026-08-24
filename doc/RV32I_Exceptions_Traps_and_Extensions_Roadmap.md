# RV32I Exceptions, Traps, and Extensions Roadmap

**Status:** Architecture planning

**Governing architecture:** [RV32I Core Architecture](RV32I_Core_Architecture.md)

**Memory contract:** [RV32I Memory Subsystem Design Contract](RV32I_Memory_Subsystem_Design_Contract.md)

**LSU contract:** [RV32I LSU Design Contract](RV32I_LSU_Contract.md)

**Core implementation:** [RV32I Core Implementation](RV32I_Core_Implementation.md)

## 1. Purpose

This document tracks architecture that must be designed before expanding the core's ISA and execution-environment claims. It is not evidence that an instruction or feature is implemented. Decoder RTL and executable tests remain authoritative for current support.

Items shall be removed from this roadmap or marked complete only when their architectural behavior, implementation, and verification evidence all exist.

## 2. Base-RV32I Completion Work

The following base-ISA behavior requires architecture beyond arithmetic, load/store, and control-transfer execution:

| Work item | Required design outcome | Completion evidence |
| --- | --- | --- |
| `FENCE` | Defined ordering behavior for the selected memory system and a rule for draining relevant transactions | Litmus or directed ordering tests and core assertions |
| `ECALL` | Defined execution-environment request or precise trap destination | Faulting-PC/cause test with no earlier or later side-effect ambiguity |
| `EBREAK` | Defined breakpoint response through the execution environment, trap path, or later debug architecture | Precise breakpoint test and documented resume/termination behavior |

For a single-issue core with no speculative or outstanding accesses, `FENCE` may require little datapath action. It shall nevertheless count as integrated support only after the ordering argument and completion condition are explicit.

## 3. Exception Architecture

### 3.1 Required event boundary

The core requires one unambiguous event path from the detecting unit to the core FSM or trap subsystem. The event representation is expected to carry, as applicable:

- event validity and cause;
- the PC of the faulting instruction;
- instruction or address context needed by the execution environment;
- whether a memory transaction has already been accepted; and
- enough completion information to prevent architectural side effects after the event.

Signal names and encoded cause values are deferred until the execution environment is selected.

### 3.2 Events to address

The architecture shall define behavior for:

- an unsupported or illegal instruction;
- instruction-address misalignment where the implemented control-transfer rules can produce it;
- load/store address misalignment under the selected policy;
- instruction or data access failure if exposed by the memory interface;
- environment calls;
- breakpoints; and
- reset or cancellation while an instruction or memory request is in progress.

Static instruction support remains a decoder responsibility. Dynamic event detection remains with the unit that has the required runtime information: data alignment belongs to the LSU, while physical range, routing, and device-access failures belong to the memory adapter.

### 3.3 Precision rule

An exception is precise when all older instructions have committed, the faulting instruction has not partially committed an architectural result, and no younger instruction has committed. The baseline one-instruction-at-a-time execution model should simplify this rule but does not replace explicit handling of accepted stores and PC updates.

## 4. Architecture Sequence

### Stage 1: Minimal execution environment

Define how the baseline system reports termination and exceptional events. Options include a testbench-visible stop interface, a platform service request, or a trap entry path. This decision shall precede `ECALL` and `EBREAK` support.

### Stage 2: Precise synchronous exceptions

Add the event boundary and implement illegal-instruction, alignment, and exposed memory-fault behavior. Verify that the core suppresses register writeback, PC redirection, and unaccepted memory side effects for the faulting instruction.

### Stage 3: Base-ISA completion

Implement and verify `FENCE`, `ECALL`, and `EBREAK` against the selected memory model and execution environment. Only then evaluate whether the integrated core may claim the intended base-RV32I profile.

### Stage 4: Privileged execution and CSRs

If software beyond the minimal execution environment is required, define the privilege level, trap-vector behavior, exception return, architectural CSRs, and the `Zicsr` instruction extension. Privileged state shall remain outside the semantic decoder unless a decode field is genuinely required at the boundary.

### Stage 5: Interrupts and platform sources

Define interrupt priority, sampling, precision, timer/software/external sources, and interaction with memory waits. Interrupt support depends on the privileged/trap state selected in Stage 4.

### Stage 6: Debug architecture

Treat halt, resume, single-step, abstract register access, and breakpoint integration as a separate architecture project. `EBREAK` behavior may later route into debug mode, but base breakpoint handling shall not assume that debug hardware already exists.

## 5. Later ISA and Microarchitecture Projects

The following work is independent of base-RV32I completion and shall receive separate design plans before implementation:

- multiplication and division;
- compressed instructions and variable-length fetch alignment;
- atomics and the accompanying memory-ordering requirements;
- caches, address translation, and protection;
- pipelining, hazards, speculation, or multiple outstanding transactions; and
- board- or SoC-specific debug and interrupt integration.

Adding one of these features may require revision of the core architecture when it changes an existing semantic or ownership boundary.

## 6. Decisions Requiring an Architecture Record

| Decision | Why it must be explicit |
| --- | --- |
| Target execution environment | Determines whether exceptions terminate, signal a host, or enter a trap handler |
| Misaligned data-error handling | Defines the architectural response to LSU-reported alignment failures |
| Memory-fault model | Determines whether access failures can occur and where they are reported |
| Trap entry and return state | Defines architectural PC/state updates and required CSRs |
| Accepted-store behavior on exception/reset | Required to preserve precise side-effect semantics |
| `FENCE` completion condition | Defines the core's observable memory-ordering guarantee |
| Interrupt sampling point | Determines precision around multicycle waits and commit |
| `EBREAK` destination | Coordinates execution-environment, trap, and debug behavior |

Each resolved item should be captured in a focused architecture decision record or in the implemented interface's protocol documentation, not left as prose in this roadmap.

## 7. Verification and Support Gates

An architecture item is complete only when:

- the integrated core advertises only encodings with a complete execution path;
- directed tests cover the normal and exceptional outcomes;
- assertions enforce precise side effects at the core boundary;
- software-visible behavior is documented for the selected execution environment; and
- advertised ISA, privilege, interrupt, and debug claims match executable regression evidence.

The RISC-V Unprivileged ISA specification is normative for base instructions and extensions. The RISC-V Privileged Architecture and Debug Specification become normative only for the corresponding stages above.
