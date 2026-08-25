# RV32I ALU Design Contract

**Scope:** Combinational RV32I integer arithmetic, logical, shift, and comparison execution

**Status:** Implemented; current module regression passes 15/15 tests

**Governing architecture:** [RV32I Core Architecture](../../Philosophy/RV32I_Core_Architecture.md)

**Core integration:** [RV32I Core Implementation](../../Roadmap/RV32I_Core_Implementation.md)

## 1. Boundary

`rv32_alu` shall consume two 32-bit operand values and one `rv32_inst_pkg::alu_op_t` operation. Operands are architectural values supplied by Core, not register indices.

The ALU shall be purely combinational. It shall own no architectural state, register-file access, destination selection, writeback authorization, PC update, or trap generation.

## 2. Operations

The implemented operations are:

| Operation | Result |
| --- | --- |
| `ALU_Add` | `a + b` modulo 2^32 |
| `ALU_Sub` | `a - b` modulo 2^32 |
| `ALU_And` | `a & b` |
| `ALU_Or` | `a \| b` |
| `ALU_Xor` | `a ^ b` |
| `ALU_Sll` | `a << b[4:0]` |
| `ALU_Srl` | logical `a >> b[4:0]` |
| `ALU_Sra` | signed `a >>> b[4:0]` |
| `ALU_Slt` | one iff signed `a < b`, otherwise zero |
| `ALU_Sltu` | one iff unsigned `a < b`, otherwise zero |

Shift distance shall use only the low five bits of operand B. Comparison results shall be zero-extended to 32 bits.

An unsupported operation may produce a benign zero result for defensive combinational completeness. The decoder and Core shall prevent that result from becoming architectural state; invalid instruction encodings are reported before ALU dispatch.

## 3. Core Integration

Core shall select register or immediate operand values according to decoded semantics and shall consume `result_o` only for a selected legal ALU-class instruction. Core retains the destination index and write intent and may commit the result only through the normal `COMMIT` path.

The ALU has no architecturally meaningful exception in the current RV32I scope and shall not receive a trap output solely for interface symmetry.

## 4. Verification

Verification shall cover every operation, signed and unsigned comparison boundaries, shift distances 0 and 31, and 32-bit arithmetic wraparound. The module regression is `testbench/cocotb/test-rv32_alu.py`.

## Metadata

- Document type: module contract
- RTL authority: `rtl/core/exec/rv32_alu.sv` and `rtl/core/type/rv32_inst_pkg.sv`
- Verification authority: `testbench/cocotb/test-rv32_alu.py` and later Core integration tests
