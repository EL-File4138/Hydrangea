`default_nettype none

module rv32_control_transfer (
    input rv32_inst_pkg::control_op_e ctrl_op_i,
    input logic [31:0] pc_v_i,
    input logic [31:0] operand_a_i,
    input logic [31:0] operand_b_i,
    input logic [31:0] imm_i,
    output logic [31:0] pc_v_o,
    output logic [31:0] rd_v_o,
    output rv32_trap_pkg::trap_req_t trap_o
);
  logic [31:0] pc_v;

  always_comb begin
    pc_v   = '0;
    pc_v_o = '0;
    rd_v_o = '0;

    trap_o = '0;

    unique case (ctrl_op_i)
      rv32_inst_pkg::CONTROL_BEQ: pc_v = pc_v_i + ((operand_a_i == operand_b_i) ? imm_i : 4);
      rv32_inst_pkg::CONTROL_BNE: pc_v = pc_v_i + ((operand_a_i != operand_b_i) ? imm_i : 4);
      rv32_inst_pkg::CONTROL_BLT:
      pc_v = pc_v_i + (($signed(operand_a_i) < $signed(operand_b_i)) ? imm_i : 4);
      rv32_inst_pkg::CONTROL_BGE:
      pc_v = pc_v_i + (($signed(operand_a_i) >= $signed(operand_b_i)) ? imm_i : 4);
      rv32_inst_pkg::CONTROL_BLTU: pc_v = pc_v_i + ((operand_a_i < operand_b_i) ? imm_i : 4);
      rv32_inst_pkg::CONTROL_BGEU: pc_v = pc_v_i + ((operand_a_i >= operand_b_i) ? imm_i : 4);
      rv32_inst_pkg::CONTROL_JALR: begin
        pc_v   = (operand_a_i + imm_i) & ~32'd1;
        rd_v_o = pc_v_i + 4;
      end
      rv32_inst_pkg::CONTROL_JAL: begin
        pc_v   = pc_v_i + imm_i;
        rd_v_o = pc_v_i + 4;
      end
    endcase

    if (pc_v[1:0] != 2'b00) begin
      trap_o = rv32_trap_pkg::make_exception(rv32_trap_pkg::EXC_INST_ADDR_MISALIGNED, pc_v);
    end

    pc_v_o = pc_v;
  end

endmodule : rv32_control_transfer

`default_nettype wire
