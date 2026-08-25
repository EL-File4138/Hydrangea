`default_nettype none

module rv32_immgen(
    input logic [31:0] inst_i,
    input rv32_inst_pkg::inst_fmt_t inst_fmt_i,
    output logic [31:0] imm_o
);

always_comb begin
  case (inst_fmt_i)
    rv32_inst_pkg::I: imm_o = {{20{inst_i[31]}}, inst_i[31:20]};
    rv32_inst_pkg::S: imm_o = {{20{inst_i[31]}}, inst_i[31:25], inst_i[11:7]};
    rv32_inst_pkg::B: imm_o = {{20{inst_i[31]}}, inst_i[7], inst_i[30:25], inst_i[11:8], 1'b0};
    rv32_inst_pkg::U: imm_o = {inst_i[31:12], 12'b0};
    rv32_inst_pkg::J: imm_o = {{12{inst_i[31]}}, inst_i[19:12], inst_i[20], inst_i[30:21], 1'b0};
    default: imm_o = '0;
  endcase
end

endmodule : rv32_immgen

`default_nettype wire
