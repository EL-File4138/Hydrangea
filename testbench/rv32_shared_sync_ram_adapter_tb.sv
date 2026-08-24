`default_nettype none

module rv32_shared_sync_ram_adapter_tb (
    input logic clk_i,
    input logic rst_ni,

    input logic imem_req_i,
    input logic imem_we_i,
    input logic [31:0] imem_addr_i,
    input logic [31:0] imem_wdata_i,
    input logic [3:0] imem_wstrb_i,
    output logic imem_ready_o,
    output logic [31:0] imem_rdata_o,
    output logic imem_err_o,

    input logic dmem_req_i,
    input logic dmem_we_i,
    input logic [31:0] dmem_addr_i,
    input logic [31:0] dmem_wdata_i,
    input logic [3:0] dmem_wstrb_i,
    output logic dmem_ready_o,
    output logic [31:0] dmem_rdata_o,
    output logic dmem_err_o
);
  rv32_mem_if imem_if ();
  rv32_mem_if dmem_if ();

  assign imem_if.req = imem_req_i;
  assign imem_if.we = imem_we_i;
  assign imem_if.addr = imem_addr_i;
  assign imem_if.wdata = imem_wdata_i;
  assign imem_if.wstrb = imem_wstrb_i;
  assign imem_ready_o = imem_if.ready;
  assign imem_rdata_o = imem_if.rdata;
  assign imem_err_o = imem_if.err;

  assign dmem_if.req = dmem_req_i;
  assign dmem_if.we = dmem_we_i;
  assign dmem_if.addr = dmem_addr_i;
  assign dmem_if.wdata = dmem_wdata_i;
  assign dmem_if.wstrb = dmem_wstrb_i;
  assign dmem_ready_o = dmem_if.ready;
  assign dmem_rdata_o = dmem_if.rdata;
  assign dmem_err_o = dmem_if.err;

  rv32_shared_sync_ram_adapter u_dut (
      .clk_i(clk_i),
      .rst_ni(rst_ni),
      .imem_if_i(imem_if),
      .dmem_if_i(dmem_if)
  );

endmodule : rv32_shared_sync_ram_adapter_tb

`default_nettype wire
