# RV32I Core Design Contract

**Scope:** Implemented `rv32_core` sequencing, retained state, datapath selection, synchronous traps, and architectural commit

**Status:** RTL authored; current directed Core regressions pass; broader verification remains open

**Governing architecture:** [RV32I Core Architecture](../Philosophy/RV32I_Core_Architecture.md)

**Execution environment:** [RV32I Execution-Environment Contract](../Philosophy/RV32I_Execution_Environment_Contract.md)

**Platform roadmap:** [RV32I SoC and Platform Roadmap](../Roadmap/RV32I_SoC_and_Platform_Roadmap.md)

**Core-owned state:** [RV32I Core-Owned State Design Contract](State/RV32I_Core_Owned_State_Design_Contract.md)

**Remaining work:** [RV32I Exceptions, Traps, and Extensions Roadmap](../Roadmap/RV32I_Exceptions_Traps_and_Extensions_Roadmap.md)

## 1. Purpose and Authority

This document records the stable implementation contract of the authored `rv32_core`. RTL is authoritative for concrete ports, identifiers, state encoding, and signal assignments. This contract records the implemented ownership, lifetime, qualification, and commit rules that integration and verification shall preserve.

The documentation boundary is:

| Document | Owns |
| --- | --- |
| [Core architecture](../Philosophy/RV32I_Core_Architecture.md) | Abstract lifecycle, architectural invariants, and responsibility boundaries |
| This contract | Concrete Core interface, retained state, RTL state mapping, selection rules, and verification evidence |
| [Core-owned state contract](State/RV32I_Core_Owned_State_Design_Contract.md) | Focused lifetime and valid-before-use rules for persistent Core state |
| [Roadmap](../Roadmap/RV32I_Exceptions_Traps_and_Extensions_Roadmap.md) | Unexecuted verification, compliance, interrupt, and extension work |

The terms **shall**, **shall not**, **should**, and **may** denote a requirement, prohibition, recommendation, and permitted implementation choice, respectively.

## 2. Implemented Boundary

`rv32_core` integrates:

- the instruction decoder and register file;
- ALU, control-transfer, LSU, and CSR/SYSTEM execution boundaries;
- the shared CSR register bank;
- the combinational trap-entry controller; and
- separate logical IMEM and DMEM `rv32_mem_if` requester interfaces.

Core owns instruction lifetime, PC state, sequencing, normal-result selection, trap qualification and retention, CSR transaction-source selection, and architectural commit authorization. Specialist modules produce combinational results or trap candidates but do not commit Core architectural state directly.

The current implementation supports precise synchronous Machine-mode exceptions. Machine timer input, synchronization, interrupt sampling, counters, and broader privileged behavior remain outside this contract.

## 3. External Interface and Reset

The concrete interface is:

```systemverilog
module rv32_core #(
    parameter logic [31:0] ResetVector = 32'h0000_0000,
    parameter bit RejectTrapWriteForTest = 1'b0
) (
    input logic clk_i,
    input logic rst_ni,
    rv32_mem_if.requester imem_if,
    rv32_mem_if.requester dmem_if
);
```

`ResetVector` is a platform-configurable Core parameter. It shall be four-byte aligned and fetchable when the SoC releases reset. Its declared default is `0x0000_0000`; that value is not a portable Core invariant.

`RejectTrapWriteForTest` is a verification-only fault-injection parameter. Normal integrations shall leave it disabled. When enabled, it rejects one mandatory trap-entry write-legality response so verification can demonstrate fail-closed behavior without changing the architectural interface.

The current asynchronous reset explicitly establishes:

```systemverilog
pc_q    <= ResetVector;
state_q <= ST_FETCH;
trap_q  <= '0;
```

`instruction_q`, `next_pc_q`, and `rd_value_q` need no reset values because the FSM prevents their use until a valid producer state has written them. Reset shall leave no stale normal value architecturally consumable.

## 4. Persistent Core State

The implemented Core-owned persistent state is:

```systemverilog
core_state_e state_q;
logic [31:0] pc_q;
logic [31:0] next_pc_q;
logic [31:0] instruction_q;
logic [31:0] rd_value_q;
rv32_trap_pkg::trap_req_t trap_q;
```

The implementation deliberately does not retain separate semantic, source-operand, destination-intent, CSR-candidate, or LSU-request bundles. Decoder semantics and register-file operands remain deterministic combinational functions of stable `instruction_q` and architectural state.

The governing lifetime invariant is:

> Every non-retained combinational value consumed after `ST_EXECUTE` shall remain a deterministic function of retained state that cannot change before its final use.

`rd_value_q` and `next_pc_q` retain only normal results that must survive into `ST_COMMIT`. `trap_q` retains the selected exceptional result through `ST_TRAP`.

## 5. Implemented State Machine

The [architecture lifecycle](../Philosophy/RV32I_Core_Architecture.md#6-abstract-instruction-lifecycle) is implemented by this concrete mapping:

| Abstract state | RTL state | Concrete role |
| --- | --- | --- |
| `FETCH` | `ST_FETCH` | Own instruction request lifetime and capture instruction or fetch trap |
| `EXECUTE` | `ST_EXECUTE` | Evaluate semantics, select normal candidates, and qualify decoder/specialist traps |
| `IO_WAIT` | `ST_IO_WAIT` | Own data request lifetime and capture data result or trap |
| `COMMIT` | `ST_COMMIT` | Authorize normal PC, GPR, and instruction-directed CSR effects |
| `TRAP` | `ST_TRAP` | Authorize atomic trap CSR effects and exceptional PC redirection |

### 5.1 Fetch

`ST_FETCH` presents `pc_q` to the LSU fetch path and holds the request until completion. A successful completion captures `instruction_q`; a fetch trap captures `trap_q` and suppresses instruction capture.

### 5.2 Execute

`ST_EXECUTE` continuously evaluates decoder semantics, register-file operands, and specialist outputs. Decoder traps have first priority. If decode is legal, only the trap candidate associated with the selected result class is eligible.

Combinational evaluation of an unselected unit is permitted. Architectural suppression requires that its result, trap, and side effects are not accepted.

### 5.3 I/O Wait

`ST_IO_WAIT` asserts the data request until completion. LSU operation, base, store data, and immediate remain stable because they are derived from unchanged `instruction_q` and register-file state; no separate request-field register is required.

A successful data completion advances to normal commit. A qualified LSU trap captures `trap_q` and advances to trap entry.

### 5.4 Commit

`ST_COMMIT` is the only normal path that may:

- authorize a GPR write;
- authorize an instruction-directed CSR transaction;
- update `pc_q` from `next_pc_q`; and
- assert the internal `retire` hook.

Core authorizes a GPR write from decoded destination intent. It may assert write enable with destination `x0`; the register file owns `x0` preservation and suppresses physical mutation of cell zero.

Normal CSR/SYSTEM candidates remain combinationally derived from stable instruction state. Core presents them to the bank outside `ST_TRAP` and enables bank commitment only in `ST_COMMIT`.

### 5.5 Trap

`ST_TRAP` presents retained `trap_q` and `pc_q` to `rv32_trap`, selects its CSR transaction over the ordinary CSR/SYSTEM candidate, and enables bank commitment only when trap-entry legality succeeds.

Trap entry atomically updates `mepc`, `mcause`, `mtval`, and `mstatus`, then updates `pc_q` from the Direct-mode `mtvec` target. Normal GPR, CSR, and PC effects from the trapped instruction remain suppressed.

If trap entry cannot produce a valid legal PC/CSR transaction, Core remains in `ST_TRAP`. It performs no partial trap update, synthetic replacement trap, or automatic reset. Verification should assert that this fail-stop containment path is unreachable in a correct integration.

## 6. Datapath and Result Selection

ALU operands are selected from live semantics:

```systemverilog
alu_operand_a = rs1_is_used ? rs1_value : pc_q;
alu_operand_b = rs2_is_used ? rs2_value : immediate;
```

The normal writeback source selects immediate, ALU, control-transfer, LSU, or CSR data. Selection creates a candidate; it does not authorize a write.

The normal PC source selects sequential `pc_q + 4`, a control-transfer result, or the CSR/SYSTEM result used by MRET. Trap redirection bypasses normal PC selection and writes `pc_q` directly from `rv32_trap.pc_o` in `ST_TRAP`.

## 7. Memory Transaction Stability

The LSU is the sole Core-side client of IMEM and DMEM. Core consumes LSU-level ready, result, and trap signals rather than interpreting adapter failures directly.

During an outstanding request:

- `instruction_q` and `pc_q` remain unchanged;
- no normal GPR or CSR write occurs;
- decoded memory operation and immediate remain unchanged;
- source register values remain unchanged; and
- every request field remains stable until completion.

Explicit request-field registers are optional while these properties follow from retained-state invariance.

## 8. CSR Transaction Selection

The CSR register bank exposes four combinational read ports and eight synchronous write lanes. Core uses the first two read ports and the required write lanes for the current instruction/trap producers.

The bank-facing source is selected combinationally:

| Core context | Read/write candidate source |
| --- | --- |
| `ST_TRAP` | `rv32_trap` reads and four trap-entry write candidates |
| Every other state | `rv32_csr_controller` reads and ordinary write candidate |

Candidate generation and legality feedback are combinational. State mutation remains synchronous and Core-authorized:

| Commit state | Authorized transaction |
| --- | --- |
| `ST_COMMIT` | Ordinary CSR/SYSTEM transaction |
| `ST_TRAP` | Legal atomic trap-entry transaction |

The controller's `pc_valid_o` remains an observability/status output. Decoder semantics own normal PC-source selection; it is not a second Core PC arbiter.

## 9. Trap Qualification and Precision

Core accepts synchronous trap sources only in their qualifying contexts:

| State | Eligible source and priority |
| --- | --- |
| `ST_FETCH` | Fetch-side LSU report |
| `ST_EXECUTE` | Decoder first; then selected CTRL, LSU, or CSR/SYSTEM class |
| `ST_IO_WAIT` | Data-side LSU report |
| `ST_COMMIT` | None for the committing instruction |
| `ST_TRAP` | No new normal-execution report |

A captured trap is precise when `mepc` identifies `pc_q`, no normal GPR or instruction-directed CSR update occurs, the normal next PC is not committed, and `mcause`/`mtval` describe the accepted report.

## 10. Architectural Invariants

The implementation shall preserve:

1. one active architectural instruction at a time;
2. stable instruction identity from fetch completion through commit or trap entry;
3. stable request fields until memory completion;
4. decoder-trap precedence and state-qualified specialist acceptance;
5. normal PC, GPR, and instruction-directed CSR effects only in `ST_COMMIT`;
6. trap CSR and exceptional PC effects only in `ST_TRAP`;
7. atomic selected CSR transactions;
8. mutual exclusion of normal commit and trap entry;
9. no later normal commit from a trapped instruction; and
10. architectural `x0` reads always returning zero.

## 11. Retirement Hook

The internal combinational `retire` signal is asserted during `ST_COMMIT`, immediately before the normal commit edge. It is not an architectural interface. A later milestone may use it for `minstret`, interrupt sampling, trace, or verification.

## 12. Verification Status and Obligations

`make check TOP=rv32_core` passes the Verilator `--lint-only` elaboration check. Current directed evidence is:

| Suite | Command | Result | Principal coverage |
| --- | --- | ---: | --- |
| Normal Core integration | `make test TOP=rv32_core` | 7/7 | Single commit/`x0`, memory programs, control flow, all Zicsr forms, ECALL/MRET, and precise synchronous traps |
| Trap-entry fail-closed | `make test TOP=rv32_core_failclosed` | 1/1 | Rejected mandatory trap write causes no partial update and retains `ST_TRAP` |
| Memory backpressure | `make test TOP=rv32_core_backpressure` | 1/1 | Delayed instruction/data completion and request stability |

These 9/9 directed results do not by themselves establish complete RV32I/Zicsr support or architectural compliance. Broader illegal-CSR cases, assertions, and applicable architectural tests remain required by the roadmap.

## 13. Planned and Excluded Work

Planned but not implemented:

- asynchronous machine-timer sampling and integration;
- Vectored-mode `mtvec` behavior required by the first interrupt milestone;
- `mcycle`, `minstret`, high halves, or `mcountinhibit`; and
- architectural conformance evidence.

Broader interrupt families may be considered only after the timer path and concrete SoC requirements exist. Lower privilege modes, PMP, MMU, virtual memory, caches, speculation, out-of-order execution, parallel Core transactions, multiple outstanding operations, and multiple harts are baseline non-goals.

## Related Documents

- [Core architecture](../Philosophy/RV32I_Core_Architecture.md)
- [Software authoring contract](../Philosophy/RV32I_Software_Authoring_Contract.md)
- [SoC and platform roadmap](../Roadmap/RV32I_SoC_and_Platform_Roadmap.md)
- [Core-owned state contract](State/RV32I_Core_Owned_State_Design_Contract.md)
- [Instruction decoder contract](Controller/RV32I_Instruction_Decoder_Design_Contract.md)
- [Trap controller contract](Controller/RV32I_Trap_Controller_Design_Contract.md)
- [ALU contract](Execution/RV32I_ALU_Design_Contract.md)
- [CTRL contract](Execution/RV32I_CTRL_Design_Contract.md)
- [LSU contract](Execution/RV32I_LSU_Contract.md)
- [CSR/SYSTEM controller contract](Execution/RV32I_CSR_SYSTEM_Design_Contract.md)
- [Register-file contract](State/RV32I_Register_File_Design_Contract.md)
- [CSR register-bank contract](State/RV32I_CSR_Register_Bank_Design_Contract.md)
- [Memory subsystem contract](IO/RV32I_Memory_Subsystem_Design_Contract.md)

## Metadata

- Document type: implemented Core design contract
- RTL authority: `rtl/core/rv32_core.sv`
- Verification authority: `testbench/rv32_core_tb.sv`, `testbench/cocotb/test-rv32_core.py`, `testbench/rv32_core_failclosed_tb.sv`, `testbench/cocotb/test-rv32_core_failclosed.py`, `testbench/rv32_core_backpressure_tb.sv`, `testbench/cocotb/test-rv32_core_backpressure.py`, and future architectural tests
