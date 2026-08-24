`default_nettype none

module sync_ram #(
  // No larger than 30 for a 32 bit address space (byte-addressed)
    parameter int unsigned AddrWidth = 8
) (
    input logic clk_i,
    input logic rst_ni,
    input logic write_enable_i,

    input logic [31:0] addr_i,

    input logic [31:0] write_data_i, // Always right aligned
    // LSU ensures type corretness and alignment with address
    input rv32_inst_pkg::mem_op_width_t write_type_i,

    output logic [31:0] read_data_o

);
  logic [AddrWidth-1:0] word_addr;
  logic [31:0] read_data_q;

  assign word_addr = addr_i[AddrWidth+1:2];
  assign read_data_o = read_data_q;

  logic [31:0] mem_cell[(2**AddrWidth)-1];

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      mem_cell <= '{default: '0};
    end else if (write_enable_i) begin
      unique case (write_type_i)
        rv32_inst_pkg::BYTE: mem_cell[word_addr][8*addr_i[1:0]+:8] <= write_data_i[7:0];
        rv32_inst_pkg::HALF: mem_cell[word_addr][16*addr_i[1:0]+:16] <= write_data_i[15:0];
        rv32_inst_pkg::WORD: mem_cell[word_addr] <= write_data_i;
      endcase
    end
    read_data_q <= mem_cell[{2'b0, addr_i[31:2]}];
  end

endmodule : sync_ram

`default_nettype wire
