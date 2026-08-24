# RV32I LSU Implementation Plan

**Status:** Pre-implementation planning

**Governing contract:** [RV32I Core Design Contract](RV32I_Core_Design_Contract.md)

**Related plans:** [Controller and Datapath](RV32I_Core_Controller_and_Datapath_Plan.md) and [Exceptions, Traps, and Extensions](RV32I_Exceptions_Traps_and_Extensions_Roadmap.md)

## 1. Purpose

This document plans the load/store unit between decoded RV32I memory semantics and the selected memory transaction interface. It does not define the current RAM module's ports or duplicate the load/store enum encodings.

Once the LSU interface and protocol are implemented, their RTL and tests become authoritative and the corresponding open items shall be removed from this plan.

## 2. LSU Responsibilities

The LSU shall provide the processor-side behavior needed to execute a decoded load or store:

- form or receive the effective address;
- determine transfer width and load-extension policy from the semantic operation;
- translate the transfer into the selected memory request representation;
- preserve request context until completion;
- place store data according to the memory-interface convention;
- extract the addressed load value and apply sign or zero extension;
- enforce the selected alignment policy;
- report completion or a dynamic memory exception to the controller; and
- prevent duplicate stores while a request is stalled.

The effective address is the architectural base-register value plus the decoded immediate. This requirement does not decide whether the addition is performed inside the LSU or by a shared ALU.

The Core Controller, including its datapath, shall perform all register-file access. The LSU shall receive the base-register and store-source contents as raw 32-bit values and shall return a raw 32-bit load result. It shall not consume source or destination register indices or authorize register-file writeback.

## 3. Memory Abstraction

The LSU input represents an ISA-level operation. The memory-facing request shall contain only generic transaction information, such as address, read/write direction, transfer width or byte enables, and write data.

Signed versus unsigned load behavior shall not be delegated to RAM. If the memory returns a containing word, the LSU shall select and extend the addressed byte or halfword after the response. If a future bus performs lane selection, the LSU or its adapter shall still determine the request lanes and final architectural extension.

Instruction fetch is not an LSU operation. A unified memory implementation requires arbitration outside the ISA-level LSU interface.

## 4. Planned Transaction Flow

### 4.1 Load

1. Accept one legal load operation and its operands.
2. Determine the effective address, transfer width, and extension policy.
3. Apply the selected alignment policy before issuing a request not permitted by that policy.
4. Issue the request sequence prescribed by the alignment policy and memory interface, retaining the required address and operation metadata.
5. Wait for completion without changing the request context.
6. Extract and extend the returned value.
7. Present one completion result to the controller for commit.

### 4.2 Store

1. Accept one legal store operation, its base-register value, decoded immediate, and source-data value.
2. Determine the effective address and transfer width.
3. Apply the selected alignment policy.
4. Adapt the source data and lane information to the memory-interface convention.
5. Issue each required write transaction exactly once and hold its required request fields stable until accepted.
6. Report completion only when the memory protocol defines the store as complete.

These flows describe ordering, not a required number of states or cycles.

## 5. Decisions to Resolve Before Implementation

| Decision | Candidate approaches | Required closure evidence |
| --- | --- | --- |
| Address addition | Shared core ALU or LSU-local adder | Datapath schedule and area/timing result |
| LSU sequencing ownership | Main-controller states or a stateful LSU request interface | One clearly owned request/completion handshake |
| Memory timing | Existing fixed-latency RAM behavior or latency-independent handshake | Protocol assertions and delayed-response tests |
| Write representation | Width plus right-aligned data, byte enables, or bus-specific strobes | Adapter tests for every address lane and width |
| Read representation | Containing word or already selected transfer | Load extraction ownership documented once |
| Misaligned access policy | Precise exception or supported split transaction | Execution-environment decision and boundary tests |
| Fault reporting | No-fault local RAM assumption or explicit response status | Top-level memory contract and exception event format |
| Unified-memory arbitration | Controller-owned or dedicated arbiter | No instruction/data request loss or starvation |
| Request cancellation | Complete every accepted request or define cancellation on reset/exception | Reset and exception protocol assertions |

The baseline one-outstanding-transaction rule shall be retained unless the core design contract is revised.

## 6. Verification Plan

Verification shall derive legal operation values from the package or decoder rather than copy their numerical encodings into this document. Tests shall cover:

- effective-address carry and signed displacement cases;
- every implemented transfer width at each valid byte lane;
- signed and unsigned load extension at boundary values;
- store data and lane behavior without corruption of adjacent bytes;
- the selected behavior for every misaligned width/address combination;
- request stability under delayed completion;
- exactly-once issuance of each required store transaction;
- reset and exception behavior while a request is pending;
- rejection or containment of invalid memory response conditions; and
- integration with both register writeback for loads and no-writeback commit for stores.

Protocol assertions should check request stability, maximum outstanding transaction count, completion ownership, and absence of unsolicited write enables.

## 7. Completion Criteria

The LSU plan is complete when:

- its processor-side and memory-side interfaces are implemented and tested;
- address-adder ownership is resolved;
- alignment and fault policies are recorded in the [exception architecture](RV32I_Exceptions_Traps_and_Extensions_Roadmap.md);
- all decoder-accepted load/store operations execute correctly;
- controller integration handles nominal and delayed completion without duplicate side effects; and
- the implemented protocol, rather than this plan, is the authoritative timing reference.
