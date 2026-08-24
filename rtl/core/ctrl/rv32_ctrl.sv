`default_nettype none

module rv32_ctrl (
    input rv32_inst_pkg::ctrl_op_t ctrl_op_i,
    input logic [31:0] pc_v_i,
    input logic [31:0] operand_a_i,
    input logic [31:0] operand_b_i,
    input logic [31:0] imm_i,
    output logic [31:0] pc_v_o,
    output logic [31:0] rd_v_o
);

  always_comb begin
    rd_v_o = '0;
    unique case (ctrl_op_i)
      rv32_inst_pkg::CTRL_Beq: pc_v_o = (operand_a_i == operand_b_i) ? pc_v_i + imm_i : pc_v_i + 4;
      rv32_inst_pkg::CTRL_Bne: pc_v_o = (operand_a_i != operand_b_i) ? pc_v_i + imm_i : pc_v_i + 4;
      rv32_inst_pkg::CTRL_Blt:
      pc_v_o = ($signed(operand_a_i) < $signed(operand_b_i)) ? pc_v_i + imm_i : pc_v_i + 4;
      rv32_inst_pkg::CTRL_Bge:
      pc_v_o = ($signed(operand_a_i) >= $signed(operand_b_i)) ? pc_v_i + imm_i : pc_v_i + 4;
      rv32_inst_pkg::CTRL_Bltu: pc_v_o = (operand_a_i < operand_b_i) ? pc_v_i + imm_i : pc_v_i + 4;
      rv32_inst_pkg::CTRL_Bgeu: pc_v_o = (operand_a_i >= operand_b_i) ? pc_v_i + imm_i : pc_v_i + 4;
      rv32_inst_pkg::CTRL_Jalr: begin
        pc_v_o = (operand_a_i + imm_i) & ~32'd1;
        rd_v_o = pc_v_i + 4;
      end
      rv32_inst_pkg::CTRL_Jal: begin
        pc_v_o = pc_v_i + imm_i;
        rd_v_o   = pc_v_i + 4;
      end
    endcase
  end

endmodule : rv32_ctrl

`default_nettype wire
