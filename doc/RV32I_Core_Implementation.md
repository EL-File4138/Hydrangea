# RV32I Core Implementation

**Status:** Implementation plan

**Governing architecture:** [RV32I Core Architecture](RV32I_Core_Architecture.md)

**Module contracts:** [Instruction Decoder](RV32I_Instruction_Decoder_Design_Contract.md), [CTRL](RV32I_CTRL_Design_Contract.md), [LSU](RV32I_LSU_Contract.md), and [Memory Subsystem](RV32I_Memory_Subsystem_Design_Contract.md)

**Architecture roadmap:** [Exceptions, Traps, and Extensions](RV32I_Exceptions_Traps_and_Extensions_Roadmap.md)

## 1. Purpose

This document defines the planned implementation of `rv32_core`, including persistent state, FSM behavior, and linkage among existing modules. It may evolve with RTL while preserving the governing architecture and module contracts.

Once implemented, `rv32_core` and its integration tests become authoritative for concrete ports, state encoding, mux structure, and cycle-level behavior.

## 2. Planned Persistent State

The baseline implementation uses:

```systemverilog
logic [31:0] pc_q;
logic [31:0] ir_q;
logic [31:0] rd_value_q;
logic [31:0] pc_next_q;
state_t      state_q;
```

- `pc_q` is the PC associated with `ir_q` and remains stable until COMMIT.
- `ir_q` is written after successful instruction fetch and remains stable through execution and commit.
- `rd_value_q` holds a pending GPR result and is meaningful only when decoded write authorization is set.
- `pc_next_q` holds the pending next architectural PC.
- `state_q` represents instruction and transaction lifetime.

Decoder output remains combinational from `ir_q`; no separate semantic register is required while `ir_q` is stable.

## 3. FSM

The initial FSM contains four states:

```systemverilog
typedef enum logic [...] {
  FETCH,
  EXECUTE,
  LSU_WAIT,
  COMMIT
} state_t;
```

```text
FETCH -> EXECUTE -> COMMIT -> FETCH
             |
             +-> LSU_WAIT -> COMMIT
```

`FETCH` and `LSU_WAIT` are latency-bearing states. ALU, CTRL, immediate, and decode evaluation are combinational.

Ignoring reset and adapter wait cycles, the expected paths are:

```text
ALU / CTRL / IMM: FETCH -> EXECUTE -> COMMIT
LOAD / STORE:     FETCH -> EXECUTE -> LSU_WAIT -> COMMIT
```

## 4. State Behavior

### 4.1 FETCH

The core asserts the LSU fetch request and supplies `pc_q` as the address for the full state duration. While completion is absent, state, PC, IR, request, and address remain stable.

On successful completion, the core captures the fetched instruction into `ir_q` and enters EXECUTE. A failed completion shall not be interpreted as an instruction; routing to the future instruction-access fault path remains pending.

Leaving FETCH deasserts the level-sensitive request and terminates the completed transaction.

### 4.2 EXECUTE

The core reads semantic fields and register values derived from stable `ir_q`. It dispatches by semantic execution/result class:

- **ALU:** select operands, capture the ALU result, capture `pc_q + 4`, and enter COMMIT.
- **CTRL:** capture CTRL's complete next PC, capture its register result when authorized, and enter COMMIT.
- **IMM:** capture the normalized immediate, capture `pc_q + 4`, and enter COMMIT.
- **LSU:** enter LSU_WAIT; the data request begins in that state.

An illegal decode shall enter an explicit stop or future exception path without architectural commit.

### 4.3 LSU_WAIT

The core asserts the LSU data request and supplies stable operation, base value, store value, and immediate. These remain stable because `ir_q`, decode output, and register-file read addresses remain stable.

On a successful load, the core captures the LSU result and `pc_q + 4`, then enters COMMIT. On a successful store, it captures `pc_q + 4` and enters COMMIT without a GPR result.

A failed completion shall enter the future data-access fault path and shall not commit as a successful instruction. The memory-visible effect of a successful store may occur before COMMIT.

Leaving LSU_WAIT deasserts the data request and terminates the completed transaction.

### 4.4 COMMIT

COMMIT writes `pc_next_q` to `pc_q`. If decoded write authorization is set, it also writes `rd_value_q` to the decoded destination register. The state then returns to FETCH.

The core need not suppress a write request whose destination is `x0`; the register file preserves the architectural zero value.

## 5. Module Linkage

### 5.1 Decoder and register file

`rv32_instdec` consumes `ir_q`. Register-file read addresses are the decoded indices when their dependency flags are set and may otherwise be driven to `x0`.

Register-file reads are combinational. Register-file writes are synchronous and occur only at the COMMIT edge.

The core retains decoded `rd` through stable `ir_q`. Register-file write enable is asserted only in COMMIT and only when `rd_write` is set.

`wb_src` is used as the execution/result class, including CTRL branches and LSU stores for which `rd_write` is clear.

### 5.2 ALU

Normal ALU operations use the first register value as operand A and select the second register value or decoded immediate as operand B. `AUIPC` selects `pc_q` and the decoded immediate. The ALU result is captured before COMMIT.

### 5.3 CTRL

CTRL receives the decoded operation, `pc_q`, both register values, and the decoded immediate. Its next-PC output is complete for branches and jumps. Its register-result output is captured only for a control transfer with decoded write authorization.

The core does not apply an additional PC increment after selecting CTRL's next-PC result.

### 5.4 LSU

The LSU fetch path receives a level-sensitive request and `pc_q`. The core captures the returned instruction; the LSU does not write `ir_q`.

The LSU data path receives the decoded operation, first register value as base, second register value as store payload, and decoded immediate. The LSU computes the effective address locally.

The core communicates with memory adapters only through the LSU. IMEM and DMEM adapters remain outside `rv32_core` implementation policy except for their required transaction connections.

## 6. Timing and Stability Rules

All persistent core state changes on `posedge clk_i`. Memory `ready` and `err` signals are sampled inputs and shall not be used as clocks.

The implementation shall preserve these invariants:

- `pc_q` changes only in COMMIT or reset;
- `ir_q` changes only after successful fetch or reset;
- GPR write enable implies COMMIT;
- pending result registers remain stable until consumed;
- an asserted memory request and its inputs remain stable until completion;
- fetch and data requests are not asserted concurrently; and
- the PC associated with every PC-relative operation is the PC of `ir_q`.

## 7. Reset

The core shall follow the project active-low reset convention `rst_ni`. Reset shall establish the configured reset vector in `pc_q`, select FETCH, and prevent any partial instruction from committing.

`ir_q` may reset to a safe value. Pending result registers may reset to zero or remain unspecified until written, provided they cannot affect architectural state before becoming valid.

Adapters reset their own transaction state independently. The stateless LSU requires no transaction-state reset.

## 8. Remaining Implementation Work

1. Implement the required IMEM and DMEM adapters against `rv32_mem_if`.
2. Define the external `rv32_core` boundary and reset-vector parameter.
3. Implement the state registers and four-state FSM.
4. Integrate decoder and register-file reads.
5. Integrate ALU, CTRL, immediate, and writeback paths.
6. Integrate LSU fetch/data requests and adapter connections.
7. Add explicit illegal-instruction and memory-error behavior consistent with the exception roadmap.
8. Add assertions and instruction-level integration tests.

## 9. Verification Criteria

The initial core implementation is complete when:

- every decoder-accepted instruction has a complete execution path;
- illegal and failed instructions produce no successful architectural commit;
- PC and IR stability hold through every wait state;
- only COMMIT updates PC or GPR state;
- execution units receive values rather than register indices;
- CTRL supplies complete control-transfer next-PC behavior;
- LSU requests and inputs remain stable until completion;
- no memory request or architectural commit is duplicated;
- instruction and data transactions remain separate and nonoverlapping;
- `x0` remains architecturally zero; and
- synchronous and delayed adapter responses require no change to core sequencing.

Exact top-level port names, state encoding, reset-vector value, and deferred trap routing remain implementation decisions until fixed by RTL or a focused architecture record.
