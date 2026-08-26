`default_nettype none

// This module intentionally consumes only the immediate encoding fields.
/* verilator lint_off UNUSEDSIGNAL */
module rv32_imm_generator(
    input logic [31:0] inst_i,
    input rv32_inst_pkg::inst_format_e inst_fmt_i,
    output logic [31:0] imm_o
);

always_comb begin
  case (inst_fmt_i)
    rv32_inst_pkg::INST_FORMAT_I: imm_o = {{20{inst_i[31]}}, inst_i[31:20]};
    rv32_inst_pkg::INST_FORMAT_S: imm_o = {{20{inst_i[31]}}, inst_i[31:25], inst_i[11:7]};
    rv32_inst_pkg::INST_FORMAT_B: imm_o = {{20{inst_i[31]}}, inst_i[7], inst_i[30:25], inst_i[11:8], 1'b0};
    rv32_inst_pkg::INST_FORMAT_U: imm_o = {inst_i[31:12], 12'b0};
    rv32_inst_pkg::INST_FORMAT_J: imm_o = {{12{inst_i[31]}}, inst_i[19:12], inst_i[20], inst_i[30:21], 1'b0};
    default: imm_o = '0;
  endcase
end

endmodule : rv32_imm_generator

/* verilator lint_on UNUSEDSIGNAL */

`default_nettype wire
