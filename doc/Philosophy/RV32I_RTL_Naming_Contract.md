# RV32I RTL Naming Contract

**Scope:** Names in synthesizable RTL, SystemVerilog test wrappers, and naming-sensitive tool configuration

**Status:** Normative target; existing sources remain subject to migration under this contract

**Governing style:** [lowRISC Verilog Coding Style Guide at commit `9c15ff5d`](https://github.com/lowRISC/style-guides/blob/9c15ff5dce23eef969e00ab3715153967419eadd/VerilogCodingStyle.md)

**Architecture:** [RV32I Core Architecture](RV32I_Core_Architecture.md)


## 1. Purpose and Authority

This contract defines one deterministic naming language for the project. It exists to make ownership, logical role, polarity, lifetime, and boundary direction visible without making names restate SystemVerilog syntax. It applies to every manually controlled identifier in `rtl/**/*.sv` and every SystemVerilog wrapper or utility under `testbench/`.

The project adopts lowRISC rules where that guide is unambiguous. This contract resolves choices left open by lowRISC and records deliberate project extensions for Boolean predicates, mixed-direction interfaces, enum members, instance names, collection names, assertion labels, and the approved abbreviation vocabulary.

The authority order is:

1. this contract governs identifier spelling and composition;
2. the pinned lowRISC guide governs style not specialized here;
3. checked-in lint configuration implements both documents but does not override either; and
4. RTL, tests, and module contracts remain authoritative for behavior.

The terms **shall**, **shall not**, **should**, and **may** denote a requirement, prohibition, recommendation, and permitted choice. A necessary exception shall be narrow, documented beside the source or in the checked-in waiver registry, and justified by a tool or external-interface constraint.

## 2. General Construction

Identifiers shall use ASCII and shall be composed from complete semantic tokens. A signal or variable name follows this order where the corresponding parts exist:

```text
[group_or_channel_]subject[_role_or_kind][lifetime_or_polarity][direction]
```

The semantic stem shall describe what a value means. Its declaration shall describe width, signedness, representation, and aggregate type. Names shall not add representation markers such as `_vector`, `_struct`, `_enum`, or `_array`. The `_if` declaration-category suffix is the sole representation-like exception.

Preferred semantic kinds include:

- `op`, `operand`, `result`, and `value`;
- `address`, `read_data`, and `write_data`;
- `request`, `response`, and `enable`;
- `index`, `count`, `mask`, and `write_strobe`; and
- `candidate` and `pending`.

An identifier shall not end in an underscore followed by a number. Pipeline suffixes `_q2`, `_q3`, and later stages are the deliberate exception.

## 3. Construct Forms

| Construct | Required form |
| --- | --- |
| File, module, package, interface, class | `lower_snake_case` |
| Port, net, variable, field, function, task | `lower_snake_case` |
| Module instance | bare semantic `lower_snake_case` role |
| Tunable or derived parameter | typed `UpperCamelCase` |
| Package-scope constant parameter or true localparam constant | typed `ALL_CAPS` |
| Enum type | `lower_snake_case_e` |
| Struct, union, or other typedef | `lower_snake_case_t` |
| Enum member | role-prefixed `ALL_CAPS` |
| Global macro | grouped `ALL_CAPS` |
| File-local macro | `_ALL_CAPS`, followed by `undef` |
| Named generate block | `gen_lower_snake_case` |
| Other named block | `lower_snake_case` |
| Procedural or generate index | `i`, then `j`, then `k` by nesting depth |

One compilation unit should contain one primary declaration, and its filename shall match that declaration.

The `rv32_` prefix denotes membership in the implemented RV32 Core, not membership in this repository. RTL that constitutes the Core shall use the prefix; the current enforcement scope is `rtl/core/**/*.sv`. Supporting memories, adapters, platform RTL, and testbench modules are outside that mandatory prefix scope. Reusable non-Core RTL should omit `rv32_`; an RV32-specific wrapper or adapter outside `rtl/core/` may retain it when the token describes its actual ABI rather than satisfying a repository-wide rule.

`RVNAME001` enforces the filename prefix only inside the configured Core RTL roots. `RVNAME002` applies the matching module-name requirement only to modules declared in those roots. Neither rule shall use a global `.sv` check or a list of one-off filename exceptions.

Declaration-category suffixes are:

- `_pkg` for packages;
- `_if` for interfaces; and
- `_tb` for SystemVerilog test wrappers.

## 4. Logical and Boolean Names

A Boolean predicate shall read as a logical proposition. Use:

```text
<subject>_is_<state>
<subject>_has_<object>
<subject>_can_<verb>
```

Examples include:

```text
rd_is_zero_i
csr_write_is_legal_i
address_is_mapped
request_has_error
csr_can_commit
```

If the module provides exactly one possible subject, the subject may be omitted, but the logical marker remains: `is_legal_o`, not `legal_o`. Singular wording shall be preferred over introducing `are_`; for example, use `write_strobe_is_valid` for a predicate over a strobe value.

Requests, commands, events, and enables are controls rather than predicates. They use action or role forms such as `write_enable`, `commit`, `retire`, and `trap_accept`. They shall not acquire a misleading `is_` prefix. Names shall not use `_flag`.

Established protocol terms such as `req`, `valid`, `ready`, `we`, and `err` are exempt from predicate grammar when they are fields of, or direct mirrors of, that protocol.

## 5. Ports, Polarity, and Direction

An ordinary module port shall end in exactly one direction suffix:

- `_i` for an input;
- `_o` for an output; and
- `_io` for a physically or logically bidirectional signal.

Polarity precedes direction and joins it without another underscore:

```text
rst_ni
interrupt_ni
fault_no
gpio_io
```

The `_n` suffix is reserved for active-low polarity. It shall not mean “next.” Differential `_p` and `_n` markers follow the same ordering rule, with direction last.

Clock and reset names are:

- `clk_i` and `rst_ni` for the default domain;
- `clk_<domain>_i` and `rst_<domain>_ni` for additional domains.

Clock ports shall be declared first and reset ports second. Signals belonging to a non-default clock domain shall use the same domain token where the domain is not otherwise unambiguous.

An internal signal connected to a child port shall not retain the child port's direction suffix. For example:

```systemverilog
logic [31:0] alu_result;

rv32_alu alu (
  .result_o(alu_result)
);
```

## 6. Mixed-Direction SystemVerilog Interfaces

A modport-typed, mixed-direction interface port is the sole exception to ordinary port-direction suffixes. Its name shall end in `_if` and shall not end in `_i`, `_o`, or `_io`:

```systemverilog
rv32_mem_if.requester imem_if;
rv32_mem_if.responder dmem_if;
```

Interface declarations shall end in `_if`. Interface instances and interface ports shall use a channel or role stem followed by `_if`. Modports shall use role nouns such as `requester` and `responder`; the existing `respondend` spelling is invalid.

Fields inside an interface shall not carry module-direction suffixes because each modport defines field ownership. The established generic memory-interface field vocabulary remains:

```text
req we addr wdata wstrb ready rdata err
```

lowRISC discourages interfaces, but this project deliberately uses one to make request and response ownership explicit. Any Verible waiver needed for direction-free interface ports shall target only those declarations.

## 7. Module-Local Concision and Hierarchy

A module shall not repeat its own identity in a port when that token adds no disambiguation. For example, `rv32_alu` uses `op_i` rather than `alu_op_i`. A reusable child may expose a concise port while its parent uses a more specific internal name:

```systemverilog
rv32_alu alu (
  .op_i    (decoded_alu_op),
  .result_o(alu_result)
);
```

A group prefix becomes mandatory when it distinguishes sibling channels, owners, or otherwise identical concepts. Directly connected names should retain the same semantic noun even when a parent adds such a group prefix.

Named port and parameter connections shall be used. A rename shall update every declaration, connection, test handle, contract reference, and waveform-facing wrapper in the same change.

## 8. IMEM and DMEM Vocabulary

Instruction-memory and data-memory paths shall use `imem` and `dmem` at every level:

- `imem_*` denotes the instruction-memory path;
- `dmem_*` denotes the data-memory path.

The token `if` shall not abbreviate instruction fetch because `_if` denotes an interface. The generic prefix `data_*` shall not be used where the concept specifically belongs to DMEM. Examples of the intended vocabulary are:

```text
imem_request_i
imem_read_data_o
imem_trap_request_o
dmem_request_i
dmem_read_data_o
dmem_trap_request_o
imem_if
dmem_if
```

## 9. Types and Enum Members

Every enum shall be a named enum with an explicit four-state storage type and an `_e` suffix. Structs, unions, signal clusters, and other typedefs shall use `_t`.

Every enum member shall be `ALL_CAPS` and shall carry the shortest registered role prefix that distinguishes its namespace. Existing enum families use:

| Enum role | Member prefix |
| --- | --- |
| Instruction format | `INST_FORMAT_` |
| Memory operation width | `MEM_WIDTH_` |
| Load signedness | `LOAD_` |
| ALU operation | `ALU_` |
| LSU operation | `LSU_` |
| Control-transfer operation | `CONTROL_` |
| CSR operation/access/address/index | `CSR_`, refined where needed |
| Writeback source | `WB_` |
| PC source | `PC_` |
| Exception code | `EXC_` |
| Interrupt code | `INT_` |
| Module-local single FSM | `ST_` |

A module with more than one FSM shall add a machine role before `ST_` in both its type and member namespace. A new package-level enum family shall add its prefix to this table before use.

Counts and sentinels are constants, not enum members. For example, the number of implemented CSRs shall be a typed `CSR_COUNT` constant rather than `NUM_CSRS` inside an index enum.

## 10. Parameters, Constants, and Units

Externally tunable parameters and local values derived from them shall be typed `UpperCamelCase`. True immutable constants shall be typed `ALL_CAPS`.

Counts shall use `Count` or `_COUNT`; widths shall use `Width` or `_WIDTH`. Units shall be the final semantic token unless the value is unitless or measured in bits:

```text
ReadPortCount
WritePortCount
UnifiedRamSizeBytes
TimeoutCycles
CSR_COUNT
SYSTEM_CLOCK_HZ
```

The checker configuration shall permit both parameter styles only in their defined semantic classes. The mere fact that Verible accepts a spelling does not change the class of the object.

## 11. Registered State and Candidate Values

Scalar and packed registered state shall use:

- `_q` for the retained register output;
- `_d` for the combinational value that directly feeds that register; and
- `_q2`, `_q3`, and later suffixes for additional pipeline latency.

The `_d` suffix shall not label an arbitrary calculated alternative. A proposed but uncommitted transaction value uses `_candidate`; a retained future effect uses `pending_*`. The words `next` and `current` may describe algorithmic values only where they do not impersonate a scalar `_d`/`_q` pair.

Unpacked arrays and inferred memories are exempt from `_q` when there is one declared storage image. They shall use semantic storage names such as `register_cell` or `memory_cell`. If current and next array images coexist, they shall use `_current` and `_next` because the array exception deliberately reserves `_q` for scalar and packed state.

## 12. Collections and Bundles

Homogeneous, interchangeable lanes shall use unpacked arrays. Their identifier shall describe one element and their count shall come from a `*Count` parameter or `*_COUNT` constant:

```systemverilog
input  logic [11:0] read_address_i[ReadPortCount];
output logic [31:0] read_data_o[ReadPortCount];
```

Letters such as `a` and `b` may distinguish fixed roles only when exchanging the roles would change semantics, as with operands of a noncommutative operation. Numeric identifier suffixes shall not represent lanes.

Production RTL shall keep a coherent typed bundle intact when its fields share ownership and lifetime. A foreign-language or Cocotb-facing wrapper shall flatten aggregate and interface fields as:

```text
<bundle_or_channel>_<field>_<direction>
```

For a Boolean field, the field retains predicate grammar:

```text
imem_trap_request_is_valid_o
imem_trap_request_is_interrupt_o
imem_trap_request_code_o
imem_trap_request_tval_o
```

Direction appears exactly once, at the wrapper boundary.

## 13. Instances, Functions, Blocks, and Indices

Module instances shall use a bare semantic role without `u_` or `i_`:

```text
alu
register_file
csr_controller
ram
dut
```

Multiple instances shall use stable role or channel prefixes rather than numeric suffixes. Interface instances follow Section 6.

Function names shall describe the returned transformation. Predicate functions follow Section 4; constructors and selectors use verbs such as `build_`, `make_`, `decode_`, and `select_`. Function arguments shall be semantic lower-snake-case names without module-port suffixes. Synthesizable functions shall be automatic; synthesizable tasks remain disallowed by the governing style guide.

Generate blocks shall be named `gen_<role>`. Procedural and generate indices shall be `i`, then `j`, then `k` according to lexical nesting. Single-letter names are otherwise prohibited except where RISC-V itself defines the architectural token.

As a project extension, assertion labels should use descriptive `UpperCamelCase` names ending `_A`, such as `RequestStable_A`. Any later assumption or cover-label convention shall be added here before use.

## 14. Approved Abbreviations

Abbreviations are closed vocabulary. The following are approved because they are architectural, electrical, memory-system, or protocol terms:

```text
alu bram clk csr dmem gpr imem imm inst io irq isa lsu mem mmio
pc ram rd rom rs1 rs2 rst rv32 sync tval uimm wb
addr err op req rsp rdata wdata we wstrb
if pkg tb
```

RISC-V instruction mnemonics, CSR names, and specified encoding field names such as `funct3` and `funct7` are also approved.

Context restrictions apply:

- `rd` means the architectural destination-register field, never generic read;
- `rdata`, `wdata`, `we`, and `err` are protocol fields or direct mirrors;
- `if` is only the declaration suffix `_if`, never instruction fetch; and
- `i`, `j`, and `k` are loop indices, not general abbreviations.

The following legacy contractions are not approved: `wr`, `en`, `var`, `fmt`, `sem`, `reg`, `impl`, `dec`, `gen` as a component noun, and `_v`. Use `write`, `enable`, `value`, `format`, `semantics`, `register`, `implementation`, `decoder`, `generator`, and the exact semantic kind instead.

An additional abbreviation requires a contract amendment; local precedent alone does not authorize it.

## 15. Macros and Generated Names

A global macro shall be `ALL_CAPS` and shall use the project/group namespace followed by a double underscore when collision is possible, for example `RV32_CSR__ASSERT_LEGAL`. A file-local macro shall begin with one underscore and shall be undefined before leaving its intended scope.

Generated RTL and tool-created wrapper identifiers should comply when the generator controls their spelling. Names emitted solely by synthesis or simulation tools are outside this contract.

## 16. Compliance and Change Control

New or materially revised RTL shall conform immediately. Existing names are not grandfathered and shall be normalized under this contract. Compatibility aliases shall not preserve obsolete internal names; an external ABI that genuinely requires stability shall be represented by an explicit wrapper.

Compliance requires all of the following:

1. the ordinary Verible profile passes under checked-in rule configuration;
2. project naming checks pass for RTL and all testbench SystemVerilog;
3. every waiver is rule-specific, source-specific, justified, and non-stale;
4. module tests and compile/elaboration checks pass after a rename;
5. design contracts and roadmap examples contain no obsolete identifiers; and
6. manifests remain authoritative and current.

The contract shall be revised when a new interface class, identifier category, external ABI, or necessary abbreviation cannot be named deterministically by the existing rules. A one-off source exception shall not silently establish new convention.

## Metadata

- Document type: normative project philosophy and naming contract
- Naming authority: all manually controlled RTL and SystemVerilog wrapper identifiers
- Behavioral authority: RTL, tests, architecture, and module contracts
- Migration authority: this naming contract.
