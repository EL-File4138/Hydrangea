# RV32I Core Architecture

**Scope:** System structure and architectural ownership for the baseline RV32I core

**Module contracts:** [Instruction Decoder](RV32I_Instruction_Decoder_Design_Contract.md), [CTRL](RV32I_CTRL_Design_Contract.md), [LSU](RV32I_LSU_Contract.md), and [Memory Subsystem](RV32I_Memory_Subsystem_Design_Contract.md)

**Implementation plan:** [RV32I Core Implementation](RV32I_Core_Implementation.md)

**Architecture roadmap:** [Exceptions, Traps, and Extensions](RV32I_Exceptions_Traps_and_Extensions_Roadmap.md)

## 1. Purpose

This document records the stable architecture of the core: design philosophy, overall structure, abstract state and execution models, and responsibility boundaries. It does not define module ports, enum encodings, instruction tables, concrete state encoding, or cycle-level signal assignments.

The RISC-V Unprivileged ISA specification governs architectural instruction behavior. Module RTL and tests govern implemented interfaces and mappings. The linked module contracts refine the boundaries summarized here.

The terms **shall**, **shall not**, and **may** denote a requirement, a prohibition, and an implementation choice, respectively.

## 2. Architectural Philosophy

The baseline processor shall be a multicycle, in-order, single-hart core with at most one architectural instruction in progress. It shall not depend on pipelining, speculative execution, or multiple outstanding memory transactions.

The architecture favors explicit instruction lifetime and ownership over minimum cycle count. Execution units describe semantic transformations; the core owns sequencing and architectural state. A module boundary does not imply a cycle boundary.

The decoder shall expose instruction semantics rather than cycle controls. The core shall resolve architectural register indices into values before invoking ALU, CTRL, or LSU execution.

The core shall use one synchronous clock for persistent state. Memory completion and error signals are sampled conditions and shall not be used as clocks.

## 3. System Structure

```text
                                 core
        +---------------------------------------------------+
        | PC / IR / instruction FSM                         |
        |      |                         |                   |
        |      v                         v                   |
        | LSU fetch path              decoder               |
        |                                |                  |
        |                           register file            |
        |                         /      |       \            |
        |                       ALU    CTRL    LSU data       |
        |                         \      |       /            |
        |                         pending results            |
        |                                |                  |
        |                              COMMIT               |
        +----------+----------------------+------------------+
                   |                      |
             IMEM adapter            DMEM adapter
                   |                      |
          instruction backend      data/MMIO backend
```

Instruction fetch and data access remain separate Harvard paths. The implemented LSU hosts the fetch path as a pass-through and the data path as an ISA-semantic translator. Each path terminates at a required memory adapter before reaching a physical backend.

## 4. Responsibility Boundaries

| Component | Architectural responsibility |
| --- | --- |
| Core | Instruction lifetime, PC and IR ownership, register-file access, execution scheduling, pending results, memory-request lifetime, and architectural commit |
| Instruction decoder | Static legality for the decoded subset and translation from instruction bits to semantic fields |
| Register file | Architectural GPR storage and preservation of `x0` |
| ALU | Combinational integer operation on supplied values |
| CTRL | Combinational branch/jump evaluation, complete control-transfer next PC, and jump link value |
| LSU | Stateless fetch pass-through plus data effective address, alignment, width, lane, and extension semantics |
| Memory adapters | Address-map validation, local-address translation, backend timing, routing, and backend error adaptation |

Execution units shall not access the register file, select destination registers, or commit architectural state. The core shall not repeat raw instruction decoding or embed the physical memory map.

## 5. State Model

Architectural state consists of the PC, general-purpose registers, and committed memory-visible effects. The implementation may retain nonarchitectural state including the current instruction, pending register result, pending next PC, and FSM state.

The PC and current instruction shall identify the same instruction throughout its execution lifetime. They shall remain stable from successful fetch completion until that instruction reaches the commit boundary or an exception path supersedes normal completion.

Execution shall first produce pending values. PC and GPR updates shall occur only at the explicit commit boundary. A completed store may already be memory-visible before the subsequent PC/GPR commit; COMMIT is therefore the core's PC/GPR architectural boundary, not a rollback mechanism for accepted stores.

## 6. Abstract Instruction Lifecycle

```text
                 +-------+
                 | FETCH |
                 +---+---+
                     |
                     v
                +---------+
                | EXECUTE |
                +----+----+
                     |
          +----------+----------+
          |                     |
   ALU / CTRL / IMM          load/store
          |                     |
          |                     v
          |                +----------+
          |                | LSU_WAIT |
          |                +----+-----+
          |                     |
          +----------+----------+
                     v
                 +--------+
                 | COMMIT |
                 +----+---+
                      |
                      +------> FETCH
```

- **FETCH** owns one instruction transaction and may last for arbitrary memory latency.
- **EXECUTE** evaluates stable decode semantics and combinational execution results.
- **LSU_WAIT** owns one data transaction until successful or failed completion.
- **COMMIT** applies pending PC and authorized GPR effects and starts the next instruction lifetime.

These names define the abstract model. Concrete state representation and signal assignments belong to the core implementation document and RTL.

## 7. Data and Control Flow

The decoder shall emit register references, dependencies, a normalized immediate, typed execution operations, an execution/result class, and write authorization. The core shall read the register file and route 32-bit values to the selected unit.

For control-transfer instructions, CTRL shall return the complete next PC, including conditional-branch fall-through. For ordinary instructions, the core shall produce sequential progression by four bytes. Jump targets and link values remain separate results.

The LSU shall receive base and store-source values directly and shall calculate data effective addresses locally. All memory paths shall carry full architectural byte addresses to adapters and shall tolerate arbitrary adapter latency under the generic transaction contract.

## 8. Scope and Evolution

Trap routing, privileged state, interrupts, debug, additional ISA extensions, caches, pipelining, speculation, and increased memory concurrency require separate architecture work. Adding one of these features requires revision here only when it changes a responsibility boundary or abstract system invariant.

Changes limited to ports, state encoding, mux structure, cycle optimization, memory-map parameters, or implementation naming belong to RTL, module contracts, or the core implementation document.
