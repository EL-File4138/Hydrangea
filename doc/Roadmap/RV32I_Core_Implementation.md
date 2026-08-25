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
- a CSR/SYSTEM instruction controller;
- a shared CSR register bank;
- a dedicated combinational trap-entry controller;
- the shared architectural trap representation; and
- separate instruction and data adapter channels.

The initial trap path is a precise Machine-mode synchronous-exception path. The architectural CSR state required by one later machine timer interrupt is included, but the timer interface, synchronization, sampling point, and interrupt arbitration remain deferred. Other interrupt sources, lower privilege modes, and nested-trap policy remain outside the current scope.

## 2. Ownership and Module Boundaries

The core shall own:

- transaction lifetime and request retention;
- instruction and operand retention;
- state-machine sequencing;
- normal result and PC selection;
- trap-source qualification, arbitration, and retention;
- architectural GPR commit authorization; and
- entry into and return from the trap path.

The decoder owns structural instruction classification and illegal-encoding reports. The ALU owns arithmetic and logical results and has no trap responsibility in the current RV32I scope. The control-transfer unit owns branch decisions, targets, link values, and applicable target-alignment reports. The LSU owns load/store formatting, memory-operation reports, fetch access-fault reports, and defensive invalid-uop reports. The CSR/SYSTEM controller owns Zicsr instruction semantics, exact SYSTEM interpretation, conversion of illegal instruction-directed bank responses into traps, and MRET results. The CSR register bank owns physical cells, address dispatch, per-CSR field and reset semantics, transaction legality, and synchronous state commitment. `rv32_trap` owns the combinational machine trap-entry CSR and PC candidates from a retained trap report.

Trap detection is decentralized across the units with the required semantic knowledge. Architectural trap handling remains centralized in the core. No unit may select the trap vector or mutate trap state directly because it detected a condition.

No execution unit may write the PC or register file directly.

## 3. External Interface Shape

The core shall expose clock and reset plus one instruction-side and one data-side adapter interface. The preferred integration form uses `rv32_mem_if` modports so the LSU remains the sole core-side memory client.

Exact top-level port names and reset-vector parameter plumbing remain RTL decisions. On reset, the PC shall take the configured, aligned, fetchable `ResetVector`; its numerical value is resolved by the active build profile rather than frozen as a Core invariant. RTL parameters, linker/startup configuration, and the boot path shall agree under the [execution-environment contract](../Philosophy/RV32I_Execution_Environment_Contract.md). The interface shall preserve the architectural address convention defined by the memory subsystem contract.

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

The [Core-owned state contract](../Implementation/State/RV32I_Core_Owned_State_Design_Contract.md) governs the lifetime and update boundaries of this retained state. The [register-file contract](../Implementation/State/RV32I_Register_File_Design_Contract.md) separately governs architectural GPR cells.

The CSR register bank shall dispatch the current implemented set:

```text
mstatus
misa
mie
mtvec
mstatush
mscratch
mepc
mcause
mtval
mip
mvendorid
marchid
mimpid
mhartid
mconfigptr
```

The bank shall use dense physical-cell indexing rather than a 4096-entry architectural-address array. Mutable state includes the required writable fields, while `misa` and identification/configuration views may be fixed and `mip.MTIP` may be hardware-driven. Unsupported fields shall be synthesized as fixed, WPRI, WARL, or WLRL values rather than generalized by the bank.

The default bank interface shall provide four combinational read ports and eight synchronous write lanes. The core may retain a candidate transaction in core-owned or controller-owned pending state, but normal CSR mutation shall remain bank-commit-qualified.

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
- select any pending legal Zicsr or MRET transaction for the shared CSR bank;
- authorize the bank's global commit only for a completely legal atomic transaction;
- update the PC from the retained normal PC result; and
- return to `FETCH`.

### 5.5 TRAP

`TRAP` is the only state that may commit a captured architectural trap.

Normal execution trap candidates shall not be accepted while the core is in `TRAP`.

[`rv32_trap`](../Implementation/Controller/RV32I_Trap_Controller_Design_Contract.md) shall consume `trap_q`, the retained instruction PC, legal read responses for `mstatus` and `mtvec`, and legality feedback for four candidate write lanes. For a valid trap with legal reads, it shall construct the candidate transaction:

- writes the synchronous faulting PC, or the later interrupt return PC selected by its sampling contract, to `mepc`;
- writes `{trap_q.interrupt, trap_q.code}` to `mcause`;
- writes `trap_q.tval` to `mtval`; and
- writes `mstatus` with the prior `MIE` copied to `MPIE`, `MIE` cleared, and `MPP` set to Machine mode (`2'b11`).

`rv32_trap` shall form the Direct-mode target `{mtvec[31:2], 2'b00}`. For a valid trap, it shall assert both `legal_o` and `pc_valid_o` only when both read responses and all four candidate write lanes are legal. A missing read legality response shall suppress the candidate transaction; a rejected write lane may leave the candidate fields visible for diagnosis but shall prevent trap acceptance. Parent integration shall present an accepted trap transaction to the bank with priority over an ordinary Zicsr transaction. The bank shall commit all enabled trap lanes together or none of them.

In the same `TRAP` transition, the core shall update the PC from `rv32_trap.pc_o` only when `rv32_trap.pc_valid_o` is asserted, suppress GPR writeback and any pending normal CSR update, and return to `FETCH`.

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
| CSR | CSR/SYSTEM next PC, including aligned `mepc` for MRET |

The core shall retain the selected normal result before `COMMIT`. Trap entry overrides normal PC selection in `TRAP`; it shall not appear as a decoder PC-source encoding.

### 6.4 Effective Address and Control Targets

For memory operations, the core shall form the 32-bit wrapped sum of the retained `rs1` value and normalized immediate and pass that architectural byte address to the LSU.

For a taken control transfer, CTRL shall validate the target after all instruction-specific target rules, including JALR low-bit clearing. A target that violates the core's four-byte instruction alignment shall produce `EXC_INST_ADDR_MISALIGNED` with the attempted target in `tval`. An untaken branch shall not report a target-alignment exception.

## 7. CSR Controller and Register Bank

### 7.1 Instruction controller

The implemented combinational CSR/SYSTEM controller consumes the decoded CSR operation, `imm[11:0]` CSR or SYSTEM field, five-bit immediate source, retained `rs1` value, `rd == x0` and `rs1 == x0` indicators, two bank read responses, and candidate-write legality feedback. It exposes two read addresses, the prior CSR result, one candidate write lane, an MRET PC result and validity flag, and a trap report. Detailed instruction semantics are defined by the [CSR/SYSTEM controller contract](../Implementation/Execution/RV32I_CSR_SYSTEM_Design_Contract.md).

For a legal Zicsr instruction, the controller shall return the prior bank read value, apply the required read/modify/write operation, and produce zero or one enabled write lane. Register and immediate set/clear forms shall suppress the write lane for zero sources as required.

For `CSR_SYS`, the controller shall interpret `imm[11:0]` at minimum as follows:

| `imm[11:0]` | CSR/SYSTEM outcome |
| --- | --- |
| `12'h000` with `rs1 == x0`, `rd == x0` | ECALL exception |
| `12'h001` with `rs1 == x0`, `rd == x0` | EBREAK exception |
| `12'h105` with `rs1 == x0`, `rd == x0` | WFI sequential no-op |
| `12'h302` with `rs1 == x0`, `rd == x0` | MRET normal execution |
| Other | Illegal-instruction exception |

Nonzero `rs1` or `rd` makes an otherwise exact SYSTEM operation illegal. WFI produces no CSR side effect or controller PC redirect, so Core retains the sequential normal PC. The controller shall convert an illegal instruction-directed bank response into `EXC_ILLEGAL_INST`. It shall not duplicate the bank's address dispatch or per-CSR field semantics.

### 7.2 Register-bank structure

The shared bank shall default to:

```systemverilog
parameter int unsigned ReadPorts  = 4;
parameter int unsigned WritePorts = 8;
```

All read ports shall be combinational and shall observe one pre-edge snapshot. The write lanes shall form one synchronous atomic transaction. Zero enabled lanes perform no update; one lane provides the ordinary Zicsr case; multiple lanes commit together.

Before commitment, the bank shall dispatch and validate every enabled lane. The complete transaction is legal only when every enabled operation is legal and no two lanes resolve to the same physical CSR cell. Duplicate-cell writes are an interface violation and shall not be resolved by lane priority. The global transaction commit remains distinct from each lane's semantic write request.

The bank shall use dense implemented-cell storage rather than a 4096-by-32 architectural-address array. One reusable dispatcher shall map each architectural address to a per-CSR semantic function and physical index. Per-CSR functions shall compute legality, architectural read data, and candidate next state without committing storage. The bank alone shall update physical cells in sequential logic.

Per-CSR reset behavior shall reside with the corresponding semantic function. During reset, the bank shall dispatch internal requests with `rst_en` set and load all returned next states through its generic reset branch.

Complete topology, field vocabulary, and address-set requirements are defined by the [CSR register-bank contract](../Implementation/State/RV32I_CSR_Register_Bank_Design_Contract.md).

### 7.3 Transaction producers and selection

All CSR state mutation shall use the same bank transaction interface:

| Producer | Transaction shape |
| --- | --- |
| Zicsr controller | Zero or one enabled lane |
| `rv32_trap` | Atomic candidate writes to `mstatus`, `mepc`, `mcause`, and `mtval` |
| CSR/SYSTEM controller during MRET | Atomic `mstatus` restoration |
| Machine timer logic | Hardware-owned pending-state update or view |
| Future extension logic | Extension-defined atomic transaction |

Parent integration shall select the transaction source presented to the bank. The CSR/SYSTEM instruction controller is not a mandatory path for Core trap, timer, or future extension writes. A trap-entry transaction shall take precedence over any retained normal Zicsr or MRET candidate. Zicsr and MRET are mutually exclusive outcomes of one selected controller operation.

The register bank is not an architectural trap engine. It returns legality; the selected instruction or event controller determines whether an illegal response becomes a trap report or an integration assertion.

### 7.4 Current architectural behavior

`mtvec` shall support Direct mode only, and `mepc` shall constrain bits 1:0 to zero for fixed `IALIGN=32`.

Successful MRET shall select aligned `mepc` as the normal PC and atomically request:

```text
mstatus.MIE   <- mstatus.MPIE
mstatus.MPIE  <- 1
```

The M-mode-only `MPP` view shall remain fixed as Machine mode (`2'b11`) through its per-CSR function.

The later machine timer interrupt becomes eligible only when `mstatus.MIE`, `mie.MTIE`, and hardware-driven `mip.MTIP` are all set. Eligibility does not define the timer input interface or the core interrupt-sampling point.

### 7.5 Current module evidence

The ALU passes its **15/15** module regression, the register file passes **6/6**, and `rv32_trap` passes **4/4**. The CSR register bank passes its **6/6** dedicated regression, the CSR/SYSTEM controller passes its **6/6** dedicated regression, and the standalone controller/bank wrapper passes its **2/2** integration regression. These results establish the module boundaries for Core integration; they do not yet establish complete `rv32_core` integration or architectural compliance.

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
| Machine timer interrupt report | Later `MIE && MTIE && MTIP` interrupt path | Deferred architecturally defined sampling point |

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
| CSR/SYSTEM illegal exact encoding or access | `EXC_ILLEGAL_INST` | Zero |
| CSR/SYSTEM breakpoint | `EXC_BREAKPOINT` | Zero |
| CSR/SYSTEM environment call from machine mode | `EXC_ECALL_M` | Zero |

Other LSU cause and `tval` semantics are defined by the LSU contract. The frozen CSR/SYSTEM controller reports zero `tval` for its current synchronous exception set.

The same core intake model shall accommodate the later machine timer interrupt report. On an accepted interrupt, `mepc` shall capture the instruction address that would otherwise execute next under the eventual sampling contract. Timer synchronization, sampling, and priority relative to synchronous exceptions remain deferred; other interrupt sources are not part of the frozen initial scope.

For the selected execution boundary, a successful result and an accepted trap are mutually exclusive architectural outcomes. Success advances toward `COMMIT`; failure advances toward `TRAP`, and any simultaneously present normal result is ignored.

A captured architectural trap is precise when:

- `mepc` identifies the synchronous faulting instruction or the instruction that would have executed next after an accepted interrupt;
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
- trap-entry side effects take precedence over every retained normal CSR candidate;
- all physical CSR-cell mutation occurs only in the register bank's sequential logic;
- every selected CSR transaction is all-or-nothing, contains only legal lanes, and contains no duplicate physical-cell target;
- `mtvec` remains Direct and `mepc[1:0]` remains zero;
- `COMMIT` and `TRAP` are mutually exclusive outcomes for an instruction;
- pending LSU request fields remain stable until completion;
- a trapped instruction performs no later normal commit; and
- register `x0` always reads as zero and ignores writes.

## 10. Reset Behavior

Reset shall place the core in `FETCH`, initialize the PC from the configured reset vector, clear pending write and trap intent, and initialize machine trap state to documented implementation values.

The CSR register bank shall obtain each implemented cell's reset state by dispatching an internal `rst_en` request to that cell's semantic function and shall load all returned values through its generic synchronous reset branch.

No GPR write, CSR write, or data-memory request may occur solely because reset is asserted or released.

## 11. Verification Obligations

The direct CSR register-bank, CSR/SYSTEM controller, controller/bank wrapper, and trap-controller regressions are complete as recorded in their respective contracts and tests. Core-level verification shall cover:

- reset and first fetch;
- all normal state transitions;
- request retention under instruction and data backpressure;
- ALU, immediate, control, load, store, CSR, SYSTEM, and FENCE paths;
- complete architectural views and write policies for `mstatus`, `misa`, `mie`, `mtvec`, `mstatush`, `mscratch`, `mepc`, `mcause`, `mtval`, `mip`, `mvendorid`, `marchid`, `mimpid`, `mhartid`, and `mconfigptr`;
- four independent combinational CSR reads observing one bank snapshot;
- zero-, one-, and multi-lane cases across the eight-lane atomic CSR write interface;
- all-or-nothing rejection of illegal lanes and duplicate physical-cell writes;
- dispatch fall-through for every unimplemented CSR address;
- per-CSR reset dispatch and generic bank reset commitment;
- decoder-owned illegal-encoding reports with raw-instruction `tval`;
- decoder-trap precedence over every specialist unit;
- rejection of inactive or wrong-state trap candidates;
- writeback and normal PC-source independence;
- load writeback only after successful completion;
- no destination write for stores, branches, SYSTEM operations, FENCE, or trapped instructions;
- illegal-instruction, breakpoint, environment-call, instruction-target, instruction-access, load, and store trap causes;
- exact `mepc` and `mcause` updates and faithful `mtval` capture from each report;
- Direct `mtvec` trap-vector selection and four-byte-aligned `mepc` behavior;
- trap-controller rejection when either required read or any required write lane is illegal;
- exact `mstatus.MIE` and `mstatus.MPIE` transitions on trap entry and MRET;
- `mie.MTIE` and hardware-driven `mip.MTIP` views and timer eligibility;
- successful MRET return and `mstatus` commitment as one selected normal controller outcome;
- suppression of normal CSR writes when a CSR operation traps;
- local LSU trap completion without a DMEM request;
- defensive invalid-LSU-uop completion with `EXC_ILLEGAL_INST` and zero `tval`;
- no duplicate commit under stretched ready; and
- `x0` immutability.

Assertions should encode the state, stability, commit, trap exclusivity, and transaction-qualification invariants directly.

## 12. Implementation Sequence

The shared CSR packages, dense register bank, per-CSR semantics, atomic interface, reset dispatch, CSR/SYSTEM controller, and combinational trap-entry controller are implemented and directly tested. Remaining implementation order is:

1. implement the five-state core controller, retained datapath, and CSR transaction-source selection;
2. integrate state-qualified decoder, LSU, CSR/SYSTEM, and control-target trap reports;
3. add focused core-level tests for normal, exceptional, and compound CSR-update flows;
4. add a small integration program covering load, store, branch, CSR, trap entry, and MRET; and
5. add the machine timer source, synchronization, eligibility, and sampling contract after the synchronous path is stable.

## 13. Deferred Decisions

The following remain explicit follow-up decisions:

- exact top-level naming, reset wiring, profile-configuration source, and parameter plumbing; each active profile resolves the concrete reset-vector value;
- the machine timer peripheral interface, synchronization, sampling point, arbitration, and priority;
- `mcycle`, `minstret`, their RV32 high halves, and associated `mcountinhibit` behavior after commit/retirement signaling is stable;
- any later interrupt sources, lower privilege modes, and nested-trap policy; and
- implementation-specific memory backend selection outside the core.

## Module Contracts

- [Core architecture](../Philosophy/RV32I_Core_Architecture.md)
- [Execution-environment contract](../Philosophy/RV32I_Execution_Environment_Contract.md)
- [Execution-environment deferred decisions](../Philosophy/RV32I_Execution_Environment_Deferred_Decisions.md)
- [Instruction decoder contract](../Implementation/Controller/RV32I_Instruction_Decoder_Design_Contract.md)
- [Trap controller contract](../Implementation/Controller/RV32I_Trap_Controller_Design_Contract.md)
- [ALU contract](../Implementation/Execution/RV32I_ALU_Design_Contract.md)
- [CTRL unit contract](../Implementation/Execution/RV32I_CTRL_Design_Contract.md)
- [LSU contract](../Implementation/Execution/RV32I_LSU_Contract.md)
- [CSR/SYSTEM controller contract](../Implementation/Execution/RV32I_CSR_SYSTEM_Design_Contract.md)
- [Register-file contract](../Implementation/State/RV32I_Register_File_Design_Contract.md)
- [Core-owned state contract](../Implementation/State/RV32I_Core_Owned_State_Design_Contract.md)
- [CSR register-bank contract](../Implementation/State/RV32I_CSR_Register_Bank_Design_Contract.md)
- [Memory subsystem contract](../Implementation/IO/RV32I_Memory_Subsystem_Design_Contract.md)
- [Exceptions, traps, and extensions roadmap](RV32I_Exceptions_Traps_and_Extensions_Roadmap.md)

## Metadata

- Document type: implementation contract
- Scope: planned `rv32_core` controller, datapath, CSR/SYSTEM controller, CSR register bank, and trap integration
- Architectural authority: [RV32I Core Architecture](../Philosophy/RV32I_Core_Architecture.md)
- Interface authority: package definitions and module RTL
- Verification authority: module and core integration tests
