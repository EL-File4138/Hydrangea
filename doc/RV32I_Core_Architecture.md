# RV32I Core Architecture

**Scope:** System structure and architectural ownership for the baseline RV32I core

**Module contracts:** [Instruction Decoder](RV32I_Instruction_Decoder_Design_Contract.md), [CTRL](RV32I_CTRL_Design_Contract.md), [LSU](RV32I_LSU_Contract.md), [CSR/SYSTEM Controller](RV32I_CSR_SYSTEM_Design_Contract.md), [CSR Register Bank](RV32I_CSR_Register_Bank_Design_Contract.md), and [Memory Subsystem](RV32I_Memory_Subsystem_Design_Contract.md)

**Implementation plan:** [RV32I Core Implementation](RV32I_Core_Implementation.md)

**Architecture roadmap:** [Exceptions, Traps, and Extensions](RV32I_Exceptions_Traps_and_Extensions_Roadmap.md)

## 1. Purpose

This document records the stable architecture of the core: design philosophy, overall structure, abstract state and execution models, and responsibility boundaries. It does not define module ports, enum encodings, instruction tables, concrete state encoding, or cycle-level signal assignments.

The RISC-V Unprivileged ISA specification governs architectural instruction behavior. Module RTL and tests govern implemented interfaces and mappings. The linked module contracts refine the boundaries summarized here.

The terms **shall**, **shall not**, and **may** denote a requirement, a prohibition, and an implementation choice, respectively.

## 2. Architectural Philosophy

The baseline processor shall be a multicycle, in-order, single-hart core with at most one architectural instruction in progress. It shall not depend on pipelining, speculative execution, or multiple outstanding memory transactions.

The architecture favors explicit instruction lifetime and ownership over minimum cycle count. Execution units describe semantic transformations; the core owns sequencing and architectural state. A module boundary does not imply a cycle boundary.

The decoder shall expose instruction semantics and an encoding-trap candidate rather than cycle controls. The core shall resolve architectural register indices into values before invoking ALU, CTRL, LSU, or CSR/SYSTEM execution.

The core shall use one synchronous clock for persistent state. Completion, error, and trap signals are sampled conditions and shall not be used as clocks.

## 3. System Structure

```text
                                 core
        +-------------------------------------------------------+
        | PC / IR / instruction FSM                             |
        |      |                         |                       |
        |      v                         v                       |
        | LSU fetch path              decoder                   |
        |      |                    semantics + trap             |
        |      |                         |                       |
        |      |                    register file                |
        |      |                  /    |    |     \               |
        |      |                ALU  CTRL  LSU  CSR/SYSTEM       |
        |      |                  \    |    |     /               |
        |      |                   pending results               |
        |      |                         |                       |
        |      |               CSR transaction select           |
        |      |                         |                       |
        |      |                    CSR register bank            |
        |      +---- trap candidates ----+                       |
        |                       trap qualification               |
        |                         /             \                 |
        |                      COMMIT           TRAP              |
        +----------+----------------------+----------------------+
                   |                      |
             IMEM adapter            DMEM adapter
                   |                      |
          instruction backend      data/MMIO backend
```

Instruction fetch and data access remain separate Harvard paths. The implemented LSU hosts the fetch path as a pass-through and the data path as an ISA-semantic translator. Each path terminates at a required memory adapter before reaching a physical backend.

## 4. Responsibility Boundaries

| Component | Architectural responsibility |
| --- | --- |
| Core | Instruction lifetime, PC and IR ownership, register-file access, execution scheduling, pending results, memory-request lifetime, trap-source qualification and arbitration, and architectural commit or trap entry |
| Instruction decoder | Translation from instruction bits to semantic fields and reporting of illegal or unsupported encodings |
| Register file | Architectural GPR storage and preservation of `x0` |
| ALU | Combinational integer operation on supplied values |
| CTRL | Combinational branch/jump evaluation, complete control-transfer next PC, jump link value, and applicable target-alignment traps |
| LSU | Stateless fetch pass-through, data effective address, alignment, width, lane, extension semantics, memory-fault traps, and defensive invalid-uop traps |
| CSR/SYSTEM controller | Zicsr instruction semantics, exact SYSTEM interpretation, conversion of illegal bank responses into trap candidates, and controller-generated CSR transactions |
| CSR register bank | Dense physical CSR cells, architectural address dispatch, per-CSR field and reset semantics, parameterized read/write plumbing, atomic validation, and synchronous transaction commit |
| Memory adapters | Address-map validation, local-address translation, backend timing, routing, and backend error adaptation |

Execution units shall not access the register file, select destination registers, or commit architectural state. The core shall not repeat raw instruction decoding or embed the physical memory map.

Trap detection is decentralized: each unit shall report only conditions within its semantic responsibility through `rv32_trap_pkg::trap_req_t`. The CSR register bank returns operation legality but is not itself an architectural trap source; the CSR/SYSTEM controller converts an illegal instruction-directed bank response into a trap candidate. Trap handling is centralized: the core alone shall qualify active sources, select one report, retain it, and sequence precise architectural trap entry. A unit without an architecturally meaningful exceptional condition shall not receive a trap output solely for interface symmetry.

## 5. State Model

Architectural state consists of the PC, general-purpose registers, machine trap state required by the supported environment, and committed memory-visible effects. The implementation may retain nonarchitectural state including the current instruction, pending register result, pending next PC, pending trap report, and FSM state.

The PC and current instruction shall identify the same instruction throughout its execution lifetime. They shall remain stable from successful fetch completion until that instruction reaches the commit boundary or an exception path supersedes normal completion.

Execution shall first produce either pending normal values or a trap candidate. Normal PC, GPR, and instruction-directed CSR updates shall occur only at `COMMIT`. A qualified exception shall instead update trap state and trap PC through `TRAP`, with no normal completion from the faulting instruction. A completed store may already be memory-visible before the subsequent PC/GPR commit; `COMMIT` is therefore not a rollback mechanism for accepted stores.

## 6. Abstract Instruction Lifecycle

```text
FETCH --successful fetch------------> EXECUTE
EXECUTE --normal non-memory---------> COMMIT
EXECUTE --memory--------------------> LSU_WAIT
LSU_WAIT --successful completion----> COMMIT
FETCH | EXECUTE | LSU_WAIT --trap---> TRAP
COMMIT | TRAP ----------------------> FETCH
```

- **FETCH** owns one instruction transaction and considers only the fetch-path trap candidate.
- **EXECUTE** gives the decoder trap precedence, then considers only the specialist unit selected by the decoded execution class.
- **LSU_WAIT** owns one data transaction and considers only the data-side LSU trap candidate.
- **COMMIT** applies pending normal PC, GPR, and CSR effects and accepts no synchronous trap from the completing instruction.
- **TRAP** applies the selected architectural trap state and starts the next fetch at the trap vector.

These names define the abstract model. Concrete state representation and signal assignments belong to the core implementation document and RTL.

## 7. Data and Control Flow

The decoder shall emit register references, dependencies, a normalized immediate, typed execution operations, an execution/result class, write authorization, and an encoding-trap candidate. The core shall ignore semantic outputs when the decoder trap is valid; otherwise it shall read the register file and route 32-bit values to the selected unit.

For control-transfer instructions, CTRL shall return the complete next PC, including conditional-branch fall-through. For ordinary instructions, the core shall produce sequential progression by four bytes. Jump targets and link values remain separate results.

The LSU shall receive base and store-source values directly and shall calculate data effective addresses locally. All memory paths shall carry full architectural byte addresses to adapters and shall tolerate arbitrary adapter latency under the generic transaction contract. Specialist result and trap outputs are mutually exclusive candidates; the core determines the architectural exit path.

All CSR mutations shall use one shared atomic register-bank transaction interface. Parent integration shall select among controller-generated Zicsr or MRET candidates, Core-generated trap entry, timer, and future extension transactions. The CSR/SYSTEM instruction controller is not a transit point for Core trap, timer, or future-extension updates.

## 8. Scope and Evolution

The machine timer interrupt is the only interrupt source in the current planned scope, but its source interface, synchronization, sampling, and arbitration require a later implementation stage. Other interrupt sources, lower privilege modes, debug, additional ISA extensions, caches, pipelining, speculation, and increased memory concurrency require separate architecture work. Adding one of these features requires revision here only when it changes a responsibility boundary or abstract system invariant.

Changes limited to ports, state encoding, mux structure, cycle optimization, memory-map parameters, or implementation naming belong to RTL, module contracts, or the core implementation document.
