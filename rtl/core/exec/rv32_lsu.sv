// `include "../type/rv32_inst_pkg.sv"

`default_nettype none

module rv32_lsu (
    input logic        if_req_i,
    input logic [31:0] if_addr_i,

    output logic                            if_ready_o,
    output logic                     [31:0] if_rdata_o,
    output rv32_trap_pkg::trap_req_t        if_trap_o,

    input logic                          data_req_i,
    input rv32_inst_pkg::lsu_op_t        lsu_op_i,
    input logic                   [31:0] base_i,
    input logic                   [31:0] store_data_i,
    input logic                   [31:0] imm_i,

    output logic                            data_ready_o,
    output logic                     [31:0] load_result_o,
    output rv32_trap_pkg::trap_req_t        data_trap_o,

    rv32_mem_if.requester imem_if_i,
    rv32_mem_if.requester dmem_if_i
);
  assign imem_if_i.req = if_req_i;
  assign imem_if_i.we = 1'b0;
  assign imem_if_i.addr = if_addr_i;
  assign imem_if_i.wdata = 32'b0;
  assign imem_if_i.wstrb = 4'b0000;

  assign if_ready_o = imem_if_i.ready;
  assign if_rdata_o = imem_if_i.rdata;

  logic [31:0] data_addr;
  logic [31:0] data_wdata;
  logic [3:0] data_wstrb;

  logic [7:0] selected_byte;
  logic [15:0] selected_half;
  logic local_data_err;

  assign data_addr = base_i + imm_i;

  assign dmem_if_i.req = data_req_i && !local_data_err;
  assign dmem_if_i.we = lsu_op_i[3];
  assign dmem_if_i.addr = data_addr;
  assign dmem_if_i.wdata = data_wdata;
  assign dmem_if_i.wstrb = data_wstrb;

  assign data_ready_o = data_req_i && (local_data_err || dmem_if_i.ready);

  always_comb begin
    data_wdata = 32'b0;
    data_wstrb = 4'b0000;

    load_result_o = 32'b0;
    selected_byte = dmem_if_i.rdata >> (8 * data_addr[1:0]);
    selected_half = dmem_if_i.rdata >> (8 * data_addr[1:0]);

    if_trap_o = '0;
    data_trap_o = '0;
    local_data_err = 0;

    if (if_req_i && imem_if_i.ready && imem_if_i.err) begin
      if_trap_o = rv32_trap_pkg::exception(rv32_trap_pkg::EXC_INST_ACCESS_FAULT, if_addr_i);
    end

    if (data_req_i) begin
      if (lsu_op_i[3]) begin  // Store
        unique case (lsu_op_i)
          rv32_inst_pkg::LSU_Sb: begin
            data_wdata = {24'b0, store_data_i[7:0]} << (8 * (data_addr[1:0]));
            data_wstrb = 4'b0001 << (data_addr[1:0]);
          end
          rv32_inst_pkg::LSU_Sh: begin
            if (data_addr[0]) begin
              data_trap_o =
                  rv32_trap_pkg::exception(rv32_trap_pkg::EXC_STORE_ADDR_MISALIGNED, data_addr);
              local_data_err = 1'b1;
            end else begin
              data_wdata = {16'b0, store_data_i[15:0]} << (8 * (data_addr[1:0]));
              data_wstrb = 4'b0011 << (data_addr[1:0]);
            end
          end
          rv32_inst_pkg::LSU_Sw: begin
            if (data_addr[1:0] != 2'b00) begin
              data_trap_o =
                  rv32_trap_pkg::exception(rv32_trap_pkg::EXC_STORE_ADDR_MISALIGNED, data_addr);
              local_data_err = 1;
            end else begin
              data_wdata = store_data_i;
              data_wstrb = 4'b1111;
            end
          end
          default: begin
            local_data_err = 1;
            data_trap_o = rv32_trap_pkg::exception(rv32_trap_pkg::EXC_ILLEGAL_INST, 32'b0);
          end
        endcase

        if (data_req_i && dmem_if_i.ready && dmem_if_i.err) begin
          data_trap_o = rv32_trap_pkg::exception(rv32_trap_pkg::EXC_STORE_ACCESS_FAULT, data_addr);
        end
      end else begin  // Load
        unique case (lsu_op_i)
          rv32_inst_pkg::LSU_Lb:  load_result_o = {{24{selected_byte[7]}}, selected_byte};
          rv32_inst_pkg::LSU_Lbu: load_result_o = {24'b0, selected_byte};
          rv32_inst_pkg::LSU_Lh: begin
            if (data_addr[0]) begin
              data_trap_o =
                  rv32_trap_pkg::exception(rv32_trap_pkg::EXC_LOAD_ADDR_MISALIGNED, data_addr);
              local_data_err = 1;
            end else begin
              load_result_o = {{16{selected_half[15]}}, selected_half};
            end
          end
          rv32_inst_pkg::LSU_Lhu: begin
            if (data_addr[0]) begin
              data_trap_o =
                  rv32_trap_pkg::exception(rv32_trap_pkg::EXC_LOAD_ADDR_MISALIGNED, data_addr);
              local_data_err = 1;
            end else begin
              load_result_o = {16'b0, selected_half};
            end
          end
          rv32_inst_pkg::LSU_Lw: begin
            if (data_addr[1:0] != 2'b00) begin
              data_trap_o =
                  rv32_trap_pkg::exception(rv32_trap_pkg::EXC_LOAD_ADDR_MISALIGNED, data_addr);
              local_data_err = 1;
            end else begin
              load_result_o = dmem_if_i.rdata;
            end
          end
          default: begin
            local_data_err = 1;
            data_trap_o = rv32_trap_pkg::exception(rv32_trap_pkg::EXC_ILLEGAL_INST, 32'b0);
          end
        endcase

        if (data_req_i && dmem_if_i.ready && dmem_if_i.err) begin
          data_trap_o = rv32_trap_pkg::exception(rv32_trap_pkg::EXC_LOAD_ACCESS_FAULT, data_addr);
        end
      end
    end
  end

endmodule : rv32_lsu

`default_nettype wire
