`default_nettype none

module rv32_alu (
    input  logic                   [31:0] operand_a_i,
    input  logic                   [31:0] operand_b_i,
    input  rv32_inst_pkg::alu_op_t        opcode_i,
    output logic                   [31:0] result_o
);

  always_comb begin
    case (opcode_i)
      rv32_inst_pkg::ALU_Add:  result_o = operand_a_i + operand_b_i;
      rv32_inst_pkg::ALU_Sub:  result_o = operand_a_i - operand_b_i;
      rv32_inst_pkg::ALU_And:  result_o = operand_a_i & operand_b_i;
      rv32_inst_pkg::ALU_Or:   result_o = operand_a_i | operand_b_i;
      rv32_inst_pkg::ALU_Xor:  result_o = operand_a_i ^ operand_b_i;
      rv32_inst_pkg::ALU_Sll:  result_o = operand_a_i << operand_b_i[4:0];
      rv32_inst_pkg::ALU_Srl:  result_o = operand_a_i >> operand_b_i[4:0];
      rv32_inst_pkg::ALU_Sra:  result_o = $signed(operand_a_i) >>> operand_b_i[4:0];
      rv32_inst_pkg::ALU_Slt:  result_o = {31'b0, ($signed(operand_a_i) < $signed(operand_b_i))};
      rv32_inst_pkg::ALU_Sltu: result_o = {31'b0, (operand_a_i < operand_b_i)};
      default:                 result_o = 32'b0 + 32'b0;
    endcase
  end

endmodule : rv32_alu

`default_nettype wire
