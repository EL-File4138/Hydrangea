# RV32I Core Controller and Datapath Plan

**Status:** Pre-implementation planning

**Governing contract:** [RV32I Core Design Contract](RV32I_Core_Design_Contract.md)

**Related plans:** [LSU Implementation](RV32I_LSU_Implementation_Plan.md) and [Exceptions, Traps, and Extensions](RV32I_Exceptions_Traps_and_Extensions_Roadmap.md)

## 1. Purpose

This document organizes the remaining work needed to integrate the existing RV32I building blocks into a baseline core. It is a planning document, not an interface specification.

Resolved interfaces and cycle behavior shall be documented in RTL, tests, or a protocol-specific document and then removed from this plan. The source manifest remains authoritative for which modules exist.

## 2. Planned Deliverables

The integration work is expected to produce:

1. A main controller that sequences one architectural instruction at a time.
2. A top-level datapath containing PC and instruction state, register-file connections, execution-unit connections, result retention, and writeback selection.
3. Integration of the existing CTRL execution unit for branch comparison, complete next-PC generation, and jump-link generation.
4. An instruction-fetch path and any arbitration required by the selected memory topology.
5. Integration tests that execute every instruction currently accepted by the decoder.

Names for the main controller and top-level core are not fixed by this plan. `rv32_ctrl` identifies the CTRL execution unit and shall not also name the main controller.

## 3. Required Instruction Lifecycle

The controller shall support the following logical phases. They need not correspond one-to-one with FSM states.

1. Request the instruction at the current fetch PC.
2. Capture the instruction and preserve its associated instruction PC.
3. Decode the captured instruction and reject unsupported encodings without architectural side effects.
4. Resolve the architectural source indices identified by the semantic dependency flags through the register file.
5. Route the resulting 32-bit values to the selected execution unit and retain returned values across cycles where required.
6. Wait for any required memory or execution completion.
7. Commit the PC and register-file effects authorized by the instruction semantics.

No later instruction may commit before the active instruction completes.

## 4. Datapath Requirements

### 4.1 PC state

The datapath shall preserve the address of the executing instruction independently of the fetch PC update policy. PC-relative execution, branch and jump targets, and jump-link generation shall use that preserved identity.

For a control-transfer instruction, the controller shall commit CTRL's complete next-PC value, including CTRL's fall-through result for a conditional branch that is not taken. For an ordinary non-control instruction, the controller shall supply the executing instruction PC plus four. A fetch-side increment may occur before execution, but it shall not alter this architectural selection rule.

### 4.2 Operand selection

The controller shall perform register-file access and provide the raw 32-bit operand values required by the decoded semantic operation. Architectural register indices shall not be routed into ALU, LSU, or CTRL. The planned datapath must accommodate at least:

- register/register and register/immediate ALU operations;
- the current instruction PC as an ALU operand for PC-relative arithmetic;
- load/store effective-address generation, whether shared or LSU-local;
- control-transfer comparison, target, and link operands; and
- direct writeback of a normalized immediate.

### 4.3 Result retention and writeback

Any result that outlives the cycle in which it is produced shall be retained explicitly. Register-file write enable shall be derived from the semantic write authorization and the controller's commit condition, not from the selected writeback source alone.

A control transfer shall route its target to PC control and its link result to register writeback. These values shall remain separate throughout the datapath.

## 5. Decisions to Resolve Before Implementation

| Decision | Candidate approaches | Required closure evidence |
| --- | --- | --- |
| Controller state partition | Dedicated fetch/decode/execute/memory/writeback states or combined states | Cycle diagram and tests for every latency path |
| Memory protocol | Fixed-latency local memory or explicit request/response handshake | Stable request rules and completion definition |
| Physical memory topology | Separate instruction/data paths or one arbitrated path | Top-level interface and arbitration behavior |
| PC update point | Advance during fetch, after capture, or at commit | Proof that the executing instruction PC remains unambiguous |
| Intermediate registers | Dedicated ALU, load, instruction-PC, or generic result registers | Data-lifetime analysis across all states |
| Arithmetic sharing | Shared ALU for data addresses and non-control PC increments or dedicated logic | Area/timing result and controller schedule |
| Memory read-during-write behavior | Avoid dependence or select a proven FPGA RAM mode | Simulation and synthesis evidence for the selected target |
| Unsupported-instruction response | Explicit simulation stop, execution-environment response, or precise exception | Alignment with the exception roadmap |
| Reset behavior | Architectural reset state and treatment of in-flight requests | Reset sequence and assertions |

An option is not a design decision until its closure evidence is recorded in implementation-facing documentation or tests.

## 6. Suggested Implementation Order

1. Select and document the instruction/data memory transaction model.
2. Define the top-level core boundary and required state registers.
3. Implement fetch, instruction capture, and instruction-PC retention.
4. Integrate decode, register reads, ALU execution, and ALU writeback.
5. Integrate `rv32_ctrl` according to the [CTRL design contract](RV32I_CTRL_Design_Contract.md), including complete next-PC selection and link writeback.
6. Integrate the LSU described in [RV32I LSU Implementation Plan](RV32I_LSU_Implementation_Plan.md).
7. Add unsupported-instruction handling compatible with the [exception roadmap](RV32I_Exceptions_Traps_and_Extensions_Roadmap.md).
8. Add integration assertions and instruction-level regression tests.

## 7. Verification and Completion Criteria

The controller/datapath work is complete for the baseline core when:

- every encoding accepted by the decoder has a complete execution and commit path;
- illegal decode results cause no register, PC-redirection, or data-memory side effect;
- inactive semantic fields do not affect execution;
- execution units receive register contents rather than architectural register indices;
- PC-relative operations use the executing instruction's PC under every fetch timing;
- register writes occur only at commit and only when authorized;
- `x0` remains architecturally zero;
- wait states do not duplicate requests or commits;
- control transfers use CTRL's complete next-PC value, including conditional fall-through, and write the jump link independently;
- reset cannot commit a partially executed instruction; and
- simulation covers both the selected nominal memory timing and any supported delayed-response timing.

After these criteria are met, unresolved future architecture work belongs in the [exception and extension roadmap](RV32I_Exceptions_Traps_and_Extensions_Roadmap.md) rather than in this integration plan.
