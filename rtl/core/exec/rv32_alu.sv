`default_nettype none

module rv32_alu (
    input  logic                   [31:0] operand_a_i,
    input  logic                   [31:0] operand_b_i,
    input  rv32_inst_pkg::alu_op_e        opcode_i,
    output logic                   [31:0] result_o
);

  always_comb begin
    case (opcode_i)
      rv32_inst_pkg::ALU_ADD:  result_o = operand_a_i + operand_b_i;
      rv32_inst_pkg::ALU_SUB:  result_o = operand_a_i - operand_b_i;
      rv32_inst_pkg::ALU_AND:  result_o = operand_a_i & operand_b_i;
      rv32_inst_pkg::ALU_OR:   result_o = operand_a_i | operand_b_i;
      rv32_inst_pkg::ALU_XOR:  result_o = operand_a_i ^ operand_b_i;
      rv32_inst_pkg::ALU_SLL:  result_o = operand_a_i << operand_b_i[4:0];
      rv32_inst_pkg::ALU_SRL:  result_o = operand_a_i >> operand_b_i[4:0];
      rv32_inst_pkg::ALU_SRA:  result_o = $signed(operand_a_i) >>> operand_b_i[4:0];
      rv32_inst_pkg::ALU_SLT:  result_o = {31'b0, ($signed(operand_a_i) < $signed(operand_b_i))};
      rv32_inst_pkg::ALU_SLTU: result_o = {31'b0, (operand_a_i < operand_b_i)};
      default:                 result_o = 32'b0 + 32'b0;
    endcase
  end

endmodule : rv32_alu

`default_nettype wire
