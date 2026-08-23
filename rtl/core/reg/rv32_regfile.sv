`default_nettype none

module rv32_regfile (
    input logic clk_i,
    input logic write_enable_i,

    input logic [4:0] read_addr_a_i,
    input logic [4:0] read_addr_b_i,
    input logic [4:0] write_addr_i,

    input logic [31:0] write_data_i,

    output logic [31:0] read_data_a_o,
    output logic [31:0] read_data_b_o
);
  logic [31:0] reg_cell[32];

  always_ff @(posedge clk_i)
    begin
      if (write_enable_i)
        begin
          reg_cell[write_addr_i] <= write_data_i;
        end
    end

  assign read_data_a_o = (read_addr_a_i != '0) ? reg_cell[read_addr_a_i] : '0;
  assign read_data_b_o = (read_addr_b_i != '0) ? reg_cell[read_addr_b_i] : '0;

endmodule : rv32_regfile

`default_nettype wire
